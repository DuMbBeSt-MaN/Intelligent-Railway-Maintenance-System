# RailGuard Backend

A proof-of-concept decision-support backend for **railway maintenance scheduling, possession utilization, and schedule validation**.

RailGuard takes a synthetic railway scenario containing:

- infrastructure and tracks;
- train occupancies;
- engineering possessions;
- maintenance jobs;
- maintenance crews;
- maintenance machines;

and generates an optimized maintenance schedule using **Google OR-Tools CP-SAT**.

The generated schedule is then independently checked by a validation layer before being returned through the FastAPI API.

> **Important:** This project uses synthetic demonstration data. It is not official Indian Railways operational data.

---

## System Overview

RailGuard follows a two-stage decision pipeline:

```text
                 Railway Scenario
                        │
                        ▼
                 Data Loader
                        │
                        ▼
              ┌─────────────────┐
              │ OR-Tools CP-SAT  │
              │    Optimizer     │
              └────────┬────────┘
                       │
                       ▼
               Proposed Schedule
                       │
                       ▼
              ┌─────────────────┐
              │    Validator    │
              │                 │
              │ Hard-rule audit │
              └────────┬────────┘
                       │
                       ▼
          Validated Optimization Result
                       │
                       ▼
                  FastAPI API
                       │
                       ▼
                Frontend Dashboard
```
