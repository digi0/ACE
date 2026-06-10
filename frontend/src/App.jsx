import { useState, useRef, useEffect, useCallback, lazy, Suspense } from "react";
import ReactMarkdown from "react-markdown";
import {
  ChevronRight, GraduationCap, BookOpen, CalendarClock,
  Compass, Upload, MessageSquare, Send, Paperclip, X, ExternalLink, Menu,
} from "lucide-react";
import { BGPattern } from "./BGPattern.jsx";
import Sidebar from "./Sidebar.jsx";
import { useAuth } from "./AuthContext.jsx";
import AccessGate from "./AccessGate.jsx";
import { apiFetch, apiStream } from "./api.js";
import { useIsMobile } from "./useIsMobile.js";
import MobileBottomNav from "./MobileBottomNav.jsx";

// Lazy-loaded views — each becomes its own chunk fetched on first use, so the
// initial load stays lean. LoginPage pulls in the ~226 kB tsparticles sparkles,
// so deferring it keeps that off the path for returning signed-in users.
const LoginPage           = lazy(() => import("./LoginPage.jsx"));
const OnboardingTour      = lazy(() => import("./OnboardingTour.jsx"));
const Dashboard           = lazy(() => import("./Dashboard.jsx"));
const ResourceHub         = lazy(() => import("./ResourceHub.jsx"));
const GpaCalculator       = lazy(() => import("./GpaCalculator.jsx"));
const AcademicCalendar    = lazy(() => import("./AcademicCalendar.jsx"));
const GraduationChecklist = lazy(() => import("./GraduationChecklist.jsx"));
const CoursePrereqMap     = lazy(() => import("./CoursePrereqMap.jsx"));
const SuggestedPlan       = lazy(() => import("./SuggestedPlan.jsx"));
const GenEdExplorer       = lazy(() => import("./GenEdExplorer.jsx"));

/* ── Icons ─────────────────────────────────────── */
function GradCapIcon({ size = 16 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="white"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {/* mortarboard top (diamond) + tassel line */}
      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
      {/* cap body with curved bottom */}
      <path d="M6 12v5c3 3 9 3 12 0v-5" />
    </svg>
  );
}


function AceLogo({ size = 36 }) {
  const iconSize = Math.round(size * 0.52);
  const radius = Math.round(size * 0.22);
  return (
    <div className="ace-logo-box" style={{ width: size, height: size, borderRadius: radius }}>
      <GradCapIcon size={iconSize} />
    </div>
  );
}

/* ── Constants ─────────────────────────────────── */
const SUGGESTION_CHIPS = [
  "Help me plan this semester",
  "What should I focus on this week?",
  "I'm worried about a deadline",
  "Check my schedule",
];

// Whiteboard quick-action cards on the empty welcome screen.
// Each card's `action` is resolved at render time inside App so it can
// access handleSend / fileInputRef / setActiveView etc.
const WELCOME_CARDS = [
  {
    icon: BookOpen,
    title: "Plan my semester",
    desc: "Lay out next term's courses",
    color: "blue",
    prompt: "Help me plan my courses for next semester. What should I be taking?",
  },
  {
    icon: GraduationCap,
    title: "Check graduation",
    desc: "How close am I to done?",
    color: "green",
    prompt: "What courses do I still need to graduate, and am I on track?",
  },
  {
    icon: CalendarClock,
    title: "Deadlines",
    desc: "What's due soon",
    color: "orange",
    prompt: "What Penn State deadlines should I be tracking right now?",
  },
  {
    icon: Compass,
    title: "Explore my major",
    desc: "Key requirements & courses",
    color: "purple",
    prompt: "Give me an overview of my major — the key required courses, electives, and what to focus on.",
  },
  {
    icon: Upload,
    title: "Upload your audit",
    desc: "Personalized analysis",
    color: "neutral",
    action: "upload",
  },
  {
    icon: MessageSquare,
    title: "Ask anything",
    desc: "Free-form chat",
    color: "neutral",
    action: "focus-input",
  },
];

