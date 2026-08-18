from __future__ import annotations

from typing import Any, Dict, List


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def within_any_window(
    start: int,
    end: int,
    windows: List[dict],
) -> bool:
    return any(
        start >= window["start"] and end <= window["end"]
        for window in windows
    )


def validate_schedule(
    data: dict,
    scheduled_jobs: List[dict],
) -> dict:

    violations = []

    jobs = {
        job["id"]: job
        for job in data["maintenance"]["jobs"]
    }

    crews = {
        crew["id"]: crew
        for crew in data["crews"]["crews"]
    }

    machines = {
        machine["id"]: machine
        for machine in data["machines"]["machines"]
    }

    possessions = data["possessions"]["possessions"]

    possession_by_id = {
        possession["id"]: possession
        for possession in possessions
    }

    # ---------------------------------------------------------
    # 1. CHECK EVERY SCHEDULED JOB
    # ---------------------------------------------------------

    for scheduled in scheduled_jobs:

        job_id = scheduled["job_id"]

        if job_id not in jobs:
            violations.append({
                "type": "UNKNOWN_JOB",
                "job_id": job_id,
                "message": f"Job {job_id} does not exist.",
            })
            continue

        job = jobs[job_id]

        start = scheduled["start"]
        end = scheduled["end"]
        track = scheduled["track"]

        # Duration
        expected_end = start + job["duration"]

        if end != expected_end:
            violations.append({
                "type": "DURATION",
                "job_id": job_id,
                "message": (
                    f"{job_id} has invalid duration. "
                    f"Expected end {expected_end}, got {end}."
                ),
            })

        # Earliest start
        if start < job["earliest_start"]:
            violations.append({
                "type": "EARLIEST_START",
                "job_id": job_id,
                "message": (
                    f"{job_id} starts before its earliest "
                    "allowed start."
                ),
            })

        # Deadline
        if end > job["deadline"]:
            violations.append({
                "type": "DEADLINE",
                "job_id": job_id,
                "message": (
                    f"{job_id} finishes after its deadline."
                ),
            })

        # Possession
        possession = possession_by_id.get(
            scheduled["possession_id"]
        )

        if possession is None:
            violations.append({
                "type": "POSSESSION",
                "job_id": job_id,
                "message": (
                    f"Possession {scheduled['possession_id']} "
                    "does not exist."
                ),
            })
        else:

            if track not in possession["tracks"]:
                violations.append({
                    "type": "POSSESSION_TRACK",
                    "job_id": job_id,
                    "message": (
                        f"Track {track} is not included in "
                        f"possession {possession['id']}."
                    ),
                })

            if not (
                start >= possession["start"]
                and end <= possession["end"]
            ):
                violations.append({
                    "type": "POSSESSION_WINDOW",
                    "job_id": job_id,
                    "message": (
                        f"{job_id} is outside its possession "
                        "window."
                    ),
                })

        # Crew
        crew_id = scheduled["crew_id"]

        crew = crews.get(crew_id)

        if crew is None:
            violations.append({
                "type": "CREW",
                "job_id": job_id,
                "message": f"Crew {crew_id} does not exist.",
            })
        else:

            if job["required_skill"] not in crew["skills"]:
                violations.append({
                    "type": "CREW_SKILL",
                    "job_id": job_id,
                    "message": (
                        f"Crew {crew_id} does not have the "
                        f"required skill "
                        f"{job['required_skill']}."
                    ),
                })

            if not within_any_window(
                start,
                end,
                crew["available"],
            ):
                violations.append({
                    "type": "CREW_AVAILABILITY",
                    "job_id": job_id,
                    "message": (
                        f"Crew {crew_id} is not available "
                        "for the complete job."
                    ),
                })

        # Machine
        machine_id = scheduled.get("machine_id")

        required_machine_type = job.get(
            "required_machine_type"
        )

        if required_machine_type is not None:

            if machine_id is None:
                violations.append({
                    "type": "MACHINE",
                    "job_id": job_id,
                    "message": (
                        f"{job_id} requires a machine but "
                        "none was assigned."
                    ),
                })

            elif machine_id not in machines:
                violations.append({
                    "type": "MACHINE",
                    "job_id": job_id,
                    "message": (
                        f"Machine {machine_id} does not exist."
                    ),
                })

            else:
                machine = machines[machine_id]

                if machine["type"] != required_machine_type:
                    violations.append({
                        "type": "MACHINE_TYPE",
                        "job_id": job_id,
                        "message": (
                            f"Machine {machine_id} has type "
                            f"{machine['type']}, but "
                            f"{job_id} requires "
                            f"{required_machine_type}."
                        ),
                    })

                if not within_any_window(
                    start,
                    end,
                    machine["available"],
                ):
                    violations.append({
                        "type": "MACHINE_AVAILABILITY",
                        "job_id": job_id,
                        "message": (
                            f"Machine {machine_id} is not "
                            "available for the complete job."
                        ),
                    })

    # ---------------------------------------------------------
    # 2. TRAIN CONFLICTS
    # ---------------------------------------------------------

    for train in data["trains"]["trains"]:

        for occupancy in train["occupancies"]:

            for scheduled in scheduled_jobs:

                if scheduled["track"] != occupancy["track"]:
                    continue

                if overlaps(
                    scheduled["start"],
                    scheduled["end"],
                    occupancy["start"],
                    occupancy["end"],
                ):
                    violations.append({
                        "type": "TRAIN_CONFLICT",
                        "job_id": scheduled["job_id"],
                        "message": (
                            f"{scheduled['job_id']} overlaps "
                            f"train {train['id']} on "
                            f"{occupancy['track']}."
                        ),
                    })

    # ---------------------------------------------------------
    # 3. JOB-TO-JOB RESOURCE CONFLICTS
    # ---------------------------------------------------------

    for i, first in enumerate(scheduled_jobs):

        for second in scheduled_jobs[i + 1:]:

            if not overlaps(
                first["start"],
                first["end"],
                second["start"],
                second["end"],
            ):
                continue

            # Same track
            if first["track"] == second["track"]:
                violations.append({
                    "type": "TRACK_CONFLICT",
                    "job_id": first["job_id"],
                    "message": (
                        f"{first['job_id']} overlaps "
                        f"{second['job_id']} on track "
                        f"{first['track']}."
                    ),
                })

            # Same crew
            if first["crew_id"] == second["crew_id"]:
                violations.append({
                    "type": "CREW_CONFLICT",
                    "job_id": first["job_id"],
                    "message": (
                        f"Crew {first['crew_id']} is assigned "
                        f"to overlapping jobs "
                        f"{first['job_id']} and "
                        f"{second['job_id']}."
                    ),
                })

            # Same machine
            first_machine = first.get("machine_id")
            second_machine = second.get("machine_id")

            if (
                first_machine is not None
                and first_machine == second_machine
            ):
                violations.append({
                    "type": "MACHINE_CONFLICT",
                    "job_id": first["job_id"],
                    "message": (
                        f"Machine {first_machine} is assigned "
                        f"to overlapping jobs."
                    ),
                })

    # ---------------------------------------------------------
    # 4. MANDATORY JOB CHECK
    # ---------------------------------------------------------

    scheduled_ids = {
        job["job_id"]
        for job in scheduled_jobs
    }

    for job in data["maintenance"]["jobs"]:

        if job["mandatory"] and job["id"] not in scheduled_ids:
            violations.append({
                "type": "MANDATORY_UNSCHEDULED",
                "job_id": job["id"],
                "message": (
                    f"Mandatory job {job['id']} was not scheduled."
                ),
            })

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    violation_types = {
        "TRAIN_CONFLICT",
        "TRACK_CONFLICT",
        "CREW_CONFLICT",
        "MACHINE_CONFLICT",
        "CREW_SKILL",
        "CREW_AVAILABILITY",
        "MACHINE_AVAILABILITY",
        "MACHINE_TYPE",
        "POSSESSION",
        "POSSESSION_TRACK",
        "POSSESSION_WINDOW",
        "EARLIEST_START",
        "DEADLINE",
        "DURATION",
        "MANDATORY_UNSCHEDULED",
        "UNKNOWN_JOB",
        "CREW",
        "MACHINE",
    }

    counts = {
        violation_type: sum(
            1
            for violation in violations
            if violation["type"] == violation_type
        )
        for violation_type in sorted(violation_types)
    }

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "violation_count": len(violations),
        "violation_counts": counts,
    }