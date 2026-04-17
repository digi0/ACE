import { useState, useEffect } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const MONTH_NAMES = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const CATEGORIES = ["all", "deadline", "holiday", "exam", "tuition", "academic"];

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// ── Category classification ───────────────────────────────────────────────────

function classifyEvent(eventName) {
  const n = eventName.toLowerCase();
  if (/(holiday|break|no classes|recess)/i.test(n))   return "holiday";
  if (/(deadline|last day|late drop|late add|late reg|withdraw)/i.test(n)) return "deadline";
  if (/(final exam)/i.test(n))                         return "exam";
  if (/(tuition|refund|billing|payment)/i.test(n))    return "tuition";
  return "academic";
}

// ── API event → component event ───────────────────────────────────────────────

function apiEventToLocal(apiEvent) {
  if (!apiEvent.iso_date) return null;
  const [, mm, dd] = apiEvent.iso_date.split("-").map(Number);
  return {
    month:    mm,
    day:      dd,
    label:    apiEvent.event + (apiEvent.time ? ` at ${apiEvent.time}` : ""),
    category: classifyEvent(apiEvent.event),
    iso_date: apiEvent.iso_date,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getDaysInMonth(year, month) {
  return new Date(year, month, 0).getDate();
}

function getFirstDayOfWeek(year, month) {
  return new Date(year, month - 1, 1).getDay();
}

function formatDay(day) {
  return day < 10 ? `0${day}` : `${day}`;
}

function categoryLabel(cat) {
  const map = { all: "All", deadline: "Deadlines", holiday: "Holidays",
                exam: "Exams", tuition: "Tuition", academic: "Academic" };
  return map[cat] || cat;
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AcademicCalendar() {
  const today       = new Date();
  const todayYear   = today.getFullYear();
  const todayMonth  = today.getMonth() + 1;
  const todayDay    = today.getDate();

  const [events, setEvents]             = useState([]);
  const [semesterName, setSemesterName] = useState("");
  const [year, setYear]                 = useState(todayYear);
  const [months, setMonths]             = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [selectedMonth, setSelectedMonth] = useState(null);
  const [activeCategory, setActiveCategory] = useState("all");

  // Fetch current semester on mount
  useEffect(() => {
    setLoading(true);
    fetch(`${API}/calendar/current`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        const localEvents = data.events
          .map(apiEventToLocal)
          .filter(Boolean);

        // Derive unique months (in order)
        const monthSet = [...new Set(localEvents.map((e) => e.month))].sort((a, b) => a - b);
        const semYear  = data.year || todayYear;

        setEvents(localEvents);
        setSemesterName(data.semester || "");
        setYear(semYear);
        setMonths(monthSet);

        // Default to current month if in range, else first month of semester
        const defaultM = monthSet.includes(todayMonth) ? todayMonth : monthSet[0];
        setSelectedMonth(defaultM ?? null);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // ── Render states ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="cal-page">
        <div className="cal-header">
          <h1 className="cal-title">Academic Calendar</h1>
          <p className="cal-subtitle">Loading…</p>
        </div>
        <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
          <div className="loading-dots"><span /><span /><span /></div>
        </div>
      </div>
    );
  }

  if (error || !selectedMonth) {
    return (
      <div className="cal-page">
        <div className="cal-header">
          <h1 className="cal-title">Academic Calendar</h1>
          <p className="cal-subtitle">Penn State University Park</p>
        </div>
        <p style={{ padding: "24px 0", color: "var(--gray-400)", fontSize: 13 }}>
          {error
            ? "Could not load calendar data. Check that the backend is running."
            : "No calendar data available."}
        </p>
        <p style={{ fontSize: 12, color: "var(--gray-400)" }}>
          Official source:{" "}
          <a href="https://www.registrar.psu.edu/academic-calendars/" target="_blank" rel="noreferrer">
            registrar.psu.edu
          </a>
        </p>
      </div>
    );
  }

  // ── Calendar math ──────────────────────────────────────────────────────────

  const daysInMonth    = getDaysInMonth(year, selectedMonth);
  const firstDayOfWeek = getFirstDayOfWeek(year, selectedMonth);

  const eventsThisMonth = events.filter((e) => e.month === selectedMonth);

  const eventsByDay = {};
  eventsThisMonth.forEach((e) => {
    if (!eventsByDay[e.day]) eventsByDay[e.day] = [];
    eventsByDay[e.day].push(e);
  });

  const filteredEvents =
    activeCategory === "all"
      ? eventsThisMonth
      : eventsThisMonth.filter((e) => e.category === activeCategory);

  const calendarCells = [];
  for (let i = 0; i < firstDayOfWeek; i++)
    calendarCells.push({ day: null, otherMonth: true });
  for (let d = 1; d <= daysInMonth; d++)
    calendarCells.push({ day: d, otherMonth: false });
  const remaining = (7 - (calendarCells.length % 7)) % 7;
  for (let i = 0; i < remaining; i++)
    calendarCells.push({ day: null, otherMonth: true });

  const isToday = (day) =>
    year === todayYear && selectedMonth === todayMonth && day === todayDay;

  const monthIndex = months.indexOf(selectedMonth);
  const prevMonth  = monthIndex > 0 ? months[monthIndex - 1] : null;
  const nextMonth  = monthIndex < months.length - 1 ? months[monthIndex + 1] : null;

  // Subtitle: derive pretty name from semester string e.g. "Spring 2026 - Regular Session"
  const subtitleParts = semesterName.split(" - ");
  const subtitle = subtitleParts[0] ? `${subtitleParts[0]} · Penn State` : "Penn State";

  return (
    <div className="cal-page">
      <div className="cal-header">
        <h1 className="cal-title">Academic Calendar</h1>
        <p className="cal-subtitle">{subtitle}</p>
      </div>

      <div className="cal-month-nav">
        <button
          className="cal-nav-arrow"
          onClick={() => prevMonth && setSelectedMonth(prevMonth)}
          disabled={!prevMonth}
          aria-label="Previous month"
        >
          &#8592;
        </button>
        <span className="cal-month-label">
          {MONTH_NAMES[selectedMonth]} {year}
        </span>
        <button
          className="cal-nav-arrow"
          onClick={() => nextMonth && setSelectedMonth(nextMonth)}
          disabled={!nextMonth}
          aria-label="Next month"
        >
          &#8594;
        </button>
      </div>

      <div className="cal-grid">
        {DAY_NAMES.map((name) => (
          <div key={name} className="cal-day-name">{name}</div>
        ))}
        {calendarCells.map((cell, idx) => {
          const dotsCategories =
            cell.day && eventsByDay[cell.day]
              ? eventsByDay[cell.day].map((e) => e.category)
              : [];
          const cellClasses = [
            "cal-day-cell",
            cell.otherMonth ? "cal-day-cell--other-month" : "",
            cell.day && isToday(cell.day) ? "cal-day-cell--today" : "",
          ].filter(Boolean).join(" ");

          return (
            <div key={idx} className={cellClasses}>
              {cell.day !== null && (
                <>
                  <span className="cal-day-number">{cell.day}</span>
                  {dotsCategories.length > 0 && (
                    <div className="cal-day-dots">
                      {[...new Set(dotsCategories)].map((cat) => (
                        <span key={cat} className={`cal-day-dot cal-day-dot--${cat}`} />
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      <div className="cal-category-tabs">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            className={`cal-category-tab${activeCategory === cat ? " cal-category-tab--active" : ""}`}
            onClick={() => setActiveCategory(cat)}
          >
            {categoryLabel(cat)}
          </button>
        ))}
      </div>

      <div className="cal-events-list">
        {filteredEvents.length === 0 ? (
          <p className="cal-empty">No events this month for the selected category.</p>
        ) : (
          filteredEvents
            .sort((a, b) => a.day - b.day)
            .map((event, idx) => (
              <div key={idx} className={`cal-event-row cal-event-row--${event.category}`}>
                <span className="cal-event-date">
                  {MONTH_NAMES[event.month].slice(0, 3)} {formatDay(event.day)}
                </span>
                <span className="cal-event-label">{event.label}</span>
                <span className={`cal-event-badge cal-event-badge--${event.category}`}>
                  {categoryLabel(event.category)}
                </span>
              </div>
            ))
        )}
      </div>
    </div>
  );
}
