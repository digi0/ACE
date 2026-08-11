import { useState, useRef, useEffect, useLayoutEffect, useCallback, lazy, Suspense, Fragment } from "react";
import PrereqMapBlock from "./PrereqMapBlock";
import { CardsBlock, ChecklistBlock, StripBlock, PlanBlock } from "./AnswerBlocks";
import ReactMarkdown from "react-markdown";
import {
  ChevronRight, GraduationCap, BookOpen, CalendarClock,
  Compass, Upload, MessageSquare, Send, Paperclip, X, ExternalLink, Menu, PanelRight,
  ThumbsUp, ThumbsDown,
} from "lucide-react";
import { BGPattern } from "./BGPattern.jsx";
import Sidebar from "./Sidebar.jsx";
import { useAuth } from "./auth-context.js";
import AccessGate from "./AccessGate.jsx";
import { apiFetch, apiStream } from "./api.js";
import { useIsMobile } from "./useIsMobile.js";
import MobileBottomNav from "./MobileBottomNav.jsx";
import { AceTile } from "./AceMark.jsx";
import WidgetRail from "./WidgetRail.jsx";
import { PRIMARY, viewLabel } from "./nav.js";

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
const SettingsPanel       = lazy(() => import("./SettingsPanel.jsx"));
const StickyBoard         = lazy(() => import("./StickyBoard.jsx"));



/* Rotating hero keyword: "What are we <planning|scheduling|…> today?"
   Slot-machine roll: all words sit in a vertical track inside a one-line
   window; the track slides up by one row each tick. The first word is
   duplicated at the end so the loop wraps seamlessly (snap back without
   transition while the duplicate is showing). */
const ROTATING_WORDS = ["planning", "scheduling", "mapping", "tracking", "solving", "exploring"];

/* MUST match the transition durations on .wb-rotator / .wb-rotator-track in
   index.css. The slide is driven by CSS; this is how JS knows it has finished. */
const SLIDE_MS = 800;

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function RotatingWord() {
  const [idx, setIdx] = useState(0);
  const [snap, setSnap] = useState(false);
  const boxRef = useRef(null);
  const itemRefs = useRef([]);
  const settledW = useRef(null);

  const widthOf = useCallback(
    (i) => itemRefs.current[i % ROTATING_WORDS.length]?.offsetWidth ?? null,
    []
  );

  /* The box width is driven imperatively rather than through state. It is a
     measured DOM value written straight back to the DOM, so routing it through
     a render adds a frame and buys nothing. */
  const applyWidth = useCallback((px, instant) => {
    const box = boxRef.current;
    if (!box) return;
    /* offsetWidth is the layout ADVANCE width. Glyphs can paint past it — Plus
       Jakarta's "g" does — and the box clips on both axes, so a box sized to
       the exact measurement sliced the tail off ("planninc today?"). A sliver
       of the font size covers the overhang; too small to see in the sentence,
       enough for the ink to land in. */
    const w = px + parseFloat(getComputedStyle(box).fontSize) * 0.08;
    if (instant) {
      box.style.transition = "none";
      box.style.width = `${w}px`;
      void box.offsetWidth;        // flush, so the NEXT change still animates
      box.style.transition = "";
    } else {
      box.style.width = `${w}px`;
    }
  }, []);

  useEffect(() => {
    // Under reduced motion the CSS disables both transitions, so transitionend
    // never fires — the duplicate-word snap-back below would never run and the
    // track would roll off the end into blank space after one lap. Step
    // straight through the real indices instead.
    const reduced = prefersReducedMotion();
    const iv = setInterval(
      () => setIdx((i) => (reduced ? (i + 1) % ROTATING_WORDS.length : i + 1)),
      4000
    );
    return () => clearInterval(iv);
  }, []);

  /* The box hugs the ACTIVE word so the rest of the sentence stays snug. The
     catch is that it also has `overflow: hidden` for the vertical slot effect,
     so easing the width to the incoming word's size clipped whatever was on
     screen: growing cut the arriving word ("scheduli| today?"), shrinking left
     a gap after the departing one ("mapping    today?").

     Fix is to never let the box be narrower than the word inside it. Grow
     immediately and without easing, hold that width for the whole slide, and
     only shrink once the word has landed (see handleEnd). */
  useLayoutEffect(() => {
    const next = widthOf(idx);
    if (next == null) return;
    if (settledW.current == null || next > settledW.current) {
      applyWidth(next, true);
      if (settledW.current == null) settledW.current = next;
    }
  }, [idx, widthOf, applyWidth]);

  /* Settle on a timer rather than on transitionend. transitionend looks like
     the natural hook but it silently never fires in several real states — a
     background tab, a hidden pane, an interrupted transition, and any browser
     honouring prefers-reduced-motion (our CSS sets transition:none there). Any
     of those left the box frozen at the previous word's width, which is the
     ~33px clip this was supposed to fix. A timer always fires. */
  useEffect(() => {
    const t = setTimeout(() => {
      // Landing on the duplicate means we wrap: the track jumps back to row 0
      // with no transition, so the width must jump with it. Easing it while the
      // word teleports is what left the box at the outgoing word's size.
      const wrapping = idx >= ROTATING_WORDS.length;
      if (wrapping) {
        setSnap(true);
        setIdx(0);
      }
      const exact = widthOf(wrapping ? 0 : idx);
      if (exact == null) return;
      settledW.current = exact;
      applyWidth(exact, wrapping);
    }, SLIDE_MS);
    return () => clearTimeout(t);
  }, [idx, widthOf, applyWidth]);

  // Re-enable the transition one frame after the silent snap-back.
  useEffect(() => {
    if (!snap) return;
    const raf = requestAnimationFrame(() => requestAnimationFrame(() => setSnap(false)));
    return () => cancelAnimationFrame(raf);
  }, [snap]);

  // Font swap and resize both change the measurement (the size is
  // container-relative), so re-measure without animating.
  useEffect(() => {
    const remeasure = () => {
      const exact = widthOf(idx);
      if (exact == null) return;
      settledW.current = exact;
      applyWidth(exact, true);
    };
    document.fonts?.ready?.then(remeasure);
    window.addEventListener("resize", remeasure);
    return () => window.removeEventListener("resize", remeasure);
  }, [idx, widthOf, applyWidth]);

  const active = idx % ROTATING_WORDS.length;

  return (
    <span className="wb-rotator" ref={boxRef}>
      <span
        className={`wb-rotator-track${snap ? " wb-rotator-track--snap" : ""}`}
        // each row is exactly 1.35em tall — translate per ROW (em-based)
        style={{ transform: `translateY(calc(${snap ? 0 : idx} * -1.35em))` }}
      >
        {[...ROTATING_WORDS, ROTATING_WORDS[0]].map((w, i) => (
          <span
            className="wb-rotator-item"
            key={i}
            /* Only the visible word is exposed. Without this the h1 reads as
               "What are we planning scheduling mapping … today?", and an
               aria-live region here would re-announce the heading every 4s. */
            aria-hidden={i === active ? undefined : "true"}
            ref={(el) => { itemRefs.current[i] = el; }}
          >
            {w}
          </span>
        ))}
      </span>
    </span>
  );
}

