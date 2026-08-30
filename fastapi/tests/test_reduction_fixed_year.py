from fastapi.testclient import TestClient

from app.main import app
from app.services import reduction_rules


def test_reduction_stays_on_2025_even_when_newer_rule_is_registered(monkeypatch):
    monkeypatch.setattr(reduction_rules, "REDUCTION_RULES", [
        *reduction_rules.REDUCTION_RULES,
        reduction_rules.ReductionRule(
            year=2026, threshold=9999,
            rate_brackets=reduction_rules.REDUCTION_RULES[-1].rate_brackets,
        ),
    ])
    client = TestClient(app)
    body = {
        "current_age": 60,
        "monthly_expenses": 2_500_000,
        "monthly_pension": 1_500_000,
        "asset": 100_000_000,
        "gender": "male",
        "reemployment_income": 4_000_000,
    }
    response = client.post("/api/retirement/reduction", json=body)
    assert response.status_code == 200
    assert response.json()["full_payment_income_threshold"] == 3_097_000
    # 기존 서비스의 만원 단위 소수 둘째 자리 반올림(100원 단위)을 유지한다.
    assert response.json()["monthly_reduction"] == 45_200

    # 기존 클라이언트가 제거된 필드를 보내더라도 고정 기준을 변경할 수 없다.
    legacy = client.post("/api/retirement/reduction", json={**body, "year": 2023})
    assert legacy.status_code == 200
    assert legacy.json() == response.json()


def test_reduction_request_schema_no_longer_has_year():
    schema = TestClient(app).get("/openapi.json").json()
    assert "year" not in schema["components"]["schemas"]["ReductionRequest"]["properties"]
