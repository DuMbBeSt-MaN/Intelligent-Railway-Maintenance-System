import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

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
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function runOptimization() {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/optimize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        throw new Error(`Optimization failed: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);

      if (data.scheduled_jobs?.length) {
        setSelectedJob(data.scheduled_jobs[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function loadScenario() {
      try {
        const response = await fetch(`${API_URL}/api/scenario`);

        if (!response.ok) {
          throw new Error("Could not load scenario");
        }

        const data = await response.json();
        setScenario(data);
      } catch (err) {
        setError(err.message);
      }
    }

    loadScenario();
    runOptimization();
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
    return ((start - minTime) / (maxTime - minTime)) * 100;
  }

  function width(start, end) {
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
          </div>

          <button className="optimize-button" onClick={runOptimization}>
            {loading ? "OPTIMIZING..." : "↻ RE-OPTIMIZE"}
          </button>
        </section>

        <section className="stats-grid">
          <StatCard
            label="PLAN STATUS"
            value={loading ? "..." : result?.status ?? "—"}
            detail="CP-SAT solver result"
            good={result?.status === "OPTIMAL"}
          />

          <StatCard
            label="JOBS SCHEDULED"
            value={
              loading
                ? "..."
                : `${result?.summary?.jobs_scheduled ?? 0} / ${
                    result?.summary?.jobs_total ?? 0
                  }`
            }
            detail={`${result?.summary?.mandatory_scheduled ?? 0} mandatory · ${
              result?.summary?.optional_scheduled ?? 0
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
              <span className="eyebrow">LIVE SCHEDULE</span>
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

          <div className="timeline">
            <div className="time-axis">
              {Array.from({ length: 6 }).map((_, index) => {
                const time =
                  minTime + ((maxTime - minTime) / 5) * index;

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
                      const isMandatory =
                        scenario?.maintenance?.jobs?.find(
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
                            width: `${Math.max(
                              width(job.start, job.end),
                              4
                            )}%`,
                          }}
                          onClick={() => setSelectedJob(job)}
                        >
                          <strong>{job.job_id}</strong>
                          <span>
                            {formatTime(job.start)} –{" "}
                            {formatTime(job.end)}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
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

            <ConstraintList
              validation={result?.validation}
            />
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
                  value={`${formatTime(
                    selectedJob.start
                  )} – ${formatTime(selectedJob.end)}`}
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
              <p className="muted">
                Click a maintenance job on the timeline.
              </p>
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
                Inject a critical maintenance job and let the optimizer
                find a new feasible plan.
              </p>
            </div>
          </div>

          <button className="emergency-button">
            SIMULATE EMERGENCY
          </button>
        </section>
      </main>

      <footer>
        <span>RAILOPS v0.1</span>
        <span>OR-Tools CP-SAT · FastAPI · React</span>
      </footer>
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