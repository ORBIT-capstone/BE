from app.repositories.employees_income_repository import get_band_mean
from app.schemas.employees import SimulateRequest, SimulateResponse


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

    severance_years = min(retire_months / 12, 33)
    severance_pay = int(req.current_income * severance_years * _severance_rate(severance_years))

    if retire_months < 12:
        monthly_pension = 0
        lump_sum = int(estimated_avg_income * (retire_months / 12) * 975 / 1000)
        severance_pay = 0
    elif retire_months < 120:
        monthly_pension = 0
        lump_sum = int(estimated_avg_income * (retire_months / 12) * 975 / 1000)
    else:
        pension_years = min(retire_months / 12, 36)
        monthly_pension = int(estimated_avg_income * pension_years * 0.017)
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
    )
