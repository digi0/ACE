import { MessageSquare, LayoutGrid, BookOpen, GraduationCap } from "lucide-react";

// The four primary views, mirroring the desktop top-bar tabs. Tools (GPA,
// calendar, prereqs, etc.) and chat history stay in the drawer, not here.
const NAV_ITEMS = [
  { id: "chat",      label: "Chat",      Icon: MessageSquare },
  { id: "dashboard", label: "Dashboard", Icon: LayoutGrid },
  { id: "resources", label: "Resources", Icon: BookOpen },
  { id: "gened",     label: "Gen Ed",    Icon: GraduationCap },
];

/**
 * Fixed bottom tab bar shown only on mobile (App renders it behind a
 * useIsMobile() gate). All of its styling lives in responsive.css under the
 * 768px breakpoint, so it never affects desktop.
 */
export default function MobileBottomNav({ activeView, onNavigate }) {
  return (
    <nav className="mobile-bottom-nav" aria-label="Primary">
      {NAV_ITEMS.map((item) => {
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
