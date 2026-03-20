import { useState, useRef, useEffect } from "react";

/* ── PSU 4.0 grade scale ─────────────────────────────────────── */
const GRADES = [
  { label: "A",  points: 4.00 },
  { label: "A-", points: 3.67 },
  { label: "B+", points: 3.33 },
  { label: "B",  points: 3.00 },
  { label: "B-", points: 2.67 },
  { label: "C+", points: 2.33 },
  { label: "C",  points: 2.00 },
  { label: "C-", points: 1.67 },
  { label: "D+", points: 1.33 },
  { label: "D",  points: 1.00 },
  { label: "F",  points: 0.00 },
];

const CREDIT_OPTIONS = [1, 2, 3, 4, 5, 6];

function makeCourse(id) {
  return { id, name: "", credits: 3, grade: "A" };
}

function calcSemester(courses) {
  if (courses.length === 0) return null;
  const totalCredits = courses.reduce((s, c) => s + Number(c.credits), 0);
  const totalQP = courses.reduce((s, c) => {
    const g = GRADES.find(g => g.label === c.grade);
    return s + (g ? g.points * Number(c.credits) : 0);
  }, 0);
  if (totalCredits === 0) return null;
  return { gpa: totalQP / totalCredits, totalCredits, totalQP };
}

function gpaVariant(gpa) {
  if (gpa >= 3.5) return "excellent";
  if (gpa >= 3.0) return "good";
  if (gpa >= 2.0) return "average";
  return "low";
}

/* ── Course row ─────────────────────────────────────────────── */
function CourseRow({ course, onChange, onRemove, canRemove }) {
  return (
    <div className="gpa-row">
      <input
        className="gpa-input gpa-input--name"
        type="text"
        placeholder="Course name (optional)"
        value={course.name}
        onChange={e => onChange({ ...course, name: e.target.value })}
      />
      <select
        className="gpa-select"
        value={course.credits}
        onChange={e => onChange({ ...course, credits: Number(e.target.value) })}
      >
        {CREDIT_OPTIONS.map(c => (
          <option key={c} value={c}>{c} cr</option>
        ))}
      </select>
      <select
        className="gpa-select gpa-select--grade"
        value={course.grade}
        onChange={e => onChange({ ...course, grade: e.target.value })}
      >
        {GRADES.map(g => (
          <option key={g.label} value={g.label}>{g.label}</option>
        ))}
      </select>
      <button
        className="gpa-remove-btn"
        onClick={onRemove}
        disabled={!canRemove}
        title="Remove course"
      >
        ×
      </button>
    </div>
  );
}

