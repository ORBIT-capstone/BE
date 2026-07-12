import pytest

from app.schemas.retirement import ReadinessStatus
from app.services import retirement_service
from app.services.retirement_service import (
    MAX_AGE,
    TARGET_AGE_FEMALE,
    TARGET_AGE_MALE,
    calculate_status,
    get_target_age,
    simulate_retirement,
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
