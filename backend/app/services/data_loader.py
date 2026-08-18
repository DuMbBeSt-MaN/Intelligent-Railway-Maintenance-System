import json
from pathlib import Path
from app.core.config import DATA_DIR


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_scenario():
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
