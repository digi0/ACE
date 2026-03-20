import { useState, useEffect, useCallback } from "react";

/* ─── Data ──────────────────────────────────────────────────────────────── */

const GEN_ED_CATS = [
  {
    id: "fyw",
    code: "FYW",
    label: "First-Year Writing",
    icon: "✍️",
    creditsRequired: 3,
    description:
      "Develops foundational college writing skills. Required for all Penn State students.",
    csNote:
      "Already required for your CMPSC degree. Satisfied by ENGL 15 or 30.",
    courses: [
      {
        code: "ENGL 015",
        name: "Rhetoric & Composition",
        cr: 3,
        tags: ["major-req"],
        doubleDip: "CMPSC Major",
      },
      {
        code: "ENGL 030",
        name: "Honors Composition",
        cr: 3,
        tags: ["major-req"],
      },
    ],
  },
  {
    id: "gq",
    code: "GQ",
    label: "Quantification",
    icon: "➗",
    creditsRequired: 3,
    description:
      "Develops mathematical reasoning and quantitative literacy.",
    csNote:
      "MATH 140 satisfies GQ and is required for your CMPSC major — no extra course needed.",
    courses: [
      {
        code: "MATH 140",
        name: "Calculus I",
        cr: 4,
        tags: ["major-req", "recommended"],
        doubleDip: "CMPSC Major",
      },
      {
        code: "MATH 110",
        name: "Techniques of Calculus I",
        cr: 4,
        tags: [],
      },
      {
        code: "STAT 200",
        name: "Elementary Statistics",
        cr: 4,
        tags: ["popular"],
      },
      {
        code: "MATH 004",
        name: "Intermediate Algebra",
        cr: 3,
        tags: [],
      },
    ],
  },
  {
    id: "gn",
    code: "GN",
    label: "Natural Sciences",
    icon: "🔬",
    creditsRequired: 6,
    description:
      "Two GN courses required (6 cr total). At least one must include a lab component.",
    csNote:
      "PHYS 211 + PHYS 212 (with labs 211N/212N) satisfy GN and are required for CMPSC — no extra courses needed.",
    courses: [
      {
        code: "PHYS 211",
        name: "General Physics I (+ Lab)",
        cr: 3,
        tags: ["major-req", "recommended"],
        doubleDip: "CMPSC Major",
      },
      {
        code: "PHYS 212",
        name: "General Physics II (+ Lab)",
        cr: 3,
        tags: ["major-req", "recommended"],
        doubleDip: "CMPSC Major",
      },
      {
        code: "CHEM 110",
        name: "Chemical Principles I",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "BIOL 110",
        name: "Biology: Concepts & Applications",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "ASTR 001",
        name: "Astronomical Universe",
        cr: 3,
        tags: ["popular", "easy"],
      },
    ],
  },
  {
    id: "ga",
    code: "GA",
    label: "Arts",
    icon: "🎨",
    creditsRequired: 3,
    description:
      "Explores creative expression in visual art, music, theatre, film, or design.",
    csNote:
      "Great low-stress elective. MUSC 008 (History of Rock) and THEA 100 are popular with CS students.",
    courses: [
      {
        code: "MUSC 007",
        name: "Music Appreciation",
        cr: 3,
        tags: ["popular", "easy"],
      },
      {
        code: "MUSC 008",
        name: "History of Rock Music",
        cr: 3,
        tags: ["popular", "easy"],
      },
      {
        code: "THEA 100",
        name: "Introduction to Theatre",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "ART 010",
        name: "Introduction to Photography",
        cr: 3,
        tags: ["hands-on"],
      },
      {
        code: "ENGL 200N",
        name: "Literature and Film",
        cr: 3,
        tags: ["online"],
      },
      {
        code: "MUSIC 045N",
        name: "Introduction to World Music",
        cr: 3,
        tags: ["online", "easy"],
      },
    ],
  },
  {
    id: "gh",
    code: "GH",
    label: "Humanities",
    icon: "📖",
    creditsRequired: 3,
    description:
      "Engages with human culture, philosophy, history, and literature.",
    csNote:
      "PHIL 010 (Ethics) is highly relevant to CS/AI careers and strongly recommended. PHIL 012 (Logic) is a natural fit for CS thinking.",
    courses: [
      {
        code: "PHIL 010",
        name: "Ethics",
        cr: 3,
        tags: ["cs-relevant", "recommended"],
      },
      {
        code: "PHIL 012",
        name: "Logic and Critical Thinking",
        cr: 3,
        tags: ["cs-relevant", "recommended"],
      },
      {
        code: "HIST 021",
        name: "United States History I",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "LING 100",
        name: "Language and Linguistics",
        cr: 3,
        tags: ["cs-relevant"],
      },
      {
        code: "ENGL 200N",
        name: "Introduction to Literature",
        cr: 3,
        tags: ["popular", "online"],
      },
      {
        code: "PHIL 001",
        name: "Introduction to Philosophy",
        cr: 3,
        tags: ["popular"],
      },
    ],
  },
  {
    id: "gs",
    code: "GS",
    label: "Social & Behavioral Sciences",
    icon: "🧠",
    creditsRequired: 3,
    description:
      "Develops understanding of human behavior, society, and social institutions.",
    csNote:
      "ECON 102 (Microeconomics) is useful for tech product thinking and entrepreneurship. PSYCH 100 is popular and easy.",
    courses: [
      {
        code: "PSYCH 100",
        name: "Introduction to Psychology",
        cr: 3,
        tags: ["popular", "easy"],
      },
      {
        code: "ECON 102",
        name: "Microeconomics",
        cr: 3,
        tags: ["cs-relevant", "recommended"],
      },
      {
        code: "SOC 001",
        name: "Introduction to Sociology",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "COMM 100",
        name: "Introduction to Communication",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "PSYCH 212",
        name: "Social Psychology",
        cr: 3,
        tags: ["interesting"],
      },
      {
        code: "ECON 104",
        name: "Macroeconomics",
        cr: 3,
        tags: ["cs-relevant"],
      },
    ],
  },
  {
    id: "gha",
    code: "GHA",
    label: "Health & Physical Activity",
    icon: "🏃",
    creditsRequired: 2,
    description:
      "Develops knowledge and habits for lifelong wellness and physical activity.",
    csNote:
      "KINES 082 (Health for Living) is very popular among CS students — often available online.",
    courses: [
      {
        code: "KINES 082",
        name: "Health for Living",
        cr: 2,
        tags: ["popular", "online", "recommended"],
      },
      {
        code: "KINES 071",
        name: "Personal Fitness & Wellness",
        cr: 1,
        tags: ["activity"],
      },
      {
        code: "KINES 001",
        name: "Walking for Fitness",
        cr: 1,
        tags: ["activity", "easy"],
      },
      {
        code: "KINES 003",
        name: "Swimming — Beginner",
        cr: 1,
        tags: ["activity"],
      },
    ],
  },
  {
    id: "us",
    code: "US",
    label: "United States Cultures",
    icon: "🇺🇸",
    creditsRequired: 3,
    description:
      "Explores diversity, equity, and the complexity of U.S. society, history, and culture.",
    csNote:
      "Look for US-designated courses in subjects you already enjoy — many history, sociology, and English courses carry the US designation.",
    courses: [
      {
        code: "HIST 026",
        name: "African American History",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "WMNST 001",
        name: "Introduction to Women's Studies",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "SOC 119",
        name: "Race and Ethnic Relations",
        cr: 3,
        tags: ["popular", "double-dip"],
        doubleDip: "GS",
      },
      {
        code: "AFAM 100",
        name: "Introduction to African American Studies",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "HIST 021",
        name: "United States History I",
        cr: 3,
        tags: ["popular", "double-dip"],
        doubleDip: "GH",
      },
      {
        code: "COMM 150",
        name: "Media and Society",
        cr: 3,
        tags: ["cs-relevant"],
      },
    ],
  },
  {
    id: "il",
    code: "IL",
    label: "International Cultures",
    icon: "🌍",
    creditsRequired: 3,
    description:
      "Broadens understanding of global cultures, perspectives, and international issues.",
    csNote:
      "Many foreign language intermediate courses (SPAN 003, FRNCH 003, etc.) satisfy IL. Great for global tech careers.",
    courses: [
      {
        code: "ANTH 001",
        name: "Introduction to Anthropology",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "INTL 100",
        name: "Introduction to International Relations",
        cr: 3,
        tags: ["popular", "cs-relevant"],
      },
      {
        code: "GEOG 020",
        name: "Geography of World Regions",
        cr: 3,
        tags: ["popular"],
      },
      {
        code: "SPAN 003",
        name: "Intermediate Spanish I",
        cr: 4,
        tags: ["language"],
      },
      {
        code: "FRNCH 003",
        name: "Intermediate French I",
        cr: 4,
        tags: ["language"],
      },
      {
        code: "JAPNS 003",
        name: "Intermediate Japanese I",
        cr: 4,
        tags: ["language"],
      },
    ],
  },
];

