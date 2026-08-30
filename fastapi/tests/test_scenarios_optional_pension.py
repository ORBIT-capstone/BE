from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.money import WON_PER_MANWON
from app.services import retirement_service
from app.services.pension_rate_model import calculate_monthly_pension_tranche


FIXED_TODAY = date(2026, 1, 1)


class FixedDate(date):
    @classmethod
    def today(cls):
        return FIXED_TODAY


@pytest.fixture
def client(monkeypatch):
    # 연도별 지급률은 퇴직연월에 의존하므로 CI 실행 날짜와 무관하게 검증한다.
    monkeypatch.setattr(retirement_service, "date", FixedDate)
    return TestClient(app)


def body(years=25):
    return {
        "current_age": 60,
        "monthly_expenses": 2_500_000,
        "asset": 100_000_000,
        "gender": "male",
        "base_monthly_income": 3_000_000,
        "total_service_years": years,
    }


@pytest.mark.parametrize("years", [10, 25, 40])
@pytest.mark.parametrize("explicit_null", [False, True])
def test_missing_pension_matches_estimated_pension(client, years, explicit_null):
    request = body(years)
    if explicit_null:
        request["monthly_pension"] = None
    response = client.post("/api/employees/scenarios", json=request)
    # 이 테스트는 생략한 월연금이 현재 모형의 추정값을 입력한 경우와 같은지 검증한다.
    # 지급률표 자체는 test_pension_rate_model.py에서 별도로 검증한다.
    # 은퇴 서비스의 내부 만원 단위와 모형 반환 정밀도를 유지한 뒤 API 단위(원)로 환산한다.
    estimated_pension = calculate_monthly_pension_tranche(
        request["base_monthly_income"] / WON_PER_MANWON,
        FIXED_TODAY.year * 100 + FIXED_TODAY.month,
        min(years, 36) * 12,
    ) * WON_PER_MANWON
    expected = client.post("/api/employees/scenarios", json={
        **body(years),
        "monthly_pension": estimated_pension,
    })
    assert response.status_code == expected.status_code == 200
    assert response.json() == expected.json()


def test_explicit_zero_pension_is_preserved(client):
    response = client.post("/api/employees/scenarios", json={**body(), "monthly_pension": 0})
    assert response.status_code == 200
    scenarios = response.json()["scenarios"]
    for scenario in scenarios:
        if scenario["scenario_type"] in ("NORMAL", "EARLY"):
            assert scenario["total_received"] == 0


def test_negative_pension_is_rejected(client):
    response = client.post("/api/employees/scenarios", json={**body(), "monthly_pension": -1})
    assert response.status_code == 400


@pytest.mark.parametrize("endpoint", ["diagnosis", "recommendations", "reduction"])
def test_other_retirement_apis_still_require_pension(client, endpoint):
    request = {**body(), "reemployment_income": 0}
    response = client.post(f"/api/retirement/{endpoint}", json=request)
    assert response.status_code == 400
    assert any(error["field"] == "monthly_pension" for error in response.json()["details"])


def test_openapi_documents_optional_pension_only_for_scenarios(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "monthly_pension" not in schemas["ScenariosRequest"]["required"]
    assert "monthly_pension" in schemas["DiagnosisRequest"]["required"]