/* Keeps its period. This only renders when the sidebar is COLLAPSED, so at that
   moment it is the single brand element on screen — dropping the dot there
   would show the identity with its defining feature removed. While the sidebar
   is open this doesn't render at all and <AceWordmark> owns the period, so the
   one-emerald-per-view rule still holds either way. */
const AceLogo = ({ size = 36 }) => <AceTile size={size} />

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
function MajorSelectModal({ onSelect, onSkip }) {
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

/* ── Answer rating ─────────────────────────────────
   Thumbs on an answer. The rating itself is the point: a down-rated answer is
   the only direct signal a student gives that ACE got it wrong. */
function MessageRating({ rating, onRate }) {
  const rated = rating === 1 || rating === -1;
  return (
    <div className="message-rating" role="group" aria-label="Was this answer helpful?">
      {!rated && <span className="message-rating-label">was this helpful?</span>}
      <button
        type="button"
        className={`message-rating-btn${rating === 1 ? " is-active" : ""}`}
        aria-label="Helpful"
        aria-pressed={rating === 1}
        onClick={() => onRate(rating === 1 ? null : 1)}
      >
        <ThumbsUp size={13} strokeWidth={2.25} aria-hidden />
      </button>
      <button
        type="button"
        className={`message-rating-btn${rating === -1 ? " is-active" : ""}`}
        aria-label="Not helpful"
        aria-pressed={rating === -1}
        onClick={() => onRate(rating === -1 ? null : -1)}
      >
        <ThumbsDown size={13} strokeWidth={2.25} aria-hidden />
      </button>
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
  /* Control panel. Two ways in, on purpose:
       hover  — transient peek, closes when the pointer leaves
       click  — pins it open, remembered per browser
     Hover alone would make it unreachable by keyboard and invisible on touch,
     where there is no hover state at all. */
  const [railPinned, setRailPinned] = useState(() => localStorage.getItem("ace_rail") === "1");
  const [railHover, setRailHover] = useState(false);
  const railTimer = useRef(null);
  const railOpen = railPinned || railHover;

  // Small grace period so the pointer can cross the gap from the trigger to the
  // panel without it closing underneath.
  const openRail  = () => { clearTimeout(railTimer.current); setRailHover(true); };
  const closeRail = () => {
    clearTimeout(railTimer.current);
    railTimer.current = setTimeout(() => setRailHover(false), 180);
  };
  useEffect(() => () => clearTimeout(railTimer.current), []);

  const toggleRailPin = () => {
    setRailPinned((prev) => {
      const next = !prev;
      localStorage.setItem("ace_rail", next ? "1" : "0");
      if (next) setRailHover(false);   // pinned now; drop the transient state
      return next;
    });
  };

  // Escape closes it however it was opened.
  useEffect(() => {
    if (!railOpen) return;
    const onKey = (e) => {
      if (e.key !== "Escape") return;
      setRailHover(false);
      setRailPinned(false);
      localStorage.setItem("ace_rail", "0");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [railOpen]);
  const [chatFont, setChatFont] = useState(() => localStorage.getItem("ace_chatfont") || "md");
  const [auditData, setAuditData] = useState(null);

  const [selectedMajor, setSelectedMajor] = useState(null);
  const [showMajorModal, setShowMajorModal] = useState(false);

  const fileInputRef = useRef(null);
  const chatInputRef = useRef(null);

  const messagesEndRef = useRef(null);
  const hasMessages = messages.length > 0;
  const isMobile = useIsMobile();

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

  // ── Chat text size (set in Settings; sm | md | lg) ──
  useEffect(() => {
    document.documentElement.setAttribute("data-chatfont", chatFont);
    localStorage.setItem("ace_chatfont", chatFont);
  }, [chatFont]);

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
    } catch { /* corrupt or unreadable history is not worth failing a render over */ }
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
  // Optimistic: the thumb fills immediately and stays filled. A failed POST is
  // logged, not surfaced — a student mid-question should not get an error toast
  // about telemetry.
  const rateMessage = async (index, messageId, value) => {
    setMessages((prev) => {
      const next = [...prev];
      if (next[index]) next[index] = { ...next[index], rating: value };
      return next;
    });
    if (value === null) return; // un-rating is local only; nothing to record
    try {
      await apiFetch(`/messages/${messageId}/rating`, {
        method: "POST",
        body: JSON.stringify({ rating: value }),
      });
    } catch (err) {
      console.warn("rating failed to save", err);
    }
  };

  const handleSend = async (text) => {
    const query = (text !== undefined ? text : input).trim();
    if (!query || loading) return;

    const userMsg = { role: "user", content: query };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    setFollowUpChips([]);

    // Resolve the conversation id locally: setActiveConvId is async, so reading
    // activeConvId below would still be the previous value on the first message
    // of a new chat — which would file that exchange under the wrong conversation.
    let convId = activeConvId;
    if (messages.length === 0) {
      convId = Date.now();
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
      const response = await apiStream("/chat/stream", {
        question: query,
        history,
        // String(): ids are minted with Date.now(), so they arrive as numbers —
        // the backend field is a string and Pydantic will not coerce one.
        conversation_id: convId != null ? String(convId) : null,
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
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                ...next[next.length - 1],
                streaming: false,
                sources: data.sources ?? [],
                messageId: data.message_id ?? null,
                // The backend's visual policy decides whether a block is
                // warranted and ships the data for it. Renderers read this;
                // when it is absent the answer is prose, which is the norm.
                visual: data.visual ?? null,
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
        } catch { /* the upload itself succeeded; a failed dashboard refresh must not report it as failed */ }
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
    } catch { /* local state is already cleared; a failed server delete is retried on next upload */ }
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
        darkMode={darkMode} setDarkMode={setDarkMode}
        onCollapse={() => setSidebarCollapsed(true)}
        conversations={conversations} activeConvId={activeConvId}
        onSwitchConversation={handleSwitchConversation}
        onNewConversation={handleNewConversation}
        onStartTour={() => setShowTour(true)}
        onNavigate={navigate}
        activeView={activeView}
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

        {/* The top bar owns the four primary views. Tools live in the sidebar,
            so when one is open no tab is active — the label next to the wordmark
            names it instead, which is what stops the bar from going blank and
            leaving you with no idea where you are. */}
        <header className="top-bar">
          {/* No wordmark here — the sidebar owns the brand, and carrying it in
              both put two lockups in one viewport. The tile reappears only when
              the sidebar is collapsed, so the brand is always present exactly
              once. What this bar states instead is where you are. */}
          <div className="top-bar-brand">
            <button
              className="top-bar-hamburger"
              onClick={() => setSidebarCollapsed(false)}
              aria-label="Open menu"
            >
              <Menu size={20} aria-hidden />
            </button>
            {sidebarCollapsed && <AceLogo size={26} />}
            <span className="top-bar-view" aria-live="polite">{viewLabel(activeView)}</span>
          </div>
          <div className="top-bar-right">
            <nav className="top-bar-nav" aria-label="Primary">
              {PRIMARY.map(({ id, label }) => (
                <button
                  key={id}
                  data-tour={id === "dashboard" ? "dashboard-tab" : undefined}
                  className={`top-bar-tab${activeView === id ? " top-bar-tab--active" : ""}`}
                  aria-current={activeView === id ? "page" : undefined}
                  onClick={() => navigate(id)}
                >
                  {label}
                </button>
              ))}
            </nav>
            <button
              className={`rail-toggle${railOpen ? " rail-toggle--on" : ""}`}
              onClick={toggleRailPin}
              onMouseEnter={openRail}
              onMouseLeave={closeRail}
              onFocus={openRail}
              onBlur={closeRail}
              aria-pressed={railPinned}
              aria-expanded={railOpen}
              title={railPinned ? "Unpin panel" : "Pin panel open"}
            >
              <PanelRight size={16} strokeWidth={1.9} aria-hidden />
              <span className="sr-only">{railPinned ? "Unpin panel" : "Pin panel open"}</span>
            </button>
          </div>
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
        ) : activeView === "notes" ? (
          <div className="dashboard-area" style={{ padding: 0 }}>
            <StickyBoard userId={user.uid} />
          </div>
        ) : activeView === "settings" ? (
          <div className="dashboard-area">
            <SettingsPanel
              user={user}
              selectedMajor={selectedMajor}
              onChangeMajor={() => setShowMajorModal(true)}
              darkMode={darkMode}
              setDarkMode={setDarkMode}
              chatFont={chatFont}
              setChatFont={setChatFont}
              onClearChats={() => {
                setConversations([]);
                setMessages([]);
                setActiveConvId(null);
                if (user?.uid) localStorage.removeItem(`ace_chats_${user.uid}`);
              }}
              onRemoveDoc={handleClearFile}
              signOut={signOut}
            />
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
          {/* fade-edges keeps the dot field off the chrome: dots stay dense
              behind the empty-state cards and dissolve before they reach the
              top bar, sidebar, and input. Flat (mask="none") they ran edge to
              edge and fought every border on the screen. */}
          <BGPattern variant="dots" mask="fade-edges" fill="var(--dots)" size={22} />
          {!hasMessages ? (
            <div className="wb-welcome">
              <div className="wb-welcome-head">
                <h1 className="wb-headline">
                  What are we <RotatingWord /> today?
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
                      // The dashboard owns the upload experience (empty state +
                      // parsed results live there) — clicking a hidden input
                      // from the welcome screen did nothing visible.
                      navigate("dashboard");
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
                <Fragment key={i}>
                <div className={`message message--${msg.role}`}>
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
                              a: ({ node: _node, ...props }) => (
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
                        {!msg.streaming && msg.messageId && (
                          <MessageRating
                            messageId={msg.messageId}
                            rating={msg.rating}
                            onRate={(value) => rateMessage(i, msg.messageId, value)}
                          />
                        )}
                      </>
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
                {/* Outside the bubble, on the dotted surface. A bubble is the
                    shape of something SAID; a map you can walk and a checklist
                    you can tick are things you work with, and a planner spread
                    squeezed into a speech bubble read as a quotation of a plan
                    rather than the plan. */}
                {!msg.streaming && msg.visual?.data && (
                  <div className="msg-visual">
                    {{
                      map: <PrereqMapBlock data={msg.visual.data} />,
                      cards: <CardsBlock data={msg.visual.data} />,
                      checklist: <ChecklistBlock data={msg.visual.data} />,
                      strip: <StripBlock data={msg.visual.data} />,
                      plan: <PlanBlock data={msg.visual.data} />,
                    }[msg.visual.block] ?? null}
                  </div>
                )}
                </Fragment>
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

      {/* ── Widget rail ──────────────────────
          Opt-in, not permanent: closed by default and toggled from the top bar,
          so the default screen stays the chat. Also hidden below 1180px
          (responsive.css) — at that width a third column squeezes the chat
          past a readable measure, and the same content is on the Dashboard. */}
      {!isMobile && railOpen && (
        <WidgetRail
          selectedMajor={selectedMajor}
          onChangeMajor={() => setShowMajorModal(true)}
          auditData={auditData}
          onNavigate={navigate}
          pinned={railPinned}
          onMouseEnter={openRail}
          onMouseLeave={closeRail}
        />
      )}

      {/* ── Onboarding tour ──────────────────── */}
      {showTour && (
        <Suspense fallback={null}>
          <OnboardingTour onFinish={handleTourFinish} />
        </Suspense>
      )}

      {/* ── Major selection modal ─────────────── */}
      {showMajorModal && (
        <MajorSelectModal
          onSelect={handleMajorSelect}
          onSkip={handleMajorSkip}
        />
      )}
    </div>
  );
}

export default App;
