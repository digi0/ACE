import { useState, useEffect, useCallback } from "react";

/* ── Tour steps ─────────────────────────────────────────────── */
const STEPS = [
  {
    id: "welcome",
    target: null,
    title: "Welcome to ACE",
    message:
      "ACE is your Academic Counselling Engine for Penn State. Ask questions about courses, requirements, and deadlines — or upload your degree audit for personalized guidance.",
  },
  {
    id: "chat",
    target: '[data-tour="chat-input"]',
    title: "Ask a question",
    message:
      "Type your questions here — courses, requirements, deadlines, policies. ACE responds with guidance grounded in Penn State CS academics.",
  },
  {
    id: "upload",
    target: '[data-tour="upload-btn"]',
    title: "Upload your degree audit",
    message:
      "Use the + button to upload your Degree Audit or What-If Report PDF from LionPATH. ACE will use it to personalize every answer to your actual progress.",
  },
  {
    id: "dashboard",
    target: '[data-tour="dashboard-tab"]',
    title: "Dashboard",
    message:
      "The Dashboard shows your credits completed, remaining requirements, and recommended courses for next semester — populated from your uploaded document.",
  },
  {
    id: "sidebar",
    target: '[data-tour="sidebar"]',
    title: "Conversation history",
    message:
      "Previous conversations are saved here. Start a new one anytime, or return to an older thread — your context is always preserved.",
  },
  {
    id: "done",
    target: null,
    title: "You're all set",
    message:
      "That's the full tour. ACE is here whenever you need help planning your degree.",
  },
];

/* ── Simple ACE mark ─────────────────────────────────────────── */
function AceMark() {
  return (
    <div style={{
      width: 52,
      height: 52,
      borderRadius: 14,
      background: "#1e3a6e",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
    }}>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
        stroke="white" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
        <path d="M6 12v5c3 3 9 3 12 0v-5" />
      </svg>
    </div>
  );
}

/* ── Bubble placement ───────────────────────────────────────── */
const BUBBLE_W = 340;
const BUBBLE_H = 220;
const GAP = 20;
const VIEW_MARGIN = 16;

function placeBubble(rect) {
  if (!rect) return null;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  // Right of target
  if (rect.right + GAP + BUBBLE_W <= vw - VIEW_MARGIN) {
    return {
      left: rect.right + GAP,
      top: clamp(rect.top, VIEW_MARGIN, vh - BUBBLE_H - VIEW_MARGIN),
      side: "right",
    };
  }
  // Left of target
  if (rect.left - GAP - BUBBLE_W >= VIEW_MARGIN) {
    return {
      left: rect.left - GAP - BUBBLE_W,
      top: clamp(rect.top, VIEW_MARGIN, vh - BUBBLE_H - VIEW_MARGIN),
      side: "left",
    };
  }
  // Below target
  if (rect.bottom + GAP + BUBBLE_H <= vh - VIEW_MARGIN) {
    return {
      top: rect.bottom + GAP,
      left: clamp(rect.left, VIEW_MARGIN, vw - BUBBLE_W - VIEW_MARGIN),
      side: "below",
    };
  }
  // Above target
  return {
    top: Math.max(VIEW_MARGIN, rect.top - GAP - BUBBLE_H),
    left: clamp(rect.left, VIEW_MARGIN, vw - BUBBLE_W - VIEW_MARGIN),
    side: "above",
  };
}

/* ── OnboardingTour ─────────────────────────────────────────── */
export default function OnboardingTour({ onFinish }) {
  const [step, setStep]             = useState(0);
  const [targetRect, setTargetRect] = useState(null);
  const [visible, setVisible]       = useState(false);

  const current = STEPS[step];
  const isLast  = step === STEPS.length - 1;
  const bubblePos = placeBubble(targetRect);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 50);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    const measure = () => {
      if (!current.target) { setTargetRect(null); return; }
      const el = document.querySelector(current.target);
      setTargetRect(el ? el.getBoundingClientRect() : null);
    };
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [step, current.target]);

  const handleNext = useCallback(() => {
    isLast ? onFinish() : setStep(s => s + 1);
  }, [isLast, onFinish]);

  const handleSkip = useCallback(() => onFinish(), [onFinish]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape")                          handleSkip();
      if (e.key === "ArrowRight" || e.key === "Enter") handleNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleNext, handleSkip]);

  return (
    <div className={`tour-root${visible ? " tour-root--visible" : ""}`}>

      <div
        className={targetRect ? "tour-overlay-clear" : "tour-overlay"}
        onClick={handleSkip}
      />

      {targetRect && (
        <div
          className="tour-spotlight"
          style={{
            top:    targetRect.top    - 10,
            left:   targetRect.left   - 10,
            width:  targetRect.width  + 20,
            height: targetRect.height + 20,
          }}
        />
      )}

      {/* ── Card (follows the highlighted target) ── */}
      <div
        className={`tour-mascot-wrap${bubblePos ? " tour-mascot-wrap--anchored" : ""}`}
        onClick={e => e.stopPropagation()}
        style={bubblePos
          ? { top: bubblePos.top, left: bubblePos.left, bottom: "auto", right: "auto" }
          : undefined}
        data-side={bubblePos?.side}
      >

        <div className="tour-bubble">
          <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem", marginBottom: "0.6rem" }}>
            <AceMark />
            <div>
              <p className="tour-bubble-title">{current.title}</p>
              <p className="tour-bubble-msg">{current.message}</p>
            </div>
          </div>

          <div className="tour-bubble-footer">
            <div className="tour-dots">
              {STEPS.map((_, i) => (
                <span key={i} className={`tour-dot${i === step ? " tour-dot--active" : ""}`} />
              ))}
            </div>

            <div className="tour-btns">
              {!isLast && (
                <button className="tour-btn tour-btn--ghost" onClick={handleSkip}>
                  Skip
                </button>
              )}
              <button className="tour-btn tour-btn--primary" onClick={handleNext}>
                {isLast ? "Get started" : "Next"}
              </button>
            </div>
          </div>

          {!bubblePos && <div className="tour-bubble-tail" />}
        </div>

      </div>

    </div>
  );
}