const SMART_PICKS = [
  {
    code: "PHIL 010",
    cat: "GH",
    name: "Ethics",
    reason:
      "Directly relevant to AI ethics, computing ethics, and tech careers. Increasingly expected of CS graduates.",
  },
  {
    code: "ECON 102",
    cat: "GS",
    name: "Microeconomics",
    reason:
      "Great foundation for product thinking, startups, and understanding tech business models.",
  },
  {
    code: "KINES 082",
    cat: "GHA",
    name: "Health for Living",
    reason:
      "Quick 2-credit online checkbox. Low workload — ideal for a heavy CS semester.",
  },
  {
    code: "MUSC 008",
    cat: "GA",
    name: "History of Rock Music",
    reason:
      "Popular, low-stress, and a great mental break from a demanding CS course load.",
  },
  {
    code: "INTL 100",
    cat: "IL",
    name: "Introduction to International Relations",
    reason:
      "Useful global perspective for international tech careers and working with distributed teams.",
  },
];

/* ─── Helpers ───────────────────────────────────────────────────────────── */

function getCategoryStatus(cat, completed) {
  const checkedCredits = cat.courses
    .filter((c) => completed[c.code])
    .reduce((sum, c) => sum + c.cr, 0);
  const anyCompleted = cat.courses.some((c) => completed[c.code]);
  if (checkedCredits >= cat.creditsRequired) return "satisfied";
  if (anyCompleted) return "partial";
  return "needed";
}

