"""API 경계의 금액 단위(원) <-> 내부 계산 단위(만원) 변환을 한 곳에 모은 모듈.

app/services/* 의 계산 로직과 상수(INVESTMENT_RETURN, reduction_rules의 threshold 등)는
전부 만원 단위를 그대로 사용한다(변경하지 않음). 이 모듈이 제공하는 타입 별칭을
요청/응답 스키마의 금액 필드에 붙이면, Pydantic이 역직렬화/직렬화 시점에 자동으로
원 <-> 만원 변환을 수행한다. 다른 곳에서 별도로 곱셈/나눗셈을 하지 않는다.
"""

from typing import Annotated

from pydantic import BeforeValidator, Field, PlainSerializer

WON_PER_MANWON = 10_000


def won_to_manwon(value: object) -> float:
    """API 요청으로 들어온 원 단위 금액을 내부 계산용 만원 단위로 변환한다."""
    return float(value) / WON_PER_MANWON


def manwon_to_won(value: float) -> int:
    """내부 계산 결과(만원)를 API 응답용 원 단위 정수로 변환한다."""
    return round(value * WON_PER_MANWON)


WonAmountInput = Annotated[
    float,
    Field(allow_inf_nan=False),
    BeforeValidator(won_to_manwon),
]
"""요청 스키마의 금액 필드에 사용한다. API 입력은 원 단위, 필드에는 만원 단위로 저장된다."""

WonAmountOutput = Annotated[float, PlainSerializer(manwon_to_won, return_type=int)]
"""응답 스키마의 금액 필드에 사용한다. 내부(만원) 값을 API 출력 시 원 단위 정수로 직렬화한다."""
