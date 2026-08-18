from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class OptimizeRequest(BaseModel):
    injected_job: Optional[Dict[str, Any]] = None


class ScheduledJob(BaseModel):
    job_id: str
    track: str
    start: int
    end: int
    crew_id: str
    machine_id: Optional[str] = None
    possession_id: str


class OptimizeResponse(BaseModel):
    status: str
    objective_value: Optional[float] = None
    scheduled_jobs: List[ScheduledJob]
    unscheduled_jobs: List[str]
    metrics: Dict[str, Any]
