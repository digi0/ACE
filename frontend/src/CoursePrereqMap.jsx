import { useState, useEffect, useCallback, useMemo } from 'react';

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

// Normalize a course code for matching against the audit: "ENGL 015" -> "ENGL 15"
function normCode(code) {
  const m = String(code).toUpperCase().match(/([A-Z]{2,6})\s*0*(\d{1,3}[A-Z]?)/);
  return m ? `${m[1]} ${m[2]}` : String(code).toUpperCase().trim();
}

// Expand a node code with slash-alternatives: "CMPSC 121/131" -> 2 codes.
function expandCodes(raw) {
  const parts = String(raw).split('/').map((s) => s.trim()).filter(Boolean);
  if (!parts.length) return [];
  const first = normCode(parts[0]);
  const fm = first.match(/^([A-Z]{2,6})\s+(\d{1,3})([A-Z]?)$/);
  if (!fm) return [first];
  const [, subj, baseNum] = fm;
  const out = [first];
  for (const p of parts.slice(1)) {
    const t = p.toUpperCase().trim();
    if (/^\d/.test(t)) out.push(normCode(`${subj} ${t}`));
    else if (/^[A-Z]$/.test(t)) out.push(`${subj} ${baseNum}${t}`);
    else out.push(normCode(t));
  }
  return out;
}

function isCourseAvailable(course, completed) {
  if (course.prereqs.length === 0) return true;
  if (course.prereqMode === 'any') {
    return course.prereqs.some((pid) => completed.has(pid));
  }
  return course.prereqs.every((pid) => completed.has(pid));
}

export default function CoursePrereqMap({ userId, progress }) {
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

  // Map the audit's completed / in-progress course codes onto node ids.
  const { auditCompletedIds, auditInProgressIds, hasAudit } = useMemo(() => {
    const comp = new Set((progress?.completed_courses || []).map(normCode));
    const ip = new Set((progress?.in_progress_courses || []).map(normCode));
    const cIds = new Set();
    const ipIds = new Set();
    for (const course of COURSES) {
      const codes = expandCodes(course.code);
      if (codes.some((c) => comp.has(c))) cIds.add(course.id);
      else if (codes.some((c) => ip.has(c))) ipIds.add(course.id);
    }
    return { auditCompletedIds: cIds, auditInProgressIds: ipIds, hasAudit: comp.size > 0 || ip.size > 0 };
  }, [progress]);

  // Manual checks ∪ audit-completed — drives availability so audit-completed
  // prereqs unlock the courses they gate.
  const effectiveCompleted = useMemo(
    () => new Set([...completed, ...auditCompletedIds]),
    [completed, auditCompletedIds]
  );

  const toggleCourse = useCallback(
    (course) => {
      const isComp = effectiveCompleted.has(course.id);
      const isAvail = isCourseAvailable(course, effectiveCompleted);
      // Only allow toggle if the course is available or already completed
      if (!isComp && !isAvail) return;

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
    [effectiveCompleted],
  );

  function getCourseStatus(course) {
    if (effectiveCompleted.has(course.id)) return 'completed';
    if (auditInProgressIds.has(course.id)) return 'in_progress';
    if (isCourseAvailable(course, effectiveCompleted)) return 'available';
    return 'locked';
  }

  return (
    <div className="prereq-page">
      <div className="prereq-header">
        <h2 className="prereq-title">Course Prerequisite Map</h2>
        <p className="prereq-subtitle">CMPSC B.S. &middot; Penn State &middot; 2024–2025</p>
      </div>

      {hasAudit && (
        <div className="audit-banner">
          <span className="audit-banner-check">✓</span>
          {auditCompletedIds.size} course{auditCompletedIds.size === 1 ? '' : 's'} marked complete from your audit
          {auditInProgressIds.size > 0 ? ` · ${auditInProgressIds.size} in progress` : ''}.
          <span className="audit-banner-hint">Prereqs unlock automatically.</span>
        </div>
      )}

      <div className="prereq-legend">
        <span className="prereq-legend-item">
          <span className="prereq-legend-dot prereq-legend-dot--completed" />
          Completed
        </span>
        <span className="prereq-legend-item">
          <span className="prereq-legend-dot prereq-legend-dot--in_progress" />
          In progress
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
                  const isInteractable = status !== 'locked';
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
                      {status === 'in_progress' && (
                        <span className="prereq-course-ip" aria-hidden="true">
                          IP
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
