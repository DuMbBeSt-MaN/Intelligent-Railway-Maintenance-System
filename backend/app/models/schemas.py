from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class OptimizeRequest(BaseModel):
    scenario_id: str = "base"
    injected_job: Optional[Dict[str, Any]] = None


class ScheduledJob(BaseModel):
    job_id: str
    track: str
    start: int
    end: int
    crew_id: str
    machine_id: Optional[str] = None
    possession_id: str


class OptimizationSummary(BaseModel):
    jobs_total: int
    jobs_scheduled: int
    mandatory_scheduled: int
    optional_scheduled: int
    jobs_unscheduled: int


class ValidationResult(BaseModel):
    valid: bool
    violations: List[Any]
    violation_count: int
    violation_counts: Dict[str, int]


class OptimizeResponse(BaseModel):
    status: str
    objective_value: Optional[float] = None

    summary: OptimizationSummary

    scheduled_jobs: List[ScheduledJob]
    unscheduled_jobs: List[str]
    metrics: Dict[str, Any]

    validation: ValidationResult
