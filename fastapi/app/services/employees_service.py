from app.repositories.employees_income_repository import get_band_mean
from app.schemas.employees import SimulateRequest, SimulateResponse
from app.services.service_cap_rules import resolve_pension_service_cap_months

LUMP_SUM_CONVERSION_FACTOR = 975 / 1000  # 일시금 환산 계수
PENSION_RATE = 0.017  # 재직연수 1년당 연금 지급률
PENSION_ELIGIBILITY_MONTHS = 120  # 연금 수급 최소 재직월수 (10년)

# 퇴직수당 재직연수 상한 — 33년 고정.
# 근거: 이 상한은 연금 산정용이 아니라 퇴직수당 산정에만 적용되는 별개 규정이다.
# service_cap_rules.py의 재직기간 상한 테이블(사학연금법 부칙 제11조, "퇴직급여
# 산정 시" 재직기간에만 적용)과는 무관하며, 그 테이블을 참조하거나 두 상수를
# 하나로 통합하지 말 것 — 값이 우연히 33과 겹치는 경우(경과조치 1호)가 있어도
# 근거 조문이 다르다.
SEVERANCE_YEARS_CAP = 33


# 근속월수 구간명
def _find_band(months: int) -> str:
    if months >= 360:
        return "360+"
    lower = (months // 60) * 60
    upper = lower + 59
    return f"{lower}~{upper}"


# 퇴직수당 지급률
def _severance_rate(years: float) -> float:
    if years < 5:
        return 0.065
    if years < 10:
        return 0.2275
    if years < 15:
        return 0.2925
    if years < 20:
        return 0.325
    return 0.39


def calculate_monthly_pension(base_income: float, retire_months: int, cap_months: int) -> int:
    """연금월액 = 기준소득월액 x min(재직월수, 상한월수)/12 x PENSION_RATE.

    retire_months/cap_months를 그대로 받는 순수 함수다 — Pydantic 요청 객체나
    소득 밴드 추정 로직과 무관하게, 백테스트가 실제 재직월수와 상한월수를
    정밀하게 직접 주입할 수 있도록 분리했다(재타이핑 없이 동일 산식 재사용 목적).
    """
    pension_years = min(retire_months, cap_months) / 12
    return int(base_income * pension_years * PENSION_RATE)


def simulate_employees(req: SimulateRequest) -> SimulateResponse:
    current_months = req.current_years * 12
    retire_after_months = (req.retire_at_age - req.current_age) * 12
    retire_months = current_months + retire_after_months

    current_band = _find_band(current_months)
    retire_band = _find_band(retire_months)

    current_band_avg = get_band_mean(current_band)
    retire_band_avg = get_band_mean(retire_band)

    income_factor = req.current_income / current_band_avg
    estimated_avg_income = retire_band_avg * income_factor

    severance_years = min(retire_months / 12, SEVERANCE_YEARS_CAP)
    severance_pay = int(req.current_income * severance_years * _severance_rate(severance_years))

    cap_months, cap_basis = resolve_pension_service_cap_months(req.service_months_as_of_2016)

    if retire_months < 12:
        monthly_pension = 0
        lump_sum = int(estimated_avg_income * (retire_months / 12) * LUMP_SUM_CONVERSION_FACTOR)
        severance_pay = 0
    elif retire_months < PENSION_ELIGIBILITY_MONTHS:
        monthly_pension = 0
        lump_sum = int(estimated_avg_income * (retire_months / 12) * LUMP_SUM_CONVERSION_FACTOR)
    else:
        monthly_pension = calculate_monthly_pension(estimated_avg_income, retire_months, cap_months)
        lump_sum = 0

    return SimulateResponse(
        retire_months=retire_months,
        current_band=current_band,
        retire_band=retire_band,
        income_factor=round(income_factor, 3),
        estimated_avg_income=int(estimated_avg_income),
        monthly_pension=monthly_pension,
        lump_sum=lump_sum,
        severance_pay=severance_pay,
        service_cap_years=cap_months // 12,
        cap_basis=cap_basis,
    )
