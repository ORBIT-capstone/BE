import math

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.retirement import DiagnosisRequest


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def diagnosis_body(**overrides):
    body = {
        "current_age": 60,
        "monthly_expenses": 2_500_000,
        "monthly_pension": 1_500_000,
        "asset": 100_000_000,
        "gender": "male",
    }
    body.update(overrides)
    return body


@pytest.mark.parametrize("current_age", [0, -1, 101])
def test_diagnosis_rejects_age_outside_simulation_range(client, current_age):
    response = client.post(
        "/api/retirement/diagnosis",
        json=diagnosis_body(current_age=current_age),
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "field,value",
    [
        ("monthly_expenses", 0),
        ("monthly_expenses", -1),
        ("monthly_pension", -1),
        ("asset", -1),
    ],
)
def test_diagnosis_rejects_invalid_money_values(client, field, value):
    response = client.post(
        "/api/retirement/diagnosis",
        json=diagnosis_body(**{field: value}),
    )
    assert response.status_code == 400


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_diagnosis_rejects_non_finite_money(value):
    # 표준 JSON 인코더가 비유한수를 전송 전에 거부하므로 스키마 경계에서 직접 검증한다.
    with pytest.raises(ValidationError):
        DiagnosisRequest.model_validate(diagnosis_body(asset=value))


def test_scenarios_rejects_invalid_service_years_at_schema_boundary(client):
    response = client.post(
        "/api/employees/scenarios",
        json={
            **diagnosis_body(),
            "base_monthly_income": 3_000_000,
            "total_service_years": 9,
        },
    )
    assert response.status_code == 400
