import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/* ── Static fallback courses for categories sparse in the bulletin scrape ── */
const STATIC_FALLBACK = {
  FYW: [
    { code: "ENGL 015", title: "Rhetoric & Composition",       credits: "3", tags: [] },
    { code: "ENGL 030", title: "Honors Composition",           credits: "3", tags: [] },
  ],
  GQ: [
    { code: "MATH 140", title: "Calculus I",                   credits: "4", tags: [] },
    { code: "MATH 110", title: "Techniques of Calculus I",     credits: "4", tags: [] },
    { code: "STAT 200", title: "Elementary Statistics",        credits: "4", tags: ["popular"] },
  ],
  GHW: [
    { code: "KINES 082", title: "Health for Living",           credits: "2", tags: ["popular"] },
    { code: "KINES 071", title: "Personal Fitness & Wellness", credits: "1", tags: [] },
    { code: "KINES 001", title: "Walking for Fitness",         credits: "1", tags: [] },
  ],
  US: [
    { code: "HIST 026",  title: "African American History",            credits: "3", tags: ["popular"] },
    { code: "WMNST 001", title: "Introduction to Women's Studies",     credits: "3", tags: ["popular"] },
    { code: "SOC 119",   title: "Race and Ethnic Relations",           credits: "3", tags: ["popular"] },
    { code: "AFAM 100",  title: "Introduction to African American Studies", credits: "3", tags: [] },
    { code: "HIST 021",  title: "United States History I",             credits: "3", tags: ["popular"] },
  ],
  IL: [
    { code: "ANTH 001",  title: "Introduction to Anthropology",        credits: "3", tags: ["popular"] },
    { code: "INTL 100",  title: "Introduction to International Relations", credits: "3", tags: ["popular"] },
    { code: "GEOG 020",  title: "Geography of World Regions",          credits: "3", tags: ["popular"] },
    { code: "SPAN 003",  title: "Intermediate Spanish I",              credits: "4", tags: [] },
    { code: "FRNCH 003", title: "Intermediate French I",               credits: "4", tags: [] },
  ],
};

/* ── Universal smart picks (shown when no major is selected) ─────────────── */
const UNIVERSAL_SMART_PICKS = [
  { code: "PHIL 010",  cat: "GH",  name: "Ethics",
    reason: "Directly relevant to AI ethics, computing ethics, and tech careers." },
  { code: "ECON 102",  cat: "GS",  name: "Microeconomics",
    reason: "Great foundation for product thinking, startups, and tech business." },
  { code: "KINES 082", cat: "GHW", name: "Health for Living",
    reason: "Quick 2-credit online checkbox — low workload." },
  { code: "MUSC 008",  cat: "GA",  name: "History of Rock Music",
    reason: "Popular, low-stress mental break from a demanding course load." },
  { code: "INTL 100",  cat: "IL",  name: "Introduction to International Relations",
    reason: "Useful global perspective for international careers." },
];

const CAT_META = {
  FYW: { label: "First-Year Writing",           creditsRequired: 3 },
  GQ:  { label: "Quantification",               creditsRequired: 3 },
  GN:  { label: "Natural Sciences",             creditsRequired: 6 },
  GA:  { label: "Arts",                         creditsRequired: 3 },
  GH:  { label: "Humanities",                   creditsRequired: 3 },
  GS:  { label: "Social & Behavioral Sciences", creditsRequired: 3 },
  GHW: { label: "Health & Physical Activity",   creditsRequired: 2 },
  US:  { label: "United States Cultures",       creditsRequired: 3 },
  IL:  { label: "International Cultures",       creditsRequired: 3 },
  GWS: { label: "Writing & Speaking",           creditsRequired: 3 },
};

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function creditNum(cr) {
  if (!cr) return 0;
  const n = parseFloat(cr);
  return isNaN(n) ? 0 : n;
}

function getCatStatus(courses, completed, creditsRequired) {
  const done = courses.filter((c) => completed[c.code]);
  const cr   = done.reduce((s, c) => s + creditNum(c.credits), 0);
  if (cr >= creditsRequired) return "satisfied";
  if (done.length > 0)        return "partial";
  return "needed";
}

