import {
  ChevronLeft, GraduationCap, LogOut, Pencil,
  Plus, Compass, MessageSquare, Calculator, LayoutGrid,
  BookOpen, Upload, AlertCircle, Info, CheckCircle,
} from "lucide-react";
import ThemeToggle from "./ThemeToggle";

/* ── Deadlines (Spring 2026 — calendar scraper will replace) ── */
const SPRING_DEADLINES = [
  { iso: "2026-01-13", label: "First day of classes" },
  { iso: "2026-01-17", label: "Last day to add (full-sem)" },
  { iso: "2026-01-20", label: "MLK Day – No classes" },
  { iso: "2026-02-14", label: "Last day to drop (no W)" },
  { iso: "2026-03-09", label: "Spring Break begins" },
  { iso: "2026-03-21", label: "Last day to withdraw (W)" },
  { iso: "2026-04-11", label: "Last day of classes" },
  { iso: "2026-04-12", label: "Final Exams begin" },
  { iso: "2026-05-10", label: "Summer tuition due" },
];

const REQ_LABEL_MAP = [
  { match: /prescribed|core\s*cs|cmpsc.*required/i, label: "Core CS"      },
  { match: /math|quantif/i,                          label: "Math"         },
  { match: /gen.*ed|general.*educ/i,                 label: "Gen Ed"       },
  { match: /elective/i,                              label: "Electives"    },
  { match: /science|physics/i,                       label: "Science"      },
  { match: /writing|communication|english/i,         label: "Writing"      },
  { match: /data|cds|computational/i,                label: "Data Science" },
];

const TOOLS = [
  { id: "gpa",       label: "GPA Calc",  Icon: Calculator },
  { id: "gened",     label: "Gen Ed",    Icon: LayoutGrid },
  { id: "prereq",    label: "Prereqs",   Icon: Compass    },
  { id: "resources", label: "Resources", Icon: BookOpen   },
];

/* ── Helpers ── */
function daysAway(iso) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((new Date(iso + "T00:00:00") - today) / 86400000);
}

