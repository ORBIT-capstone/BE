import pytest

from app.schemas.retirement import ReadinessStatus, RecommendationType, ScenarioOutcome, ScenarioType
from app.services import retirement_service
from app.services.reduction_rules import get_reduction_rule
from app.services.retirement_service import (
    EARLY_REDUCTION_RATE_PER_YEAR,
    EARLY_YEARS_MAX,
    MAX_AGE,
    MAX_DEDUCTION_YEARS,
    MAX_REDUCTION_RATIO,
    MIN_PENSION_YEARS,
    SAVING_CAP_RATIO,
    TARGET_AGE_FEMALE,
    TARGET_AGE_MALE,
    _calculate_lump_sum_and_pension,
    _early_reduction_rate,
    _resolve_split_deduction_years,
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
        assert point.annual_gap == pytest.approx(point.annual_expense - point.annual_income)


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
    assert result.target_status == ReadinessStatus.SUFFICIENT
    assert 0 < result.required_saving <= monthly_expenses * SAVING_CAP_RATIO
    assert result.status == ReadinessStatus.SUFFICIENT

    # 개선안(절약 적용) 시뮬레이션이 실제로 자산 고갈 없이(SUFFICIENT) 유지되는지 검증
    improved = simulate_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses - result.required_saving,
        monthly_pension=200,
        asset=15_000,
        gender="male",
    )
    assert improved.status == ReadinessStatus.SUFFICIENT

    # required_saving이 최소값에 가까운지: 조금 덜 절약하면 여전히 SUFFICIENT에 못 미쳐야 함
    under_saving = simulate_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses - (result.required_saving - 1.0),
        monthly_pension=200,
        asset=15_000,
        gender="male",
    )
    assert under_saving.status != ReadinessStatus.SUFFICIENT


def test_recommend_retirement_middle_baseline_gets_meaningful_saving():
    # baseline이 이미 MIDDLE(고갈되지만 target_age 이후)이어도, 목표 기준은 SUFFICIENT(고갈 없음)이므로
    # required_saving이 0에 가까운 무의미한 값이 아니라 실제로 유의미해야 한다
    baseline = simulate_retirement(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=32_000,
        gender="male",
    )
    assert baseline.status == ReadinessStatus.MIDDLE

    result = recommend_retirement(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=32_000,
        gender="male",
    )

    assert result.recommendation_type == RecommendationType.SAVING_ONLY
    assert result.target_status == ReadinessStatus.SUFFICIENT
    assert result.status == ReadinessStatus.SUFFICIENT
    assert result.required_saving > 10.0  # 0.01만원 같은 무의미한 값이 아님


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
    assert result.target_status == ReadinessStatus.SUFFICIENT
    assert result.status == ReadinessStatus.SUFFICIENT

    improved = simulate_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses - result.required_saving,
        monthly_pension=100 + result.required_income,
        asset=5_000,
        gender="female",
    )
    assert improved.status == ReadinessStatus.SUFFICIENT

    # required_income이 최소값에 가까운지: 조금 덜 벌면 여전히 SUFFICIENT에 못 미쳐야 함
    under_income = simulate_retirement(
        current_age=60,
        monthly_expenses=monthly_expenses - result.required_saving,
        monthly_pension=100 + (result.required_income - 1.0),
        asset=5_000,
        gender="female",
    )
    assert under_income.status != ReadinessStatus.SUFFICIENT


def test_simulate_pension_reduction_no_reduction_at_exact_threshold():
    rule = get_reduction_rule(2025)

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
    rule = get_reduction_rule(2025)
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
        base_monthly_income=300,
        total_service_years=25,
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
        base_monthly_income=300,
        total_service_years=25,
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
        base_monthly_income=300,
        total_service_years=25,
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
        ScenarioOutcome(
            scenario_type=ScenarioType.NORMAL, depletion_age=80, depleted=True, total_received=1000.0,
            break_even_age=None, timeline=[],
        ),
        ScenarioOutcome(
            scenario_type=ScenarioType.EARLY, depletion_age=80, depleted=True, total_received=1500.0,
            break_even_age=None, timeline=[],
        ),
        ScenarioOutcome(
            scenario_type=ScenarioType.LUMP_SUM, depletion_age=75, depleted=True, total_received=9999.0,
            break_even_age=70, timeline=[],
        ),
    ]

    assert retirement_service._select_best_scenario(outcomes) == ScenarioType.EARLY