const FOLLOW_UP_MAP = {
  courses:          ["What are the prerequisites?", "When is this offered?", "How does this fit my degree plan?"],
  student_progress: ["What courses do I still need?", "Am I on track to graduate?", "What's my GPA situation?"],
  wellbeing:        ["How do I schedule a CAPS appointment?", "Are there peer support options?", "What other wellness resources exist?"],
  substitution:     ["Who approves substitutions?", "What's the petition process?", "Can a different course count instead?"],
  etm:              ["What elective options do I have?", "How many elective credits do I need?", "Suggest related courses"],
  transfer:         ["Will this transfer credit count?", "How do I request a transfer evaluation?", "What documentation do I need?"],
  gen_ed:           ["What Gen Ed do I still need?", "Which courses double-dip with my major?", "What's the easiest way to finish Gen Ed?"],
  financial_aid:    ["How do I contact the Office of Student Aid?", "Where do I start with FAFSA?", "What scholarships does Penn State offer?"],
  international:     ["How do I reach an international student adviser?", "Where do I ask about my visa status?", "What support does Penn State Global offer?"],
  general:          ["Tell me more", "How does this affect my graduation?", "What should I do next?"],
};


const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/* ── MajorSelectModal ──────────────────────────── */
function MajorSelectModal({ userId, onSelect, onSkip }) {
  const [programs, setPrograms]   = useState([]);
  const [query, setQuery]         = useState("");
  const [loading, setLoading]     = useState(true);
  const [saving, setSaving]       = useState(false);
  const [selected, setSelected]   = useState(null);

  useEffect(() => {
    fetch(`${API}/programs?degree_type=baccalaureate`)
      .then((r) => r.json())
      .then((data) => { setPrograms(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = query.trim()
    ? programs.filter((p) =>
        p.program_name.toLowerCase().includes(query.trim().toLowerCase())
      )
    : programs;

  const handleConfirm = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await apiFetch(`/user/major`, {
        method: "POST",
        body: JSON.stringify({ major: selected.program_name }),
      });
      onSelect(selected.program_name);
    } catch {
      onSelect(selected.program_name);   // store locally even if API fails
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="major-modal-overlay">
      <div className="major-modal">
        <div className="major-modal-header">
          <GraduationCap size={20} strokeWidth={1.75} />
          <h2 className="major-modal-title">What's your major?</h2>
        </div>
        <p className="major-modal-desc">
          ACE will personalize Gen Ed suggestions, course recommendations, and advising
          context for your specific degree program.
        </p>
        <input
          className="major-modal-search"
          type="text"
          placeholder="Search programs (e.g. Computer Science, Psychology…)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <div className="major-modal-list">
          {loading ? (
            <div className="major-modal-loading">
              <div className="loading-dots"><span /><span /><span /></div>
            </div>
          ) : filtered.length === 0 ? (
            <p className="major-modal-empty">No programs found.</p>
          ) : (
            filtered.slice(0, 80).map((p) => (
              <button
                key={p.program_name}
                className={`major-modal-item${selected?.program_name === p.program_name ? " major-modal-item--selected" : ""}`}
                onClick={() => setSelected(p)}
              >
                <span className="major-modal-item-name">{p.program_name}</span>
                <span className="major-modal-item-college">{p.college?.replace(/-/g, " ")}</span>
              </button>
            ))
          )}
        </div>
        <div className="major-modal-actions">
          <button className="major-modal-skip" onClick={onSkip}>
            I haven't declared a major yet
          </button>
          <button
            className="major-modal-confirm"
            disabled={!selected || saving}
            onClick={handleConfirm}
          >
            {saving ? "Saving…" : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── App ───────────────────────────────────────── */
function App() {
  const { user, syncData, signOut } = useAuth();
  const [accessOk, setAccessOk] = useState(
    () => typeof window !== "undefined" && localStorage.getItem("ace_access_ok") === "1"
  );
  const [showTour, setShowTour] = useState(false);
  // tourDone gates the major modal: it must not appear until the first-time
  // tour has been taken or skipped (otherwise the two overlay each other).
  // For returning (already-onboarded) users it flips true immediately.
  const [tourDone, setTourDone] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => typeof window !== "undefined" && window.innerWidth < 900
  );
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [activeView, setActiveView] = useState("chat");
  const [followUpChips, setFollowUpChips] = useState([]);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("ace_darkmode") === "1");
  const [auditData, setAuditData] = useState(null);

  const [selectedMajor, setSelectedMajor] = useState(null);
  const [showMajorModal, setShowMajorModal] = useState(false);

  const [headerText, setHeaderText] = useState('');
  const fileInputRef = useRef(null);
  const chatInputRef = useRef(null);

  const messagesEndRef = useRef(null);
  const hasMessages = messages.length > 0;
  const isMobile = useIsMobile();

  // Typewriter for top-bar title on mount
  useEffect(() => {
    const full = ' | Academic Counseling Engine';
    let i = 0;
    const start = setTimeout(() => {
      const iv = setInterval(() => {
        i++;
        setHeaderText(full.slice(0, i));
        if (i >= full.length) clearInterval(iv);
      }, 45);
      return () => clearInterval(iv);
    }, 700);
    return () => clearTimeout(start);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Auto-grow the chat textarea with its content, up to a max height
  useEffect(() => {
    const el = chatInputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  // Keep the active conversation's stored messages in sync
  useEffect(() => {
    if (!activeConvId || messages.length === 0) return;
    setConversations((prev) =>
      prev.map((c) => (c.id === activeConvId ? { ...c, messages } : c))
    );
  }, [messages, activeConvId]);

  // ── Reset all user-scoped state when the signed-in user changes ──
  useEffect(() => {
    setMessages([]);
    setInput("");
    setConversations([]);
    setActiveConvId(null);
    setFollowUpChips([]);
    setAuditData(null);
    setSelectedMajor(null);
    setUploadedFile(null);
    setUploadStatus("");
    setActiveView("chat");
    setShowTour(false);
    setShowMajorModal(false);
    setTourDone(false);
  }, [user?.uid]);

  // ── Dark mode ──
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
    localStorage.setItem("ace_darkmode", darkMode ? "1" : "0");
  }, [darkMode]);

  // ── Fetch audit data on mount (document may already be uploaded) ──
  useEffect(() => {
    if (!user?.uid) return;
    apiFetch("/dashboard")
      .then(r => r.json())
      .then(d => { if (d.available) setAuditData(d); })
      .catch(() => {});
  }, [user?.uid]);

  // ── Conversation persistence: load ──
  useEffect(() => {
    if (!user?.uid) return;
    try {
      const saved = localStorage.getItem(`ace_chats_${user.uid}`);
      if (saved) setConversations(JSON.parse(saved));
    } catch {}
  }, [user?.uid]);

  // ── Conversation persistence: save ──
  useEffect(() => {
    if (!user?.uid) return;
    localStorage.setItem(`ace_chats_${user.uid}`, JSON.stringify(conversations));
  }, [conversations, user?.uid]);

  // ── Show tour for first-time users ──
  useEffect(() => {
    if (!user?.uid) return;
    const key = `ace_onboarded_${user.uid}`;
    if (!localStorage.getItem(key)) {
      const t = setTimeout(() => setShowTour(true), 900);
      return () => clearTimeout(t);
    }
    // Already onboarded — no tour, so the major modal may proceed immediately.
    setTourDone(true);
  }, [user?.uid]);

  const handleTourFinish = () => {
    setShowTour(false);
    setTourDone(true);   // unblocks the major modal (see major-selection effect)
    if (user?.uid) localStorage.setItem(`ace_onboarded_${user.uid}`, "1");
  };

  // ── Major selection ──
  // Source of truth is syncData from /auth/sync (hydrated before user state
  // propagates, so no race). localStorage cache is kept as a paint-immediately
  // hint while syncData is still null on this render.
  useEffect(() => {
    if (!user?.uid) return;
    const cacheKey = `ace_major_${user.uid}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached && !selectedMajor) setSelectedMajor(cached);

    if (!syncData) return;  // wait for /auth/sync to land
    if (syncData.major) {
      setSelectedMajor(syncData.major);
      localStorage.setItem(cacheKey, syncData.major);
    } else if (!cached && tourDone) {
      // Only prompt for major AFTER the tour is taken/skipped, so the two
      // don't pop over one another. tourDone is in the deps, so finishing the
      // tour re-runs this effect and surfaces the modal then.
      const skipKey = `ace_major_skipped_${user.uid}`;
      if (!localStorage.getItem(skipKey)) {
        const t = setTimeout(() => setShowMajorModal(true), 500);
        return () => clearTimeout(t);
      }
    }
  }, [user?.uid, syncData, tourDone]);

  const handleMajorSelect = useCallback((majorName) => {
    setSelectedMajor(majorName);
    setShowMajorModal(false);
    if (user?.uid) localStorage.setItem(`ace_major_${user.uid}`, majorName);
  }, [user?.uid]);

  const handleMajorSkip = useCallback(() => {
    setShowMajorModal(false);
    if (user?.uid) localStorage.setItem(`ace_major_skipped_${user.uid}`, "1");
  }, [user?.uid]);

  // ── Send (real SSE streaming) ──
  const handleSend = async (text) => {
    const query = (text !== undefined ? text : input).trim();
    if (!query || loading) return;

    const userMsg = { role: "user", content: query };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    setFollowUpChips([]);

    if (messages.length === 0) {
      const convId = Date.now();
      setActiveConvId(convId);
      setConversations((prev) => [{ preview: query, id: convId, messages: [] }, ...prev]);
    }

    // Build history from prior completed messages (cap at 6 = 3 turns)
    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .filter((m) => !m.streaming)
      .map((m) => ({ role: m.role, content: m.content }))
      .slice(-6);

    try {
      const response = await apiStream("/chat/stream", { question: query, history });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let started = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          let data;
          try { data = JSON.parse(part.slice(6)); } catch { continue; }

          if (data.text !== undefined) {
            if (!started) {
              started = true;
              setLoading(false);
              setMessages([...newMessages, {
                role: "assistant", content: data.text, sources: [], streaming: true,
              }]);
            } else {
              setMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = {
                  ...next[next.length - 1],
                  content: next[next.length - 1].content + data.text,
                };
                return next;
              });
            }
          }

          if (data.done) {
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                ...next[next.length - 1],
                streaming: false,
                sources: data.sources ?? [],
              };
              return next;
            });
            const chips = FOLLOW_UP_MAP[data.intent] ?? FOLLOW_UP_MAP.general;
            setFollowUpChips(chips);
          }

          if (data.error) {
            setLoading(false);
            setMessages([...newMessages, {
              role: "assistant",
              content: "The chatbot could not answer right now. Please try again.",
              sources: [], streaming: false,
            }]);
          }
        }
      }
    } catch {
      setLoading(false);
      setMessages([...newMessages, {
        role: "assistant",
        content: "Could not connect to the backend. Make sure the backend server is running.",
        sources: [], streaming: false,
      }]);
    }
  };

  // ── File upload ──
  const handleFileUpload = async (file) => {
    if (!file) return;
    if (!user?.uid) { setUploadStatus("Sign in to upload"); return; }
    setUploadStatus("Uploading...");
    setUploadedFile(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await apiFetch("/upload-student-doc", {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadedFile(file);
        setUploadStatus("Uploaded");
        // Fetch parsed audit data and push it to the widget section
        try {
          const dashRes = await apiFetch("/dashboard");
          const dashData = await dashRes.json();
          if (dashData.available) setAuditData(dashData);
          // Use auto-detected major if user hasn't set one yet
          if (data.detected_major && !selectedMajor) {
            setSelectedMajor(data.detected_major);
          }
        } catch {}
      } else {
        setUploadStatus(data.detail || "Upload failed");
      }
    } catch {
      setUploadStatus("Could not upload file");
    }
  };

  const handleClearFile = async () => {
    setUploadedFile(null);
    setUploadStatus("");
    setAuditData(null);
    if (!user?.uid) return;
    try {
      await apiFetch("/clear-student-doc", { method: "POST" });
    } catch {}
  };

  const handleSwitchConversation = (conv) => {
    setMessages(conv.messages);
    setActiveConvId(conv.id);
    setInput("");
    if (isMobile) setSidebarCollapsed(true);
  };

  const handleNewConversation = () => {
    setMessages([]);
    setInput("");
    setUploadedFile(null);
    setUploadStatus("");
    setActiveConvId(null);
    if (isMobile) setSidebarCollapsed(true);
  };

  // Switch the main view; on mobile this also closes the slide-in drawer.
  const navigate = useCallback((view) => {
    setActiveView(view);
    if (isMobile) setSidebarCollapsed(true);
  }, [isMobile]);

  // ── Pilot access gate: ACE is invite-only until the first cohort is in.
  // The code is verified server-side (ACCESS_CODE on the backend); a
  // successful unlock is remembered per-browser.
  if (!accessOk) {
    return <AccessGate onUnlock={() => setAccessOk(true)} />;
  }

  // Still checking auth state
  if (user === undefined) {
    return (
      <div className="auth-loading">
        <div className="loading-dots"><span /><span /><span /></div>
        <p>Loading…</p>
      </div>
    );
  }

  // Not signed in → show login page
  if (user === null) {
    return (
      <Suspense fallback={<div className="auth-loading"><div className="loading-dots"><span /><span /><span /></div></div>}>
        <LoginPage />
      </Suspense>
    );
  }

  return (
    <div className={`app-layout${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>

      {/* ── Sidebar ─────────────────────────── */}
      <Sidebar
        user={user} signOut={signOut}
        selectedMajor={selectedMajor} setShowMajorModal={setShowMajorModal}
        auditData={auditData}
        darkMode={darkMode} setDarkMode={setDarkMode}
        onCollapse={() => setSidebarCollapsed(true)}
        conversations={conversations} activeConvId={activeConvId}
        onSwitchConversation={handleSwitchConversation}
        onNewConversation={handleNewConversation}
        onStartTour={() => setShowTour(true)}
        onNavigate={navigate}
      />

      {sidebarCollapsed && (
        <button
          className="sidebar-expand-btn"
          onClick={() => setSidebarCollapsed(false)}
          title="Open sidebar"
        >
          <ChevronRight size={15} />
        </button>
      )}

      {/* Mobile drawer backdrop — only visible when sidebar is open AND
          viewport is in drawer mode (the .sidebar-backdrop class is hidden
          via CSS above 900px). */}
      {!sidebarCollapsed && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarCollapsed(true)}
          aria-hidden
        />
      )}

      {/* ── Main panel ──────────────────────── */}
      <div className="main-panel">

        <header className="top-bar">
          <div className="top-bar-brand">
            <button
              className="top-bar-hamburger"
              onClick={() => setSidebarCollapsed(false)}
              aria-label="Open menu"
            >
              <Menu size={20} aria-hidden />
            </button>
            <AceLogo size={30} />
            <span className="top-bar-name">ACE</span>
            <span className="top-bar-subtitle">{headerText}</span>
          </div>
          <nav className="top-bar-nav">
            <button
              className={`top-bar-tab${activeView === "chat" ? " top-bar-tab--active" : ""}`}
              onClick={() => setActiveView("chat")}
            >
              Chat
            </button>
            <button
              data-tour="dashboard-tab"
              className={`top-bar-tab${activeView === "dashboard" ? " top-bar-tab--active" : ""}`}
              onClick={() => setActiveView("dashboard")}
            >
              Dashboard
            </button>
            <button
              className={`top-bar-tab${activeView === "resources" ? " top-bar-tab--active" : ""}`}
              onClick={() => setActiveView("resources")}
            >
              Resources
            </button>
            <button
              className={`top-bar-tab${activeView === "gened" ? " top-bar-tab--active" : ""}`}
              onClick={() => setActiveView("gened")}
            >
              Gen Ed
            </button>
          </nav>
        </header>

        {/* Hidden file input reused by dashboard empty state */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.doc,.docx"
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files[0]) {
              handleFileUpload(e.target.files[0]);
              setActiveView("chat");
            }
          }}
        />

        <Suspense fallback={<div className="dashboard-area"><div className="loading-dots"><span /><span /><span /></div></div>}>
        {activeView === "resources" ? (
          <div className="dashboard-area">
            <ResourceHub />
          </div>
        ) : activeView === "gpa" ? (
          <div className="dashboard-area">
            <GpaCalculator userId={user.uid} progress={auditData?.progress} />
          </div>
        ) : activeView === "calendar" ? (
          <div className="dashboard-area">
            <AcademicCalendar />
          </div>
        ) : activeView === "checklist" ? (
          <div className="dashboard-area">
            <GraduationChecklist userId={user.uid} progress={auditData?.progress} />
          </div>
        ) : activeView === "prereq" ? (
          <div className="dashboard-area">
            <CoursePrereqMap userId={user.uid} progress={auditData?.progress} selectedMajor={selectedMajor} />
          </div>
        ) : activeView === "plan" ? (
          <div className="dashboard-area">
            <SuggestedPlan selectedMajor={selectedMajor} progress={auditData?.progress} />
          </div>
        ) : activeView === "gened" ? (
          <div className="dashboard-area">
            <GenEdExplorer userId={user.uid} selectedMajor={selectedMajor} progress={auditData?.progress} />
          </div>
        ) : activeView === "dashboard" ? (
          <div className="dashboard-area">
            <Dashboard
              uploadedFile={uploadedFile}
              onUploadClick={() => fileInputRef.current?.click()}
              onRemoveClick={handleClearFile}
              userId={user?.uid}
            />
          </div>
        ) : (
        <>
        <div className="chat-area">
          <BGPattern variant="dots" fill="#e4e4e7" size={20} />
          {!hasMessages ? (
            <div className="wb-welcome">
              <div className="wb-welcome-head">
                <h1 className="wb-headline">
                  What are we planning <span className="wb-headline-accent">today?</span>
                </h1>
                <p className="wb-subline">
                  Pick a starting point — or just ask.
                </p>
              </div>

              <div className="wb-card-grid">
                {WELCOME_CARDS.map((card) => {
                  const Icon = card.icon;
                  const onClick = () => {
                    if (card.action === "upload") {
                      fileInputRef.current?.click();
                    } else if (card.action === "focus-input") {
                      chatInputRef.current?.focus();
                    } else if (card.prompt) {
                      handleSend(card.prompt);
                    }
                  };
                  return (
                    <button
                      key={card.title}
                      className={`wb-card wb-card--${card.color}`}
                      onClick={onClick}
                    >
                      <div className="wb-card-icon">
                        <Icon size={18} strokeWidth={1.75} />
                      </div>
                      <div className="wb-card-text">
                        <span className="wb-card-title">{card.title}</span>
                        <span className="wb-card-desc">{card.desc}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((msg, i) => (
                <div key={i} className={`message message--${msg.role}`}>
                  {msg.role === "assistant" && (
                    <div className="msg-avatar">
                      <AceLogo size={28} />
                    </div>
                  )}
                  <div className="message-bubble">
                    {msg.role === "assistant" ? (
                      <>
                        <div className="answer-body">
                          <ReactMarkdown
                            components={{
                              a: ({ node, ...props }) => (
                                <a {...props} target="_blank" rel="noreferrer" />
                              ),
                            }}
                          >{msg.content}</ReactMarkdown>
                          {msg.streaming && <span className="typing-cursor" />}
                        </div>
                        {!msg.streaming && msg.sources?.length > 0 && (
                          <div className="message-sources">
                            {msg.sources.map((s, si) => (
                              <div key={si} className="source-chip">
                                {s.title || "Official Source"}
                                {s.link && (
                                  <a href={s.link} target="_blank" rel="noreferrer" className="source-chip-link" aria-label="Open source">
                                    <ExternalLink size={11} strokeWidth={2.25} aria-hidden />
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="message message--assistant">
                  <div className="msg-avatar"><AceLogo size={28} /></div>
                  <div className="message-bubble">
                    <div className="loading-dots"><span /><span /><span /></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="input-section">
          {hasMessages && !loading && followUpChips.length > 0 && (
            <div className="followup-chips-row">
              {followUpChips.map((chip) => (
                <button
                  key={chip}
                  className="followup-chip"
                  onClick={() => handleSend(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          )}

          {(uploadedFile || (uploadStatus && uploadStatus !== "Uploaded")) && (
            <div className={`upload-badge${uploadedFile ? " upload-badge--ok" : ""}`}>
              {uploadedFile ? (
                <>
                  <span>✓</span>
                  <span>{uploadedFile.name}</span>
                  <button className="upload-badge-x" onClick={handleClearFile} aria-label="Remove uploaded file"><X size={14} strokeWidth={2.25} aria-hidden /></button>
                </>
              ) : (
                <span>{uploadStatus}</span>
              )}
            </div>
          )}

          <div className="input-bar" data-tour="chat-input">
            <label className="attach-btn" data-tour="upload-btn" title="Upload degree audit or what-if report">
              <Paperclip size={17} strokeWidth={1.75} aria-hidden />
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                style={{ display: "none" }}
                onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0])}
              />
            </label>
            <textarea
              ref={chatInputRef}
              className="chat-input"
              rows={1}
              placeholder="Type, paste, or upload..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <button
              className="send-btn"
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              title="Send"
              aria-label="Send message"
            >
              <Send size={16} strokeWidth={2} aria-hidden />
            </button>
          </div>

          <p className="input-disclaimer">ACE is a planning tool. Always confirm academic decisions with your advisor.</p>

        </div>
        </>
        )}
        </Suspense>

        {isMobile && (
          <MobileBottomNav activeView={activeView} onNavigate={navigate} />
        )}
      </div>

      {/* ── Onboarding tour ──────────────────── */}
      {showTour && (
        <Suspense fallback={null}>
          <OnboardingTour onFinish={handleTourFinish} />
        </Suspense>
      )}

      {/* ── Major selection modal ─────────────── */}
      {showMajorModal && (
        <MajorSelectModal
          userId={user.uid}
          onSelect={handleMajorSelect}
          onSkip={handleMajorSkip}
        />
      )}
    </div>
  );
}

export default App;
