"""고갈(depletion) 표현 통일에 대한 회귀 테스트.

- timeline의 asset은 고갈 이후 음수로 계속 내려가지 않고 0으로 클램프되어야 한다.
- ScenarioOutcome.depletion_age는 diagnosis 등 다른 응답과 마찬가지로
  무고갈이면 None이어야 한다(더 이상 MAX_AGE(100)를 "무고갈" sentinel로 쓰지 않는다).
- depleted: bool 필드가 depletion_age is not None과 항상 일치해야 한다.
- _select_best_scenario가 depletion_age=None(무고갈) 시나리오를 다른 유한 시나리오보다
  우선해야 한다(무고갈이 가장 좋은 결과라는 기존 의도는 유지).
"""

import pytest

from app.schemas.retirement import ScenarioOutcome, ScenarioType
from app.services import retirement_service
from app.services.retirement_service import MAX_AGE, simulate_retirement, simulate_scenarios


def test_timeline_asset_clamped_to_zero_after_depletion():
    result = simulate_retirement(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10000,
        gender="male",
    )

    assert result.depletion_age is not None
    for point in result.timeline:
        if point.age >= result.depletion_age:
            assert point.asset == 0.0
        else:
            assert point.asset > 0.0


def test_simulation_result_depleted_flag_matches_depletion_age():
    depleting = simulate_retirement(
        current_age=60, monthly_expenses=250, monthly_pension=150, asset=10000, gender="male"
    )
    assert depleting.depletion_age is not None
    assert depleting.depleted is True

    sufficient = simulate_retirement(
        current_age=65, monthly_expenses=150, monthly_pension=200, asset=10000, gender="male"
    )
    assert sufficient.depletion_age is None
    assert sufficient.depleted is False


def test_scenario_outcome_depletion_age_is_none_when_never_depletes():
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=100,
        monthly_pension=200,
        asset=1_000_000,
        gender="male",
        base_monthly_income=300,
        total_service_years=25,
    )

    for outcome in result.scenarios:
        assert outcome.depletion_age is None, f"{outcome.scenario_type}는 무고갈이어야 하는데 {outcome.depletion_age}"
        assert outcome.depleted is False


def test_scenario_outcome_depleted_true_when_depletes_before_max_age():
    result = simulate_scenarios(
        current_age=60,
        monthly_expenses=250,
        monthly_pension=150,
        asset=10000,
        gender="male",
        base_monthly_income=300,
        total_service_years=25,
    )

    for outcome in result.scenarios:
        assert outcome.depletion_age is not None
        assert outcome.depletion_age < MAX_AGE
        assert outcome.depleted is True


def test_select_best_scenario_prefers_never_depleting_scenario_over_finite_ones():
    outcomes = [
        ScenarioOutcome(
            scenario_type=ScenarioType.NORMAL, depletion_age=80, depleted=True,
            total_received=1000.0, break_even_age=None, timeline=[],
        ),
        ScenarioOutcome(
            scenario_type=ScenarioType.EARLY, depletion_age=None, depleted=False,
            total_received=500.0, break_even_age=60, timeline=[],
        ),
        ScenarioOutcome(
            scenario_type=ScenarioType.LUMP_SUM, depletion_age=75, depleted=True,
            total_received=9999.0, break_even_age=70, timeline=[],
        ),
    ]

    assert retirement_service._select_best_scenario(outcomes) == ScenarioType.EARLY
