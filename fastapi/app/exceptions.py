class DomainValidationError(ValueError):
    """호출자가 수정할 수 있는 도메인 입력 오류."""


class DataSourceError(RuntimeError):
    """필수 통계 데이터가 없거나 형식이 잘못된 서버 구성 오류."""
