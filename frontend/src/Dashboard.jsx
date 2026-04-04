import { useState, useEffect } from "react";

/* ── Degree Progress Bar ────────────────────────────────────── */
function DegreeProgressBar({ pct, completed, remaining, required }) {
  return (
    <div className="dpb-wrap">
      <div className="dpb-top">
        <span className="dpb-pct">{pct.toFixed(0)}%</span>
        <span className="dpb-label">Complete</span>
      </div>
      <div className="dpb-track">
        <div className="dpb-fill" style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <div className="dpb-legend">
        <span className="dpb-legend-item">
          <span className="dpb-dot dpb-dot--navy" />
          Completed — {completed} cr
        </span>
        <span className="dpb-legend-item">
          <span className="dpb-dot dpb-dot--gold" />
          Remaining — {remaining} cr
        </span>
      </div>
      <div className="dpb-totals">{completed} of {required} total credits</div>
    </div>
  );
}

/* ── Stat Card ──────────────────────────────────────────────── */
function StatCard({ label, value, sub, variant }) {
  return (
    <div className={`stat-card${variant ? ` stat-card--${variant}` : ""}`}>
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value">{value}</div>
      {sub && <div className="stat-card-sub">{sub}</div>}
    </div>
  );
}

/* ── Progress Bar ───────────────────────────────────────────── */
function ProgressBar({ needed, required }) {
  const pct = required > 0 ? Math.max(0, Math.min(100, ((required - needed) / required) * 100)) : 0;
  return (
    <div className="req-bar">
      <div className="req-bar-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

/* ── Empty State ────────────────────────────────────────────── */
function EmptyDashboard({ onUploadClick }) {
  return (
    <div className="dash-empty-state">
      <div className="dash-empty-icon">📊</div>
      <h2 className="dash-empty-title">No Document Uploaded</h2>
      <p className="dash-empty-body">
        Upload your What-If Report or Degree Audit PDF to see your personalized
        dashboard with credits, requirements, and semester recommendations.
      </p>
      <button className="dash-upload-btn" onClick={onUploadClick}>
        + Upload PDF
      </button>
    </div>
  );
}

/* ── Dashboard ──────────────────────────────────────────────── */
export default function Dashboard({ uploadedFile, onUploadClick }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setFetchError(null);
    fetch(`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/dashboard`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => { setFetchError("Could not connect to the backend."); setLoading(false); });
  }, [uploadedFile]);

  if (loading) {
    return (
      <div className="dash-loading">
        <div className="loading-dots"><span /><span /><span /></div>
        <p>Loading dashboard…</p>
      </div>
    );
  }

  if (fetchError) {
    return <div className="dash-error">{fetchError}</div>;
  }

  if (!data?.available) {
    return <EmptyDashboard onUploadClick={onUploadClick} />;
  }

  const {
    credits_completed,
    credits_remaining,
    credits_required,
    degree_progress_pct,
    status,
    advisor,
    remaining_requirements,
    in_progress_courses,
    recommended_next_semester,
    alerts,
  } = data;

  const statusVariant = status === "On Track" ? "success" : status === "In Progress" ? "warning" : "info";

  return (
    <div className="dashboard">

      {/* ── Alerts bar ────────────────────────────────── */}
      {alerts.length > 0 && (
        <div className="dash-alerts">
          {alerts.map((a, i) => (
            <div key={i} className={`dash-alert dash-alert--${a.type}`}>
              <span className="dash-alert-icon">
                {a.type === "warning" ? "⚠" : a.type === "success" ? "✓" : "ℹ"}
              </span>
              {a.message}
            </div>
          ))}
        </div>
      )}

      {/* ── Top cards ─────────────────────────────────── */}
      <div className="dash-cards">
        <StatCard
          label="Credits Completed"
          value={credits_completed}
          sub={`of ${credits_required} required`}
          variant="navy"
        />
        <StatCard
          label="Credits Remaining"
          value={credits_remaining}
          sub="to graduate"
          variant="gold"
        />
        <StatCard
          label="Degree Progress"
          value={`${degree_progress_pct}%`}
          sub="overall completion"
          variant="progress"
        />
        <StatCard
          label="Status"
          value={status}
          sub={advisor ? `Advisor: ${advisor}` : ""}
          variant={statusVariant}
        />
      </div>

      {/* ── Chart + Recommended ───────────────────────── */}
      <div className="dash-mid-row">

        {/* Degree progress bar */}
        <div className="dash-card dash-card--chart">
          <h3 className="dash-card-title">Degree Completion</h3>
          <DegreeProgressBar
            pct={degree_progress_pct}
            completed={credits_completed}
            remaining={credits_remaining}
            required={credits_required}
          />
        </div>

        {/* Recommended next semester */}
        <div className="dash-card dash-card--recommended">
          <h3 className="dash-card-title">Recommended Next Semester</h3>
          {recommended_next_semester.length === 0 ? (
            <p className="dash-card-empty">No specific recommendations available.</p>
          ) : (
            <div className="rec-grid">
              {recommended_next_semester.map((course, i) => (
                <div key={i} className="rec-course-card">
                  <span className="rec-course-code">{course}</span>
                  <span className="rec-course-tag">Required</span>
                </div>
              ))}
            </div>
          )}
          {in_progress_courses.length > 0 && (
            <div className="dash-inprogress">
              <div className="dash-inprogress-label">Currently In Progress</div>
              <div className="course-chip-row">
                {in_progress_courses.map((c) => (
                  <span key={c} className="course-chip course-chip--ip">{c}</span>
                ))}
              </div>
            </div>
          )}
          <p className="rec-disclaimer">
            Based on your remaining required courses. Always confirm with your advisor.
          </p>
        </div>
      </div>

      {/* ── Remaining Requirements ────────────────────── */}
      <div className="dash-card dash-card--requirements">
        <h3 className="dash-card-title">Remaining Requirements</h3>
        {remaining_requirements.length === 0 ? (
          <p className="dash-card-empty">All requirements satisfied — congratulations!</p>
        ) : (
          <div className="req-list">
            {remaining_requirements.map((req, i) => (
              <div key={i} className="req-item">
                <div className="req-item-header">
                  <span className="req-item-title">{req.title}</span>
                  <span className="req-item-credits">
                    {req.credits_needed > 0 ? `${req.credits_needed} cr needed` : "pending"}
                  </span>
                </div>
                <ProgressBar needed={req.credits_needed} required={req.credits_required} />
                {req.courses.length > 0 && (
                  <div className="course-chip-row">
                    {req.courses.map((c) => (
                      <span key={c} className="course-chip">{c}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
