from engine_baseline import PENSION_RATE, predict_monthly_pension


def test_below_eligibility_returns_zero():
    assert predict_monthly_pension(3_000_000, 119) == 0


def test_at_eligibility_boundary_nonzero():
    result = predict_monthly_pension(3_000_000, 120)
    assert result == int(3_000_000 * 10 * PENSION_RATE)


def test_cap_applies_beyond_36_years():
    uncapped = predict_monthly_pension(3_000_000, 36 * 12)
    over_cap = predict_monthly_pension(3_000_000, 40 * 12)
    assert uncapped == over_cap


def test_matches_engine_formula_exactly():
    income, months = 4_123_000, 300
    expected = int(income * min(months / 12, 36) * PENSION_RATE)
    assert predict_monthly_pension(income, months) == expected
