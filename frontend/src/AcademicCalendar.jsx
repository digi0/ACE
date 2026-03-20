import { useState } from "react";

const EVENTS = [
  { month: 1, day: 13, label: "First day of classes", category: "academic" },
  { month: 1, day: 17, label: "Last day to add full-semester courses", category: "deadline" },
  { month: 1, day: 20, label: "MLK Day – No classes", category: "holiday" },
  { month: 1, day: 26, label: "Last day to drop with 100% refund", category: "tuition" },
  { month: 2, day: 14, label: "Last day to drop without W grade", category: "deadline" },
  { month: 2, day: 16, label: "Presidents' Day – No classes", category: "holiday" },
  { month: 3, day: 9,  label: "Spring Break begins", category: "holiday" },
  { month: 3, day: 13, label: "Spring Break ends", category: "holiday" },
  { month: 3, day: 21, label: "Last day to withdraw (W grade)", category: "deadline" },
  { month: 4, day: 3,  label: "Good Friday – No classes", category: "holiday" },
  { month: 4, day: 11, label: "Last day of classes", category: "academic" },
  { month: 4, day: 12, label: "Final Exams begin", category: "exam" },
  { month: 4, day: 18, label: "Final Exams end", category: "exam" },
  { month: 4, day: 25, label: "Grades due", category: "academic" },
  { month: 5, day: 2,  label: "Commencement", category: "academic" },
  { month: 5, day: 10, label: "Summer tuition due", category: "tuition" },
  { month: 5, day: 18, label: "Summer session begins", category: "academic" },
];

const MONTHS = [
  { index: 1, name: "January" },
  { index: 2, name: "February" },
  { index: 3, name: "March" },
  { index: 4, name: "April" },
  { index: 5, name: "May" },
];

const CATEGORIES = ["all", "deadline", "holiday", "exam", "tuition", "academic"];

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

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
  if (cat === "all") return "All";
  if (cat === "deadline") return "Deadlines";
  if (cat === "holiday") return "Holidays";
  if (cat === "exam") return "Exams";
  if (cat === "tuition") return "Tuition";
  if (cat === "academic") return "Academic";
  return cat;
}

export default function AcademicCalendar() {
  const today = new Date();
  const todayYear = today.getFullYear();
  const todayMonth = today.getMonth() + 1;
  const todayDay = today.getDate();

  const defaultMonth =
    todayYear === 2026 && todayMonth >= 1 && todayMonth <= 5
      ? todayMonth
      : 3;

  const [selectedMonth, setSelectedMonth] = useState(defaultMonth);
  const [activeCategory, setActiveCategory] = useState("all");

  const year = 2026;
  const daysInMonth = getDaysInMonth(year, selectedMonth);
  const firstDayOfWeek = getFirstDayOfWeek(year, selectedMonth);

  const eventsThisMonth = EVENTS.filter((e) => e.month === selectedMonth);
  const eventDaySet = new Set(eventsThisMonth.map((e) => e.day));

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
  for (let i = 0; i < firstDayOfWeek; i++) {
    calendarCells.push({ day: null, otherMonth: true });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    calendarCells.push({ day: d, otherMonth: false });
  }
  const remaining = (7 - (calendarCells.length % 7)) % 7;
  for (let i = 0; i < remaining; i++) {
    calendarCells.push({ day: null, otherMonth: true });
  }

  const isToday = (day) =>
    year === todayYear && selectedMonth === todayMonth && day === todayDay;

  const monthIndex = MONTHS.findIndex((m) => m.index === selectedMonth);
  const prevMonth = monthIndex > 0 ? MONTHS[monthIndex - 1].index : null;
  const nextMonth = monthIndex < MONTHS.length - 1 ? MONTHS[monthIndex + 1].index : null;

  return (
    <div className="cal-page">
      <div className="cal-header">
        <h1 className="cal-title">Academic Calendar</h1>
        <p className="cal-subtitle">Spring 2026 · Penn State University Park</p>
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
          {MONTHS.find((m) => m.index === selectedMonth)?.name} {year}
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
          <div key={name} className="cal-day-name">
            {name}
          </div>
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
          ]
            .filter(Boolean)
            .join(" ");

          return (
            <div key={idx} className={cellClasses}>
              {cell.day !== null && (
                <>
                  <span className="cal-day-number">{cell.day}</span>
                  {dotsCategories.length > 0 && (
                    <div className="cal-day-dots">
                      {[...new Set(dotsCategories)].map((cat) => (
                        <span
                          key={cat}
                          className={`cal-day-dot cal-day-dot--${cat}`}
                        />
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
              <div
                key={idx}
                className={`cal-event-row cal-event-row--${event.category}`}
              >
                <span className="cal-event-date">
                  {MONTHS.find((m) => m.index === event.month)?.name.slice(0, 3)}{" "}
                  {formatDay(event.day)}
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
