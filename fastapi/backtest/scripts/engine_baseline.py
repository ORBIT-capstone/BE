"""현재 프로덕션 엔진의 연금월액 산식 재현 (baseline 예측용).

fastapi/app/services/employees_service.py 의 실제 산식(PENSION_RATE 상수, 재직연수
상한 캡 로직)을 그대로 재사용한다. 상수는 재타이핑하지 않고 모듈에서 직접 import한다.

주의: 프로덕션 REST 엔드포인트(/api/employees/simulate)는 SimulateRequest.current_years가
정수(int) 필드라 연 단위 미만 정밀도가 손실된다. 이는 API 입력 스키마의 제약이지
산식 자체(연산은 retire_months/12로 이미 소수 재직연수를 지원)의 제약이 아니므로,
여기서는 정수 월 단위로 정밀한 실제 재직월수를 그대로 사용해 산식 핵심 로직만 재현한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

FASTAPI_ROOT = Path(__file__).resolve().parent.parent.parent
if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))

from app.services.employees_service import PENSION_RATE  # noqa: E402

PENSION_ELIGIBILITY_MONTHS = 120  # employees_service.py: retire_months < 120 -> monthly_pension = 0
SERVICE_YEARS_CAP = 36  # employees_service.py: pension_years = min(retire_months / 12, 36)


def predict_monthly_pension(base_income: float, months: int) -> int:
    """app/services/employees_service.py::simulate_employees 의 연금 산식 분기를 그대로 재현.

    원본 소스:
        elif retire_months < 120:
            monthly_pension = 0
        else:
            pension_years = min(retire_months / 12, 36)
            monthly_pension = int(estimated_avg_income * pension_years * PENSION_RATE)
    """
    if months < PENSION_ELIGIBILITY_MONTHS:
        return 0
    pension_years = min(months / 12, SERVICE_YEARS_CAP)
    return int(base_income * pension_years * PENSION_RATE)
