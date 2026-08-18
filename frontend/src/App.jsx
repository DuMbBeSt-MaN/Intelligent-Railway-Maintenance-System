import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function formatTime(minutes) {
  const day = Math.floor(minutes / 1440);
  const minuteOfDay = minutes % 1440;
  const hours = Math.floor(minuteOfDay / 60);
  const mins = minuteOfDay % 60;

  return `${day > 0 ? `D+${day} ` : ""}${String(hours).padStart(
    2,
    "0"
  )}:${String(mins).padStart(2, "0")}`;
}

function App() {
  const [result, setResult] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [scenarioOptions, setScenarioOptions] = useState([]);
  const [activeScenarioId, setActiveScenarioId] = useState("base");
  const [pendingScenarioId, setPendingScenarioId] = useState("base");
  const [scenarioDialogOpen, setScenarioDialogOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const activeScenario = useMemo(
    () => scenarioOptions.find((item) => item.id === activeScenarioId),
    [scenarioOptions, activeScenarioId]
  );

  async function loadAndOptimizeScenario(scenarioId) {
    try {
      setLoading(true);
      setError(null);

      const scenarioResponse = await fetch(
        `${API_URL}/api/scenarios/${scenarioId}`
      );

      if (!scenarioResponse.ok) {
        throw new Error(`Could not load scenario: ${scenarioResponse.status}`);
      }

      const scenarioData = await scenarioResponse.json();
      setScenario(scenarioData);

      const optimizeResponse = await fetch(`${API_URL}/api/optimize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ scenario_id: scenarioId }),
      });

      if (!optimizeResponse.ok) {
        throw new Error(`Optimization failed: ${optimizeResponse.status}`);
      }

      const optimizationData = await optimizeResponse.json();
      setResult(optimizationData);
      setActiveScenarioId(scenarioId);
      setPendingScenarioId(scenarioId);

      if (optimizationData.scheduled_jobs?.length) {
        setSelectedJob(optimizationData.scheduled_jobs[0]);
      } else {
        setSelectedJob(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function runOptimization() {
    await loadAndOptimizeScenario(activeScenarioId);
  }

  function openScenarioDialog(preselectedId = activeScenarioId) {
    setPendingScenarioId(preselectedId);
    setScenarioDialogOpen(true);
  }

  async function applySelectedScenario() {
    setScenarioDialogOpen(false);
    await loadAndOptimizeScenario(pendingScenarioId);
  }

  useEffect(() => {
    async function initialize() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_URL}/api/scenarios`);

        if (!response.ok) {
          throw new Error("Could not load scenario list");
        }

        const data = await response.json();
        const options = data.scenarios ?? [];
        const defaultScenarioId = data.default_scenario_id ?? "base";

        setScenarioOptions(options);
        setActiveScenarioId(defaultScenarioId);
        setPendingScenarioId(defaultScenarioId);

        await loadAndOptimizeScenario(defaultScenarioId);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }

    initialize();
  }, []);

  const tracks = useMemo(() => {
    if (!result?.scheduled_jobs) return [];

    return [...new Set(result.scheduled_jobs.map((job) => job.track))];
  }, [result]);

  const maxTime = useMemo(() => {
    if (!result?.scheduled_jobs?.length) return 1800;

    return Math.max(...result.scheduled_jobs.map((job) => job.end));
  }, [result]);

  const minTime = useMemo(() => {
    if (!result?.scheduled_jobs?.length) return 1400;

    return Math.min(...result.scheduled_jobs.map((job) => job.start));
  }, [result]);

  function position(start) {
    if (maxTime === minTime) return 0;
    return ((start - minTime) / (maxTime - minTime)) * 100;
  }

  function width(start, end) {
    if (maxTime === minTime) return 100;
    return ((end - start) / (maxTime - minTime)) * 100;
  }

  const violations =
    result?.validation?.violation_count ??
    result?.validation?.violations?.length ??
    0;

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="brand">
            <span className="brand-mark">R</span>
            <div>
              <h1>RAILOPS</h1>
              <p>Intelligent Railway Maintenance Optimizer</p>
            </div>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          SYSTEM OPERATIONAL
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <strong>Backend connection error:</strong> {error}
          <button onClick={runOptimization}>Retry</button>
        </div>
      )}

      <main>
        <section className="hero">
          <div>
            <span className="eyebrow">NETWORK CONTROL CENTER</span>
            <h2>Maintenance Command Dashboard</h2>
            <p>
              Optimize railway maintenance around infrastructure, crews,
              machines, possessions and train occupancy.
            </p>
            <div className="active-scenario">
              <span>ACTIVE SCENARIO</span>
              <strong>{activeScenario?.name ?? result?.scenario_name ?? "Base"}</strong>
              {activeScenario?.description && <small>{activeScenario.description}</small>}
            </div>
          </div>

          <div className="hero-actions">
            <button
              className="scenario-button"
              onClick={() => openScenarioDialog()}
              disabled={loading}
            >
              CHOOSE SCENARIO
            </button>
            <button
              className="optimize-button"
              onClick={runOptimization}
              disabled={loading}
            >
              {loading ? "OPTIMIZING..." : "↻ RE-OPTIMIZE"}
            </button>
          </div>
        </section>

        <section className="stats-grid">
          <StatCard
            label="PLAN STATUS"
            value={loading ? "..." : result?.status ?? "—"}
            detail="CP-SAT solver result"
            good={result?.status === "OPTIMAL" || result?.status === "FEASIBLE"}
          />

          <StatCard
            label="JOBS SCHEDULED"
            value={
              loading
                ? "..."
                : `${result?.summary?.jobs_scheduled ?? 0} / ${
                    result?.summary?.jobs_total ?? result?.metrics?.jobs_total ?? 0
                  }`
            }
            detail={`${result?.summary?.mandatory_scheduled ?? result?.metrics?.mandatory_scheduled ?? 0} mandatory · ${
              result?.summary?.optional_scheduled ?? result?.metrics?.optional_scheduled ?? 0
            } optional`}
            good
          />

          <StatCard
            label="VALIDATION"
            value={loading ? "..." : violations === 0 ? "VERIFIED" : "ISSUES"}
            detail={`${violations} constraint violations`}
            good={violations === 0}
          />

          <StatCard
            label="SOLVER TIME"
            value={
              loading
                ? "..."
                : `${(
                    result?.metrics?.solver_wall_time_seconds ?? 0
                  ).toFixed(3)}s`
            }
            detail={`${
              result?.metrics?.candidate_placements ?? 0
            } candidate placements`}
            good
          />
        </section>

        <section className="panel timeline-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">OPTIMIZED SCHEDULE</span>
              <h3>Maintenance Timeline</h3>
            </div>

            <div className="legend">
              <span>
                <i className="legend-dot mandatory" /> Mandatory
              </span>
              <span>
                <i className="legend-dot optional" /> Optional
              </span>
            </div>
          </div>

          {result?.scheduled_jobs?.length ? (
            <div className="timeline">
              <div className="time-axis">
                {Array.from({ length: 6 }).map((_, index) => {
                  const time = minTime + ((maxTime - minTime) / 5) * index;

                  return (
                    <span key={index} style={{ left: `${index * 20}%` }}>
                      {formatTime(Math.round(time))}
                    </span>
                  );
                })}
              </div>

              {tracks.map((track) => {
                const jobs = result.scheduled_jobs.filter(
                  (job) => job.track === track
                );

                return (
                  <div className="track-row" key={track}>
                    <div className="track-name">{track}</div>

                    <div className="track-lane">
                      {jobs.map((job) => {
                        const isMandatory = scenario?.maintenance?.jobs?.find(
                          (j) => j.id === job.job_id
                        )?.mandatory;

                        return (
                          <button
                            key={job.job_id}
                            className={`job-block ${
                              isMandatory ? "mandatory" : "optional"
                            } ${
                              selectedJob?.job_id === job.job_id
                                ? "selected"
                                : ""
                            }`}
                            style={{
                              left: `${position(job.start)}%`,
                              width: `${Math.max(width(job.start, job.end), 4)}%`,
                            }}
                            onClick={() => setSelectedJob(job)}
                          >
                            <strong>{job.job_id}</strong>
                            <span>
                              {formatTime(job.start)} – {formatTime(job.end)}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-schedule">
              <strong>{loading ? "Optimizing scenario..." : "No feasible schedule returned"}</strong>
              {!loading && (
                <span>
                  Try another scenario or inspect the unscheduled mandatory jobs.
                </span>
              )}
            </div>
          )}
        </section>

        <section className="bottom-grid">
          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">CONSTRAINT ENGINE</span>
                <h3>Constraint Health</h3>
              </div>

              <div className="verified-badge">
                ✓ {violations === 0 ? "ALL PASSED" : "CHECK REQUIRED"}
              </div>
            </div>

            <ConstraintList validation={result?.validation} />
          </section>

          <section className="panel job-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">JOB INSPECTOR</span>
                <h3>{selectedJob?.job_id ?? "Select a job"}</h3>
              </div>
            </div>

            {selectedJob ? (
              <div className="job-details">
                <Detail label="Track" value={selectedJob.track} />
                <Detail
                  label="Time"
                  value={`${formatTime(selectedJob.start)} – ${formatTime(
                    selectedJob.end
                  )}`}
                />
                <Detail
                  label="Duration"
                  value={`${selectedJob.end - selectedJob.start} min`}
                />
                <Detail label="Crew" value={selectedJob.crew_id} />
                <Detail
                  label="Machine"
                  value={selectedJob.machine_id ?? "None"}
                />
                <Detail
                  label="Possession"
                  value={selectedJob.possession_id}
                />
              </div>
            ) : (
              <p className="muted">Click a maintenance job on the timeline.</p>
            )}
          </section>
        </section>

        <section className="emergency-panel">
          <div>
            <span className="emergency-icon">!</span>
            <div>
              <span className="eyebrow">WHAT-IF CONTROL</span>
              <h3>Emergency Maintenance Simulation</h3>
              <p>
                Select an urgent fault or another disruption and let the optimizer
                produce a new feasible plan.
              </p>
            </div>
          </div>

          <button
            className="emergency-button"
            onClick={() => openScenarioDialog("urgent_track_fault")}
            disabled={loading}
          >
            SIMULATE EMERGENCY
          </button>
        </section>
      </main>

      <footer>
        <span>RAILOPS v0.2</span>
        <span>OR-Tools CP-SAT · FastAPI · React</span>
      </footer>

      {scenarioDialogOpen && (
        <div
          className="scenario-dialog-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setScenarioDialogOpen(false);
            }
          }}
        >
          <section
            className="scenario-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="scenario-dialog-title"
          >
            <div className="scenario-dialog-header">
              <div>
                <span className="eyebrow">SIMULATION CONTROL</span>
                <h3 id="scenario-dialog-title">Choose a railway scenario</h3>
                <p>
                  The selected case is fetched from FastAPI and then sent to the
                  OR-Tools optimizer.
                </p>
              </div>
              <button
                className="dialog-close"
                onClick={() => setScenarioDialogOpen(false)}
                aria-label="Close scenario dialog"
              >
                ×
              </button>
            </div>

            <div className="scenario-options">
              {scenarioOptions.map((item) => (
                <button
                  key={item.id}
                  className={`scenario-option ${
                    pendingScenarioId === item.id ? "selected" : ""
                  }`}
                  onClick={() => setPendingScenarioId(item.id)}
                >
                  <div className="scenario-option-topline">
                    <strong>{item.name}</strong>
                    {item.id === activeScenarioId && (
                      <span className="current-scenario-badge">CURRENT</span>
                    )}
                  </div>
                  <span>{item.description}</span>
                  <small>{item.id}</small>
                </button>
              ))}
            </div>

            <div className="scenario-dialog-actions">
              <button
                className="dialog-secondary"
                onClick={() => setScenarioDialogOpen(false)}
              >
                CANCEL
              </button>
              <button
                className="optimize-button"
                onClick={applySelectedScenario}
                disabled={!pendingScenarioId}
              >
                RUN SELECTED SCENARIO
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, detail, good }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <strong className={good ? "good" : ""}>{value}</strong>
      <span className="stat-detail">{detail}</span>
    </div>
  );
}

function ConstraintList({ validation }) {
  const counts = validation?.violation_counts ?? {};

  const items = [
    ["TRAIN_CONFLICT", "Train conflicts"],
    ["TRACK_CONFLICT", "Track conflicts"],
    ["CREW_CONFLICT", "Crew conflicts"],
    ["CREW_AVAILABILITY", "Crew availability"],
    ["CREW_SKILL", "Crew skills"],
    ["MACHINE_CONFLICT", "Machine conflicts"],
    ["MACHINE_AVAILABILITY", "Machine availability"],
    ["POSSESSION", "Possession"],
    ["POSSESSION_WINDOW", "Possession window"],
    ["DEADLINE", "Deadlines"],
    ["EARLIEST_START", "Earliest start"],
    ["DURATION", "Duration"],
  ];

  return (
    <div className="constraint-list">
      {items.map(([key, label]) => {
        const count = counts[key] ?? 0;

        return (
          <div className="constraint-row" key={key}>
            <span className={count === 0 ? "check" : "warning"}>
              {count === 0 ? "✓" : "!"}
            </span>
            <span>{label}</span>
            <strong>{count}</strong>
          </div>
        );
      })}
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div className="detail">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default App;
