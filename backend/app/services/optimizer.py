from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from ortools.sat.python import cp_model


@dataclass(frozen=True)
class Candidate:
    job_id: str
    track: str
    start: int
    end: int
    crew_id: str
    machine_id: Optional[str]
    possession_id: str
    cost: int


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def within_any_window(start: int, end: int, windows: List[dict]) -> bool:
    return any(start >= w["start"] and end <= w["end"] for w in windows)


def build_train_occupancy(trains: List[dict]) -> Dict[str, List[Tuple[int, int, str]]]:
    occupancy: Dict[str, List[Tuple[int, int, str]]] = {}
    for train in trains:
        for occ in train["occupancies"]:
            occupancy.setdefault(occ["track"], []).append((occ["start"], occ["end"], train["id"]))
    return occupancy


def generate_candidates(data: dict) -> Tuple[Dict[str, List[Candidate]], Dict[str, dict]]:
    jobs = list(data["maintenance"]["jobs"])
    crews = data["crews"]["crews"]
    machines = data["machines"]["machines"]
    possessions = data["possessions"]["possessions"]
    trains = data["trains"]["trains"]
    step = data["meta"]["optimizer"]["time_step_minutes"]
    weights = data["meta"]["optimizer"]["weights"]

    job_by_id = {j["id"]: j for j in jobs}
    train_occ = build_train_occupancy(trains)

    possession_by_track: Dict[str, List[dict]] = {}
    for p in possessions:
        for track in p["tracks"]:
            possession_by_track.setdefault(track, []).append(p)

    eligible_crews: Dict[str, List[dict]] = {}
    for job in jobs:
        eligible_crews[job["id"]] = [c for c in crews if job["required_skill"] in c["skills"]]

    eligible_machines: Dict[str, List[Optional[dict]]] = {}
    for job in jobs:
        mtype = job.get("required_machine_type")
        if mtype is None:
            eligible_machines[job["id"]] = [None]
        else:
            eligible_machines[job["id"]] = [m for m in machines if m["type"] == mtype]

    candidates: Dict[str, List[Candidate]] = {j["id"]: [] for j in jobs}

    for job in jobs:
        track = job["track"]
        duration = job["duration"]
        earliest = job["earliest_start"]
        deadline = job["deadline"]
        track_possessions = possession_by_track.get(track, [])

        for p in track_possessions:
            min_start = max(earliest, p["start"])
            max_start = min(deadline - duration, p["end"] - duration)
            if min_start > max_start:
                continue

            aligned_start = ((min_start + step - 1) // step) * step
            for start in range(aligned_start, max_start + 1, step):
                end = start + duration

                if any(overlaps(start, end, t0, t1) for t0, t1, _ in train_occ.get(track, [])):
                    continue

                for crew in eligible_crews[job["id"]]:
                    if not within_any_window(start, end, crew["available"]):
                        continue

                    for machine in eligible_machines[job["id"]]:
                        if machine is not None and not within_any_window(start, end, machine["available"]):
                            continue

                        preferred = job.get("preferred_start")
                        existing = job.get("existing_start")
                        cost = 0
                        if preferred is not None:
                            cost += abs(start - preferred) * weights["preferred_start_deviation_per_minute"]
                        if existing is not None:
                            cost += abs(start - existing) * weights["schedule_change_per_minute"]

                        candidates[job["id"]].append(
                            Candidate(
                                job_id=job["id"],
                                track=track,
                                start=start,
                                end=end,
                                crew_id=crew["id"],
                                machine_id=None if machine is None else machine["id"],
                                possession_id=p["id"],
                                cost=cost,
                            )
                        )

    return candidates, job_by_id


def solve(data: dict) -> dict:
    candidates, job_by_id = generate_candidates(data)
    model = cp_model.CpModel()
    weights = data["meta"]["optimizer"]["weights"]

    x: Dict[Tuple[str, int], cp_model.IntVar] = {}
    for job_id, options in candidates.items():
        for idx, _ in enumerate(options):
            x[(job_id, idx)] = model.NewBoolVar(f"x_{job_id}_{idx}")

    # Each mandatory job must be placed exactly once. Optional jobs may be skipped.
    for job_id, job in job_by_id.items():
        vars_for_job = [x[(job_id, i)] for i in range(len(candidates[job_id]))]
        if job["mandatory"]:
            if not vars_for_job:
                return {
                    "status": "INFEASIBLE",
                    "objective_value": None,
                    "scheduled_jobs": [],
                    "unscheduled_jobs": [job_id],
                    "metrics": {"reason": f"Mandatory job {job_id} has no feasible candidate placements before optimisation."},
                }
            model.Add(sum(vars_for_job) == 1)
        else:
            model.Add(sum(vars_for_job) <= 1)

    # Pairwise resource/track incompatibilities.
    flat: List[Tuple[str, int, Candidate]] = []
    for job_id, options in candidates.items():
        for idx, c in enumerate(options):
            flat.append((job_id, idx, c))

    for a in range(len(flat)):
        j1, i1, c1 = flat[a]
        for b in range(a + 1, len(flat)):
            j2, i2, c2 = flat[b]
            if j1 == j2:
                continue
            if not overlaps(c1.start, c1.end, c2.start, c2.end):
                continue

            same_track = c1.track == c2.track
            same_crew = c1.crew_id == c2.crew_id
            same_machine = c1.machine_id is not None and c1.machine_id == c2.machine_id
            if same_track or same_crew or same_machine:
                model.Add(x[(j1, i1)] + x[(j2, i2)] <= 1)

    objective_terms = []
    for job_id, options in candidates.items():
        job = job_by_id[job_id]
        for idx, c in enumerate(options):
            objective_terms.append(c.cost * x[(job_id, idx)])

        # Strongly reward scheduling optional work, weighted by priority. This also
        # encourages opportunistic use of possession windows when resources permit.
        if not job["mandatory"]:
            scheduled = sum(x[(job_id, i)] for i in range(len(options)))
            objective_terms.append(-weights["unscheduled_priority"] * job["priority"] * scheduled)

    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    status_name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": status_name,
            "objective_value": None,
            "scheduled_jobs": [],
            "unscheduled_jobs": list(job_by_id.keys()),
            "metrics": {},
        }

    scheduled = []
    scheduled_ids = set()
    for job_id, options in candidates.items():
        for idx, c in enumerate(options):
            if solver.Value(x[(job_id, idx)]) == 1:
                scheduled_ids.add(job_id)
                scheduled.append({
                    "job_id": c.job_id,
                    "track": c.track,
                    "start": c.start,
                    "end": c.end,
                    "crew_id": c.crew_id,
                    "machine_id": c.machine_id,
                    "possession_id": c.possession_id,
                })

    scheduled.sort(key=lambda r: (r["start"], r["track"]))
    unscheduled = [jid for jid in job_by_id if jid not in scheduled_ids]
    optional_scheduled = sum(1 for jid in scheduled_ids if not job_by_id[jid]["mandatory"])
    mandatory_scheduled = sum(1 for jid in scheduled_ids if job_by_id[jid]["mandatory"])

    return {
        "status": status_name,
        "objective_value": solver.ObjectiveValue(),
        "scheduled_jobs": scheduled,
        "unscheduled_jobs": unscheduled,
        "metrics": {
            "jobs_total": len(job_by_id),
            "jobs_scheduled": len(scheduled_ids),
            "mandatory_scheduled": mandatory_scheduled,
            "optional_scheduled": optional_scheduled,
            "candidate_placements": sum(len(v) for v in candidates.values()),
            "solver_wall_time_seconds": solver.WallTime(),
        },
    }
