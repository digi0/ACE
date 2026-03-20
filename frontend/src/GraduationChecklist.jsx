import { useState, useEffect } from "react";

const SECTIONS = [
  {
    id: "core",
    name: "Required CS Courses",
    icon: "💻",
    items: [
      { id: "cmpsc121", code: "CMPSC 121/131", name: "Introduction to Programming", cr: 3 },
      { id: "cmpsc122", code: "CMPSC 122/132", name: "Intermediate Programming", cr: 3 },
      { id: "cmpsc221", code: "CMPSC 221", name: "Object-Oriented Programming", cr: 3 },
      { id: "cmpsc311", code: "CMPSC 311", name: "Introduction to Systems Programming", cr: 3 },
      { id: "cmpsc312", code: "CMPSC 312", name: "Computer Organization", cr: 3 },
      { id: "cmpsc360", code: "CMPSC 360", name: "Discrete Mathematics", cr: 3 },
      { id: "cmpsc431w", code: "CMPSC 431W", name: "Database Management Systems", cr: 3 },
      { id: "cmpsc441", code: "CMPSC 441", name: "Artificial Intelligence", cr: 3 },
      { id: "cmpsc461", code: "CMPSC 461", name: "Programming Language Concepts", cr: 3 },
      { id: "cmpsc462", code: "CMPSC 462", name: "Data Structures", cr: 3 },
      { id: "cmpsc463", code: "CMPSC 463", name: "Algorithm Design", cr: 3 },
      { id: "cmpsc473", code: "CMPSC 473", name: "Operating Systems", cr: 3 },
      { id: "cmpsc483w", code: "CMPSC 483W", name: "Senior Design Project", cr: 3 },
    ],
  },
  {
    id: "math",
    name: "Mathematics",
    icon: "∑",
    items: [
      { id: "math140", code: "MATH 140", name: "Calculus I", cr: 4 },
      { id: "math141", code: "MATH 141", name: "Calculus II", cr: 4 },
      { id: "math220", code: "MATH 220", name: "Matrices", cr: 2 },
      { id: "stat318", code: "STAT 318/319", name: "Statistics", cr: 3 },
    ],
  },
  {
    id: "science",
    name: "Science",
    icon: "⚗",
    items: [
      { id: "phys211", code: "PHYS 211", name: "General Physics I", cr: 3 },
      { id: "phys212", code: "PHYS 212", name: "General Physics II", cr: 3 },
      { id: "phys211n", code: "PHYS 211N/212N", name: "Physics Lab", cr: 1 },
    ],
  },
  {
    id: "writing",
    name: "Writing & Communication",
    icon: "✍",
    items: [
      { id: "engl15", code: "ENGL 15/30", name: "Rhetoric & Composition", cr: 3 },
      { id: "engl202", code: "ENGL 202C/202D", name: "Technical Writing", cr: 3 },
      { id: "cas100", code: "CAS 100A/B/C", name: "Effective Speech", cr: 3 },
    ],
  },
  {
    id: "gened",
    name: "General Education",
    icon: "🎓",
    items: [
      { id: "ga", code: "GA", name: "Arts", cr: 3 },
      { id: "gh", code: "GH", name: "Humanities", cr: 3 },
      { id: "gs", code: "GS", name: "Social/Behavioral Sciences", cr: 3 },
      { id: "gha", code: "GHA", name: "Health & Physical Activity", cr: 2 },
      { id: "gn", code: "GN", name: "Natural Sciences", cr: 3 },
    ],
  },
  {
    id: "electives",
    name: "Electives",
    icon: "📚",
    items: [
      { id: "elec1", code: "CMPSC Elective", name: "Upper-level CMPSC elective 1", cr: 3 },
      { id: "elec2", code: "CMPSC Elective", name: "Upper-level CMPSC elective 2", cr: 3 },
      { id: "elec3", code: "CMPSC Elective", name: "Upper-level CMPSC elective 3", cr: 3 },
      { id: "free", code: "Free Elective", name: "Free elective", cr: 3 },
    ],
  },
];

