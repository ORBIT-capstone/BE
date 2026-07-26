"""전 엔드포인트가 공유하는 단일 에러 응답 스키마.

Pydantic 422(RequestValidationError)와 라우터의 HTTPException(400/500 등)을
app/main.py의 예외 핸들러가 전부 이 형태로 변환해서 내보낸다. 프론트는 항상
code로 분기하고, message를 사용자에게 그대로 보여주고, details로 어떤 필드가
문제인지 알 수 있다.
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None  # 문제가 된 필드명(점 표기, 예: "current_age"). 특정 필드에 속하지 않으면 None
    reason: str  # 해당 필드가 왜 문제인지에 대한 한국어 설명


class ErrorResponse(BaseModel):
    code: str  # 프론트 분기용 에러 코드 (예: VALIDATION_ERROR, INVALID_INPUT, INTERNAL_ERROR)
    message: str  # 사용자에게 그대로 보여줄 수 있는 한국어 메시지
    details: list[ErrorDetail] = []  # 필드별 상세 (없으면 빈 리스트)
