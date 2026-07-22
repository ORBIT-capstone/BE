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
    target_status: ReadinessStatus  # 추천 산정에 사용된 목표 기준 (항상 SUFFICIENT="고갈 없음")
    depletion_age: int | None  # 개선 적용 후 자산 고갈 나이
    target_age: int  # 목표연령
    status: ReadinessStatus  # 개선 적용 후 노후 준비 상태
    timeline: list[TimelinePoint]  # 개선 적용 후 연도별 자산 추이


class ReductionRequest(DiagnosisRequest):
    """진단(diagnosis)과 동일한 입력 스키마를 재사용하고 재취업 관련 필드를 추가"""

    reemployment_income: float  # 재취업 예상 월소득 (만원)
    year: int | None = None  # 소득심사 기준 연도 (미지정 시 최신 규칙 적용)


class ReductionResult(BaseModel):
    current_age: int  # 현재 나이
    reemployment_income: float  # 재취업 예상 월소득 (만원)
    monthly_reduction: float  # 월 감액액 (만원)
    reduced_monthly_pension: float  # 감액 후 월 실수령 연금액 (만원)
    full_payment_income_threshold: float  # 전액 수령 가능 소득 상한 (만원)
    depletion_age: int | None  # 감액 반영 후 자산 고갈 나이
    target_age: int  # 목표연령
    status: ReadinessStatus  # 감액 반영 후 노후 준비 상태
    timeline: list[TimelinePoint]  # 감액 반영 후 연도별 자산 추이


class ScenariosRequest(DiagnosisRequest):
    """진단(diagnosis)과 동일한 입력 스키마를 재사용하고 수령방식 계산에 필요한 필드를 추가"""

    early_years: int = 5  # 조기수령 연수 (1~5년, 1년당 5% 감액)
    base_monthly_income: float  # 기준소득월액 (만원) - LUMP_SUM/SPLIT 공제일시금 산식에 사용
    total_service_years: int  # 총 재직연수 - LUMP_SUM/SPLIT 공제일시금 산식에 사용
    deduction_years: int | None = None  # SPLIT(분할수령) 공제연수. 미지정 시 제약 내 최댓값으로 클램프


class ScenarioType(str, Enum):
    """연금 수령방식"""

    NORMAL = "NORMAL"  # 정상수령
    EARLY = "EARLY"  # 조기수령 (감액)
    LUMP_SUM = "LUMP_SUM"  # 일시금수령
    INSTALLMENT = "INSTALLMENT"  # 분할수령 (일시금 + 월연금 혼합)


class ScenarioOutcome(BaseModel):
    scenario_type: ScenarioType  # 수령방식
    depletion_age: int  # 자산 고갈 나이 (고갈되지 않으면 MAX_AGE)
    total_received: float  # 총 수령액 (만원, current_age~MAX_AGE 동일 기간 기준)
    break_even_age: int | None  # NORMAL 대비 손익분기 나이 (이 나이 이상 생존 시 NORMAL이 유리해짐). NORMAL 자신은 None
    timeline: list[TimelinePoint]  # 연도별 자산 추이


class ScenariosResult(BaseModel):
    current_age: int  # 현재 나이
    scenarios: list[ScenarioOutcome]  # 수령방식별 결과
    best_scenario: ScenarioType  # 최적 수령방식