def test_simulate_scenarios_break_even_age_is_none_for_normal():
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
        base_monthly_income=300,
        total_service_years=25,
    )

    normal_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.NORMAL)
    assert normal_outcome.break_even_age is None


def test_simulate_scenarios_lump_sum_break_even_age_is_consistent_with_cumulative_totals():
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
        base_monthly_income=300,
        total_service_years=25,
    )

    normal_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.NORMAL)
    lump_sum_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.LUMP_SUM)

    assert lump_sum_outcome.break_even_age is not None

    # LUMP_SUM은 초기 자산이 더 크므로(업프론트 일시금), 그 차액을 업프론트 수령액으로 취급한다.
    upfront = lump_sum_outcome.timeline[0].asset - normal_outcome.timeline[0].asset

    # break_even_age 이전에는 LUMP_SUM 누적 수령액이 NORMAL보다 많아야 하고,
    # break_even_age 시점에는 NORMAL이 LUMP_SUM을 따라잡아야 한다.
    normal_running = 0.0
    lump_running = upfront
    for n_point, l_point in zip(normal_outcome.timeline, lump_sum_outcome.timeline):
        normal_running += n_point.annual_income
        lump_running += l_point.annual_income
        if n_point.age < lump_sum_outcome.break_even_age:
            assert normal_running < lump_running
        elif n_point.age == lump_sum_outcome.break_even_age:
            assert normal_running >= lump_running
            break


def test_simulate_scenarios_early_years_out_of_range_raises():
    with pytest.raises(ValueError):
        simulate_scenarios(
            current_age=60,
            monthly_expenses=250,
            monthly_pension=150,
            asset=10_000,
            gender="male",
            base_monthly_income=300,
            total_service_years=25,
            early_years=6,
        )

    with pytest.raises(ValueError):
        simulate_scenarios(
            current_age=60,
            monthly_expenses=250,
            monthly_pension=150,
            asset=10_000,
            gender="male",
            base_monthly_income=300,
            total_service_years=25,
            early_years=0,
        )


def test_simulate_scenarios_early_reduction_matches_per_year_rate():
    monthly_pension = 150
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=monthly_pension,
        asset=10_000,
        gender="male",
        base_monthly_income=300,
        total_service_years=25,
        early_years=2,
    )

    early_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.EARLY)
    expected_monthly_income = monthly_pension * (1 - EARLY_REDUCTION_RATE_PER_YEAR * 2) * 12
    assert early_outcome.timeline[0].annual_income == pytest.approx(expected_monthly_income)


def test_calculate_lump_sum_and_pension_matches_manual_example():
    # 수기 계산 예시: 기준소득월액 300만원, 공제 13년, 총재직연수 30년
    # 공제일시금 = 300 x 13 x (0.975 + 0.0065 x 13) = 300 x 13 x 1.0595 = 4132.05
    # 연금 선택 연수 = 30 - 13 = 17년 -> 월연금 = 300 x 17 x 0.017 = 86.7
    lump_sum, monthly_pension = _calculate_lump_sum_and_pension(
        base_monthly_income=300,
        total_service_years=30,
        deduction_years=13,
    )

    assert lump_sum == pytest.approx(4132.05)
    assert monthly_pension == pytest.approx(86.7)


