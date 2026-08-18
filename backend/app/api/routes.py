from copy import deepcopy

from fastapi import APIRouter, HTTPException

from app.models.schemas import OptimizeRequest
from app.services.data_loader import list_scenarios, load_scenario
from app.services.optimizer import solve
from app.services.validator import validate_schedule

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/scenario")
def scenario():
    """Backward-compatible base scenario endpoint."""
    return load_scenario("base")


@router.get("/scenarios")
def scenarios():
    """List all predefined simulation scenarios."""
    return list_scenarios()


@router.get("/scenarios/{scenario_id}")
def scenario_by_id(scenario_id: str):
    """Return all raw data after applying a predefined scenario's events."""
    try:
        return load_scenario(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_id}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/optimize")
def optimize(request: OptimizeRequest):
    """Optimize the selected scenario. Defaults to the base scenario."""
    try:
        data = load_scenario(request.scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {request.scenario_id}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if request.injected_job:
        data = deepcopy(data)
        data["maintenance"]["jobs"].append(request.injected_job)

    result = solve(data)

    validation = validate_schedule(
        data,
        result["scheduled_jobs"],
    )

    result["scenario_id"] = request.scenario_id
    result["scenario_name"] = data["meta"].get("scenario_name", data["meta"].get("name"))
    result["validation"] = validation

    return result
