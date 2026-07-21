from enum import Enum

from pydantic import BaseModel


class ReadinessStatus(str, Enum):
    """노후 준비 상태 판정 결과"""

    SUFFICIENT = "SUFFICIENT"  # 자산이 고갈되지 않음
    MIDDLE = "MIDDLE"  # target_age 이후에 자산이 고갈됨
    INSUFFICIENT = "INSUFFICIENT"  # target_age 이전에 자산이 고갈됨


class TimelinePoint(BaseModel):
    age: int  # 나이
    asset: float  # 해당 나이 시점의 자산
    income: float  # 해당 연도 소득(연금)
    expense: float  # 해당 연도 지출
    gap: float  # 연간 Gap (지출 - 소득)
    cumulative_gap: float  # 누적 Gap


class SimulationResult(BaseModel):
    current_age: int  # 현재 나이
    monthly_gap: float  # 현재 시점의 월 Gap (월 생활비 - 월 연금)
    depletion_age: int | None  # 자산 고갈 나이 (고갈되지 않으면 None)
    target_age: int  # 목표연령 (성별 고정값)
    status: ReadinessStatus  # 노후 준비 상태
    timeline: list[TimelinePoint]  # 연도별 자산 추이


class DiagnosisRequest(BaseModel):
    current_age: int  # 현재 나이
    monthly_expenses: float  # 월 생활비
    monthly_pension: float  # 월 연금 수령액
    asset: float  # 현재 보유 자산
    gender: str  # 성별 ("male" 또는 "female")


class RecommendationRequest(DiagnosisRequest):
    """진단(diagnosis)과 동일한 입력 스키마를 재사용"""


class RecommendationType(str, Enum):
    """추천 유형"""

    SUFFICIENT = "SUFFICIENT"  # 이미 준비 상태가 충분하여 추천 불필요
    SAVING_ONLY = "SAVING_ONLY"  # 생활비 절약만으로 목표연령 도달 가능
    SAVING_AND_INCOME = "SAVING_AND_INCOME"  # 절약 상한을 적용하고도 추가 소득이 필요


class RecommendationResult(BaseModel):
    current_age: int  # 현재 나이
    recommendation_type: RecommendationType  # 추천 유형
    required_saving: float  # 필요 월 절약액 (만원)
    required_income: float  # 필요 월 추가 소득액 (만원)
    depletion_age: int | None  # 개선 적용 후 자산 고갈 나이
    target_age: int  # 목표연령
    status: ReadinessStatus  # 개선 적용 후 노후 준비 상태
    timeline: list[TimelinePoint]  # 개선 적용 후 연도별 자산 추이
