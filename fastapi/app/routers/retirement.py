from fastapi import APIRouter

from app.schemas.retirement import (
    DiagnosisRequest,
    RecommendationRequest,
    RecommendationResult,
    ReductionRequest,
    ReductionResult,
    ScenariosRequest,
    ScenariosResult,
    SimulationResult,
)
from app.services.retirement_service import (
    diagnose_core,
    recommend_retirement,
    simulate_pension_reduction,
    simulate_scenarios,
)

router = APIRouter(prefix="/api/retirement", tags=["retirement"])


@router.post(
    "/diagnosis",
    response_model=SimulationResult,
    summary="은퇴 자산 진단",
    description="현재 나이, 월 생활비, 월 연금, 자산, 성별로 자산 고갈 시점과 노후 준비 상태를 계산",
)
def diagnose(req: DiagnosisRequest) -> SimulationResult:
    return diagnose_core(
        current_age=req.current_age,
        monthly_expenses=req.monthly_expenses,
        monthly_pension=req.monthly_pension,
        asset=req.asset,
        gender=req.gender,
    )


@router.post(
    "/recommendations",
    response_model=RecommendationResult,
    summary="은퇴 자산 준비 추천",
    description="MIDDLE/INSUFFICIENT 판정 시 목표연령 도달에 필요한 최소 절약액/추가소득액을 계산",
)
def recommend(req: RecommendationRequest) -> RecommendationResult:
    return recommend_retirement(
        current_age=req.current_age,
        monthly_expenses=req.monthly_expenses,
        monthly_pension=req.monthly_pension,
        asset=req.asset,
        gender=req.gender,
    )


@router.post(
    "/reduction",
    response_model=ReductionResult,
    summary="재취업 소득에 따른 연금 감액 계산",
    description="재취업 예상 월소득에 소득심사 감액 규칙을 적용해 월 감액액과 감액 반영 timeline을 계산",
)
def reduction(req: ReductionRequest) -> ReductionResult:
    return simulate_pension_reduction(
        current_age=req.current_age,
        monthly_expenses=req.monthly_expenses,
        monthly_pension=req.monthly_pension,
        asset=req.asset,
        gender=req.gender,
        reemployment_income=req.reemployment_income,
        year=req.year,
    )


@router.post(
    "/scenarios",
    response_model=ScenariosResult,
    summary="연금 수령방식 시나리오 비교",
    description="정상/조기/일시금/분할 4가지 연금 수령방식별 고갈 나이와 총 수령액을 비교하고 최적 방식을 추천",
)
def scenarios(req: ScenariosRequest) -> ScenariosResult:
    return simulate_scenarios(
        current_age=req.current_age,
        monthly_expenses=req.monthly_expenses,
        monthly_pension=req.monthly_pension,
        asset=req.asset,
        gender=req.gender,
        base_monthly_income=req.base_monthly_income,
        total_service_years=req.total_service_years,
        early_years=req.early_years,
        deduction_years=req.deduction_years,
    )