/* ── Result card ────────────────────────────────────────────── */
function ResultCard({ label, gpa, meta, badge }) {
  const variant = gpaVariant(gpa);
  return (
    <div className={`gpa-result gpa-result--${variant}`}>
      <div className="gpa-result-left">
        <span className="gpa-result-label">{label}</span>
        <span className="gpa-result-value">{gpa.toFixed(2)}</span>
        {badge && <span className="gpa-result-badge">{badge}</span>}
      </div>
      <div className="gpa-result-right">
        {meta.map((m, i) => (
          <span key={i} className={`gpa-result-meta-item${m.highlight ? ` gpa-result-meta-item--${m.highlight}` : ""}`}>
            {m.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── History tab ────────────────────────────────────────────── */
function HistoryTab({ userId }) {
  const storageKey = `ace_gpa_history_${userId}`;

  const [history, setHistory] = useState(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  const [showForm, setShowForm]       = useState(false);
  const [formName, setFormName]       = useState("");
  const [formGpa, setFormGpa]         = useState("");
  const [formCredits, setFormCredits] = useState("");
  const [formError, setFormError]     = useState("");

  const histIdRef = useRef(Date.now());

  /* Persist to localStorage whenever history changes */
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(history));
    } catch {
      /* quota exceeded — silently ignore */
    }
  }, [history, storageKey]);

  function handleAdd() {
    const name    = formName.trim();
    const gpa     = parseFloat(formGpa);
    const credits = parseFloat(formCredits);

    if (!name) {
      setFormError("Please enter a semester name.");
      return;
    }
    if (isNaN(gpa) || gpa < 0 || gpa > 4.0) {
      setFormError("GPA must be between 0 and 4.0.");
      return;
    }
    if (isNaN(credits) || credits <= 0) {
      setFormError("Credits must be a positive number.");
      return;
    }

    const entry = { id: histIdRef.current++, name, gpa, credits };
    setHistory(prev => [...prev, entry]);
    setFormName("");
    setFormGpa("");
    setFormCredits("");
    setFormError("");
    setShowForm(false);
  }

  function handleCancel() {
    setFormName("");
    setFormGpa("");
    setFormCredits("");
    setFormError("");
    setShowForm(false);
  }

  function handleDelete(id) {
    setHistory(prev => prev.filter(e => e.id !== id));
  }

  /* Running cumulative GPA across all saved semesters */
  let cumGpa = null;
  if (history.length > 0) {
    const totalQP  = history.reduce((s, e) => s + e.gpa * e.credits, 0);
    const totalCr  = history.reduce((s, e) => s + e.credits, 0);
    cumGpa = totalCr > 0 ? totalQP / totalCr : null;
  }

  return (
    <div className="gpa-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h3 className="gpa-card-title" style={{ margin: 0 }}>Semester History</h3>
        {!showForm && (
          <button className="gpa-add-btn" style={{ marginTop: 0 }} onClick={() => setShowForm(true)}>
            + Add Semester
          </button>
        )}
      </div>

      {/* ── Add form ── */}
      {showForm && (
        <div className="gpa-add-form">
          <div className="gpa-add-form-row">
            <div className="gpa-field">
              <label className="gpa-label">Semester Name</label>
              <input
                className="gpa-input"
                type="text"
                placeholder='e.g. "Fall 2024"'
                value={formName}
                onChange={e => setFormName(e.target.value)}
              />
            </div>
            <div className="gpa-field">
              <label className="gpa-label">GPA Earned</label>
              <input
                className="gpa-input"
                type="number"
                min="0"
                max="4.0"
                step="0.01"
                placeholder="0.00 – 4.00"
                value={formGpa}
                onChange={e => setFormGpa(e.target.value)}
              />
            </div>
            <div className="gpa-field">
              <label className="gpa-label">Credits Attempted</label>
              <input
                className="gpa-input"
                type="number"
                min="1"
                step="1"
                placeholder="e.g. 15"
                value={formCredits}
                onChange={e => setFormCredits(e.target.value)}
              />
            </div>
          </div>
          {formError && (
            <p style={{ color: "var(--color-error, #ef4444)", fontSize: "0.8rem", margin: "0.25rem 0 0.5rem" }}>
              {formError}
            </p>
          )}
          <div className="gpa-add-form-actions">
            <button className="gpa-add-btn" style={{ marginTop: 0 }} onClick={handleAdd}>
              Add
            </button>
            <button
              className="gpa-remove-btn"
              style={{ padding: "0.4rem 0.85rem", fontSize: "0.85rem", opacity: 1, cursor: "pointer" }}
              onClick={handleCancel}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ── Semester list ── */}
      {history.length === 0 ? (
        <p className="gpa-history-empty">
          No semesters recorded yet. Add your first semester above.
        </p>
      ) : (
        <>
          <div className="gpa-history-list">
            {history.map(entry => {
              const variant = gpaVariant(entry.gpa);
              return (
                <div key={entry.id} className="gpa-history-row">
                  <span className="gpa-history-name">{entry.name}</span>
                  <span className={`gpa-history-gpa gpa-history-gpa--${variant}`}>
                    {entry.gpa.toFixed(2)}
                  </span>
                  <span className="gpa-history-credits">{entry.credits} cr</span>
                  <button
                    className="gpa-history-delete"
                    title="Remove semester"
                    onClick={() => handleDelete(entry.id)}
                  >
                    ×
                  </button>
                </div>
              );
            })}
          </div>

          {/* ── Bar chart ── */}
          <div className="gpa-history-chart">
            {history.map(entry => {
              const variant = gpaVariant(entry.gpa);
              const pct     = ((entry.gpa / 4.0) * 100).toFixed(1);
              return (
                <div key={entry.id} className="gpa-history-bar-row">
                  <span className="gpa-history-bar-label">
                    {entry.name} · {entry.gpa.toFixed(2)}
                  </span>
                  <div className="gpa-history-bar-track">
                    <div
                      className={`gpa-history-bar-fill gpa-history-bar-fill--${variant}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* ── Cumulative summary ── */}
          {cumGpa !== null && (
            <div className={`gpa-history-cumulative gpa-result--${gpaVariant(cumGpa)}`}>
              <span className="gpa-result-label">Running Cumulative GPA</span>
              <span className="gpa-result-value">{cumGpa.toFixed(2)}</span>
              <span className="gpa-result-meta-item">
                {history.reduce((s, e) => s + e.credits, 0)} total credits ·{" "}
                {history.length} semester{history.length !== 1 ? "s" : ""}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── GpaCalculator ──────────────────────────────────────────── */
export default function GpaCalculator({ userId = "guest" }) {
  const [mode, setMode]               = useState("semester");
  const [courses, setCourses]         = useState([makeCourse(1)]);
  const [currentGpa, setCurrentGpa]   = useState("");
  const [currentCr, setCurrentCr]     = useState("");
  const idRef = useRef(2);

  const addCourse = () => {
    setCourses(prev => [...prev, makeCourse(idRef.current++)]);
  };

  const updateCourse = (id, updated) =>
    setCourses(prev => prev.map(c => (c.id === id ? updated : c)));

  const removeCourse = (id) =>
    setCourses(prev => prev.filter(c => c.id !== id));

  const semResult  = calcSemester(courses);

  /* cumulative projection */
  let cumResult = null;
  if (mode === "cumulative" && semResult) {
    const prevGpa = parseFloat(currentGpa);
    const prevCr  = parseFloat(currentCr);
    if (!isNaN(prevGpa) && !isNaN(prevCr) && prevGpa >= 0 && prevGpa <= 4.0 && prevCr >= 0) {
      const totalQP  = prevGpa * prevCr + semResult.totalQP;
      const totalCr  = prevCr + semResult.totalCredits;
      const newGpa   = totalCr > 0 ? totalQP / totalCr : 0;
      const diff     = newGpa - prevGpa;
      cumResult = { gpa: newGpa, totalCr, totalQP, diff, prevGpa };
    }
  }

  return (
    <div className="gpa-calc">

      {/* ── Header ── */}
      <div className="gpa-header">
        <h1 className="gpa-title">GPA Calculator</h1>
        <p className="gpa-subtitle">
          Calculate your Penn State semester or cumulative GPA using the official 4.0 scale.
        </p>
      </div>

      {/* ── Mode tabs ── */}
      <div className="gpa-tabs">
        <button
          className={`gpa-tab${mode === "semester" ? " gpa-tab--active" : ""}`}
          onClick={() => setMode("semester")}
        >
          Semester GPA
        </button>
        <button
          className={`gpa-tab${mode === "cumulative" ? " gpa-tab--active" : ""}`}
          onClick={() => setMode("cumulative")}
        >
          Cumulative GPA
        </button>
        <button
          className={`gpa-tab${mode === "history" ? " gpa-tab--active" : ""}`}
          onClick={() => setMode("history")}
        >
          History
        </button>
      </div>

      {/* ── History tab ── */}
      {mode === "history" && (
        <HistoryTab userId={userId} />
      )}

      {/* ── Current standing (cumulative only) ── */}
      {mode === "cumulative" && (
        <div className="gpa-card">
          <h3 className="gpa-card-title">Current Academic Standing</h3>
          <div className="gpa-standing-row">
            <div className="gpa-field">
              <label className="gpa-label">Current Cumulative GPA</label>
              <input
                className="gpa-input"
                type="number"
                min="0" max="4.0" step="0.01"
                placeholder="e.g.  3.45"
                value={currentGpa}
                onChange={e => setCurrentGpa(e.target.value)}
              />
            </div>
            <div className="gpa-field">
              <label className="gpa-label">Credits Earned So Far</label>
              <input
                className="gpa-input"
                type="number"
                min="0"
                placeholder="e.g.  60"
                value={currentCr}
                onChange={e => setCurrentCr(e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Course table (semester + cumulative only) ── */}
      {mode !== "history" && (
        <div className="gpa-card">
          <h3 className="gpa-card-title">
            {mode === "cumulative" ? "Courses This Semester" : "Your Courses"}
          </h3>

          {/* Column header */}
          <div className="gpa-row gpa-row--header">
            <span className="gpa-col gpa-col--name">Course</span>
            <span className="gpa-col">Credits</span>
            <span className="gpa-col">Grade</span>
            <span className="gpa-col" />
          </div>

          {courses.map(course => (
            <CourseRow
              key={course.id}
              course={course}
              onChange={updated => updateCourse(course.id, updated)}
              onRemove={() => removeCourse(course.id)}
              canRemove={courses.length > 1}
            />
          ))}

          <button className="gpa-add-btn" onClick={addCourse}>
            + Add Course
          </button>
        </div>
      )}

      {/* ── Semester result ── */}
      {mode === "semester" && semResult && (
        <ResultCard
          label="Semester GPA"
          gpa={semResult.gpa}
          badge={semResult.gpa >= 3.5 ? "Dean's List range 🎉" : null}
          meta={[
            { label: `${semResult.totalCredits} credits` },
            { label: `${semResult.totalQP.toFixed(2)} quality points` },
          ]}
        />
      )}

      {/* ── Cumulative result ── */}
      {mode === "cumulative" && cumResult && (
        <ResultCard
          label="Projected Cumulative GPA"
          gpa={cumResult.gpa}
          badge={cumResult.gpa >= 3.5 ? "Dean's List range 🎉" : null}
          meta={[
            { label: `${cumResult.prevGpa.toFixed(2)} → ${cumResult.gpa.toFixed(2)}` },
            {
              label: `${cumResult.diff >= 0 ? "▲" : "▼"} ${Math.abs(cumResult.diff).toFixed(3)}`,
              highlight: cumResult.diff >= 0 ? "up" : "down",
            },
            { label: `${cumResult.totalCr} total credits` },
          ]}
        />
      )}

      {/* Hint when cumulative fields not filled */}
      {mode === "cumulative" && semResult && !cumResult && (
        <div className="gpa-hint">
          Enter your current GPA and credits earned above to see your projected cumulative GPA.
        </div>
      )}

      {/* ── Grade scale reference ── */}
      <div className="gpa-card gpa-card--reference">
        <h3 className="gpa-card-title">Penn State Grade Scale</h3>
        <div className="gpa-scale-grid">
          {GRADES.map(g => (
            <div key={g.label} className="gpa-scale-item">
              <span className="gpa-scale-grade">{g.label}</span>
              <span className="gpa-scale-pts">{g.points.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="gpa-disclaimer">
        Results are estimates based on the PSU 4.0 scale. Always verify with your official transcript on LionPATH.
      </p>
    </div>
  );
}