function TagBadge({ tag, doubleDip }) {
  if (tag === "major-req")
    return (
      <span className="gened-tag gened-tag--major" title="Already required by CMPSC Major">
        Already in Major
      </span>
    );
  if (tag === "recommended")
    return (
      <span className="gened-tag gened-tag--recommended">Recommended</span>
    );
  if (tag === "cs-relevant")
    return <span className="gened-tag gened-tag--cs">CS-Relevant</span>;
  if (tag === "popular")
    return <span className="gened-tag gened-tag--popular">Popular</span>;
  if (tag === "online")
    return <span className="gened-tag gened-tag--online">Online</span>;
  if (tag === "double-dip")
    return (
      <span
        className="gened-tag gened-tag--doubledip"
        title={doubleDip ? `Also satisfies ${doubleDip}` : "Can double-count"}
      >
        Double-Dip{doubleDip ? ` → ${doubleDip}` : ""}
      </span>
    );
  return null;
}

/* ─── CourseRow ─────────────────────────────────────────────────────────── */

function CourseRow({ course, done, onToggle }) {
  const visibleTags = course.tags.filter(
    (t) =>
      ["major-req", "recommended", "cs-relevant", "popular", "online", "double-dip"].includes(t)
  );

  return (
    <label className={`gened-course-row${done ? " gened-course-row--done" : ""}`}>
      <input
        type="checkbox"
        className="gened-checkbox"
        checked={done}
        onChange={() => onToggle(course.code)}
      />
      <span className="gened-course-code">{course.code}</span>
      <span className="gened-course-name">{course.name}</span>
      <span className="gened-course-cr">{course.cr} cr</span>
      {visibleTags.length > 0 && (
        <span className="gened-tags">
          {visibleTags.map((t) => (
            <TagBadge key={t} tag={t} doubleDip={course.doubleDip} />
          ))}
        </span>
      )}
    </label>
  );
}

/* ─── CategoryCard ──────────────────────────────────────────────────────── */

