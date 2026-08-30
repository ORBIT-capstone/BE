from fastapi import APIRouter

from app.schemas.employees import SimulateRequest, SimulateResponse
from app.schemas.retirement import ScenariosRequest, ScenariosResult
from app.services.employees_service import simulate_employees
from app.services.retirement_service import simulate_scenarios

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    summary="재직자 연금 시뮬레이션",
    description="현재 나이, 은퇴 예정 나이, 현재 소득, 현재 근속연수로 예상 연금과 퇴직금을 계산",
)
def simulate(req: SimulateRequest) -> SimulateResponse:
    return simulate_employees(req)


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
