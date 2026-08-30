import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
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
    expected = client.post("/api/employees/scenarios", json={
        **body(years),
        "monthly_pension": 3_000_000 * min(years, 36) * 0.017,
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
