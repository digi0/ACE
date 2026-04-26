import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

const STORAGE_KEY = "ace_darkmode";

const readInitial = () => {
  if (typeof window === "undefined") return false;
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "1") return true;
  if (saved === "0") return false;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
};

export default function ThemeToggle({ size = 30, style }) {
  const [isDark, setIsDark] = useState(readInitial);

  useEffect(() => {
    const html = document.documentElement;
    html.setAttribute("data-theme", isDark ? "dark" : "light");
    localStorage.setItem(STORAGE_KEY, isDark ? "1" : "0");
  }, [isDark]);

  const trackWidth = size * 1.8;
  const trackHeight = size;
  const knobSize = size * 0.8;
  const knobInset = (trackHeight - knobSize) / 2;
  const iconSize = knobSize * 0.6;

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setIsDark((v) => !v)}
      style={{
        width: trackWidth,
        height: trackHeight,
        background: isDark ? "#1a1a1a" : "#dbdbdb",
        border: "none",
        borderRadius: trackHeight / 2,
        position: "relative",
        cursor: "pointer",
        transition: "background 200ms ease",
        boxShadow: isDark
          ? "0 2px 8px rgba(0, 0, 0, 0.35)"
          : "0 1px 3px rgba(0, 0, 0, 0.12)",
        outline: "none",
        padding: 0,
        ...style,
      }}
    >
      <span
        style={{
          position: "absolute",
          top: knobInset,
          left: isDark ? trackWidth - knobSize - knobInset : knobInset,
          width: knobSize,
          height: knobSize,
          borderRadius: "50%",
          background: "#ffffff",
          boxShadow: "0 2px 6px rgba(0, 0, 0, 0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "left 250ms cubic-bezier(0.4, 1.2, 0.6, 1)",
        }}
      >
        {isDark ? (
          <Moon size={iconSize} color="#6b6b6b" strokeWidth={1.75} fill="#6b6b6b" />
        ) : (
          <Sun size={iconSize} color="#ff9100" strokeWidth={2} fill="#ff9100" />
        )}
      </span>
    </button>
  );
}
