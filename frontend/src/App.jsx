import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { ChevronRight, GraduationCap } from "lucide-react";
import { BGPattern } from "./BGPattern.jsx";
import Dashboard from "./Dashboard.jsx";
import ResourceHub from "./ResourceHub.jsx";
import GpaCalculator from "./GpaCalculator.jsx";
import LoginPage from "./LoginPage.jsx";
import OnboardingTour from "./OnboardingTour.jsx";
import Sidebar from "./Sidebar.jsx";
import AcademicCalendar from "./AcademicCalendar.jsx";
import GraduationChecklist from "./GraduationChecklist.jsx";
import CoursePrereqMap from "./CoursePrereqMap.jsx";
import GenEdExplorer from "./GenEdExplorer.jsx";
import { useAuth } from "./AuthContext.jsx";

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

const FOLLOW_UP_MAP = {
  courses:          ["What are the prerequisites?", "When is this offered?", "How does this fit my degree plan?"],
  student_progress: ["What courses do I still need?", "Am I on track to graduate?", "What's my GPA situation?"],
  wellbeing:        ["How do I schedule a CAPS appointment?", "Are there peer support options?", "What other wellness resources exist?"],
  substitution:     ["Who approves substitutions?", "What's the petition process?", "Can a different course count instead?"],
  etm:              ["What elective options do I have?", "How many elective credits do I need?", "Suggest related courses"],
  transfer:         ["Will this transfer credit count?", "How do I request a transfer evaluation?", "What documentation do I need?"],
  gen_ed:           ["What Gen Ed counts for CS students?", "Which courses double-dip?", "What's the easiest way to finish Gen Ed?"],
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
      await fetch(`${API}/user/major`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ major: selected.program_name, user_id: userId }),
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
            Skip for now
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
  const { user, signOut } = useAuth();
  const [showTour, setShowTour] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
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

  const messagesEndRef = useRef(null);
  const hasMessages = messages.length > 0;

  // Typewriter for top-bar title on mount
  useEffect(() => {
    const full = ' | Academic Counselling Engine';
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

  // Keep the active conversation's stored messages in sync
  useEffect(() => {
    if (!activeConvId || messages.length === 0) return;
    setConversations((prev) =>
      prev.map((c) => (c.id === activeConvId ? { ...c, messages } : c))
    );
  }, [messages, activeConvId]);

  // ── Dark mode ──
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
    localStorage.setItem("ace_darkmode", darkMode ? "1" : "0");
  }, [darkMode]);

  // ── Fetch audit data on mount (document may already be uploaded) ──
  useEffect(() => {
    if (!user?.uid) return;
    fetch(`${API}/dashboard?user_id=${encodeURIComponent(user.uid)}`)
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
  }, [user?.uid]);

  const handleTourFinish = () => {
    setShowTour(false);
    if (user?.uid) localStorage.setItem(`ace_onboarded_${user.uid}`, "1");
  };

  // ── Major selection ──
  useEffect(() => {
    if (!user?.uid) return;
    fetch(`${API}/user/major?user_id=${encodeURIComponent(user.uid)}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.major) {
          setSelectedMajor(data.major);
        } else {
          // First time: show modal after a short delay
          const key = `ace_major_skipped_${user.uid}`;
          if (!localStorage.getItem(key)) {
            setTimeout(() => setShowMajorModal(true), 1200);
          }
        }
      })
      .catch(() => {});
  }, [user?.uid]);

  const handleMajorSelect = useCallback((majorName) => {
    setSelectedMajor(majorName);
    setShowMajorModal(false);
  }, []);

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
      const response = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query, history, user_id: user?.uid || null }),
      });

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
            const SOURCED_INTENTS = ["courses", "student_progress", "substitution", "etm", "transfer"];
            const showSources = SOURCED_INTENTS.includes(data.intent);
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                ...next[next.length - 1],
                streaming: false,
                sources: showSources ? (data.sources ?? []) : [],
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
    fd.append("user_id", user.uid);
    try {
      const res = await fetch(`${API}/upload-student-doc`, {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadedFile(file);
        setUploadStatus("Uploaded");
        // Fetch parsed audit data and push it to the widget section
        try {
          const dashRes = await fetch(`${API}/dashboard?user_id=${encodeURIComponent(user.uid)}`);
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
      await fetch(
        `${API}/clear-student-doc?user_id=${encodeURIComponent(user.uid)}`,
        { method: "POST" }
      );
    } catch {}
  };

  const handleSwitchConversation = (conv) => {
    setMessages(conv.messages);
    setActiveConvId(conv.id);
    setInput("");
  };

  const handleNewConversation = () => {
    setMessages([]);
    setInput("");
    setUploadedFile(null);
    setUploadStatus("");
    setActiveConvId(null);
  };

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
    return <LoginPage />;
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
        onNavigate={setActiveView}
        conversations={conversations} activeConvId={activeConvId}
        onSwitchConversation={handleSwitchConversation}
        onNewConversation={handleNewConversation}
        onStartTour={() => setShowTour(true)}
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

      {/* ── Main panel ──────────────────────── */}
      <div className="main-panel">

        <header className="top-bar">
          <div className="top-bar-brand">
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

        {activeView === "resources" ? (
          <div className="dashboard-area">
            <ResourceHub />
          </div>
        ) : activeView === "gpa" ? (
          <div className="dashboard-area">
            <GpaCalculator userId={user.uid} />
          </div>
        ) : activeView === "calendar" ? (
          <div className="dashboard-area">
            <AcademicCalendar />
          </div>
        ) : activeView === "checklist" ? (
          <div className="dashboard-area">
            <GraduationChecklist userId={user.uid} />
          </div>
        ) : activeView === "prereq" ? (
          <div className="dashboard-area">
            <CoursePrereqMap userId={user.uid} />
          </div>
        ) : activeView === "gened" ? (
          <div className="dashboard-area">
            <GenEdExplorer userId={user.uid} selectedMajor={selectedMajor} />
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
            <div className="welcome-screen">
              <AceLogo size={72} />
              <h1 className="welcome-title">How can I help you today?</h1>
              <p className="welcome-subtitle">
                I'm ACE, your academic advisor assistant. Ask me about
                <br />
                courses, deadlines, policies, or academic planning.
              </p>
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
                                📄 {s.title || "Official Source"}
                                {s.link && (
                                  <a href={s.link} target="_blank" rel="noreferrer" className="source-chip-link">
                                    ↗
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
          {!hasMessages && (
            <div className="chips-row">
              {SUGGESTION_CHIPS.map((chip) => (
                <button
                  key={chip}
                  className="suggestion-chip"
                  onClick={() => handleSend(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          )}

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
                  <button className="upload-badge-x" onClick={handleClearFile}>×</button>
                </>
              ) : (
                <span>{uploadStatus}</span>
              )}
            </div>
          )}

          <div className="input-bar" data-tour="chat-input">
            <label className="attach-btn" data-tour="upload-btn" title="Upload degree audit or what-if report">
              +
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                style={{ display: "none" }}
                onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0])}
              />
            </label>
            <input
              className="chat-input"
              type="text"
              placeholder="Type, paste, or upload..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button
              className="send-btn"
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              title="Send"
            >
              ➤
            </button>
          </div>

          <p className="input-disclaimer">ACE is a planning tool. Always confirm academic decisions with your advisor.</p>

        </div>
        </>
        )}
      </div>

      {/* ── Onboarding tour ──────────────────── */}
      {showTour && <OnboardingTour onFinish={handleTourFinish} />}

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
