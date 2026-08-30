"""미래 외삽 시나리오: 2009년 이전 재직기간이 0인 가상 프로필 비교.

30-파라미터 모형(철회, backtest/analysis/) vs tranche+α(프로덕션, app/services/)의
예측을 비교한다. 실제 데이터가 아닌 가상 입력이므로 원본 데이터 취급 제한과
무관하다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\coding\BE\fastapi")))
sys.path.insert(0, str(Path(r"C:\coding\BE\fastapi\backtest\analysis")))

from app.services.pension_rate_model import calculate_monthly_pension_tranche  # noqa: E402
from effective_rate_model_30param import effective_pension_rate  # noqa: E402

HYPOTHETICAL_INCOME = 5_000_000  # 가상 프로필 — 실제 데이터 아님

PROFILES = [
    # (label, retire_year, retire_age, service_years)
    ("2025년 퇴직, 33년 근속 (학습표본 내부)", 2025, 62, 33),
    ("2040년 퇴직, 33년 근속 (학습표본 밖, 2009년 이전 0)", 2040, 62, 33),
    ("2055년 퇴직, 33년 근속 (학습표본 밖, 2009년 이전 0)", 2055, 62, 33),
    ("2070년 퇴직, 33년 근속 (학습표본 밖, 2009년 이전 0)", 2070, 62, 33),
]

rows = []
for label, retire_year, retire_age, service_years in PROFILES:
    rate_30p = effective_pension_rate(
        service_years=service_years, base_income=HYPOTHETICAL_INCOME,
        retire_year=retire_year, retire_age=retire_age,
    )
    pension_30p = int(HYPOTHETICAL_INCOME * service_years * rate_30p)

    retire_yyyymm = retire_year * 100 + 1
    pension_tranche = calculate_monthly_pension_tranche(
        HYPOTHETICAL_INCOME, retire_yyyymm, service_years * 12
    )

    # pct_vs_30p: tranche+α가 30-파라미터 모형보다 몇 % 높게(양수)/낮게(음수) 예측하는가.
    # (30p - tranche)처럼 방향을 반대로 잡으면 표를 읽을 때 부호가 직관과 어긋나므로
    # "채택 모형이 기준 대비 얼마나 높은가"로 고정한다.
    pct_vs_30p = (pension_tranche - pension_30p) / pension_30p * 100
    rows.append((label, pension_30p, pension_tranche, pct_vs_30p))

lines = [
    "| 프로필 | 30-파라미터 모형 월연금(원) | tranche+α 월연금(원) | tranche+α가 30-파라미터보다 몇 % 높은가 |",
    "|:---|---:|---:|---:|",
]
for label, p30, ptr, pct in rows:
    lines.append(f"| {label} | {p30:,} | {ptr:,} | {pct:+.1f}% |")
lines.append("")
lines.append(
    "마지막 열 = (tranche+α - 30-파라미터) / 30-파라미터 x 100. 양수는 tranche+α가 "
    "더 높게, 음수는 더 낮게 예측한다는 뜻이다."
)
out = Path(__file__).parent / "future_extrapolation_result.md"
out.write_text("\n".join(lines), encoding="utf-8")
print("written", out)
