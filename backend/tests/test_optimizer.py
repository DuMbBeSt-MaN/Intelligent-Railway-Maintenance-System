from app.services.data_loader import load_scenario
from app.services.optimizer import solve


def test_base_scenario_is_solvable():
    result = solve(load_scenario())
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}
    assert result["metrics"]["mandatory_scheduled"] == 4


def test_no_selected_jobs_overlap_on_same_track_or_crew_or_machine():
    result = solve(load_scenario())
    jobs = result["scheduled_jobs"]

    def overlaps(a, b):
        return a["start"] < b["end"] and b["start"] < a["end"]

    for i, a in enumerate(jobs):
        for b in jobs[i + 1:]:
            if not overlaps(a, b):
                continue
            assert a["track"] != b["track"]
            assert a["crew_id"] != b["crew_id"]
            if a["machine_id"] is not None:
                assert a["machine_id"] != b["machine_id"]
