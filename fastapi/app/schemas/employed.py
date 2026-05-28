from pydantic import BaseModel, Field, model_validator


class SimulateRequest(BaseModel):
    current_years: int = Field(..., ge=0)
    current_income: int = Field(..., gt=0)
    current_age: int = Field(..., gt=0)
    retire_at_age: int = Field(..., gt=0)

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
    severance_pay: int
