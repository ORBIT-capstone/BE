import pytest

from app.schemas.retirement import ReadinessStatus, RecommendationType, ScenarioOutcome, ScenarioType
from app.services import retirement_service
from app.services.reduction_rules import get_reduction_rule
from app.services.retirement_service import (
    MAX_AGE,
    MAX_REDUCTION_RATIO,
    SAVING_CAP_RATIO,
    TARGET_AGE_FEMALE,
    TARGET_AGE_MALE,
    calculate_status,
    get_target_age,
    recommend_retirement,
    simulate_pension_reduction,
    simulate_retirement,
    simulate_scenarios,
)


def test_get_target_age_male():
    assert get_target_age("male") == TARGET_AGE_MALE


def test_get_target_age_female():
    assert get_target_age("female") == TARGET_AGE_FEMALE


def test_calculate_status_sufficient_when_never_depletes():
    assert calculate_status(None, TARGET_AGE_MALE) == ReadinessStatus.SUFFICIENT


def test_calculate_status_middle_when_depletes_after_target_age():
    assert calculate_status(TARGET_AGE_MALE, TARGET_AGE_MALE) == ReadinessStatus.MIDDLE


def test_calculate_status_insufficient_when_depletes_before_target_age():
    assert calculate_status(TARGET_AGE_MALE - 1, TARGET_AGE_MALE) == ReadinessStatus.INSUFFICIENT


def test_simulate_retirement_gap_non_positive_never_depletes():
    result = simulate_retirement(
        current_age=65,
        monthly_expenses=150,
        monthly_pension=200,
        asset=10_000,
        gender="male",
    )

    assert result.monthly_gap == -50
    assert result.depletion_age is None
    assert result.status == ReadinessStatus.SUFFICIENT


def test_simulate_retirement_reaches_max_age_without_depletion():
    result = simulate_retirement(
        current_age=60,
        monthly_expenses=200,
        monthly_pension=100,
        asset=1_000_000_000,
        gender="female",
    )

    assert result.depletion_age is None
    assert result.status == ReadinessStatus.SUFFICIENT
    assert result.timeline[0].age == 60
    assert result.timeline[-1].age == MAX_AGE
    assert len(result.timeline) == MAX_AGE - 60 + 1


@pytest.mark.parametrize("monthly_expenses", [0, -100])
def test_simulate_retirement_raises_for_non_positive_monthly_expenses(monthly_expenses):
    with pytest.raises(ValueError):
        simulate_retirement(
            current_age=60,
            monthly_expenses=monthly_expenses,
            monthly_pension=100,
            asset=10_000,
            gender="male",
        )


def test_simulate_retirement_gap_matches_expense_minus_income_when_pension_grows(monkeypatch):
    monkeypatch.setattr(retirement_service, "PENSION_GROWTH_RATE", 0.05)

    result = retirement_service.simulate_retirement(
        current_age=60,
        monthly_expenses=200,
        monthly_pension=100,
        asset=100_000,
        gender="male",
    )

    for point in result.timeline:
        assert point.gap == pytest.approx(point.expense - point.income)


def test_simulate_retirement_depletion_age_capped_at_max_age():
    # 자산이 asset(현재=99세)에서 1년은 버티지만 age=100(마지막 루프)에서 고갈되어,
    # 캡이 없다면 depletion_age가 101로 계산될 조건
    result = simulate_retirement(
        current_age=99,
        monthly_expenses=1_000,
        monthly_pension=0,
        asset=18_000,
        gender="male",
    )

    assert result.depletion_age == MAX_AGE


def test_recommend_retirement_sufficient_when_baseline_already_sufficient():
    result = recommend_retirement(
        current_age=65,
        monthly_expenses=150,
        monthly_pension=200,
        asset=10_000,
        gender="male",
    )

    assert result.recommendation_type == RecommendationType.SUFFICIENT
    assert result.required_saving == 0.0
    assert result.required_income == 0.0
    assert result.status == ReadinessStatus.SUFFICIENT


def test_recommend_retirement_saving_only_within_cap():
    monthly_expenses = 250
    result = recommend_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses,
        monthly_pension=200,
        asset=15_000,
        gender="male",
    )

    assert result.recommendation_type == RecommendationType.SAVING_ONLY
    assert result.required_income == 0.0
    assert 0 < result.required_saving <= monthly_expenses * SAVING_CAP_RATIO
    assert result.status != ReadinessStatus.INSUFFICIENT

    # 개선안(절약 적용) 시뮬레이션이 실제로 목표연령 이상까지 자산을 유지시키는지 검증
    improved = simulate_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses - result.required_saving,
        monthly_pension=200,
        asset=15_000,
        gender="male",
    )
    assert improved.status != ReadinessStatus.INSUFFICIENT

    # required_saving이 최소값에 가까운지: 조금 덜 절약하면 여전히 부족해야 함
    under_saving = simulate_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses - (result.required_saving - 1.0),
        monthly_pension=200,
        asset=15_000,
        gender="male",
    )
    assert under_saving.status == ReadinessStatus.INSUFFICIENT


