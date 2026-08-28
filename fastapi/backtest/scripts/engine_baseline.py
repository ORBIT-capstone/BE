"""프로덕션 엔진의 연금월액 산식 재현 (baseline/tranche+α 예측용).

fastapi/app/services/employees_service.py 의 실제 산식(calculate_monthly_pension)과
fastapi/app/services/service_cap_rules.py의 재직기간 상한 판정(사학연금법 부칙
제11조 경과조치)을 그대로 재사용한다. 상수·산식은 재타이핑하지 않고 모듈에서
직접 import한다.

주의: 프로덕션 REST 엔드포인트(/api/employees/simulate)는 SimulateRequest.current_years가
정수(int) 필드라 연 단위 미만 정밀도가 손실된다. 이는 API 입력 스키마의 제약이지
산식 자체의 제약이 아니므로, 여기서는 정수 월 단위로 정밀한 실제 재직월수를
그대로 사용해 산식 핵심 로직만 재현한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

FASTAPI_ROOT = Path(__file__).resolve().parent.parent.parent
if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))
BACKTEST_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(BACKTEST_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(BACKTEST_SCRIPTS_DIR))

from app.services.employees_service import PENSION_ELIGIBILITY_MONTHS  # noqa: E402
from app.services.employees_service import calculate_monthly_pension as _calculate_monthly_pension  # noqa: E402
from app.services.service_cap_rules import resolve_pension_service_cap_months  # noqa: E402
from tranche import idx_from_yyyymm  # noqa: E402

_IDX_2016_01 = idx_from_yyyymm(201601)

# --- 과거(legacy) baseline 상수 — 프로덕션에서는 이미 제거됐다 ---
# Phase 3 baseline_report.md("개선 전" 상태)를 재현하기 위한 동결값이다. 당시
# 엔진은 단일 상수 1.7%와 재직연수 일괄 36년 캡을 썼다. 프로덕션이 바뀐 뒤에도
# 이 "개선 전" 수치를 그대로 재현할 수 있어야 하므로 여기에 동결해 둔다 —
# 프로덕션 코드에서 import하지 않는다(import하면 개선 전 baseline이 프로덕션이
# 바뀔 때마다 조용히 따라 움직인다).
LEGACY_PENSION_RATE = 0.017
LEGACY_SERVICE_YEARS_CAP = 36


def predict_monthly_pension_legacy(base_income: float, months: int) -> int:
    """개선 전 엔진(단일 상수 1.7% + 일괄 36년 캡)의 연금월액 예측값."""
    if months < PENSION_ELIGIBILITY_MONTHS:
        return 0
    pension_years = min(months / 12, LEGACY_SERVICE_YEARS_CAP)
    return int(base_income * pension_years * LEGACY_PENSION_RATE)


def service_months_as_of_2016_from_appointment(추정임용연월: pd.Series) -> pd.Series:
    """추정임용연월로부터 2016.1.1 시점 인정 재직월수를 역산한다.

    service_cap_rules.resolve_pension_service_cap_months가 요구하는 입력이며,
    이 값 자체가 인정 재직기간(추정임용연월)에서 파생된 근사치라는 한계는
    build_clean_dataset.py 한계 서술·scope_limitations.md §2-1과 동일하게 적용된다.
    2016.1.1 이후 임용(idx(추정임용연월) > idx(2016-01))이면 0(경과조치 비대상)으로 처리한다.
    """
    months = _IDX_2016_01 - idx_from_yyyymm(추정임용연월)
    return months.clip(lower=0).astype("int64")


def predict_monthly_pension(
    base_income: float,
    months: int,
    service_months_as_of_2016: int | None = None,
    *,
    retire_yyyymm: int,
) -> int:
    """app/services/employees_service.py::simulate_employees 의 연금 산식 분기를 그대로 재현.

    원본 소스:
        elif retire_months < 120:
            monthly_pension = 0
        else:
            cap_months, cap_basis = resolve_pension_service_cap_months(service_months_as_of_2016)
            monthly_pension = calculate_monthly_pension(estimated_avg_income, retire_months, cap_months, retire_yyyymm)

    service_months_as_of_2016을 넘기지 않으면(None) DEFAULT_MAX(36년 고정)로 판정된다.
    retire_yyyymm은 tranche+α 모형이 연도별 요율을 적용하는 기준점이라 필수
    키워드다 — 백테스트에서는 실제 퇴직연월(`추정임용연월 + 재직월수`)을 그대로 쓴다.
    """
    if months < PENSION_ELIGIBILITY_MONTHS:
        return 0
    cap_months, _cap_basis = resolve_pension_service_cap_months(service_months_as_of_2016)
    return _calculate_monthly_pension(base_income, months, cap_months, retire_yyyymm)