const TOTAL_ITEMS = SECTIONS.reduce((acc, s) => acc + s.items.length, 0);

export default function GraduationChecklist({ userId }) {
  const storageKey = `ace_checklist_${userId || "default"}`;

  const [checked, setChecked] = useState(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  const [openSections, setOpenSections] = useState(() => {
    const initial = {};
    SECTIONS.forEach((s) => (initial[s.id] = true));
    return initial;
  });

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(checked));
    } catch {
      // ignore storage errors
    }
  }, [checked, storageKey]);

  const totalDone = Object.values(checked).filter(Boolean).length;

  const toggleItem = (itemId) => {
    setChecked((prev) => ({ ...prev, [itemId]: !prev[itemId] }));
  };

  const toggleSection = (sectionId) => {
    setOpenSections((prev) => ({ ...prev, [sectionId]: !prev[sectionId] }));
  };

  const getSectionStatus = (section) => {
    const done = section.items.filter((item) => checked[item.id]).length;
    const total = section.items.length;
    if (done === total) return "complete";
    if (done > 0) return "partial";
    return "none";
  };

  const progressPercent = TOTAL_ITEMS > 0 ? Math.round((totalDone / TOTAL_ITEMS) * 100) : 0;

  return (
    <div className="checklist-page">
      <div className="checklist-header">
        <h1 className="checklist-title">Graduation Checklist</h1>
        <p className="checklist-subtitle">
          CMPSC B.S. Degree · 2024–2025 Handbook · Penn State University Park
        </p>
      </div>

      <div className="checklist-overall">
        <div className="checklist-overall-label">
          <span>
            <strong>{totalDone}</strong> of <strong>{TOTAL_ITEMS}</strong> requirements completed
          </span>
          <span>{progressPercent}%</span>
        </div>
        <div className="checklist-overall-bar">
          <div
            className="checklist-overall-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {SECTIONS.map((section) => {
        const doneCnt = section.items.filter((item) => checked[item.id]).length;
        const total = section.items.length;
        const status = getSectionStatus(section);
        const isOpen = openSections[section.id];

        const sectionClasses = [
          "checklist-section",
          status === "complete" ? "checklist-section--complete" : "",
          status === "partial" ? "checklist-section--partial" : "",
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <div key={section.id} className={sectionClasses}>
            <button
              className="checklist-section-header"
              onClick={() => toggleSection(section.id)}
              aria-expanded={isOpen}
            >
              <span className="checklist-section-icon">{section.icon}</span>
              <span className="checklist-section-name">{section.name}</span>
              <span className="checklist-section-count">
                {doneCnt}/{total} done
              </span>
              <span className={`checklist-chevron${isOpen ? " checklist-chevron--open" : ""}`}>
                ›
              </span>
            </button>

            {isOpen && (
              <div className="checklist-items">
                {section.items.map((item) => {
                  const isDone = !!checked[item.id];
                  return (
                    <div
                      key={item.id}
                      className={`checklist-item${isDone ? " checklist-item--done" : ""}`}
                      onClick={() => toggleItem(item.id)}
                      role="checkbox"
                      aria-checked={isDone}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === " " || e.key === "Enter") {
                          e.preventDefault();
                          toggleItem(item.id);
                        }
                      }}
                    >
                      <span className={`checklist-checkbox${isDone ? " checklist-checkbox--checked" : ""}`}>
                        {isDone && "✓"}
                      </span>
                      <span className="checklist-course-code">{item.code}</span>
                      <span className="checklist-course-name">{item.name}</span>
                      <span className="checklist-course-cr">{item.cr} cr</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}

      <p className="checklist-disclaimer">
        This checklist is for reference only. Always verify your degree requirements with your
        official academic advisor and the Penn State Degree Audit system.
      </p>
    </div>
  );
}
