"""5개 엔드포인트의 현재(수정 전) 응답을 고정하는 골든 스냅샷 테스트.

이후 이슈 수정 작업에서 의도한 필드 외의 값이 조금이라도 바뀌면 이 테스트가
즉시 실패해야 한다. 산식/응답 형식을 의도적으로 바꾼 뒤에는:
  1) 새 응답이 의도한 변경과 정확히 일치하는지 직접 확인하고
  2) tests/golden/_generate.py로 해당 케이스의 픽스처만 다시 생성한다.
케이스를 통과시키기 위해 무비판적으로 재생성하지 말 것.
"""

import json
from datetime import date as _real_date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

GOLDEN_DIR = Path(__file__).parent / "golden"

# tranche+α 지급률 모형(app/services/pension_rate_model.py)은 퇴직연월을 date.today()
# 기준으로 계산한다 — 같은 요청이라도 호출 시점(오늘 날짜)에 따라 연도별 tranche
# 요율이 달라지므로 monthly_pension이 달라진다(의도된 동작: "지금부터 몇 년 후
# 퇴직하는가"를 매번 오늘 기준으로 다시 계산한다). 골든 스냅샷은 응답을 영구
# 고정해야 하므로, employees_service/retirement_service가 보는 "오늘"을 고정값으로
# 패치한다 — 그러지 않으면 이 테스트들은 매달(정확히는 tranche 연도 경계를
# 지날 때마다) 이유 없이 실패한다.
FIXED_TODAY = _real_date(2026, 1, 1)


class _FixedDate(_real_date):
    @classmethod
    def today(cls) -> _real_date:  # type: ignore[override]
        return FIXED_TODAY

# retirement 계열 엔드포인트는 #1(금액 단위 통일)로 요청/응답이 만원 -> 원으로 바뀌었다.
# 케이스가 나타내는 실제 시나리오(예: "월 생활비 250만원")는 그대로 유지하기 위해
# 만원 단위였던 리터럴에 WON_PER_MANWON을 곱해 원 단위로 표현한다.
WON_PER_MANWON = 10_000

CASES = [
    # --- /api/retirement/diagnosis ---
    {
        "name": "diagnosis_sufficient",
        "path": "/api/retirement/diagnosis",
        "body": {
            "current_age": 65,
            "monthly_expenses": 150 * WON_PER_MANWON,
            "monthly_pension": 200 * WON_PER_MANWON,
            "asset": 10000 * WON_PER_MANWON,
            "gender": "male",
        },
    },
    {
        "name": "diagnosis_insufficient",
        "path": "/api/retirement/diagnosis",
        "body": {
            "current_age": 60,
            "monthly_expenses": 250 * WON_PER_MANWON,
            "monthly_pension": 150 * WON_PER_MANWON,
            "asset": 10000 * WON_PER_MANWON,
            "gender": "male",
        },
    },
    {
        "name": "diagnosis_middle",
        "path": "/api/retirement/diagnosis",
        "body": {
            "current_age": 60,
            "monthly_expenses": 200 * WON_PER_MANWON,
            "monthly_pension": 150 * WON_PER_MANWON,
            "asset": 32000 * WON_PER_MANWON,
            "gender": "female",
        },
    },
    # --- /api/retirement/recommendations ---
    {
        "name": "recommendations_sufficient",
        "path": "/api/retirement/recommendations",
        "body": {
            "current_age": 65,
            "monthly_expenses": 150 * WON_PER_MANWON,
            "monthly_pension": 200 * WON_PER_MANWON,
            "asset": 10000 * WON_PER_MANWON,
            "gender": "male",
        },
    },
    {
        "name": "recommendations_saving_only",
        "path": "/api/retirement/recommendations",
        "body": {
            "current_age": 60,
            "monthly_expenses": 250 * WON_PER_MANWON,
            "monthly_pension": 200 * WON_PER_MANWON,
            "asset": 15000 * WON_PER_MANWON,
            "gender": "male",
        },
    },
    {
        "name": "recommendations_saving_and_income",
        "path": "/api/retirement/recommendations",
        "body": {
            "current_age": 60,
            "monthly_expenses": 400 * WON_PER_MANWON,
            "monthly_pension": 100 * WON_PER_MANWON,
            "asset": 5000 * WON_PER_MANWON,
            "gender": "female",
        },
    },
    # --- /api/retirement/reduction ---
    {
        "name": "reduction_no_reduction",
        "path": "/api/retirement/reduction",
        "body": {
            "current_age": 60,
            "monthly_expenses": 200 * WON_PER_MANWON,
            "monthly_pension": 150 * WON_PER_MANWON,
            "asset": 10000 * WON_PER_MANWON,
            "gender": "male",
            "reemployment_income": 0,
        },
    },
    {
        "name": "reduction_partial",
        "path": "/api/retirement/reduction",
        "body": {
            "current_age": 60,
            "monthly_expenses": 200 * WON_PER_MANWON,
            "monthly_pension": 150 * WON_PER_MANWON,
            "asset": 10000 * WON_PER_MANWON,
            "gender": "male",
            "reemployment_income": 500 * WON_PER_MANWON,
        },
    },
    {
        "name": "reduction_capped",
        "path": "/api/retirement/reduction",
        "body": {
            "current_age": 60,
            "monthly_expenses": 200 * WON_PER_MANWON,
            "monthly_pension": 150 * WON_PER_MANWON,
            "asset": 10000 * WON_PER_MANWON,
            "gender": "male",
            "reemployment_income": 99999 * WON_PER_MANWON,
        },
    },
    # --- /api/employees/scenarios ---
    {
        "name": "scenarios_basic",
        "path": "/api/employees/scenarios",
        "body": {
            "current_age": 60,
            "monthly_expenses": 250 * WON_PER_MANWON,
            "monthly_pension": 150 * WON_PER_MANWON,
            "asset": 10000 * WON_PER_MANWON,
            "gender": "male",
            "base_monthly_income": 300 * WON_PER_MANWON,
            "total_service_years": 25,
        },
    },
    {
        "name": "scenarios_with_deduction_years",
        "path": "/api/employees/scenarios",
        "body": {
            "current_age": 60,
            "monthly_expenses": 250 * WON_PER_MANWON,
            "monthly_pension": 150 * WON_PER_MANWON,
            "asset": 10000 * WON_PER_MANWON,
            "gender": "male",
            "base_monthly_income": 300 * WON_PER_MANWON,
            "total_service_years": 25,
            "deduction_years": 15,
        },
    },
    # --- /api/employees/simulate ---
    {
        "name": "simulate_normal",
        "path": "/api/employees/simulate",
        "body": {
            "current_years": 20,
            "current_income": 5000000,
            "current_age": 50,
            "retire_at_age": 62,
        },
    },
    {
        "name": "simulate_lump_sum_only",
        "path": "/api/employees/simulate",
        "body": {
            "current_years": 2,
            "current_income": 5000000,
            "current_age": 30,
            "retire_at_age": 35,
        },
    },
    {
        "name": "simulate_zero_months",
        "path": "/api/employees/simulate",
        "body": {
            "current_years": 0,
            "current_income": 5000000,
            "current_age": 30,
            "retire_at_age": 30,
        },
    },
]


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    monkeypatch.setattr("app.services.employees_service.date", _FixedDate)
    monkeypatch.setattr("app.services.retirement_service.date", _FixedDate)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_golden_snapshot(client, case):
    fixture_path = GOLDEN_DIR / f"{case['name']}.json"
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))

    response = client.post(case["path"], json=case["body"])

    assert response.status_code == expected["status_code"]
    assert response.json() == expected["body"]