def test_calculate_lump_sum_and_pension_full_deduction_matches_lump_sum_only():
    # 공제연수 == 총재직연수(전액 공제)이면 LUMP_SUM과 동일: 연금 선택 연수 0, 월연금 0
    lump_sum, monthly_pension = _calculate_lump_sum_and_pension(
        base_monthly_income=300,
        total_service_years=25,
        deduction_years=25,
    )

    assert monthly_pension == 0.0
    assert lump_sum == pytest.approx(300 * 25 * (0.975 + 0.0065 * 25))


def test_resolve_split_deduction_years_clamps_to_max_allowed_when_omitted():
    # total_service_years=25 -> max(25-10, ...) = 15, MAX_DEDUCTION_YEARS=26이므로 15로 클램프
    assert _resolve_split_deduction_years(total_service_years=25, deduction_years=None) == 15


def test_resolve_split_deduction_years_clamps_to_cap_when_service_years_large():
    # total_service_years=40 -> 40-10=30 > MAX_DEDUCTION_YEARS(26) -> 26으로 클램프
    assert _resolve_split_deduction_years(total_service_years=40, deduction_years=None) == MAX_DEDUCTION_YEARS


def test_resolve_split_deduction_years_raises_when_service_years_below_minimum():
    with pytest.raises(ValueError):
        _resolve_split_deduction_years(total_service_years=MIN_PENSION_YEARS - 1, deduction_years=None)


def test_resolve_split_deduction_years_raises_when_explicit_value_violates_pension_minimum():
    # total_service_years=25, deduction_years=20 -> 연금 선택 연수 5년 < MIN_PENSION_YEARS(10)
    with pytest.raises(ValueError):
        _resolve_split_deduction_years(total_service_years=25, deduction_years=20)


def test_resolve_split_deduction_years_raises_when_explicit_value_exceeds_max():
    with pytest.raises(ValueError):
        _resolve_split_deduction_years(total_service_years=40, deduction_years=MAX_DEDUCTION_YEARS + 1)


def test_simulate_scenarios_raises_400_when_total_service_years_below_pension_minimum():
    with pytest.raises(ValueError):
        simulate_scenarios(
            current_age=60,
            monthly_expenses=250,
            monthly_pension=150,
            asset=10_000,
            gender="male",
            base_monthly_income=300,
            total_service_years=5,
        )


def test_simulate_scenarios_raises_when_explicit_deduction_years_violates_constraints():
    with pytest.raises(ValueError):
        simulate_scenarios(
            current_age=60,
            monthly_expenses=250,
            monthly_pension=150,
            asset=10_000,
            gender="male",
            base_monthly_income=300,
            total_service_years=25,
            deduction_years=20,
        )


def test_simulate_scenarios_lump_sum_and_installment_use_unified_formula():
    total_service_years = 25
    base_monthly_income = 300
    deduction_years = 15

    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
        base_monthly_income=base_monthly_income,
        total_service_years=total_service_years,
        deduction_years=deduction_years,
    )

    expected_full_lump_sum, expected_full_pension = _calculate_lump_sum_and_pension(
        base_monthly_income, total_service_years, total_service_years
    )
    expected_split_lump_sum, expected_split_pension = _calculate_lump_sum_and_pension(
        base_monthly_income, total_service_years, deduction_years
    )

    lump_sum_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.LUMP_SUM)
    installment_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.INSTALLMENT)

    assert expected_full_pension == 0.0

    upfront_lump = lump_sum_outcome.timeline[0].asset - 10_000
    assert upfront_lump == pytest.approx(expected_full_lump_sum)
    assert lump_sum_outcome.timeline[0].annual_income == pytest.approx(expected_full_pension * 12)

    upfront_installment = installment_outcome.timeline[0].asset - 10_000
    assert upfront_installment == pytest.approx(expected_split_lump_sum)
    assert installment_outcome.timeline[0].annual_income == pytest.approx(expected_split_pension * 12)


# --- Step 2: 조기수령 감액 - 경계값 및 회귀 테스트 ---


