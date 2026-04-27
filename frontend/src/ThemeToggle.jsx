import { Sun, Moon } from "lucide-react";

export default function ThemeToggle({ value, onChange, size = 30, style }) {
  const isDark = !!value;
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
      onClick={() => onChange?.(!isDark)}
      style={{
        width: trackWidth,
        height: trackHeight,
        background: isDark ? "#3f3f46" : "#dbdbdb",
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
        flexShrink: 0,
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
