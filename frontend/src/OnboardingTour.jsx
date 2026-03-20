import { useState, useEffect, useCallback } from "react";
import NittanyLion from "./NittanyLion.jsx";

/* ── Tour steps ─────────────────────────────────────────────── */
const STEPS = [
  {
    id: "welcome",
    target: null,
    title: "Hey there, I'm ACE! 👋",
    message:
      "Welcome to the Academic Counselling Engine — your personal AI advisor at Penn State. I'm here to help you navigate your CS degree. Let me show you around!",
  },
  {
    id: "chat",
    target: '[data-tour="chat-input"]',
    title: "Ask Me Anything",
    message:
      "Type your questions right here — courses, requirements, deadlines, policies. I'll give you personalized guidance based on Penn State CS academics.",
  },
  {
    id: "upload",
    target: '[data-tour="upload-btn"]',
    title: "Upload Your Degree Audit",
    message:
      "Hit the '+' to upload your Degree Audit or What-If Report PDF from LionPATH. Once uploaded I can give you advice specific to your actual progress.",
  },
  {
    id: "dashboard",
    target: '[data-tour="dashboard-tab"]',
    title: "Your Dashboard",
    message:
      "The Dashboard gives you a visual overview — credits completed, remaining requirements, and recommended courses for next semester.",
  },
  {
    id: "sidebar",
    target: '[data-tour="sidebar"]',
    title: "Your Conversation History",
    message:
      "All your previous chats are saved here. Start a new conversation anytime or jump back into an old one — your context is always preserved.",
  },
  {
    id: "done",
    target: null,
    title: "You're all set! 🎓",
    message:
      "That's the full tour! I'm always here whenever you need help. Feel free to explore, and remember — Go State! Let's get started.",
  },
];

/* ── OnboardingTour ─────────────────────────────────────────── */
export default function OnboardingTour({ onFinish }) {
  const [step, setStep]           = useState(0);
  const [targetRect, setTargetRect] = useState(null);
  const [visible, setVisible]     = useState(false);

  const current = STEPS[step];
  const isLast  = step === STEPS.length - 1;

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 50);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (!current.target) { setTargetRect(null); return; }
    const el = document.querySelector(current.target);
    setTargetRect(el ? el.getBoundingClientRect() : null);
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

      {/* Dim layer — transparent when spotlight active so target is fully visible */}
      <div
        className={targetRect ? "tour-overlay-clear" : "tour-overlay"}
        onClick={handleSkip}
      />

      {/* Spotlight ring around target element */}
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

      {/* ── Mascot + speech bubble (fixed bottom-left) ── */}
      <div className="tour-mascot-wrap" onClick={e => e.stopPropagation()}>

        {/* Speech bubble */}
        <div className="tour-bubble">
          <p className="tour-bubble-title">{current.title}</p>
          <p className="tour-bubble-msg">{current.message}</p>

          <div className="tour-bubble-footer">
            {/* Progress dots */}
            <div className="tour-dots">
              {STEPS.map((_, i) => (
                <span key={i} className={`tour-dot${i === step ? " tour-dot--active" : ""}`} />
              ))}
            </div>

            {/* Buttons */}
            <div className="tour-btns">
              {!isLast && (
                <button className="tour-btn tour-btn--ghost" onClick={handleSkip}>
                  Skip
                </button>
              )}
              <button className="tour-btn tour-btn--primary" onClick={handleNext}>
                {isLast ? "Let's go! 🚀" : "Next →"}
              </button>
            </div>
          </div>

          {/* Bubble tail pointing down toward the lion */}
          <div className="tour-bubble-tail" />
        </div>

        {/* Lion mascot */}
        <NittanyLion size={110} />
      </div>

    </div>
  );
}