def test_recommend_retirement_saving_and_income_when_cap_alone_insufficient():
    monthly_expenses = 400
    result = recommend_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses,
        monthly_pension=100,
        asset=5_000,
        gender="female",
    )

    assert result.recommendation_type == RecommendationType.SAVING_AND_INCOME
    assert result.required_saving == pytest.approx(monthly_expenses * SAVING_CAP_RATIO)
    assert result.required_income > 0
    assert result.status != ReadinessStatus.INSUFFICIENT

    improved = simulate_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses - result.required_saving,
        monthly_pension=100 + result.required_income,
        asset=5_000,
        gender="female",
    )
    assert improved.status != ReadinessStatus.INSUFFICIENT

    # required_income이 최소값에 가까운지: 조금 덜 벌면 여전히 부족해야 함
    under_income = simulate_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses - result.required_saving,
        monthly_pension=100 + (result.required_income - 1.0),
        asset=5_000,
        gender="female",
    )
    assert under_income.status == ReadinessStatus.INSUFFICIENT


def test_simulate_pension_reduction_no_reduction_at_exact_threshold():
    rule = get_reduction_rule(None)

    result = simulate_pension_reduction(
        current_age=60,
        monthly_expenses=200,
        monthly_pension=150,
        asset=10_000,
        gender="male",
        reemployment_income=rule.threshold,
    )

    baseline = simulate_retirement(
        current_age=60,
        monthly_expenses=200,
        monthly_pension=150,
        asset=10_000,
        gender="male",
    )

    assert result.monthly_reduction == 0.0
    assert result.reduced_monthly_pension == 150
    assert result.full_payment_income_threshold == rule.threshold
    assert result.depletion_age == baseline.depletion_age
    assert result.status == baseline.status
    assert result.timeline == baseline.timeline


def test_simulate_pension_reduction_no_reduction_when_income_is_zero():
    result = simulate_pension_reduction(
        current_age=60,
        monthly_expenses=200,
        monthly_pension=150,
        asset=10_000,
        gender="male",
        reemployment_income=0,
    )

    assert result.monthly_reduction == 0.0
    assert result.reduced_monthly_pension == 150


def test_simulate_pension_reduction_capped_when_income_far_exceeds_threshold():
    rule = get_reduction_rule(None)
    monthly_pension = 150

    result = simulate_pension_reduction(
        current_age=60,
        monthly_expenses=200,
        monthly_pension=monthly_pension,
        asset=10_000,
        gender="male",
        reemployment_income=rule.threshold + 2_000,
    )

    max_reduction = monthly_pension * MAX_REDUCTION_RATIO
    assert result.monthly_reduction == pytest.approx(max_reduction)
    assert result.reduced_monthly_pension == pytest.approx(monthly_pension - max_reduction)

    improved = simulate_retirement(
        current_age=60,
        monthly_expenses=200,
        monthly_pension=monthly_pension - max_reduction,
        asset=10_000,
        gender="male",
    )
    assert result.depletion_age == improved.depletion_age
    assert result.status == improved.status


def test_simulate_pension_reduction_raises_for_negative_income():
    with pytest.raises(ValueError):
        simulate_pension_reduction(
            current_age=60,
            monthly_expenses=200,
            monthly_pension=150,
            asset=10_000,
            gender="male",
            reemployment_income=-1,
        )


def test_simulate_scenarios_produces_distinct_results_per_scenario():
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
    )

    assert {outcome.scenario_type for outcome in result.scenarios} == {
        ScenarioType.NORMAL,
        ScenarioType.EARLY,
        ScenarioType.LUMP_SUM,
        ScenarioType.INSTALLMENT,
    }

    depletion_ages = {outcome.scenario_type: outcome.depletion_age for outcome in result.scenarios}
    total_received = {outcome.scenario_type: outcome.total_received for outcome in result.scenarios}

    # 4가지 방식은 서로 다른 monthly_pension/asset 조합을 사용하므로 결과가 달라야 한다
    assert len(set(depletion_ages.values())) > 1
    assert len(set(total_received.values())) == len(total_received)

    # 조기수령은 정상수령보다 월 수령액이 적으므로 총 수령액도 더 적어야 한다
    assert total_received[ScenarioType.EARLY] < total_received[ScenarioType.NORMAL]


def test_simulate_scenarios_selects_scenario_with_max_depletion_age_as_best():
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
    )

    best_outcome = max(result.scenarios, key=lambda outcome: (outcome.depletion_age, outcome.total_received))
    assert result.best_scenario == best_outcome.scenario_type


def test_simulate_scenarios_timeline_matches_diagnosis_core_format():
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
    )

    baseline = simulate_retirement(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
    )

    normal_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.NORMAL)
    assert normal_outcome.timeline == baseline.timeline
    assert normal_outcome.depletion_age == baseline.depletion_age


def test_select_best_scenario_breaks_tie_by_total_received():
    outcomes = [
        ScenarioOutcome(scenario_type=ScenarioType.NORMAL, depletion_age=80, total_received=1000.0, timeline=[]),
        ScenarioOutcome(scenario_type=ScenarioType.EARLY, depletion_age=80, total_received=1500.0, timeline=[]),
        ScenarioOutcome(scenario_type=ScenarioType.LUMP_SUM, depletion_age=75, total_received=9999.0, timeline=[]),
    ]

    assert retirement_service._select_best_scenario(outcomes) == ScenarioType.EARLY
