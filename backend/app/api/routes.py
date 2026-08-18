from copy import deepcopy
from fastapi import APIRouter
from app.models.schemas import OptimizeRequest, OptimizeResponse
from app.services.data_loader import load_scenario
from app.services.optimizer import solve

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/scenario")
def scenario():
    return load_scenario()


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(request: OptimizeRequest):
    data = load_scenario()
    if request.injected_job:
        data = deepcopy(data)
        data["maintenance"]["jobs"].append(request.injected_job)
    return solve(data)
