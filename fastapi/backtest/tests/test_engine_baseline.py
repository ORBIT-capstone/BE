from app.services.pension_rate_model import calculate_monthly_pension_tranche
from engine_baseline import (
    LEGACY_PENSION_RATE,
    LEGACY_SERVICE_YEARS_CAP,
    predict_monthly_pension,
    predict_monthly_pension_legacy,
)


def test_legacy_below_eligibility_returns_zero():
    assert predict_monthly_pension_legacy(3_000_000, 119) == 0


def test_legacy_at_eligibility_boundary_nonzero():
    result = predict_monthly_pension_legacy(3_000_000, 120)
    assert result == int(3_000_000 * 10 * LEGACY_PENSION_RATE)


def test_legacy_cap_applies_beyond_36_years():
    uncapped = predict_monthly_pension_legacy(3_000_000, LEGACY_SERVICE_YEARS_CAP * 12)
    over_cap = predict_monthly_pension_legacy(3_000_000, 40 * 12)
    assert uncapped == over_cap


def test_legacy_matches_frozen_formula_exactly():
    income, months = 4_123_000, 300
    expected = int(income * min(months / 12, LEGACY_SERVICE_YEARS_CAP) * LEGACY_PENSION_RATE)
    assert predict_monthly_pension_legacy(income, months) == expected


# --- 프로덕션 tranche+α 모형(predict_monthly_pension) ---


def test_below_eligibility_returns_zero():
    assert predict_monthly_pension(3_000_000, 119, retire_yyyymm=202601) == 0


def test_matches_production_calculate_monthly_pension_exactly():
    # 이 함수는 프로덕션 calculate_monthly_pension을 그대로 호출한다 — 재타이핑 없이
    # 위임하는지만 확인한다(요율표 자체는 tests/test_pension_rate_model.py가 검증한다).
    income, months, retire_yyyymm = 4_123_000, 300, 203001
    expected = calculate_monthly_pension_tranche(income, retire_yyyymm, min(months, 432))
    assert predict_monthly_pension(income, months, retire_yyyymm=retire_yyyymm) == expected