@pytest.mark.parametrize("early_years", [0.0, EARLY_YEARS_MAX + 0.01, 6])
def test_early_reduction_rate_out_of_range_raises(early_years):
    with pytest.raises(ValueError):
        simulate_scenarios(
            current_age=60,
            monthly_expenses=250,
            monthly_pension=150,
            asset=10_000,
            gender="male",
            base_monthly_income=300,
            total_service_years=25,
            early_years=early_years,
        )


@pytest.mark.parametrize("early_years", [1, EARLY_YEARS_MAX])
def test_early_reduction_boundary_values_do_not_raise(early_years):
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
        base_monthly_income=300,
        total_service_years=25,
        early_years=early_years,
    )
    early_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.EARLY)
    expected_rate = EARLY_REDUCTION_RATE_PER_YEAR * early_years
    expected_annual_income = 150 * (1 - expected_rate) * 12
    assert early_outcome.timeline[0].annual_income == pytest.approx(expected_annual_income)


@pytest.mark.parametrize("early_years", [1, 2, 3, 4, 5])
def test_early_reduction_rate_matches_legacy_linear_formula_for_integer_input(early_years):
    """회귀 테스트: 정수 early_years에 대해 새 계단식(ceil) 공식이 이전 선형식과
    정확히 같은 결과를 내야 한다 — early_years는 정수일 때 ceil(early_years) ==
    early_years이므로 항상 성립해야 한다."""
    legacy_rate = EARLY_REDUCTION_RATE_PER_YEAR * early_years
    assert _early_reduction_rate(early_years) == pytest.approx(legacy_rate)


def test_early_reduction_rate_steps_up_for_fractional_years():
    # 1.5년 미달 -> "1년 초과 2년 이내" 계단(2년치 5%=10%)로 올림
    assert _early_reduction_rate(1.5) == pytest.approx(0.10)
    # 정확히 1.0년 -> "1년 이내" 계단(5%) 유지
    assert _early_reduction_rate(1.0) == pytest.approx(0.05)
    # 4.9년 미달 -> "4년 초과 5년 이내" 계단(최대 25%)
    assert _early_reduction_rate(4.9) == pytest.approx(0.25)


# --- Step 1(c): LUMP_SUM/SPLIT 재직연수 상한 (이전에는 무제한이었던 결함) ---


def test_calculate_lump_sum_and_pension_caps_service_years_at_36():
    # total_service_years=40(상한 36년 초과), deduction_years=0
    # -> pension_years는 min(40,36)-0 = 36 이어야 한다(40이 아니라).
    _lump_sum, monthly_pension = _calculate_lump_sum_and_pension(
        base_monthly_income=300,
        total_service_years=40,
        deduction_years=0,
    )
    from app.services.employees_service import PENSION_RATE

    assert monthly_pension == pytest.approx(300 * 36 * PENSION_RATE)


def test_calculate_lump_sum_and_pension_applies_cap_before_deduction_not_after():
    # 캡을 공제 전에 적용해야 한다: min(40,36)-10 = 26.
    # 만약 순서가 바뀌어 공제를 먼저 하면 (40-10)=30 -> min(30,36)=30 이 되어 다른 값이 나온다.
    _lump_sum, monthly_pension = _calculate_lump_sum_and_pension(
        base_monthly_income=300,
        total_service_years=40,
        deduction_years=10,
    )
    from app.services.employees_service import PENSION_RATE

    correct_order_years = 26  # min(40, 36) - 10
    wrong_order_years = 30  # (40 - 10), 이후 min(30,36)=30 (캡이 안 걸림)
    assert monthly_pension == pytest.approx(300 * correct_order_years * PENSION_RATE)
    assert monthly_pension != pytest.approx(300 * wrong_order_years * PENSION_RATE)


def test_calculate_lump_sum_and_pension_under_cap_unaffected():
    # 상한 이내(25년)에서는 기존 동작과 동일해야 한다 — 기존 골든 스냅샷/수기예시 테스트
    # (test_calculate_lump_sum_and_pension_matches_manual_example)와 정합.
    lump_sum, monthly_pension = _calculate_lump_sum_and_pension(
        base_monthly_income=300,
        total_service_years=30,
        deduction_years=13,
    )
    assert lump_sum == pytest.approx(4132.05)
    assert monthly_pension == pytest.approx(86.7)


