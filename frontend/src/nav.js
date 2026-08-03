import {
  MessageSquare, LayoutGrid, BookOpen, GraduationCap,
  Calculator, Compass, CalendarRange, CalendarDays, ListChecks, StickyNote,
} from "lucide-react";

/**
 * The single source of truth for every destination in the app.
 *
 * There used to be three nav lists — the top-bar tabs, the sidebar TOOLS grid,
 * and MobileBottomNav — each with its own copy of the destinations. Gen Ed and
 * Resources appeared in two of them, `checklist` appeared in none (the view was
 * rendered and lazy-loaded but unreachable), and only the four top-bar views
 * ever computed an active state, so the other seven left the nav showing a
 * stale highlight or nothing at all.
 *
 * One list fixes all of that: every consumer maps over the same ids, so active
 * state is a single comparison and a new view can only be added in one place.
 */
export const PRIMARY = [
  { id: "chat",      label: "Chat",      Icon: MessageSquare },
  { id: "dashboard", label: "Dashboard", Icon: LayoutGrid },
  { id: "gened",     label: "Gen Ed",    Icon: GraduationCap },
  { id: "resources", label: "Resources", Icon: BookOpen },
];

export const TOOLS = [
  { id: "gpa",       label: "GPA Calc",  Icon: Calculator },
  { id: "prereq",    label: "Prereqs",   Icon: Compass },
  { id: "plan",      label: "Plan",      Icon: CalendarRange },
  { id: "calendar",  label: "Calendar",  Icon: CalendarDays },
  { id: "checklist", label: "Checklist", Icon: ListChecks },
  { id: "notes",     label: "Notes",     Icon: StickyNote },
];

/** Settings sits with the sidebar's footer actions, not in the tools grid. */
export const SETTINGS_ID = "settings";

const LABELS = Object.fromEntries(
  [...PRIMARY, ...TOOLS, { id: SETTINGS_ID, label: "Settings" }].map((v) => [v.id, v.label])
);

/** Human label for a view id — used by the top bar to name the current view. */
export const viewLabel = (id) => LABELS[id] ?? "";

/** True for the four views the top-bar tabs can represent. Everything else is a
 *  tool, and gets named beside the wordmark instead of highlighting a tab. */
export const isPrimaryView = (id) => PRIMARY.some((v) => v.id === id);
