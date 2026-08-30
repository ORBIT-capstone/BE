from fastapi import APIRouter

from app.schemas.retirement import (
    DiagnosisRequest,
    RecommendationRequest,
    RecommendationResult,
    ReductionRequest,
    ReductionResult,
    SimulationResult,
)
from app.services.retirement_service import (
    diagnose_core,
    recommend_retirement,
    simulate_pension_reduction,
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
    description="재취업 예상 월소득에 2025년 소득심사 감액 규칙을 고정 적용해 월 감액액과 감액 반영 timeline을 계산",
)
def reduction(req: ReductionRequest) -> ReductionResult:
    return simulate_pension_reduction(
        current_age=req.current_age,
        monthly_expenses=req.monthly_expenses,
        monthly_pension=req.monthly_pension,
        asset=req.asset,
        gender=req.gender,
        reemployment_income=req.reemployment_income,
    )
