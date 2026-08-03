import { useEffect, useState } from "react";
import {
  GraduationCap, Pencil, Upload, CalendarDays, BookOpen,
  UserRound, Check, SlidersHorizontal,
} from "lucide-react";
import { nextDeadlines, daysAway, fmtDate } from "./deadlines.js";
import { cn } from "@/lib/utils";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const STORE_KEY = "ace_panel_widgets";

/* Major-neutral short labels for the progress rows. The matches are generic
   requirement-block vocabulary so they read correctly for any of the 749
   majors (a "Prescribed Courses" block → "Required", not "Core CS"). */
const REQ_LABEL_MAP = [
  { match: /prescribed|required|^core\b/i,         label: "Required"  },
  { match: /math|quantif/i,                        label: "Math"      },
  { match: /gen.*ed|general.*educ/i,               label: "Gen Ed"    },
  { match: /elective/i,                            label: "Electives" },
  { match: /science|physics|natural\s*sci/i,       label: "Science"   },
  { match: /writing|communication|english|speak/i, label: "Writing"   },
];

const reqLabel = (title) => {
  for (const { match, label } of REQ_LABEL_MAP) if (match.test(title)) return label;
  return title.length > 16 ? title.slice(0, 15) + "…" : title;
};

/**
 * The widget catalogue. `needsAudit` tiles are hidden entirely until a degree
 * audit is uploaded — a grid of "no data yet" tiles is worse than a smaller
 * grid — and they're also filtered out of the customise list, so the options
 * shown are always ones that would actually render something.
 */
const WIDGETS = [
  { id: "major",     label: "Major",           span: 2, needsAudit: false },
  { id: "progress",  label: "Degree progress", span: 1, needsAudit: true  },
  { id: "gpa",       label: "GPA",             span: 1, needsAudit: true  },
  { id: "deadlines", label: "Deadlines",       span: 2, needsAudit: false },
  { id: "taking",    label: "Taking now",      span: 2, needsAudit: true  },
  { id: "advisor",   label: "Advisor",         span: 2, needsAudit: true  },
];

const DEFAULT_ON = ["major", "progress", "gpa", "deadlines"];

function loadEnabled() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORE_KEY));
    // Drop ids that no longer exist so a renamed/removed widget can't wedge the
    // panel into rendering nothing.
    if (Array.isArray(raw)) return raw.filter((id) => WIDGETS.some((w) => w.id === id));
  } catch { /* corrupt or absent — fall through to defaults */ }
  return DEFAULT_ON;
}

/* ── Tile chrome ─────────────────────────────────────────────────────────── */
function Tile({ span = 1, className, children, ...rest }) {
  const Cmp = rest.onClick ? "button" : "div";
  return (
    <Cmp
      className={cn("wtile", span === 2 && "wtile--wide", rest.onClick && "wtile--action", className)}
      {...rest}
    >
      {children}
    </Cmp>
  );
}

const TileLabel = ({ children }) => (
  <span className="wtile-label">{children}</span>
);

/**
 * The control panel: a floating, glass-backed grid of widgets, opened from the
 * top bar on hover and pinned with a click. Sits OVER the chat rather than in a
 * third column, which is what lets the blur read as glass — there has to be
 * something behind it.
 */
