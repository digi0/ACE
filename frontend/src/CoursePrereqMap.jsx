import { useState, useEffect, useCallback } from 'react';

const COURSES = [
  // Tier 1
  { id: 'CMPSC121', code: 'CMPSC 121/131', name: 'Intro to Programming', tier: 1, prereqs: [] },
  { id: 'MATH140',  code: 'MATH 140',      name: 'Calculus I',            tier: 1, prereqs: [] },
  { id: 'ENGL15',   code: 'ENGL 15',       name: 'Rhetoric & Composition', tier: 1, prereqs: [] },
  { id: 'CAS100',   code: 'CAS 100',       name: 'Effective Speech',       tier: 1, prereqs: [] },

  // Tier 2
  { id: 'CMPSC122', code: 'CMPSC 122/132', name: 'Intermediate Programming', tier: 2, prereqs: ['CMPSC121'] },
  { id: 'MATH141',  code: 'MATH 141',      name: 'Calculus II',              tier: 2, prereqs: ['MATH140'] },
  { id: 'PHYS211',  code: 'PHYS 211',      name: 'General Physics I',        tier: 2, prereqs: ['MATH140'] },
  { id: 'ENGL202C', code: 'ENGL 202C',     name: 'Technical Writing',        tier: 2, prereqs: ['ENGL15'] },

  // Tier 3
  { id: 'CMPSC221', code: 'CMPSC 221',  name: 'OOP',              tier: 3, prereqs: ['CMPSC122'] },
  { id: 'CMPSC360', code: 'CMPSC 360',  name: 'Discrete Math',    tier: 3, prereqs: ['CMPSC122', 'MATH141'] },
  { id: 'MATH220',  code: 'MATH 220',   name: 'Matrices',         tier: 3, prereqs: ['MATH141'] },
  { id: 'PHYS212',  code: 'PHYS 212',   name: 'General Physics II', tier: 3, prereqs: ['PHYS211'] },
  { id: 'STAT318',  code: 'STAT 318',   name: 'Statistics',       tier: 3, prereqs: ['MATH141'] },

  // Tier 4
  { id: 'CMPSC311', code: 'CMPSC 311', name: 'Systems Programming',   tier: 4, prereqs: ['CMPSC221'] },
  { id: 'CMPSC312', code: 'CMPSC 312', name: 'Computer Organization', tier: 4, prereqs: ['CMPSC221'] },
  { id: 'CMPSC462', code: 'CMPSC 462', name: 'Data Structures',       tier: 4, prereqs: ['CMPSC221', 'CMPSC360'] },

  // Tier 5
  { id: 'CMPSC431W', code: 'CMPSC 431W', name: 'Database Mgmt',    tier: 5, prereqs: ['CMPSC311'] },
  { id: 'CMPSC461',  code: 'CMPSC 461',  name: 'PL Concepts',      tier: 5, prereqs: ['CMPSC311', 'CMPSC462'] },
  { id: 'CMPSC463',  code: 'CMPSC 463',  name: 'Algorithm Design', tier: 5, prereqs: ['CMPSC462'] },
  { id: 'CMPSC473',  code: 'CMPSC 473',  name: 'Operating Systems', tier: 5, prereqs: ['CMPSC311', 'CMPSC312'] },

  // Tier 6
  { id: 'CMPSC441',  code: 'CMPSC 441',  name: 'AI',            tier: 6, prereqs: ['CMPSC463', 'STAT318'] },
  {
    id: 'CMPSC483W',
    code: 'CMPSC 483W',
    name: 'Senior Design',
    tier: 6,
    // OR logic: any one of these satisfies the prereq
    prereqs: ['CMPSC431W', 'CMPSC461', 'CMPSC473'],
    prereqMode: 'any',
  },
];

const TIERS = [1, 2, 3, 4, 5, 6];
const TIER_LABELS = {
  1: 'Year 1',
  2: 'Year 1–2',
  3: 'Year 2',
  4: 'Year 2–3',
  5: 'Year 3–4',
  6: 'Year 4',
};

function isCourseAvailable(course, completed) {
  if (course.prereqs.length === 0) return true;
  if (course.prereqMode === 'any') {
    return course.prereqs.some((pid) => completed.has(pid));
  }
  return course.prereqs.every((pid) => completed.has(pid));
}

export default function CoursePrereqMap({ userId }) {
  const storageKey = `ace_prereq_${userId}`;

  const [completed, setCompleted] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  // Re-load from localStorage whenever userId changes
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      setCompleted(saved ? new Set(JSON.parse(saved)) : new Set());
    } catch {
      setCompleted(new Set());
    }
  }, [storageKey]);

  // Persist to localStorage on every change
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify([...completed]));
    } catch {
      // storage quota exceeded or unavailable — silently ignore
    }
  }, [completed, storageKey]);

  const toggleCourse = useCallback(
    (course) => {
      const isCompleted = completed.has(course.id);
      const isAvailable = isCourseAvailable(course, completed);

      // Only allow toggle if the course is available or already completed
      if (!isCompleted && !isAvailable) return;

      setCompleted((prev) => {
        const next = new Set(prev);
        if (next.has(course.id)) {
          next.delete(course.id);
        } else {
          next.add(course.id);
        }
        return next;
      });
    },
    [completed],
  );

  function getCourseStatus(course) {
    if (completed.has(course.id)) return 'completed';
    if (isCourseAvailable(course, completed)) return 'available';
    return 'locked';
  }

  return (
    <div className="prereq-page">
      <div className="prereq-header">
        <h2 className="prereq-title">Course Prerequisite Map</h2>
        <p className="prereq-subtitle">CMPSC B.S. &middot; Penn State &middot; 2024–2025</p>
      </div>

      <div className="prereq-legend">
        <span className="prereq-legend-item">
          <span className="prereq-legend-dot prereq-legend-dot--completed" />
          Completed
        </span>
        <span className="prereq-legend-item">
          <span className="prereq-legend-dot prereq-legend-dot--available" />
          Available
        </span>
        <span className="prereq-legend-item">
          <span className="prereq-legend-dot prereq-legend-dot--locked" />
          Locked
        </span>
      </div>

      <div className="prereq-scroll">
        <div className="prereq-map">
          {TIERS.map((tier) => {
            const tierCourses = COURSES.filter((c) => c.tier === tier);
            return (
              <div className="prereq-tier" key={tier}>
                <div className="prereq-tier-label">{TIER_LABELS[tier]}</div>
                {tierCourses.map((course) => {
                  const status = getCourseStatus(course);
                  const isInteractable = status === 'available' || status === 'completed';
                  return (
                    <div
                      key={course.id}
                      className={`prereq-course prereq-course--${status}`}
                      onClick={() => toggleCourse(course)}
                      role="button"
                      tabIndex={isInteractable ? 0 : -1}
                      aria-pressed={status === 'completed'}
                      aria-disabled={!isInteractable}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          toggleCourse(course);
                        }
                      }}
                    >
                      <span className="prereq-course-code">{course.code}</span>
                      <span className="prereq-course-name">{course.name}</span>
                      {status === 'completed' && (
                        <span className="prereq-course-check" aria-hidden="true">
                          ✓
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      <p className="prereq-disclaimer">
        Click an available or completed course to toggle its status. Locked courses require their
        prerequisites to be completed first. CMPSC 483W requires any one of: 431W, 461, or 473.
      </p>
    </div>
  );
}
