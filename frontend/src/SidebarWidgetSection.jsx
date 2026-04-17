import { LayoutGrid, Check, ExternalLink } from "lucide-react";

/* ── Spring 2026 deadlines ────────────────────────────────────── */
const SPRING_DEADLINES = [
  { date: "Jan 13", label: "First day of classes",       type: "info"    },
  { date: "Jan 17", label: "Last day to add (full-sem)", type: "warning" },
  { date: "Jan 20", label: "MLK Day – No classes",       type: "holiday" },
  { date: "Feb 14", label: "Last day to drop (no W)",    type: "warning" },
  { date: "Mar 9",  label: "Spring Break begins",        type: "holiday" },
  { date: "Mar 21", label: "Last day to withdraw (W)",   type: "warning" },
  { date: "Apr 11", label: "Last day of classes",        type: "info"    },
  { date: "Apr 12", label: "Final Exams begin",          type: "exam"    },
  { date: "May 10", label: "Summer tuition due",         type: "tuition" },
];

function parseDate(s) { return new Date(`${s} 2026`); }

/* ── Widget registry ──────────────────────────────────────────── */
const WIDGET_DEFS = [
  { id: "deadlines", label: "Upcoming Deadlines", viewId: "calendar",  desc: "Key dates & deadlines"            },
  { id: "progress",  label: "Degree Progress",    viewId: "checklist", desc: "Track graduation requirements"    },
  { id: "gened",     label: "Gen Ed Explorer",    viewId: "gened",     desc: "Manage Gen Ed credits"            },
  { id: "resources", label: "Quick Resources",    viewId: "resources", desc: "Campus services & support"        },
  { id: "gpa",       label: "GPA Tracker",        viewId: "gpa",       desc: "Calculate & track your GPA"      },
  { id: "prereq",    label: "Course Map",         viewId: "prereq",    desc: "Visualize course prerequisites"   },
];

/* ── Compact widget content ───────────────────────────────────── */
function DeadlinesWidget({ onNavigate }) {
  const now = new Date();
  const upcoming = SPRING_DEADLINES.filter(d => parseDate(d.date) >= now).slice(0, 3);
  return (
    <div className="wc-body">
      {upcoming.length === 0
        ? <p className="wc-empty">No upcoming deadlines</p>
        : upcoming.map((d, i) => (
          <div key={i} className={`wc-deadline wc-deadline--${d.type}`}>
            <span className="wc-date">{d.date}</span>
            <span className="wc-dlabel">{d.label}</span>
          </div>
        ))
      }
      {onNavigate && (
        <button className="wc-link" onClick={() => onNavigate("calendar")}>View full calendar →</button>
      )}
    </div>
  );
}

/* Map audit requirement block titles to short widget labels */
const REQ_LABEL_MAP = [
  { match: /prescribed|core\s*cs|cmpsc.*required/i,  label: "Core CS"   },
  { match: /math|quantif/i,                           label: "Math"      },
  { match: /gen.*ed|general.*educ/i,                  label: "Gen Ed"    },
  { match: /elective/i,                               label: "Electives" },
  { match: /science|physics/i,                        label: "Science"   },
  { match: /writing|communication|english/i,          label: "Writing"   },
];

function auditToProgressItems(auditData) {
  if (!auditData) return null;

  const overall = {
    label: "Overall",
    pct: Math.min(100, Math.round(auditData.degree_progress_pct ?? 0)),
  };

  const cats = [];
  const seen = new Set();
  for (const req of (auditData.remaining_requirements ?? [])) {
    const cr = req.credits_required ?? 0;
    const needed = req.credits_needed ?? 0;
    if (cr <= 0) continue;
    const pct = Math.min(100, Math.round(((cr - needed) / cr) * 100));
    let label = null;
    for (const { match, label: l } of REQ_LABEL_MAP) {
      if (match.test(req.title)) { label = l; break; }
    }
    if (!label) continue;
    if (seen.has(label)) continue;
    seen.add(label);
    cats.push({ label, pct });
    if (cats.length >= 3) break;
  }

  return [overall, ...cats];
}

function ProgressWidget({ onNavigate, auditData }) {
  const liveItems = auditToProgressItems(auditData);
  const items = liveItems ?? [
    { label: "Core CS",   pct: 72 },
    { label: "Math",      pct: 85 },
    { label: "Gen Ed",    pct: 60 },
    { label: "Electives", pct: 40 },
  ];
  return (
    <div className="wc-body">
      {liveItems && (
        <p className="wc-desc" style={{ marginBottom: 2 }}>From your uploaded audit</p>
      )}
      {items.map(item => (
        <div key={item.label} className="wc-prog-row">
          <div className="wc-prog-meta">
            <span className="wc-prog-label">{item.label}</span>
            <span className="wc-prog-pct">{item.pct}%</span>
          </div>
          <div className="wc-prog-track">
            <div className="wc-prog-fill" style={{ width: `${item.pct}%` }} />
          </div>
        </div>
      ))}
      {onNavigate && (
        <button className="wc-link" onClick={() => onNavigate("checklist")}>View checklist →</button>
      )}
    </div>
  );
}

