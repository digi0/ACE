import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import Dashboard from "./Dashboard.jsx";

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

function MicrosoftIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" style={{ flexShrink: 0 }}>
      <rect x="0" y="0" width="7" height="7" fill="#f25022" />
      <rect x="9" y="0" width="7" height="7" fill="#7fba00" />
      <rect x="0" y="9" width="7" height="7" fill="#00a4ef" />
      <rect x="9" y="9" width="7" height="7" fill="#ffb900" />
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
  { icon: "🎯", text: "Help me plan this semester" },
  { icon: "✨", text: "What should I focus on this week?" },
  { icon: "⚠️", text: "I'm worried about a deadline" },
  { icon: "📅", text: "Check my schedule" },
];

const QUICK_ACCESS = [
  { icon: "💬", label: "Chat", view: "chat" },
  { icon: "📊", label: "Dashboard", view: "dashboard" },
  { icon: "📅", label: "Weekly Calendar", view: null },
  { icon: "🕐", label: "Check Deadlines", view: null },
];

/* ── App ───────────────────────────────────────── */
function App() {
  const [user, setUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [activeView, setActiveView] = useState("chat");

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

  // ── Mock sign-in; replace with real Microsoft OAuth ──
  const handleSignIn = () => {
    setUser({ name: "PSU Student", email: "xyz1234@psu.edu" });
  };

  // ── Send (real SSE streaming) ──
  const handleSend = async (text) => {
    const query = (text !== undefined ? text : input).trim();
    if (!query || loading) return;

    const userMsg = { role: "user", content: query };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

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
      const response = await fetch("http://127.0.0.1:8000/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query, history }),
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
    setUploadStatus("Uploading...");
    setUploadedFile(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("http://127.0.0.1:8000/upload-student-doc", {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadedFile(file);
        setUploadStatus("Uploaded");
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
    try {
      await fetch("http://127.0.0.1:8000/clear-student-doc", { method: "POST" });
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

  const initials = user
    ? user.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : "";

  return (
    <div className={`app-layout${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>

      {/* ── Sidebar ─────────────────────────── */}
      <aside className="sidebar">

        {/* Brand */}
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <AceLogo size={34} />
            <span className="sidebar-brand-name">ACE</span>
          </div>
          <button
            className="sidebar-icon-btn"
            onClick={() => setSidebarCollapsed(true)}
            title="Collapse sidebar"
          >
            ◀
          </button>
        </div>

        {/* User / sign-in */}
        {user ? (
          <div className="sidebar-user">
            <div className="sidebar-avatar">{initials}</div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-name">{user.name}</div>
              <div className="sidebar-user-email">{user.email}</div>
            </div>
            <button className="sidebar-icon-btn" title="Settings">⚙</button>
          </div>
        ) : (
          <div className="sidebar-signin">
            <p className="sidebar-signin-hint">Sign in to save your chats</p>
            <button className="signin-btn" onClick={handleSignIn}>
              <MicrosoftIcon />
              Sign in with PSU Outlook
            </button>
          </div>
        )}

        {/* Alert card — only when signed in */}
        {user && (
          <div className="sidebar-alert">
            <div className="sidebar-alert-meta">SPRING 2026 · JUNIOR · FULL-TIME</div>
            <p className="sidebar-alert-text">
              As an international student, any enrollment changes require prior
              approval from Global Programs.
            </p>
            <button className="sidebar-alert-link">Check requirements →</button>
          </div>
        )}

        {/* Quick access */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <span className="sidebar-section-label">QUICK ACCESS</span>
          </div>
          {QUICK_ACCESS.map((item) => (
            <button
              key={item.label}
              className={`sidebar-nav-item${activeView === item.view ? " sidebar-nav-item--active" : ""}`}
              onClick={() => item.view && setActiveView(item.view)}
            >
              <span className="sidebar-nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        {/* New conversation */}
        <button className="new-conv-btn" onClick={handleNewConversation}>
          + New conversation
        </button>

        {/* Previous chats */}
        <div className="sidebar-section sidebar-section--chats">
          <div className="sidebar-section-label">PREVIOUS CHATS</div>
          {conversations.length === 0 ? (
            <p className="sidebar-empty">No previous chats</p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                className={`sidebar-nav-item${activeConvId === conv.id ? " sidebar-nav-item--active" : ""}`}
                onClick={() => handleSwitchConversation(conv)}
              >
                <span className="sidebar-nav-icon">💬</span>
                <span className="sidebar-chat-preview">{conv.preview}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      {sidebarCollapsed && (
        <button
          className="sidebar-expand-btn"
          onClick={() => setSidebarCollapsed(false)}
          title="Open sidebar"
        >
          ▶
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
              💬 Chat
            </button>
            <button
              className={`top-bar-tab${activeView === "dashboard" ? " top-bar-tab--active" : ""}`}
              onClick={() => setActiveView("dashboard")}
            >
              📊 Dashboard
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

        {activeView === "dashboard" ? (
          <div className="dashboard-area">
            <Dashboard
              uploadedFile={uploadedFile}
              onUploadClick={() => fileInputRef.current?.click()}
            />
          </div>
        ) : (
        <>
        <div className="chat-area">
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
                  key={chip.text}
                  className="suggestion-chip"
                  onClick={() => handleSend(chip.text)}
                >
                  <span>{chip.icon}</span>
                  <span>{chip.text}</span>
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

          <div className="input-bar">
            <label className="attach-btn" title="Upload degree audit or what-if report">
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
    </div>
  );
}

export default App;
