import { PRIMARY } from "./nav.js";

/**
 * Fixed bottom tab bar shown only on mobile (App renders it behind a
 * useIsMobile() gate). All of its styling lives in responsive.css under the
 * 768px breakpoint, so it never affects desktop.
 */
export default function MobileBottomNav({ activeView, onNavigate }) {
  return (
    <nav className="mobile-bottom-nav" aria-label="Primary">
      {PRIMARY.map((item) => {
        const Icon = item.Icon;
        const active = activeView === item.id;
        return (
          <button
            key={item.id}
            className={`mbn-item${active ? " mbn-item--active" : ""}`}
            onClick={() => onNavigate(item.id)}
            aria-current={active ? "page" : undefined}
          >
            <Icon size={20} strokeWidth={active ? 2.25 : 1.9} aria-hidden />
            <span className="mbn-label">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
