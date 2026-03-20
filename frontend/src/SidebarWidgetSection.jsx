import { useState, useRef, useEffect } from "react";

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
  { id: "deadlines", label: "Upcoming Deadlines", icon: "🗓️", viewId: "calendar",  desc: "Key dates & deadlines"            },
  { id: "progress",  label: "Degree Progress",    icon: "📊", viewId: "checklist", desc: "Track graduation requirements"    },
  { id: "gened",     label: "Gen Ed Explorer",    icon: "🎓", viewId: "gened",     desc: "Manage Gen Ed credits"            },
  { id: "resources", label: "Quick Resources",    icon: "🔗", viewId: "resources", desc: "Campus services & support"        },
  { id: "gpa",       label: "GPA Tracker",        icon: "🧮", viewId: "gpa",       desc: "Calculate & track your GPA"      },
  { id: "prereq",    label: "Course Map",         icon: "🗺️", viewId: "prereq",   desc: "Visualize course prerequisites"   },
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

  // Overall bar from credit totals
  const overall = {
    label: "Overall",
    pct: Math.min(100, Math.round(auditData.degree_progress_pct ?? 0)),
  };

  // Build per-category bars from unsatisfied blocks (up to 3)
  const cats = [];
  const seen = new Set();
  for (const req of (auditData.remaining_requirements ?? [])) {
    const cr = req.credits_required ?? 0;
    const needed = req.credits_needed ?? 0;
    if (cr <= 0) continue;
    const pct = Math.min(100, Math.round(((cr - needed) / cr) * 100));
    // Find a human label
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
  const cats = ["GQ","GN","GA","GH","GS","GHA","US","IL"];
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
  { icon: "💬", label: "CAPS Counseling",  url: "https://studentaffairs.psu.edu/counseling" },
  { icon: "📖", label: "LRC Tutoring",     url: "https://lrc.psu.edu/" },
  { icon: "💼", label: "Career Services",  url: "https://careerservices.psu.edu/" },
  { icon: "🩺", label: "UHS Medical",      url: "https://studentaffairs.psu.edu/health" },
];

function ResourcesWidget() {
  return (
    <div className="wc-body">
      {QUICK_RES.map(r => (
        <a key={r.label} className="wc-res-link" href={r.url} target="_blank" rel="noreferrer">
          <span>{r.icon}</span>
          <span className="wc-res-name">{r.label}</span>
          <span className="wc-res-arrow">↗</span>
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

/* ── Default config — only Deadlines on by default ───────────── */
function defaultConfig() {
  return {
    order:   ["deadlines", "progress", "gened", "resources", "gpa", "prereq"],
    enabled: { deadlines: true, progress: false, gened: false, resources: false, gpa: false, prereq: false },
  };
}

/* ── Main component ───────────────────────────────────────────── */
export default function SidebarWidgetSection({ userId, onNavigate, auditData }) {
  const storageKey = `ace_widgets2_${userId}`;   // new key → fresh defaults

  const [config, setConfig] = useState(() => {
    const def = defaultConfig();
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        // Merge any widget IDs added since last save
        const allIds  = WIDGET_DEFS.map(d => d.id);
        const missing = allIds.filter(id => !parsed.order.includes(id));
        return {
          order:   [...parsed.order, ...missing],
          enabled: { ...def.enabled, ...parsed.enabled },
        };
      }
    } catch {}
    return def;
  });

  const [showPicker, setShowPicker] = useState(false);
  const [dragOver, setDragOver]     = useState(null);
  const dragItem = useRef(null);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(config));
  }, [config, storageKey]);

  const toggleEnabled = id =>
    setConfig(p => ({ ...p, enabled: { ...p.enabled, [id]: !p.enabled[id] } }));

  /* drag-to-reorder (in picker) */
  const handleDragStart = (e, id) => {
    dragItem.current = id;
    e.dataTransfer.effectAllowed = "move";
  };
  const handleDragOver = (e, id) => {
    e.preventDefault();
    if (dragOver !== id) setDragOver(id);
  };
  const handleDrop = (e, targetId) => {
    e.preventDefault();
    if (!dragItem.current || dragItem.current === targetId) { setDragOver(null); return; }
    setConfig(p => {
      const order = [...p.order];
      const fi = order.indexOf(dragItem.current);
      const ti = order.indexOf(targetId);
      order.splice(fi, 1);
      order.splice(ti, 0, dragItem.current);
      return { ...p, order };
    });
    dragItem.current = null;
    setDragOver(null);
  };
  const handleDragEnd = () => { dragItem.current = null; setDragOver(null); };

  /* Notification badge: any deadline within 7 days */
  const deadlineBadge = SPRING_DEADLINES.some(d => {
    const ms = parseDate(d.date) - new Date();
    return ms >= 0 && ms <= 7 * 24 * 60 * 60 * 1000;
  });

  const enabledWidgets = config.order.filter(id => config.enabled[id]);

  return (
    <div className="ws-root">

      {/* ── Widget picker panel ── */}
      {showPicker && (
        <div className="ws-picker">
          <div className="ws-picker-top">
            <span className="ws-picker-title">Edit Widgets</span>
            <button className="ws-picker-done" onClick={() => setShowPicker(false)}>Done</button>
          </div>
          <p className="ws-picker-hint">Toggle to add · drag ⠿ to reorder</p>

          {config.order.map(id => {
            const def = WIDGET_DEFS.find(d => d.id === id);
            const on  = config.enabled[id];
            return (
              <div
                key={id}
                className={`ws-picker-row${dragOver === id ? " ws-picker-row--over" : ""}`}
                draggable
                onDragStart={e => handleDragStart(e, id)}
                onDragOver={e => handleDragOver(e, id)}
                onDrop={e => handleDrop(e, id)}
                onDragEnd={handleDragEnd}
              >
                <span className="ws-drag-handle">⠿</span>
                <span className="ws-picker-icon">{def.icon}</span>
                <div className="ws-picker-info">
                  <span className="ws-picker-name">{def.label}</span>
                  <span className="ws-picker-desc">{def.desc}</span>
                </div>
                <button
                  className={`ws-toggle${on ? " ws-toggle--on" : ""}`}
                  onClick={() => toggleEnabled(id)}
                >
                  <span className="ws-toggle-thumb" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Widget stack ── */}
      {!showPicker && (
        <div className="ws-stack">
          {enabledWidgets.map(id => {
            const def     = WIDGET_DEFS.find(d => d.id === id);
            const Content = WIDGET_COMPONENTS[id];
            const badge   = id === "deadlines" && deadlineBadge;
            return (
              <div key={id} className="ws-card">
                <div className="ws-card-header">
                  <span className="ws-card-icon">{def.icon}</span>
                  <span className="ws-card-label">{def.label}</span>
                  {badge && <span className="ws-badge" />}
                  {onNavigate && def.viewId && (
                    <button
                      className="ws-open-btn"
                      onClick={() => onNavigate(def.viewId)}
                      title={`Open ${def.label}`}
                    >
                      ↗
                    </button>
                  )}
                </div>
                <Content onNavigate={onNavigate} auditData={auditData} />
              </div>
            );
          })}

          {enabledWidgets.length === 0 && (
            <p className="ws-empty">No widgets added yet.</p>
          )}
        </div>
      )}

      {/* ── Edit button ── */}
      <button
        className={`ws-edit-btn${showPicker ? " ws-edit-btn--active" : ""}`}
        onClick={() => setShowPicker(v => !v)}
      >
        {showPicker ? "← Back" : "⊕ Edit Widgets"}
      </button>
    </div>
  );
}
