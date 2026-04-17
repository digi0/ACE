import { useState, useEffect } from "react";
import { Settings, Check, ExternalLink, LayoutGrid, Upload } from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/* ── Widget registry ──────────────────────────────────────────── */
const WIDGET_DEFS = [
  { id: "deadlines", label: "Upcoming Deadlines", viewId: "calendar",  desc: "Key dates & deadlines"            },
  { id: "progress",  label: "Degree Progress",    viewId: "checklist", desc: "Track graduation requirements"    },
  { id: "gened",     label: "Gen Ed Explorer",    viewId: "gened",     desc: "Manage Gen Ed credits"            },
  { id: "resources", label: "Quick Resources",    viewId: "resources", desc: "Campus services & support"        },
  { id: "gpa",       label: "GPA Tracker",        viewId: "gpa",       desc: "Calculate & track your GPA"      },
  { id: "prereq",    label: "Course Map",         viewId: "prereq",    desc: "Visualize course prerequisites"   },
];

/* ── Category → deadline type mapping ────────────────────────── */
function calEventType(eventName) {
  const n = eventName.toLowerCase();
  if (/(holiday|break|no classes|recess)/i.test(n))          return "holiday";
  if (/(deadline|last day|late drop|late add|late reg|withdraw)/i.test(n)) return "warning";
  if (/(final exam)/i.test(n))                                return "exam";
  if (/(tuition|refund|billing|payment)/i.test(n))           return "tuition";
  return "info";
}

function formatShortDate(isoDate) {
  const [, mm, dd] = isoDate.split("-").map(Number);
  const months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[mm]} ${dd}`;
}

/* ── Compact widget content ───────────────────────────────────── */
function DeadlinesWidget({ onNavigate }) {
  const [upcoming, setUpcoming] = useState(null); // null = loading

  useEffect(() => {
    fetch(`${API}/calendar/current`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) { setUpcoming([]); return; }
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const items = (data.events || [])
          .filter(e => e.iso_date && new Date(e.iso_date + "T00:00:00") >= today)
          .slice(0, 3)
          .map(e => ({
            date:  formatShortDate(e.iso_date),
            label: e.event,
            type:  calEventType(e.event),
          }));
        setUpcoming(items);
      })
      .catch(() => setUpcoming([]));
  }, []);

  return (
    <div className="wc-body">
      {upcoming === null ? (
        <p className="wc-empty">Loading…</p>
      ) : upcoming.length === 0 ? (
        <p className="wc-empty">No upcoming deadlines</p>
      ) : (
        upcoming.map((d, i) => (
          <div key={i} className={`wc-deadline wc-deadline--${d.type}`}>
            <span className="wc-date">{d.date}</span>
            <span className="wc-dlabel">{d.label}</span>
          </div>
        ))
      )}
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

  if (!liveItems) {
    return (
      <div className="wc-body">
        <p className="wc-empty">
          <Upload size={11} style={{ display: "inline", marginRight: 5, verticalAlign: "middle", opacity: 0.6 }} />
          Upload your degree audit to track progress
        </p>
      </div>
    );
  }

  return (
    <div className="wc-body">
      <p className="wc-desc" style={{ marginBottom: 4 }}>From your uploaded audit</p>
      {liveItems.map(item => (
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
  return (
    <div className="ws-root">
      <div className="ws-section-header">
        <span className="ws-section-label">WIDGETS</span>
        {onNavigate && (
          <button
            className="ws-gear-btn"
            onClick={() => onNavigate("widgets")}
            title="Manage widgets"
          >
            <Settings size={13} />
          </button>
        )}
      </div>

      <div className="ws-stack">
        {activeWidgets.map(id => {
          const def     = WIDGET_DEFS.find(d => d.id === id);
          if (!def) return null;
          const Content = WIDGET_COMPONENTS[id];
          return (
            <div key={id} className="ws-card">
              <div className="ws-card-header">
                <span className="ws-card-label">{def.label}</span>
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
          <div className="ws-empty-state">
            <p className="ws-empty-state-msg">Add widgets to customize your sidebar</p>
            {onNavigate && (
              <button className="ws-empty-add-btn" onClick={() => onNavigate("widgets")}>
                <LayoutGrid size={12} /> Add widgets
              </button>
            )}
          </div>
        )}
      </div>
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
