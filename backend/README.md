# RailGuard Backend Starter

A small proof-of-concept backend for **railway maintenance scheduling and possession opportunity use**.

The data is synthetic, but its schema and concepts are inspired by real/open railway resources:

- **OSRD / RailJSON**: railway infrastructure, timetables, simulation and conflict detection.
- **railML 3.3**: infrastructure/timetable interchange and possession-management concepts.
- **Network Rail EAS/TPR**: engineering-access windows and timetable-planning rules.
- **Google OR-Tools CP-SAT**: constraint-programming scheduler.

This is **not official Indian Railways operational data**. The station/section names are used only to make the demo intuitive; train movements, crew rosters, possessions and maintenance jobs are synthetic.

## Project structure

```text
railguard-backend/
├── app/
│   ├── api/routes.py
│   ├── core/config.py
│   ├── models/schemas.py
│   ├── services/data_loader.py
│   ├── services/optimizer.py
│   └── main.py
├── data/
│   ├── scenario.json
│   ├── infrastructure.json
│   ├── trains.json
│   ├── possessions.json
│   ├── crews.json
│   ├── machines.json
│   └── maintenance.json
├── tests/test_optimizer.py
├── requirements.txt
└── run_demo.py
```

## Setup

Python 3.11 or 3.12 is recommended.

```bash
cd railguard-backend
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the optimiser without a web server

```bash
python run_demo.py
```

## Run FastAPI

```bash
uvicorn app.main:app --reload
```

Open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

Useful endpoints:

- `GET /api/health`
- `GET /api/scenario`
- `POST /api/optimize`

Basic optimisation request:

```json
{}
```

You can also inject a new urgent maintenance job without editing the JSON files:

```json
{
  "injected_job": {
    "id": "EMG001",
    "track": "BBQ_PER_UP",
    "work_type": "track_inspection",
    "duration": 30,
    "earliest_start": 1660,
    "deadline": 1740,
    "priority": 10,
    "mandatory": true,
    "required_skill": "track_inspection",
    "required_machine_type": null,
    "preferred_start": 1660,
    "existing_start": null,
    "bundle_group": "BBQ_PER"
  }
}
```

## What the current optimiser enforces

1. Mandatory maintenance jobs must be scheduled.
2. Work must be inside a valid engineering possession/access window.
3. Maintenance cannot overlap a fixed train occupancy on the same track.
4. A crew cannot perform two jobs at once.
5. A machine cannot perform two jobs at once.
6. Crew must have the required skill and be on shift.
7. Required machine type must be available.
8. Optional jobs are rewarded based on priority, encouraging the solver to use spare possession capacity.
9. Moving an already-planned job away from its existing start is penalised.

## Deliberately NOT implemented yet

This starter does **not** yet delay or reroute trains. Trains are hard, fixed occupancies. Therefore it finds maintenance around trains rather than calculating passenger delay itself.

That should be the next modelling upgrade:

- train delay decision variables;
- passenger/freight disruption cost;
- adjacent-track safety restrictions;
- crew travel times;
- task precedence;
- possession setup/handback times;
- explicit maintenance-debt/bundling objective;
- multiple Pareto-style recovery plans;
- deterministic explanation engine.

Only after that should you add ML for uncertain inputs such as job duration or overrun probability.