function GenEdWidget({ onNavigate }) {
  const cats = ["FYW","GQ","GN","GA","GH","GS","GHA","US","IL"];
  return (
    <div className="wc-body">
      <p className="wc-desc">Track Gen Ed across 9 categories</p>
      <div className="wc-pills">
        {cats.map(c => <span key={c} className="wc-pill">{c}</span>)}
      </div>
      {onNavigate && (
        <button className="wc-link" onClick={() => onNavigate("gened")}>Open Explorer →</button>
      )}
    </div>
  );
}

const QUICK_RES = [
  { label: "CAPS Counseling",  url: "https://studentaffairs.psu.edu/counseling" },
  { label: "LRC Tutoring",     url: "https://lrc.psu.edu/" },
  { label: "Career Services",  url: "https://careerservices.psu.edu/" },
  { label: "UHS Medical",      url: "https://studentaffairs.psu.edu/health" },
];

function ResourcesWidget() {
  return (
    <div className="wc-body">
      {QUICK_RES.map(r => (
        <a key={r.label} className="wc-res-link" href={r.url} target="_blank" rel="noreferrer">
          <span className="wc-res-name">{r.label}</span>
          <ExternalLink size={11} className="wc-res-arrow" />
        </a>
      ))}
    </div>
  );
}

function GpaWidget({ onNavigate }) {
  return (
    <div className="wc-body wc-body--cta">
      <p className="wc-desc">Semester & cumulative GPA calculator using PSU 4.0 scale</p>
      {onNavigate && (
        <button className="wc-cta-btn" onClick={() => onNavigate("gpa")}>Open Calculator →</button>
      )}
    </div>
  );
}

function PrereqWidget({ onNavigate }) {
  return (
    <div className="wc-body wc-body--cta">
      <p className="wc-desc">Interactive CMPSC course prerequisite map</p>
      {onNavigate && (
        <button className="wc-cta-btn" onClick={() => onNavigate("prereq")}>Open Course Map →</button>
      )}
    </div>
  );
}

const WIDGET_COMPONENTS = {
  deadlines: DeadlinesWidget,
  progress:  ProgressWidget,
  gened:     GenEdWidget,
  resources: ResourcesWidget,
  gpa:       GpaWidget,
  prereq:    PrereqWidget,
};

/* ── Main sidebar widget section ─────────────────────────────── */
export default function SidebarWidgetSection({ activeWidgets, onNavigate, auditData }) {
  const deadlineBadge = SPRING_DEADLINES.some(d => {
    const ms = parseDate(d.date) - new Date();
    return ms >= 0 && ms <= 7 * 24 * 60 * 60 * 1000;
  });

  return (
    <div className="ws-root">
      <div className="ws-stack">
        {activeWidgets.map(id => {
          const def     = WIDGET_DEFS.find(d => d.id === id);
          if (!def) return null;
          const Content = WIDGET_COMPONENTS[id];
          const badge   = id === "deadlines" && deadlineBadge;
          return (
            <div key={id} className="ws-card">
              <div className="ws-card-header">
                <span className="ws-card-label">{def.label}</span>
                {badge && <span className="ws-badge" />}
                {onNavigate && def.viewId && (
                  <button
                    className="ws-open-btn"
                    onClick={() => onNavigate(def.viewId)}
                    title={`Open ${def.label}`}
                  >
                    <ExternalLink size={11} />
                  </button>
                )}
              </div>
              <Content onNavigate={onNavigate} auditData={auditData} />
            </div>
          );
        })}
        {activeWidgets.length === 0 && (
          <p className="ws-empty">No widgets added yet.</p>
        )}
      </div>

      <button className="ws-edit-btn" onClick={() => onNavigate("widgets")}>
        <LayoutGrid size={13} /> Manage Widgets
      </button>
    </div>
  );
}

/* ── Widget picker full page ──────────────────────────────────── */
export function WidgetPickerPage({ activeWidgets, setActiveWidgets, onDone }) {
  const toggle = (id) => {
    setActiveWidgets(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  };

  return (
    <div className="wpp-root">
      <div className="wpp-header">
        <h2 className="wpp-title">Choose Your Widgets</h2>
        <p className="wpp-subtitle">
          Pick up to <strong>3 widgets</strong> to display in your sidebar.
        </p>
        <div className="wpp-counter">{activeWidgets.length} / 3 selected</div>
      </div>

      <div className="wpp-grid">
        {WIDGET_DEFS.map(def => {
          const active   = activeWidgets.includes(def.id);
          const disabled = !active && activeWidgets.length >= 3;
          return (
            <button
              key={def.id}
              className={`wpp-card${active ? " wpp-card--active" : ""}${disabled ? " wpp-card--disabled" : ""}`}
              onClick={() => toggle(def.id)}
              disabled={disabled}
            >
              {active && <Check size={14} className="wpp-check" />}
              <span className="wpp-card-name">{def.label}</span>
              <span className="wpp-card-desc">{def.desc}</span>
            </button>
          );
        })}
      </div>

      <div className="wpp-footer">
        <button className="wpp-done-btn" onClick={onDone}>
          Done
        </button>
      </div>
    </div>
  );
}