export default function WidgetRail({
  selectedMajor, onChangeMajor, auditData, onNavigate,
  onMouseEnter, onMouseLeave, pinned,
}) {
  const [deadlines, setDeadlines] = useState(null); // null = loading, [] = none
  const [enabled, setEnabled] = useState(loadEnabled);
  const [customising, setCustomising] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/calendar`)
      .then((r) => r.json())
      .then((data) => { if (!cancelled) setDeadlines(nextDeadlines(data?.semesters, 3)); })
      .catch(() => { if (!cancelled) setDeadlines([]); });
    return () => { cancelled = true; };
  }, []);

  const toggle = (id) => {
    setEnabled((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      localStorage.setItem(STORE_KEY, JSON.stringify(next));
      return next;
    });
  };

  const hasAudit = !!auditData?.available;
  const pct = Math.min(100, Math.round(auditData?.degree_progress_pct ?? 0));
  const gpa = auditData?.progress?.cumulative_gpa;
  const taking = auditData?.in_progress_courses ?? [];
  const advisor = auditData?.advisor;

  const reqRows = hasAudit
    ? (auditData.remaining_requirements ?? [])
        .filter((r) => (r.credits_required ?? 0) > 0)
        .slice(0, 3)
        .map((r) => ({
          label: reqLabel(r.title),
          pct: Math.min(100, Math.round(((r.credits_required - (r.credits_needed ?? 0)) / r.credits_required) * 100)),
        }))
    : [];

  // Catalogue order wins over the order things were switched on, so the layout
  // is stable no matter how the user toggled them.
  const visible = WIDGETS.filter(
    (w) => enabled.includes(w.id) && (hasAudit || !w.needsAudit)
  );

  const tiles = {
    major: (
      <Tile key="major" span={2} onClick={onChangeMajor} title="Change major">
        <TileLabel>Major</TileLabel>
        <span className="wtile-major">
          <GraduationCap size={13} className="shrink-0 opacity-50" aria-hidden />
          <span className="truncate">{selectedMajor || "Set your major"}</span>
          <Pencil size={10} className="wtile-major-edit" aria-hidden />
        </span>
      </Tile>
    ),
    progress: (
      <Tile key="progress">
        <TileLabel>Progress</TileLabel>
        <span className="wtile-stat">{pct}<small>%</small></span>
        <div
          className="wtile-bar"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label="Degree completion"
        >
          <div className="wtile-bar-fill" style={{ width: `${pct}%` }} />
        </div>
        {reqRows.length > 0 && (
          <ul className="wtile-reqs">
            {reqRows.map((r) => (
              <li key={r.label}>
                <span className="truncate">{r.label}</span>
                <span className="tabular-nums opacity-60">{r.pct}%</span>
              </li>
            ))}
          </ul>
        )}
      </Tile>
    ),
    gpa: (
      <Tile key="gpa">
        <TileLabel>GPA</TileLabel>
        <span className="wtile-stat">
          {gpa != null ? Number(gpa).toFixed(2) : "—"}
        </span>
        <span className="wtile-sub">
          {auditData?.credits_completed ?? 0} credits earned
        </span>
      </Tile>
    ),
    deadlines: (
      <Tile key="deadlines" span={2}>
        <span className="wtile-head">
          <TileLabel>Deadlines</TileLabel>
          <button className="wtile-link" onClick={() => onNavigate("calendar")}>All dates</button>
        </span>
        {deadlines === null ? (
          <span className="wtile-sub">Loading…</span>
        ) : deadlines.length === 0 ? (
          <button className="wtile-empty" onClick={() => onNavigate("calendar")}>
            <CalendarDays size={12} aria-hidden /> Nothing scheduled
          </button>
        ) : (
          <ul className="wtile-dl">
            {deadlines.map((d) => {
              const days = daysAway(d.iso_date);
              return (
                <li key={`${d.iso_date}-${d.event}`}>
                  <span className="wtile-dl-date">{fmtDate(d.iso_date)}</span>
                  <span className="wtile-dl-body">
                    <span className="wtile-dl-event">{d.event}</span>
                    <span className="wtile-dl-when">
                      {days === 0 ? "Today" : days === 1 ? "Tomorrow" : `In ${days} days`}
                    </span>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Tile>
    ),
    taking: (
      <Tile key="taking" span={2}>
        <TileLabel>Taking now</TileLabel>
        {taking.length === 0 ? (
          <span className="wtile-sub">Nothing in progress</span>
        ) : (
          <span className="wtile-chips">
            {taking.slice(0, 6).map((c) => <span key={c} className="wchip">{c}</span>)}
          </span>
        )}
      </Tile>
    ),
    advisor: (
      <Tile key="advisor" span={2}>
        <TileLabel>Advisor</TileLabel>
        <span className="wtile-major">
          <UserRound size={13} className="shrink-0 opacity-50" aria-hidden />
          <span className="truncate">{advisor || "Not listed on your audit"}</span>
        </span>
      </Tile>
    ),
  };

  return (
    <aside
      className={cn("wpanel", pinned && "wpanel--pinned")}
      aria-label="Your status"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="wpanel-grid">
        {visible.map((w) => tiles[w.id])}

        {!hasAudit && (
          <Tile span={2} onClick={() => onNavigate("dashboard")} className="wtile--prompt">
            <Upload size={13} className="shrink-0 opacity-60" aria-hidden />
            <span className="flex flex-col gap-0.5 text-left">
              <strong>Upload your audit</strong>
              <span className="wtile-sub">Unlocks progress, GPA, and your advisor</span>
            </span>
          </Tile>
        )}

        {visible.length === 0 && hasAudit && (
          <Tile span={2} className="wtile--prompt">
            <BookOpen size={13} className="shrink-0 opacity-60" aria-hidden />
            <span className="wtile-sub">Everything is switched off — pick some below.</span>
          </Tile>
        )}
      </div>

      <div className="wpanel-foot">
        <button
          className={cn("wpanel-edit", customising && "wpanel-edit--on")}
          onClick={() => setCustomising((v) => !v)}
          aria-expanded={customising}
        >
          <SlidersHorizontal size={12} aria-hidden />
          {customising ? "Done" : "Customise"}
        </button>
      </div>

      {customising && (
        <div className="wpanel-picker">
          {WIDGETS.filter((w) => hasAudit || !w.needsAudit).map((w) => {
            const on = enabled.includes(w.id);
            return (
              <button
                key={w.id}
                className={cn("wpick", on && "wpick--on")}
                onClick={() => toggle(w.id)}
                role="switch"
                aria-checked={on}
              >
                <span className="wpick-box">{on && <Check size={10} strokeWidth={3} aria-hidden />}</span>
                {w.label}
              </button>
            );
          })}
          {WIDGETS.some((w) => w.needsAudit) && !hasAudit && (
            <span className="wtile-sub">Upload an audit to unlock the rest.</span>
          )}
        </div>
      )}
    </aside>
  );
}
