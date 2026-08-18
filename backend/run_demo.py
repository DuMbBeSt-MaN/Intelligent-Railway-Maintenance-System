import json
from app.services.data_loader import load_scenario
from app.services.optimizer import solve


def hhmm(minute: int) -> str:
    day = minute // 1440
    m = minute % 1440
    label = f"{m // 60:02d}:{m % 60:02d}"
    return label if day == 0 else f"+{day}d {label}"


if __name__ == "__main__":
    result = solve(load_scenario())
    print(f"Status: {result['status']}")
    print(f"Objective: {result['objective_value']}")
    print()
    for job in result["scheduled_jobs"]:
        print(
            f"{job['job_id']:>4} | {job['track']:<12} | "
            f"{hhmm(job['start'])} - {hhmm(job['end'])} | "
            f"crew={job['crew_id']:<10} machine={job['machine_id'] or '-'}"
        )
    print("\nMetrics:")
    print(json.dumps(result["metrics"], indent=2))
    print("Unscheduled:", result["unscheduled_jobs"])
