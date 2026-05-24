from fastapi import APIRouter, HTTPException

from app.schemas.employed import SimulateRequest, SimulateResponse
from app.services.employed_service import simulate_employed

router = APIRouter(prefix="/api/employed", tags=["employed"])


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    try:
        return simulate_employed(req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"CSV 파일을 찾을 수 없습니다: {exc.filename}")
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
