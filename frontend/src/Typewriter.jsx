import { useEffect, useRef, useState } from "react";

export default function Typewriter({
  words = [],
  typingSpeed = 90,
  deletingSpeed = 50,
  pauseDuration = 1500,
  cursorColor,
  cursorWidth = 2,
  cursorHeightPct = 100,
  style,
}) {
  const [displayed, setDisplayed] = useState("");
  const [wordIndex, setWordIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showCursor, setShowCursor] = useState(true);
  const timerRef = useRef(null);

  const current = words.length > 0 ? words[wordIndex % words.length] : "";

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    if (!isDeleting && charIndex < current.length) {
      timerRef.current = setTimeout(() => {
        setDisplayed(current.slice(0, charIndex + 1));
        setCharIndex((i) => i + 1);
      }, typingSpeed);
    } else if (!isDeleting && charIndex === current.length) {
      timerRef.current = setTimeout(() => setIsDeleting(true), pauseDuration);
    } else if (isDeleting && charIndex > 0) {
      timerRef.current = setTimeout(() => {
        setDisplayed(current.slice(0, charIndex - 1));
        setCharIndex((i) => i - 1);
      }, deletingSpeed);
    } else if (isDeleting && charIndex === 0) {
      timerRef.current = setTimeout(() => {
        setIsDeleting(false);
        setWordIndex((i) => (i + 1) % words.length);
      }, pauseDuration / 2);
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [charIndex, isDeleting, current, typingSpeed, deletingSpeed, pauseDuration, words.length]);

  useEffect(() => {
    const blink = setInterval(() => setShowCursor((v) => !v), 500);
    return () => clearInterval(blink);
  }, []);

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "baseline",
        whiteSpace: "pre",
        ...style,
      }}
      aria-live="polite"
    >
      {displayed}
      <span
        aria-hidden="true"
        style={{
          display: "inline-block",
          width: cursorWidth,
          height: `${cursorHeightPct}%`,
          minHeight: "0.9em",
          background: cursorColor || "currentColor",
          marginLeft: 3,
          opacity: showCursor ? 1 : 0,
          transition: "opacity 80ms",
          borderRadius: 2,
          alignSelf: "center",
        }}
      />
    </span>
  );
}
