from enum import Enum

from pydantic import BaseModel, Field, model_validator


class CapBasis(str, Enum):
    """연금월액 계산에 적용된 재직기간 상한의 근거.

    - STATUTORY_TIERED: 사학연금법 부칙(법률 제13561호) 제11조 경과조치 표
      (2016.1.1 시점 재직기간에 따라 33/34/35/36년 차등).
    - STATUTORY_DEFAULT: 2016.1.1 이후 임용(경과조치 비대상) -> 본칙 36년.
    - DEFAULT_MAX: service_months_as_of_2016 미제공 -> 판정 불가, 36년 폴백.
    """

    STATUTORY_TIERED = "STATUTORY_TIERED"
    STATUTORY_DEFAULT = "STATUTORY_DEFAULT"
    DEFAULT_MAX = "DEFAULT_MAX"


class SimulateRequest(BaseModel):
    current_years: int = Field(..., ge=0)
    current_income: int = Field(..., gt=0)
    current_age: int = Field(..., gt=0)
    retire_at_age: int = Field(..., gt=0)
    service_months_as_of_2016: int | None = Field(
        default=None,
        ge=0,
        description=(
            "2016.1.1 시점 인정 재직월수(옵셔널). 사학연금법 부칙(법률 제13561호) 제11조는 "
            "'이 법 시행 전의 재직기간'으로 재직기간 상한(33/34/35/36년)을 차등 적용하는데, "
            "이 조문은 '제32조제1항에 따라 합산한 사람을 포함한다'고 명시한다 — 즉 이 값은 "
            "캘린더상 실제 근무개월수가 아니라 군복무 소급·경력합산·소급통산이 반영된 "
            "'인정 재직월수'다. 임용연월(또는 그 추정치)로부터 역산하는 경우 근사치일 수밖에 "
            "없다는 점에 유의할 것 — 동일한 한계가 backtest/scripts/build_clean_dataset.py의 "
            "재직월수/추정임용연월 한계 서술 및 backtest/reports/scope_limitations.md §2-1에도 "
            "기록돼 있다. 0=2016.1.1 이후 임용(경과조치 비대상, 본칙 36년), 양수=경과조치 표 "
            "적용, None(미제공)=판정 불가로 기존 동작(36년) 유지."
        ),
    )

    @model_validator(mode="after")
    def validate_retire_at_age(self) -> "SimulateRequest":
        if self.retire_at_age < self.current_age:
            raise ValueError("퇴직 예정 나이는 현재 나이보다 작을 수 없습니다.")
        return self


class SimulateResponse(BaseModel):
    retire_months: int
    current_band: str
    retire_band: str
    income_factor: float
    estimated_avg_income: int
    monthly_pension: int
    lump_sum: int
    severance_pay: int
    service_cap_years: int  # 연금월액 계산에 적용된 재직기간 상한(년) — 33/34/35/36
    cap_basis: CapBasis  # 위 상한의 판정 근거