# --- 회귀 수정: 전액공제(LUMP_SUM) + 총재직연수>36년일 때 음수 pension_years 방지 ---


def test_calculate_lump_sum_and_pension_full_deduction_over_cap_stays_zero():
    # total_service_years=40(>36), deduction_years=40(전액공제) -> 캡을 일시금·연금
    # 양쪽에 일관 적용해야 pension_years가 음수가 되지 않고 0을 유지해야 한다.
    # 수정 전에는 min(40,36)-40 = -4로 음수가 나왔다(회귀).
    _lump_sum, monthly_pension = _calculate_lump_sum_and_pension(
        base_monthly_income=300,
        total_service_years=40,
        deduction_years=40,
    )
    assert monthly_pension == pytest.approx(0.0)


def test_calculate_lump_sum_and_pension_full_deduction_over_cap_uses_capped_years_for_lump_sum():
    # 공제일시금도 퇴직급여이므로 부칙 제11조 상한(36년)이 적용돼야 한다 —
    # effective_deduction_years는 min(40,36)=36으로 캡된 값을 써야 한다.
    lump_sum, _monthly_pension = _calculate_lump_sum_and_pension(
        base_monthly_income=300,
        total_service_years=40,
        deduction_years=40,
    )
    from app.services.retirement_service import LUMP_SUM_CONVERSION_FACTOR, LUMP_SUM_SQUARE_FACTOR

    expected = 300 * 36 * (LUMP_SUM_CONVERSION_FACTOR + LUMP_SUM_SQUARE_FACTOR * 36)
    assert lump_sum == pytest.approx(expected)


def test_simulate_scenarios_lump_sum_over_cap_matches_unified_formula():
    # simulate_scenarios의 LUMP_SUM 시나리오(공제연수=총재직연수)가 total_service_years>36
    # 케이스에서도 _calculate_lump_sum_and_pension과 정확히 같은 값을 내는지 확인
    # (기존 test_simulate_scenarios_lump_sum_and_installment_use_unified_formula와 동일 성격).
    total_service_years = 40
    base_monthly_income = 300

    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10_000,
        gender="male",
        base_monthly_income=base_monthly_income,
        total_service_years=total_service_years,
        deduction_years=None,
    )

    expected_lump_sum, expected_pension = _calculate_lump_sum_and_pension(
        base_monthly_income, total_service_years, total_service_years
    )
    assert expected_pension == 0.0

    lump_sum_outcome = next(o for o in result.scenarios if o.scenario_type == ScenarioType.LUMP_SUM)
    upfront_lump = lump_sum_outcome.timeline[0].asset - 10_000
    assert upfront_lump == pytest.approx(expected_lump_sum)
    assert lump_sum_outcome.timeline[0].annual_income == pytest.approx(0.0)


@pytest.mark.parametrize(
    "total_service_years,deduction_years",
    [
        (30, 13),
        (25, 25),
        (25, 0),
        (36, 36),  # 상한과 정확히 같은 경계값 — 캡이 걸리지 않는 경계
    ],
)
def test_calculate_lump_sum_and_pension_under_or_at_cap_matches_uncapped_formula(
    total_service_years, deduction_years
):
    """회귀 방지: total_service_years <= 36(상한)인 기존 케이스들은 캡 적용 여부와
    무관하게 이전의 단순식(total_service_years - deduction_years)과 정확히 같아야 한다."""
    from app.services.employees_service import PENSION_RATE

    _lump_sum, monthly_pension = _calculate_lump_sum_and_pension(
        base_monthly_income=300,
        total_service_years=total_service_years,
        deduction_years=deduction_years,
    )
    expected_pension_years = total_service_years - deduction_years
    assert monthly_pension == pytest.approx(300 * expected_pension_years * PENSION_RATE)
