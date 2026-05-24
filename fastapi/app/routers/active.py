from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/active", tags=["active"])

_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "active_income_stats.csv"
_stats: pd.DataFrame | None = None


def _get_stats() -> pd.DataFrame:
    global _stats
    if _stats is None:
        _stats = pd.read_csv(_CSV_PATH)
    return _stats


# 근속월수 → 구간명
def _find_band(months: int) -> str:
    if months >= 360:
        return "360+"
    lower = (months // 60) * 60
    upper = lower + 59
    return f"{lower}~{upper}"


# 구간명 → 해당 행 평균
def _band_mean(band: str) -> float:
    df = _get_stats()
    row = df[df["구간"] == band]
    if row.empty:
        raise HTTPException(status_code=500, detail=f"구간 '{band}' 데이터 없음")
    return float(row.iloc[0]["평균"])


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


class SimulateRequest(BaseModel):
    current_years: int
    current_income: int
    current_age: int
    retire_at_age: int


class SimulateResponse(BaseModel):
    retire_months: int
    current_band: str
    retire_band: str
    income_factor: float
    estimated_avg_income: int
    monthly_pension: int
    severance_pay: int


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    current_months = req.current_years * 12
    retire_after_months = (req.retire_at_age - req.current_age) * 12
    retire_months = current_months + retire_after_months

    current_band = _find_band(current_months)
    retire_band  = _find_band(retire_months)

    current_band_avg = _band_mean(current_band)
    retire_band_avg  = _band_mean(retire_band)

    income_factor = req.current_income / current_band_avg
    estimated_avg_income = retire_band_avg * income_factor

    pension_years  = min(retire_months / 12, 36)
    monthly_pension = int(estimated_avg_income * pension_years * 0.017)

    severance_years = min(retire_months / 12, 33)
    severance_pay   = int(req.current_income * severance_years * _severance_rate(severance_years))

    return SimulateResponse(
        retire_months=retire_months,
        current_band=current_band,
        retire_band=retire_band,
        income_factor=round(income_factor, 3),
        estimated_avg_income=int(estimated_avg_income),
        monthly_pension=monthly_pension,
        severance_pay=severance_pay,
    )
