"""전 엔드포인트의 에러 응답을 app/schemas/errors.py의 단일 포맷으로 통일하는 핸들러.

- RequestValidationError(Pydantic 422): 필드별 원인을 한국어로 번역해 details에 담는다.
- HTTPException(라우터가 ValueError를 잡아 400/500으로 던진 것): 동일 포맷으로 감싼다.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import ErrorDetail, ErrorResponse

_PYDANTIC_ERROR_MESSAGES: dict[str, str] = {
    "missing": "필수 항목입니다.",
    "int_parsing": "정수여야 합니다.",
    "int_type": "정수여야 합니다.",
    "float_parsing": "숫자여야 합니다.",
    "float_type": "숫자여야 합니다.",
    "string_type": "문자열이어야 합니다.",
    "enum": "허용되지 않는 값입니다.",
    "bool_parsing": "true/false 값이어야 합니다.",
    "bool_type": "true/false 값이어야 합니다.",
}


def _translate_pydantic_error(error: dict) -> str:
    """Pydantic 에러 하나를 한국어 문구로 번역한다. 매핑에 없는 타입은 원문 메시지를 그대로 쓴다."""
    error_type = error.get("type", "")
    if error_type == "value_error":
        # model_validator가 던진 ValueError는 이미 한국어지만, Pydantic이 "Value error, " 접두사를 붙인다.
        return error.get("msg", "").removeprefix("Value error, ")
    return _PYDANTIC_ERROR_MESSAGES.get(error_type, error.get("msg", "입력값이 올바르지 않습니다."))


def _field_name(loc: tuple) -> str | None:
    """Pydantic의 loc(예: ("body", "current_age"))를 "current_age" 같은 점 표기 필드명으로 변환한다.
    특정 필드에 속하지 않는 에러(예: 모델 전체에 대한 검증)면 None을 반환한다."""
    path = [str(part) for part in loc if part != "body"]
    return ".".join(path) if path else None


def _validation_error_message(details: list[ErrorDetail]) -> str:
    if len(details) == 1:
        return details[0].reason
    return f"입력값을 확인해주세요. ({len(details)}개 항목에 문제가 있습니다.)"


_STATUS_CODE_TO_ERROR_CODE: dict[int, str] = {
    400: "INVALID_INPUT",
    404: "NOT_FOUND",
    500: "INTERNAL_ERROR",
}


def _error_code_for_status(status_code: int) -> str:
    return _STATUS_CODE_TO_ERROR_CODE.get(status_code, "ERROR")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(field=_field_name(error["loc"]), reason=_translate_pydantic_error(error))
            for error in exc.errors()
        ]
        body = ErrorResponse(
            code="VALIDATION_ERROR",
            message=_validation_error_message(details),
            details=details,
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "요청을 처리할 수 없습니다."
        body = ErrorResponse(code=_error_code_for_status(exc.status_code), message=message, details=[])
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())