function fmtDate(iso) {
  const [, mm, dd] = iso.split("-").map(Number);
  const M = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${M[mm]} ${dd}`;
}

function reqLabel(title) {
  for (const { match, label } of REQ_LABEL_MAP) {
    if (match.test(title)) return label;
  }
  return title.length > 16 ? title.slice(0, 15) + "…" : title;
}

/* ── Logo: 7px radius square, black bg, gold grad cap ── */
function SbLogo() {
  return (
    <div className="sb-logo">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
        stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
        aria-hidden>
        <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
        <path d="M6 12v5c3 3 9 3 12 0v-5" />
      </svg>
    </div>
  );
}

/* ── Main component ── */
export default function Sidebar({
  user, signOut,
  selectedMajor, setShowMajorModal,
  auditData,
  darkMode, setDarkMode,
  onCollapse,
  onNavigate,
  conversations, activeConvId,
  onSwitchConversation,
  onNewConversation,
  onStartTour,
}) {
  const displayName = user?.displayName || user?.email || "";
  const initials = displayName
    .split(/[\s@]/).filter(Boolean)
    .map(n => n[0]).join("").slice(0, 2).toUpperCase();

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const upcomingDeadlines = SPRING_DEADLINES
    .map(d => ({ ...d, days: daysAway(d.iso) }))
    .filter(d => d.days >= 0)
    .slice(0, 3);

  const hasAudit = auditData && auditData.available;

  const reqRows = hasAudit
    ? (auditData.remaining_requirements ?? [])
        .filter(r => (r.credits_required ?? 0) > 0)
        .slice(0, 4)
        .map(r => {
          const cr = r.credits_required;
          const needed = r.credits_needed ?? 0;
          return { label: reqLabel(r.title), pct: Math.min(100, Math.round(((cr - needed) / cr) * 100)) };
        })
    : [];

  return (
    <aside className="sidebar" data-tour="sidebar">

      {/* ── Top: brand + user + major ── */}
      <div className="sb-top">
        <div className="sb-header">
          <div className="sb-brand">
            <SbLogo />
            <span className="sb-brand-name">ACE</span>
          </div>
          <div className="sb-header-btns">
            <ThemeToggle value={darkMode} onChange={setDarkMode} size={18} />
            <button className="sb-icon-btn" onClick={onCollapse} title="Collapse sidebar">
              <ChevronLeft size={14} />
            </button>
          </div>
        </div>

        <div className="sb-user">
          <div className="sb-avatar">{initials}</div>
          <div className="sb-user-info">
            <div className="sb-user-name">{user?.displayName || user?.email}</div>
            <div className="sb-user-email">{user?.email}</div>
          </div>
          <button className="sb-icon-btn" title="Sign out" onClick={signOut}>
            <LogOut size={13} />
          </button>
        </div>

        <button className="sb-major" onClick={() => setShowMajorModal(true)}>
          <GraduationCap size={12} className="sb-major-icon" />
          {selectedMajor
            ? <span className="sb-major-name">{selectedMajor}</span>
            : <span className="sb-major-name sb-major-name--empty">Set your major</span>
          }
          <Pencil size={10} className="sb-major-edit" />
        </button>

        <hr className="sb-divider" />
      </div>

      {/* ── Middle: scrollable content ── */}
      <div className="sb-middle">

        {/* Status Card or Upload Prompt */}
        {hasAudit ? (
          <div className="sb-status">
            <div className="sb-status-hdr">
              <span className="sb-section-label">DEGREE PROGRESS</span>
              <span className={`sb-status-badge sb-status-badge--${(auditData.status || "in-progress").toLowerCase().replace(/\s+/g, "-")}`}>
                {auditData.status || "In Progress"}
              </span>
            </div>

            <div className="sb-stat-row">
              <span className="sb-stat-big">{Math.round(auditData.degree_progress_pct ?? 0)}</span>
              <span className="sb-stat-suffix">% complete</span>
            </div>

            <div className="sb-bar">
              <div className="sb-bar-fill" style={{ width: `${Math.min(100, auditData.degree_progress_pct ?? 0)}%` }} />
            </div>

            <div className="sb-stat-sub">
              {auditData.credits_completed ?? 0} of {auditData.credits_required ?? 0} credits earned
            </div>

            {reqRows.length > 0 && (
              <div className="sb-reqs">
                {reqRows.map((r, i) => (
                  <div key={i} className="sb-req-row">
                    <span className="sb-req-label">{r.label}</span>
                    <span className="sb-req-pct">{r.pct}%</span>
                    <div className="sb-req-bar">
                      <div className={`sb-req-fill ${r.pct >= 70 ? "sb-req-fill--dark" : "sb-req-fill--gold"}`}
                        style={{ width: `${r.pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {auditData.alerts && auditData.alerts.length > 0 && (
              <div className="sb-alerts">
                {auditData.alerts.slice(0, 2).map((a, i) => (
                  <div key={i} className={`sb-alert sb-alert--${a.type}`}>
                    {a.type === "warning" && <AlertCircle size={10} />}
                    {a.type === "success" && <CheckCircle size={10} />}
                    {a.type === "info"    && <Info size={10} />}
                    <span>{a.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <button className="sb-upload-compact" onClick={() => onNavigate("chat")}>
            <Upload size={13} className="sb-upload-compact-icon" />
            <span className="sb-upload-compact-text">
              Upload audit for personalized dashboard
            </span>
          </button>
        )}

        {/* Deadlines */}
        <div className="sb-section">
          <div className="sb-section-hdr">
            <span className="sb-section-label">DEADLINES</span>
            <button className="sb-section-link" onClick={() => onNavigate("calendar")}>All dates</button>
          </div>
          {upcomingDeadlines.length === 0 ? (
            <button
              className="sb-empty sb-empty-link"
              onClick={() => onNavigate("calendar")}
            >
              Spring 2026 complete — view full calendar
            </button>
          ) : upcomingDeadlines.map((d, i) => (
            <div key={i} className="sb-dl-row">
              <span className="sb-dl-date">{fmtDate(d.iso)}</span>
              <span className={`sb-dl-dot sb-dl-dot--${d.days <= 7 ? "red" : d.days <= 21 ? "amber" : "gray"}`} />
              <div className="sb-dl-info">
                <span className="sb-dl-label">{d.label}</span>
                <span className="sb-dl-meta">{d.days}d away</span>
              </div>
            </div>
          ))}
        </div>

        {/* Tools */}
        <div className="sb-section">
          <div className="sb-section-hdr">
            <span className="sb-section-label">TOOLS</span>
          </div>
          <div className="sb-tools-grid">
            {TOOLS.map(({ id, label, Icon }) => (
              <button key={id} className="sb-tool-btn" onClick={() => onNavigate(id)}>
                <Icon size={13} className="sb-tool-icon" />
                <span className="sb-tool-label">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Recent chats */}
        <div className="sb-section">
          <div className="sb-section-hdr">
            <span className="sb-section-label">RECENT</span>
          </div>
          {conversations.length === 0 ? (
            <p className="sb-empty">No previous chats</p>
          ) : conversations.slice(0, 5).map(conv => (
            <button
              key={conv.id}
              className={`sb-chat-btn${activeConvId === conv.id ? " sb-chat-btn--active" : ""}`}
              onClick={() => onSwitchConversation(conv)}
            >
              <MessageSquare size={12} className="sb-chat-icon" />
              <span className="sb-chat-preview">{conv.preview}</span>
            </button>
          ))}
        </div>

      </div>

      {/* ── Bottom: actions ── */}
      <div className="sb-bottom">
        <button className="sb-new-btn" onClick={onNewConversation}>
          <Plus size={13} strokeWidth={2} />
          New conversation
        </button>
        <button className="sb-tour-btn" onClick={onStartTour}>
          <Compass size={12} />
          Take the tour
        </button>
      </div>
    </aside>
  );
}
