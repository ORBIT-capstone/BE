import pytest

from app.schemas.employees import CapBasis, SimulateRequest
from app.services.employees_service import (
    PENSION_ELIGIBILITY_MONTHS,
    PENSION_RATE,
    SEVERANCE_YEARS_CAP,
    _severance_rate,
    calculate_monthly_pension,
    simulate_employees,
)
from app.services.service_cap_rules import (
    DEFAULT_MAX_CAP_MONTHS,
    resolve_pension_service_cap_months,
)


# --- service_cap_rules.resolve_pension_service_cap_months ---


def test_resolve_cap_none_input_defaults_to_36_years():
    cap_months, cap_basis = resolve_pension_service_cap_months(None)
    assert cap_months == 432
    assert cap_basis == "DEFAULT_MAX"
    assert cap_months == DEFAULT_MAX_CAP_MONTHS


def test_resolve_cap_zero_is_statutory_default_not_tiered():
    # 2016.1.1 이후 임용자(경과조치 비대상) -> 본칙 36년. 값은 4호와 같지만 근거가 다르다.
    cap_months, cap_basis = resolve_pension_service_cap_months(0)
    assert cap_months == 432
    assert cap_basis == "STATUTORY_DEFAULT"


def test_resolve_cap_negative_raises():
    with pytest.raises(ValueError):
        resolve_pension_service_cap_months(-1)


@pytest.mark.parametrize(
    "service_months_as_of_2016,expected_cap_months",
    [
        (1, 432),  # 15년 미만(최소값 근처) -> 36년
        (179, 432),  # 14년 11개월 -> 36년
        (180, 420),  # 정확히 15년 -> 35년 (경계: 15년 이상)
        (181, 420),  # 15년 초과 -> 35년
        (203, 420),  # 16년 11개월 -> 35년
        (204, 408),  # 정확히 17년 -> 34년 (경계: 17년 이상)
        (205, 408),  # 17년 초과 -> 34년
        (251, 408),  # 20년 11개월 -> 34년
        (252, 396),  # 정확히 21년 -> 33년 (경계: 21년 이상)
        (253, 396),  # 21년 초과 -> 33년
        (600, 396),  # 장기재직자(50년) -> 33년 상한 유지
    ],
)
def test_resolve_cap_tiered_boundaries(service_months_as_of_2016, expected_cap_months):
    cap_months, cap_basis = resolve_pension_service_cap_months(service_months_as_of_2016)
    assert cap_months == expected_cap_months
    assert cap_basis == "STATUTORY_TIERED"


# --- employees_service.calculate_monthly_pension (순수 함수) ---


def test_calculate_monthly_pension_below_eligibility_not_this_functions_concern():
    # calculate_monthly_pension 자체는 최소가입월수 분기를 모른다(simulate_employees가 처리) —
    # 캡만 적용해 그대로 계산한다는 걸 확인.
    result = calculate_monthly_pension(base_income=3_000_000, retire_months=1, cap_months=432)
    assert result == int(3_000_000 * (1 / 12) * PENSION_RATE)


def test_calculate_monthly_pension_cap_applies_exactly_at_boundary():
    income = 3_000_000
    at_cap = calculate_monthly_pension(income, retire_months=396, cap_months=396)
    over_cap = calculate_monthly_pension(income, retire_months=500, cap_months=396)
    assert at_cap == over_cap == int(income * 33 * PENSION_RATE)


def test_calculate_monthly_pension_under_cap_uses_actual_months():
    income = 3_000_000
    result = calculate_monthly_pension(income, retire_months=240, cap_months=432)
    assert result == int(income * 20 * PENSION_RATE)


# --- employees_service.simulate_employees (통합) ---


def _build_request(service_months_as_of_2016: int | None, service_years: int) -> SimulateRequest:
    return SimulateRequest(
        current_years=service_years,
        current_income=5_000_000,
        current_age=30,
        retire_at_age=30 + service_years,
        service_months_as_of_2016=service_months_as_of_2016,
    )


def test_simulate_employees_omits_field_keeps_default_36_year_cap():
    # service_months_as_of_2016 미제공 -> 기존 동작(36년 고정) 유지
    req = _build_request(service_months_as_of_2016=None, service_years=40)
    res = simulate_employees(req)
    assert res.cap_basis == CapBasis.DEFAULT_MAX
    assert res.service_cap_years == 36


def test_simulate_employees_statutory_tiered_reduces_pension_vs_default():
    # 2016.1.1 시점 21년 이상 재직 -> 33년 상한 -> DEFAULT_MAX(36년)보다 연금액이 작거나 같다
    req_default = _build_request(service_months_as_of_2016=None, service_years=40)
    req_tiered = _build_request(service_months_as_of_2016=252, service_years=40)

    res_default = simulate_employees(req_default)
    res_tiered = simulate_employees(req_tiered)

    assert res_tiered.cap_basis == CapBasis.STATUTORY_TIERED
    assert res_tiered.service_cap_years == 33
    assert res_tiered.monthly_pension < res_default.monthly_pension


def test_simulate_employees_severance_cap_independent_of_pension_cap():
    # 퇴직수당 상한(33년)은 연금 상한 테이블과 무관하게 항상 33년으로 고정돼야 한다 —
    # service_months_as_of_2016을 바꿔도(연금 상한이 34/35/36년으로 바뀌어도) 영향 없음.
    req_tiered_34 = _build_request(service_months_as_of_2016=204, service_years=40)  # 연금상한 34년
    req_default_36 = _build_request(service_months_as_of_2016=None, service_years=40)  # 연금상한 36년

    res_34 = simulate_employees(req_tiered_34)
    res_36 = simulate_employees(req_default_36)

    assert res_34.cap_basis == CapBasis.STATUTORY_TIERED
    assert res_34.service_cap_years == 34
    assert res_36.cap_basis == CapBasis.DEFAULT_MAX
    # 두 케이스의 재직연수(40년)가 SEVERANCE_YEARS_CAP(33)을 넘으므로 퇴직수당은
    # 둘 다 동일하게 33년 기준으로 계산돼야 한다(연금 상한과 무관).
    assert SEVERANCE_YEARS_CAP == 33
    expected_severance = int(
        5_000_000 * SEVERANCE_YEARS_CAP * _severance_rate(SEVERANCE_YEARS_CAP)
    )
    assert res_34.severance_pay == res_36.severance_pay == expected_severance


def test_simulate_employees_below_pension_eligibility_still_reports_cap_fields():
    # 최소가입월수(120개월) 미달(retire_months=108<120)이라 monthly_pension=0이어도
    # cap 필드는 항상 채워진다.
    req = SimulateRequest(
        current_years=5,
        current_income=5_000_000,
        current_age=30,
        retire_at_age=34,  # retire_after_months=48 -> retire_months=60+48=108 < 120
        service_months_as_of_2016=180,
    )
    res = simulate_employees(req)
    assert res.retire_months == 108
    assert res.monthly_pension == 0
    assert res.cap_basis == CapBasis.STATUTORY_TIERED
    assert res.service_cap_years == 35


def test_pension_eligibility_months_constant_matches_ten_years():
    assert PENSION_ELIGIBILITY_MONTHS == 120
