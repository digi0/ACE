import { useState, useEffect } from "react";

/* ── Donut Chart ────────────────────────────────────────────── */
function DonutChart({ pct, completed, remaining }) {
  const r = 68;
  const cx = 90;
  const cy = 90;
  const circ = 2 * Math.PI * r;
  const filled = Math.min((pct / 100) * circ, circ);

  return (
    <div className="donut-wrap">
      <svg width="180" height="180" viewBox="0 0 180 180" aria-label={`${pct}% degree complete`}>
        {/* Track */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e5e7eb" strokeWidth="18" />
        {/* Gold segment (remaining) */}
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke="#c9a227" strokeWidth="18"
          strokeDasharray={`${circ - filled} ${filled}`}
          strokeDashoffset={-(filled)}
          transform={`rotate(-90 ${cx} ${cy})`}
          strokeLinecap="butt"
        />
        {/* Navy segment (completed) */}
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke="#1a2744" strokeWidth="18"
          strokeDasharray={`${filled} ${circ - filled}`}
          transform={`rotate(-90 ${cx} ${cy})`}
          strokeLinecap="butt"
        />
        {/* Center text */}
        <text x={cx} y={cy - 10} textAnchor="middle" fill="#1a2744" fontSize="26" fontWeight="700" fontFamily="Inter, sans-serif">
          {pct.toFixed(0)}%
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" fill="#6b7280" fontSize="11" fontFamily="Inter, sans-serif">
          Complete
        </text>
      </svg>
      <div className="donut-legend">
        <span className="donut-legend-item">
          <span className="donut-dot donut-dot--navy" />
          Completed ({completed} cr)
        </span>
        <span className="donut-legend-item">
          <span className="donut-dot donut-dot--gold" />
          Remaining ({remaining} cr)
        </span>
      </div>
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
    fetch("http://127.0.0.1:8000/dashboard")
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

        {/* Donut chart */}
        <div className="dash-card dash-card--chart">
          <h3 className="dash-card-title">Degree Completion</h3>
          <DonutChart
            pct={degree_progress_pct}
            completed={credits_completed}
            remaining={credits_remaining}
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
