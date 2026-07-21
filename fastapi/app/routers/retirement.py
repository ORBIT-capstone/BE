from fastapi import APIRouter, HTTPException

from app.schemas.retirement import (
    DiagnosisRequest,
    RecommendationRequest,
    RecommendationResult,
    SimulationResult,
)
from app.services.retirement_service import diagnose_core, recommend_retirement

router = APIRouter(prefix="/api/retirement", tags=["retirement"])


@router.post(
    "/diagnosis",
    response_model=SimulationResult,
    summary="은퇴 자산 진단",
    description="현재 나이, 월 생활비, 월 연금, 자산, 성별로 자산 고갈 시점과 노후 준비 상태를 계산",
)
def diagnose(req: DiagnosisRequest) -> SimulationResult:
    try:
        return diagnose_core(
            current_age=req.current_age,
            monthly_expenses=req.monthly_expenses,
            monthly_pension=req.monthly_pension,
            asset=req.asset,
            gender=req.gender,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/recommendations",
    response_model=RecommendationResult,
    summary="은퇴 자산 준비 추천",
    description="MIDDLE/INSUFFICIENT 판정 시 목표연령 도달에 필요한 최소 절약액/추가소득액을 계산",
)
def recommend(req: RecommendationRequest) -> RecommendationResult:
    try:
        return recommend_retirement(
            current_age=req.current_age,
            monthly_expenses=req.monthly_expenses,
            monthly_pension=req.monthly_pension,
            asset=req.asset,
            gender=req.gender,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
