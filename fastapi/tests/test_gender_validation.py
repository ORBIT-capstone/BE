"""gender 필드 검증에 대한 회귀 테스트.

기존에는 gender: str에 아무 제약이 없어, "MALE"(대문자 오타) 같은 값이
get_target_age()의 `if gender == "male": ... else: FEMALE` 분기를 타고
조용히 여성 목표연령(88세)으로 처리됐다(HTTP 200). 이제는 "male"/"female"
외의 값은 422로 거부되어야 한다.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _diagnosis_body(gender) -> dict:
    return {
        "current_age": 60,
        "monthly_expenses": 2_000_000,
        "monthly_pension": 1_500_000,
        "asset": 100_000_000,
        "gender": gender,
    }


def test_diagnosis_accepts_male(client):
    response = client.post("/api/retirement/diagnosis", json=_diagnosis_body("male"))
    assert response.status_code == 200
    assert response.json()["target_age"] == 84


def test_diagnosis_accepts_female(client):
    response = client.post("/api/retirement/diagnosis", json=_diagnosis_body("female"))
    assert response.status_code == 200
    assert response.json()["target_age"] == 88


@pytest.mark.parametrize("invalid_gender", ["MALE", "Male", "m", "남성", "unknown", ""])
def test_diagnosis_rejects_invalid_gender_with_422(client, invalid_gender):
    response = client.post("/api/retirement/diagnosis", json=_diagnosis_body(invalid_gender))
    assert response.status_code == 422