function TagBadge({ tag }) {
  const map = {
    "major-req":   ["gened-tag gened-tag--major",       "Already in Major"],
    popular:       ["gened-tag gened-tag--popular",      "Popular"],
    recommended:   ["gened-tag gened-tag--recommended",  "Recommended"],
  };
  const entry = map[tag];
  if (!entry) return null;
  return <span className={entry[0]}>{entry[1]}</span>;
}

function CourseRow({ course, done, onToggle }) {
  const tags = (course.tags || []).filter((t) => t in { "major-req": 1, popular: 1, recommended: 1 });
  return (
    <label className={`gened-course-row${done ? " gened-course-row--done" : ""}`}>
      <input
        type="checkbox"
        className="gened-checkbox"
        checked={done}
        onChange={() => onToggle(course.code)}
      />
      <span className="gened-course-code">{course.code}</span>
      <span className="gened-course-name">{course.title || course.name}</span>
      <span className="gened-course-cr">{course.credits} cr</span>
      {tags.length > 0 && (
        <span className="gened-tags">
          {tags.map((t) => <TagBadge key={t} tag={t} />)}
        </span>
      )}
    </label>
  );
}

function CategoryCard({ catCode, catData, completed, onToggle, defaultOpen, programName }) {
  const [open, setOpen] = useState(defaultOpen || false);
  const meta   = CAT_META[catCode] || { label: catCode, creditsRequired: 3 };
  const courses = catData?.courses || STATIC_FALLBACK[catCode] || [];
  const status  = getCatStatus(courses, completed, meta.creditsRequired);

  const doneCr    = courses.filter((c) => completed[c.code]).reduce((s, c) => s + creditNum(c.credits), 0);
  const doneCount = courses.filter((c) => completed[c.code]).length;

  const overlapCr = catData?.overlap_credits || 0;
  const totalInDb = catData?.course_count || 0;

  return (
    <div className={`gened-cat-card gened-cat-card--${status}`}>
      <button
        className="gened-cat-header"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className={`gened-cat-code gened-cat-code--${status}`}>{catCode}</span>
        <span className="gened-cat-label">{meta.label}</span>
        <span className="gened-cat-meta">
          <span className="gened-cat-credits">{doneCr}/{meta.creditsRequired} cr</span>
          <span className="gened-cat-count">{doneCount}/{courses.length}</span>
          <span className={`gened-cat-chevron${open ? " gened-cat-chevron--open" : ""}`}>›</span>
        </span>
      </button>

      {open && (
        <div className="gened-cat-body">
          {overlapCr > 0 && (
            <div className="gened-cat-note">
              <strong>{overlapCr} credits</strong> of {catCode} are already covered by your{" "}
              {programName || "major"} requirements — no extra course needed for those.
            </div>
          )}
          {totalInDb > courses.length && (
            <p className="gened-cat-desc">
              Showing {courses.length} of {totalInDb} {catCode} courses in the Penn State catalog.
            </p>
          )}
          <div className="gened-course-list">
            {courses.length === 0 ? (
              <p className="gened-empty" style={{ padding: "8px 0" }}>
                No {catCode} courses found in database. Check the{" "}
                <a href="https://bulletins.psu.edu/undergraduate/general-education/" target="_blank" rel="noreferrer">
                  bulletin
                </a>{" "}
                for options.
              </p>
            ) : (
              courses.map((c) => (
                <CourseRow
                  key={c.code}
                  course={c}
                  done={!!completed[c.code]}
                  onToggle={onToggle}
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────────────────── */

export default function GenEdExplorer({ userId, selectedMajor }) {
  const storageKey = `ace_gened_${userId}`;

  const [completed, setCompleted] = useState(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : {};
    } catch { return {}; }
  });

  const [genEdData, setGenEdData]   = useState(null);   // API response
  const [loading, setLoading]       = useState(false);
  const [filter, setFilter]         = useState("all");  // "all" | "remaining" | "major-dips"

  // Persist checked courses
  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(completed)); }
    catch { /* quota */ }
  }, [completed, storageKey]);

  // Fetch from API when major or userId changes
  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (selectedMajor) params.set("major", selectedMajor);
    else if (userId)   params.set("user_id", userId);

    fetch(`${API}/gen-ed?${params}`)
      .then((r) => r.json())
      .then((data) => { setGenEdData(data); setLoading(false); })
      .catch(() => { setGenEdData(null); setLoading(false); });
  }, [selectedMajor, userId]);

  const toggleCourse = useCallback((code) => {
    setCompleted((prev) => ({ ...prev, [code]: !prev[code] }));
  }, []);

  // Build category map from API data
  const catMap = {};
  if (genEdData?.categories) {
    for (const cat of genEdData.categories) {
      catMap[cat.code] = cat;
    }
  }

  const catCodes = Object.keys(CAT_META);

  const satisfiedCount = catCodes.filter((code) => {
    const meta    = CAT_META[code];
    const courses = catMap[code]?.courses || STATIC_FALLBACK[code] || [];
    return getCatStatus(courses, completed, meta.creditsRequired) === "satisfied";
  }).length;

  const progressPct = Math.round((satisfiedCount / catCodes.length) * 100);

  const visibleCodes = catCodes.filter((code) => {
    if (filter === "all") return true;
    const meta    = CAT_META[code];
    const courses = catMap[code]?.courses || STATIC_FALLBACK[code] || [];
    if (filter === "remaining")
      return getCatStatus(courses, completed, meta.creditsRequired) !== "satisfied";
    if (filter === "major-dips")
      return (catMap[code]?.courses || []).some((c) => c.tags?.includes("major-req"));
    return true;
  });

  const programName = genEdData?.program?.name || selectedMajor || null;

  // Build smart picks: major-req courses from double-dips, else universal
  const smartPicks = [];
  if (genEdData?.categories) {
    for (const cat of genEdData.categories) {
      for (const c of (cat.courses || [])) {
        if (c.tags?.includes("major-req") && smartPicks.length < 5) {
          smartPicks.push({ code: c.code, cat: cat.code, name: c.title,
            reason: `Required by your major and satisfies ${cat.code} (${cat.label}).` });
        }
      }
    }
  }
  const displayPicks = smartPicks.length > 0 ? smartPicks : UNIVERSAL_SMART_PICKS;

  return (
    <div className="gened-page">
      {/* Header */}
      <div className="gened-header">
        <div>
          <h1 className="gened-title">Gen Ed Explorer</h1>
          <p className="gened-subtitle">
            Penn State{programName ? ` · ${programName}` : ""} · 2024–2025
          </p>
        </div>
        {loading && <span style={{ fontSize: 12, color: "var(--gray-400)" }}>Loading…</span>}
      </div>

      {/* Overall Progress */}
      <div className="gened-overall">
        <span className="gened-overall-label">
          {satisfiedCount} of {catCodes.length} categories satisfied
        </span>
        <div className="gened-overall-bar" aria-label={`${progressPct}% complete`}>
          <div className="gened-overall-fill" style={{ width: `${progressPct}%` }} />
        </div>
        <span className="gened-overall-pct">{progressPct}%</span>
      </div>

      {/* Overlap summary */}
      {genEdData?.program?.gen_ed_overlap_note && (
        <div className="gened-overlap-note">
          {genEdData.program.gen_ed_overlap_note}
        </div>
      )}

      {/* Filter Tabs */}
      <div className="gened-filter-tabs" role="tablist">
        {[
          { id: "all",        label: "All" },
          { id: "remaining",  label: "Remaining" },
          { id: "major-dips", label: "Major Double-Dips" },
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
        {visibleCodes.length === 0 ? (
          <p className="gened-empty">All categories satisfied! Great work.</p>
        ) : (
          visibleCodes.map((code) => (
            <CategoryCard
              key={code}
              catCode={code}
              catData={catMap[code] || null}
              completed={completed}
              onToggle={toggleCourse}
              defaultOpen={false}
              programName={programName}
            />
          ))
        )}
      </div>

      {/* Smart Picks */}
      <div className="gened-smart-picks">
        <h2 className="gened-smart-title">
          {smartPicks.length > 0 ? "Major Double-Dip Picks" : "Smart Picks"}
        </h2>
        <ul className="gened-smart-list">
          {displayPicks.map((pick) => (
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
        verify with your official degree audit on LionPATH or your academic advisor.
      </p>
    </div>
  );
}
