"""전 엔드포인트 에러 응답 포맷 통일에 대한 회귀 테스트.

기존에는 에러가 세 가지 다른 모양으로 나갔다:
  - Pydantic 422: {"detail": [{"type":..., "loc":..., "msg": 영문, ...}, ...]}
  - 라우터의 HTTPException(400): {"detail": "한국어 문자열"}
  - model_validator가 던진 ValueError도 422로 나가되 msg 앞에 "Value error, "가 붙음
프론트가 error.detail을 그대로 쓸 수 없었다(문자열/배열이 상황마다 달랐음).

이제는 모든 에러가 {"code": str, "message": str(한국어), "details": [{"field", "reason"}, ...]}
단일 포맷으로 나가야 한다.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _assert_unified_error_shape(body: dict) -> None:
    assert set(body.keys()) == {"code", "message", "details", "timestamp"}
    assert isinstance(body["code"], str) and body["code"]
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["details"], list)
    assert datetime.fromisoformat(body["timestamp"])
    for detail in body["details"]:
        assert set(detail.keys()) == {"field", "reason"}
        assert isinstance(detail["reason"], str) and detail["reason"]


def test_pydantic_type_error_returns_unified_shape(client):
    response = client.post(
        "/api/retirement/diagnosis",
        json={
            "current_age": "abc",
            "monthly_expenses": 2_000_000,
            "monthly_pension": 1_500_000,
            "asset": 100_000_000,
            "gender": "male",
        },
    )
    assert response.status_code == 400
    body = response.json()
    _assert_unified_error_shape(body)
    assert body["code"] == "VALIDATION_ERROR"
    fields = {d["field"] for d in body["details"]}
    assert "current_age" in fields


def test_non_positive_expenses_returns_validation_error(client):
    response = client.post(
        "/api/retirement/diagnosis",
        json={
            "current_age": 60,
            "monthly_expenses": 0,
            "monthly_pension": 1_500_000,
            "asset": 100_000_000,
            "gender": "male",
        },
    )
    assert response.status_code == 400
    body = response.json()
    _assert_unified_error_shape(body)
    assert body["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "monthly_expenses" for detail in body["details"])


def test_model_validator_error_strips_english_value_error_prefix(client):
    response = client.post(
        "/api/employees/simulate",
        json={
            "current_years": 20,
            "current_income": 5_000_000,
            "current_age": 60,
            "retire_at_age": 50,
        },
    )
    assert response.status_code == 400
    body = response.json()
    _assert_unified_error_shape(body)
    assert "Value error" not in body["message"]
    assert not any("Value error" in d["reason"] for d in body["details"])


def test_invalid_gender_enum_returns_unified_shape(client):
    response = client.post(
        "/api/retirement/diagnosis",
        json={
            "current_age": 60,
            "monthly_expenses": 2_000_000,
            "monthly_pension": 1_500_000,
            "asset": 100_000_000,
            "gender": "MALE",
        },
    )
    assert response.status_code == 400
    body = response.json()
    _assert_unified_error_shape(body)
    fields = {d["field"] for d in body["details"]}
    assert "gender" in fields


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/retirement/diagnosis", {"current_age": "abc"}),
        ("/api/retirement/recommendations", {"current_age": "abc"}),
        ("/api/retirement/reduction", {"current_age": "abc"}),
        ("/api/retirement/scenarios", {"current_age": "abc"}),
        ("/api/employees/simulate", {"current_age": "abc"}),
    ],
)
def test_all_endpoints_share_same_error_envelope(client, path, body):
    response = client.post(path, json=body)
    assert response.status_code == 400
    _assert_unified_error_shape(response.json())


def test_openapi_documents_400_with_unified_error_schema(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/retirement/diagnosis"]["post"]

    assert "422" not in operation["responses"]
    assert operation["responses"]["400"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
    error_schema = schema["components"]["schemas"]["ErrorResponse"]
    assert set(error_schema["required"]) == {"code", "message"}
    assert {"details", "timestamp"} <= set(error_schema["properties"])
