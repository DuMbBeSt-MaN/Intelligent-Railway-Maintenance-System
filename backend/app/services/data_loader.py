import json
from copy import deepcopy
from pathlib import Path
from app.core.config import DATA_DIR


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_base_scenario():
    scenario = _read_json(DATA_DIR / "scenario.json")
    files = scenario["files"]
    return {
        "meta": scenario,
        "infrastructure": _read_json(DATA_DIR / files["infrastructure"]),
        "trains": _read_json(DATA_DIR / files["trains"]),
        "possessions": _read_json(DATA_DIR / files["possessions"]),
        "crews": _read_json(DATA_DIR / files["crews"]),
        "machines": _read_json(DATA_DIR / files["machines"]),
        "maintenance": _read_json(DATA_DIR / files["maintenance"]),
    }


def list_scenarios():
    registry = _read_json(DATA_DIR / "scenarios.json")
    return {
        "default_scenario_id": registry["default_scenario_id"],
        "scenarios": [
            {
                "id": item["id"],
                "name": item["name"],
                "description": item["description"],
            }
            for item in registry["scenarios"]
        ],
    }


def _subtract_window(windows, blocked_start: int, blocked_end: int):
    remaining = []
    for window in windows:
        start = window["start"]
        end = window["end"]

        if blocked_end <= start or blocked_start >= end:
            remaining.append(window)
            continue

        if start < blocked_start:
            remaining.append({"start": start, "end": blocked_start})
        if blocked_end < end:
            remaining.append({"start": blocked_end, "end": end})

    return remaining


def _apply_event(data: dict, event: dict):
    event_type = event["type"]

    if event_type == "inject_job":
        data["maintenance"]["jobs"].append(deepcopy(event["job"]))
        return

    if event_type == "crew_unavailable":
        for crew in data["crews"]["crews"]:
            if crew["id"] == event["crew_id"]:
                crew["available"] = _subtract_window(
                    crew["available"], event["start"], event["end"]
                )
                return
        raise ValueError(f"Unknown crew: {event['crew_id']}")

    if event_type == "machine_unavailable":
        for machine in data["machines"]["machines"]:
            if machine["id"] == event["machine_id"]:
                machine["available"] = _subtract_window(
                    machine["available"], event["start"], event["end"]
                )
                return
        raise ValueError(f"Unknown machine: {event['machine_id']}")

    if event_type == "shorten_possession":
        for possession in data["possessions"]["possessions"]:
            if possession["id"] == event["possession_id"]:
                possession["start"] = event["new_start"]
                possession["end"] = event["new_end"]
                return
        raise ValueError(f"Unknown possession: {event['possession_id']}")

    raise ValueError(f"Unsupported scenario event type: {event_type}")


def load_scenario(scenario_id: str = "base"):
    registry = _read_json(DATA_DIR / "scenarios.json")
    definition = next(
        (item for item in registry["scenarios"] if item["id"] == scenario_id),
        None,
    )

    if definition is None:
        raise KeyError(scenario_id)

    data = deepcopy(load_base_scenario())
    data["meta"] = deepcopy(data["meta"])
    data["meta"]["scenario_id"] = definition["id"]
    data["meta"]["scenario_name"] = definition["name"]
    data["meta"]["scenario_description"] = definition["description"]
    data["meta"]["events"] = deepcopy(definition["events"])

    for event in definition["events"]:
        _apply_event(data, event)

    return data
