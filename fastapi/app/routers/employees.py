from fastapi import APIRouter

from app.schemas.employees import SimulateRequest, SimulateResponse
from app.services.employees_service import simulate_employees

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    summary="재직자 연금 시뮬레이션",
    description="현재 나이, 은퇴 예정 나이, 현재 소득, 현재 근속연수로 예상 연금과 퇴직금을 계산",
)
def simulate(req: SimulateRequest) -> SimulateResponse:
    return simulate_employees(req)
