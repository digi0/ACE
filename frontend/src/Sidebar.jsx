import { useEffect, useRef, useState } from "react";
import {
  ChevronLeft, ChevronUp, LogOut, Plus, MessageSquare, Settings, Compass,
} from "lucide-react";
import ThemeToggle from "./ThemeToggle";
import { AceWordmark } from "./AceMark.jsx";
import { TOOLS, SETTINGS_ID } from "./nav.js";

/* ── Main component ── */
export default function Sidebar({
  user, signOut,
  darkMode, setDarkMode,
  onCollapse,
  onNavigate,
  activeView,
  conversations, activeConvId,
  onSwitchConversation,
  onNewConversation,
  onStartTour,
}) {
  const displayName = user?.displayName || user?.email || "";
  const initials = displayName
    .split(/[\s@]/).filter(Boolean)
    .map(n => n[0]).join("").slice(0, 2).toUpperCase();

  const [menuOpen, setMenuOpen] = useState(false);
  const accountRef = useRef(null);

  // Close on outside click or Escape. Both matter: the menu holds Sign out, and
  // a popover you can only dismiss by re-clicking the trigger is a trap on a
  // narrow sidebar where the trigger may be scrolled out of reach.
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e) => {
      if (!accountRef.current?.contains(e.target)) setMenuOpen(false);
    };
    const onKey = (e) => { if (e.key === "Escape") setMenuOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  return (
    <aside className="sidebar" data-tour="sidebar">

      {/* ── Top: brand + user ── */}
      <div className="sb-top">
        <div className="sb-header">
          {/* The real wordmark, not a tile plus the letters "ACE" in the UI
              font. This is the app's ONE brand moment — the top bar carries no
              logo while this is visible, so the two never double up. 116px sits
              comfortably above the 96px legibility floor from BRAND.md §2. */}
          <div className="sb-brand">
            <AceWordmark width={116} />
          </div>
          <div className="sb-header-btns">
            {/* Track height in px; the sky artwork is em-scaled off it, so this
                one number drives the whole thing. Around 18 is the floor —
                below that the moon spots and stars stop resolving. */}
            <ThemeToggle value={darkMode} onChange={setDarkMode} size={21} />
            <button className="sb-icon-btn" onClick={onCollapse} title="Collapse sidebar">
              <ChevronLeft size={14} />
            </button>
          </div>
        </div>

        <hr className="sb-divider" />
      </div>

      {/* ── Middle: scrollable content ──
          Primary nav went back to the top bar, and the major chip, degree
          progress, and deadlines moved to the widget rail. What's left is the
          one job this panel should have had all along: getting you somewhere. */}
      <div className="sb-middle">

        {/* Tools */}
        <div className="sb-section">
          <div className="sb-section-hdr">
            <span className="sb-section-label">TOOLS</span>
          </div>
          <div className="sb-tools-grid">
            {TOOLS.map(({ id, label, Icon }) => (
              <button
                key={id}
                className={`sb-tool-btn${activeView === id ? " sb-tool-btn--active" : ""}`}
                aria-current={activeView === id ? "page" : undefined}
                onClick={() => onNavigate(id)}
              >
                <Icon size={15} className="sb-tool-icon" />
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

      {/* ── Bottom: new chat + account ──
          The profile moved down here so every account action lives in one
          place. It used to sit at the top as avatar + name + email over two
          lines, where the email rendered at 2.32:1 — half the AA minimum — and
          duplicated the name for anyone without a display name set. One line at
          full contrast now; the email and the actions live in the menu. */}
      <div className="sb-bottom">
        <button className="sb-new-btn" onClick={onNewConversation}>
          <Plus size={13} strokeWidth={2} />
          New conversation
        </button>

        <div className="sb-account" ref={accountRef}>
          {menuOpen && (
            <div className="sb-account-menu" role="menu">
              {user?.email && (
                <div className="sb-account-email" title={user.email}>{user.email}</div>
              )}
              <button
                role="menuitem"
                className={`sb-account-item${activeView === SETTINGS_ID ? " sb-account-item--active" : ""}`}
                onClick={() => { setMenuOpen(false); onNavigate(SETTINGS_ID); }}
              >
                <Settings size={13} aria-hidden />
                Settings
              </button>
              <button
                role="menuitem"
                className="sb-account-item"
                onClick={() => { setMenuOpen(false); onStartTour(); }}
              >
                <Compass size={13} aria-hidden />
                Take the tour
              </button>
              <hr className="sb-account-sep" />
              {/* Sign out is behind one deliberate click now. It used to be a
                  13px icon permanently parked beside the user's name — the
                  smallest target in the sidebar and the only destructive one. */}
              <button
                role="menuitem"
                className="sb-account-item sb-account-item--exit"
                onClick={() => { setMenuOpen(false); signOut(); }}
              >
                <LogOut size={13} aria-hidden />
                Sign out
              </button>
            </div>
          )}

          <button
            className={`sb-account-btn${menuOpen ? " sb-account-btn--open" : ""}`}
            onClick={() => setMenuOpen((v) => !v)}
            aria-expanded={menuOpen}
            aria-haspopup="menu"
          >
            <span className="sb-avatar" aria-hidden>{initials}</span>
            <span className="sb-account-name">{displayName}</span>
            <ChevronUp size={13} className="sb-account-caret" aria-hidden />
          </button>
        </div>
      </div>
    </aside>
  );
}
