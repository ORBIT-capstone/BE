import pytest

from app.services.reduction_rules import (
    REDUCTION_RULES,
    RateBracket,
    ReductionRule,
    calculate_bracket_reduction,
    get_reduction_rule,
)


def test_get_reduction_rule_returns_latest_when_year_is_none():
    latest = max(REDUCTION_RULES, key=lambda rule: rule.year)
    assert get_reduction_rule(None) == latest


def test_get_reduction_rule_returns_exact_year_match():
    target = REDUCTION_RULES[0]
    assert get_reduction_rule(target.year) == target


def test_get_reduction_rule_falls_back_to_earliest_when_year_before_all_rules():
    earliest = min(REDUCTION_RULES, key=lambda rule: rule.year)
    assert get_reduction_rule(earliest.year - 100) == earliest


def test_get_reduction_rule_picks_nearest_earlier_year_for_future_year():
    latest = max(REDUCTION_RULES, key=lambda rule: rule.year)
    assert get_reduction_rule(latest.year + 100) == latest


@pytest.fixture
def rate_brackets() -> list[RateBracket]:
    return [
        RateBracket(upper_bound=100, base_amount=0, rate=0.05),
        RateBracket(upper_bound=200, base_amount=5, rate=0.10),
        RateBracket(upper_bound=None, base_amount=15, rate=0.15),
    ]


def test_calculate_bracket_reduction_zero_when_no_excess_income(rate_brackets):
    assert calculate_bracket_reduction(0, rate_brackets) == 0.0


def test_calculate_bracket_reduction_zero_when_negative_excess_income(rate_brackets):
    assert calculate_bracket_reduction(-50, rate_brackets) == 0.0


def test_calculate_bracket_reduction_within_first_bracket(rate_brackets):
    assert calculate_bracket_reduction(50, rate_brackets) == pytest.approx(50 * 0.05)


def test_calculate_bracket_reduction_at_bracket_boundary_is_continuous(rate_brackets):
    # 100만원 구간 경계에서 첫 구간 산식과 정확히 일치해야 한다 (불연속 없음)
    assert calculate_bracket_reduction(100, rate_brackets) == pytest.approx(5.0)


def test_calculate_bracket_reduction_beyond_last_bound(rate_brackets):
    # 200 초과분은 마지막(무제한) 구간 산식 적용: base(15) + (300-200)*0.15
    assert calculate_bracket_reduction(300, rate_brackets) == pytest.approx(15 + 100 * 0.15)


def test_get_reduction_rule_raises_when_no_rules_registered(monkeypatch):
    import app.services.reduction_rules as reduction_rules_module

    monkeypatch.setattr(reduction_rules_module, "REDUCTION_RULES", [])
    with pytest.raises(ValueError):
        get_reduction_rule(2024)
