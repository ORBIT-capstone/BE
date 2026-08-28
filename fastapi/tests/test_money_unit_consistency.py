"""API 경계의 금액 단위(원) 일관성 검증.

simulate의 monthly_pension 출력을 diagnosis의 monthly_pension 입력에 그대로
넣었을 때, 두 API가 같은 단위(원)를 쓰고 있다면 diagnosis의 monthly_gap이
(입력한 monthly_expenses - monthly_pension)과 정확히 일치해야 한다.
단위가 어긋나 있으면(예: 한쪽 원, 한쪽 만원) 이 값이 10,000배 가까이 벌어진다.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_simulate_monthly_pension_feeds_consistently_into_diagnosis(client):
    simulate_response = client.post(
        "/api/employees/simulate",
        json={
            "current_years": 20,
            "current_income": 5_000_000,
            "current_age": 50,
            "retire_at_age": 62,
        },
    )
    assert simulate_response.status_code == 200
    monthly_pension_won = simulate_response.json()["monthly_pension"]
    assert monthly_pension_won > 100_000  # 원 단위라면 이 정도 규모가 정상

    monthly_expenses_won = monthly_pension_won + 500_000

    diagnosis_response = client.post(
        "/api/retirement/diagnosis",
        json={
            "current_age": 62,
            "monthly_expenses": monthly_expenses_won,
            "monthly_pension": monthly_pension_won,
            "asset": 100_000_000,
            "gender": "male",
        },
    )
    assert diagnosis_response.status_code == 200
    body = diagnosis_response.json()

    assert body["monthly_gap"] == pytest.approx(
        monthly_expenses_won - monthly_pension_won, abs=2
    )


def test_reduction_income_at_threshold_produces_zero_reduction(client):
    """reduction_rules.threshold(309.7만원, 고정 상수)는 입력값 스케일과 무관하게
    고정돼 있으므로, reemployment_income을 '원' 단위로 넣었을 때 내부 변환이
    빠지면 이 값이 threshold를 훨씬 초과한 것처럼 오인되어 감액이 발생한다.
    threshold와 정확히 같은 소득(원 단위)을 넣으면 감액이 0이어야 한다.
    """
    from app.services.reduction_rules import get_reduction_rule

    threshold_manwon = get_reduction_rule(2025).threshold
    reemployment_income_won = round(threshold_manwon * 10_000)

    response = client.post(
        "/api/retirement/reduction",
        json={
            "current_age": 60,
            "monthly_expenses": 2_000_000,
            "monthly_pension": 1_500_000,
            "asset": 100_000_000,
            "gender": "male",
            "reemployment_income": reemployment_income_won,
            "year": 2025,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["monthly_reduction"] == 0