function CategoryCard({ cat, completed, onToggle, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen || false);
  const status = getCategoryStatus(cat, completed);

  const checkedCredits = cat.courses
    .filter((c) => completed[c.code])
    .reduce((sum, c) => sum + c.cr, 0);
  const completedCount = cat.courses.filter((c) => completed[c.code]).length;

  return (
    <div className={`gened-cat-card gened-cat-card--${status}`}>
      <button
        className="gened-cat-header"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className={`gened-cat-code gened-cat-code--${status}`}>
          {cat.icon} {cat.code}
        </span>
        <span className="gened-cat-label">{cat.label}</span>
        <span className="gened-cat-meta">
          <span className="gened-cat-credits">
            {checkedCredits}/{cat.creditsRequired} cr
          </span>
          <span className="gened-cat-count">
            {completedCount}/{cat.courses.length}
          </span>
          <span className={`gened-cat-chevron${open ? " gened-cat-chevron--open" : ""}`}>
            ›
          </span>
        </span>
      </button>

      {open && (
        <div className="gened-cat-body">
          <div className="gened-cat-note">
            <strong>CS Tip:</strong> {cat.csNote}
          </div>
          <p className="gened-cat-desc">{cat.description}</p>
          <div className="gened-course-list">
            {cat.courses.map((course) => (
              <CourseRow
                key={course.code}
                course={course}
                done={!!completed[course.code]}
                onToggle={onToggle}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Main Component ────────────────────────────────────────────────────── */

export default function GenEdExplorer({ userId }) {
  const storageKey = `ace_gened_${userId}`;

  const [completed, setCompleted] = useState(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });

  const [filter, setFilter] = useState("all"); // "all" | "remaining" | "double-dips"

  // Persist on change
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(completed));
    } catch {
      // ignore quota errors
    }
  }, [completed, storageKey]);

  const toggleCourse = useCallback((code) => {
    setCompleted((prev) => ({ ...prev, [code]: !prev[code] }));
  }, []);

  // Compute overall progress
  const satisfiedCats = GEN_ED_CATS.filter(
    (cat) => getCategoryStatus(cat, completed) === "satisfied"
  ).length;
  const totalCats = GEN_ED_CATS.length;
  const progressPct = Math.round((satisfiedCats / totalCats) * 100);

  // Apply filter
  const visibleCats = GEN_ED_CATS.filter((cat) => {
    if (filter === "all") return true;
    if (filter === "remaining")
      return getCategoryStatus(cat, completed) !== "satisfied";
    if (filter === "double-dips")
      return cat.courses.some((c) => c.tags.includes("major-req"));
    return true;
  });

  return (
    <div className="gened-page">
      {/* Header */}
      <div className="gened-header">
        <div>
          <h1 className="gened-title">Gen Ed Explorer</h1>
          <p className="gened-subtitle">Penn State · CMPSC B.S. · 2024–2025</p>
        </div>
      </div>

      {/* Overall Progress */}
      <div className="gened-overall">
        <span className="gened-overall-label">
          {satisfiedCats} of {totalCats} categories satisfied
        </span>
        <div className="gened-overall-bar" aria-label={`${progressPct}% complete`}>
          <div
            className="gened-overall-fill"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="gened-overall-pct">{progressPct}%</span>
      </div>

      {/* Filter Tabs */}
      <div className="gened-filter-tabs" role="tablist">
        {[
          { id: "all", label: "All" },
          { id: "remaining", label: "Remaining" },
          { id: "double-dips", label: "Major Double-Dips" },
        ].map((tab) => (
          <button
            key={tab.id}
            className={`gened-filter-tab${filter === tab.id ? " gened-filter-tab--active" : ""}`}
            role="tab"
            aria-selected={filter === tab.id}
            onClick={() => setFilter(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Category Cards */}
      <div className="gened-cat-list">
        {visibleCats.length === 0 && (
          <p className="gened-empty">
            All categories satisfied! Great work.
          </p>
        )}
        {visibleCats.map((cat) => (
          <CategoryCard
            key={cat.id}
            cat={cat}
            completed={completed}
            onToggle={toggleCourse}
            defaultOpen={false}
          />
        ))}
      </div>

      {/* Smart Picks */}
      <div className="gened-smart-picks">
        <h2 className="gened-smart-title">Smart Picks for CS Students</h2>
        <ul className="gened-smart-list">
          {SMART_PICKS.map((pick) => (
            <li key={pick.code} className="gened-smart-item">
              <span className="gened-smart-course">
                {pick.code} — {pick.name}
                <span className="gened-smart-cat">({pick.cat})</span>
              </span>
              <span className="gened-smart-reason">{pick.reason}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Disclaimer */}
      <p className="gened-disclaimer">
        Gen Ed requirements may vary by degree program and catalog year. Always
        verify with your official degree audit on LionPATH or your academic
        advisor.
      </p>
    </div>
  );
}
