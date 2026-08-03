import { useState, useEffect, useCallback, useMemo } from 'react';
import { apiFetch } from './api.js';

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
  if (!course.prereqs || course.prereqs.length === 0) return true;
  if (course.prereqMode === 'any') {
    return course.prereqs.some((pid) => completed.has(pid));
  }
  return course.prereqs.every((pid) => completed.has(pid));
}

export default function CoursePrereqMap({ userId, progress, selectedMajor }) {
  const storageKey = `ace_prereq_${userId}`;

  // ── Dynamic, per-major course graph (fetched from the backend) ──
  const [courses, setCourses] = useState([]);
  const [programName, setProgramName] = useState('');
  const [tierLabels, setTierLabels] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!selectedMajor) {
      setCourses([]);
      setProgramName('');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    apiFetch(`/prereq-map?major=${encodeURIComponent(selectedMajor)}`)
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        setCourses(Array.isArray(data?.courses) ? data.courses : []);
        setProgramName(data?.program_name || selectedMajor);
        setTierLabels(data?.tier_labels || {});
      })
      .catch(() => {
        if (!cancelled) { setCourses([]); setProgramName(selectedMajor); setTierLabels({}); }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedMajor]);

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
    for (const course of courses) {
      const codes = expandCodes(course.code);
      if (codes.some((c) => comp.has(c))) cIds.add(course.id);
      else if (codes.some((c) => ip.has(c))) ipIds.add(course.id);
    }
    return { auditCompletedIds: cIds, auditInProgressIds: ipIds, hasAudit: comp.size > 0 || ip.size > 0 };
  }, [progress, courses]);

  // Manual checks ∪ audit-completed — drives availability so audit-completed
  // prereqs unlock the courses they gate.
  const effectiveCompleted = useMemo(
    () => new Set([...completed, ...auditCompletedIds]),
    [completed, auditCompletedIds]
  );

  const tiers = useMemo(
    () => [...new Set(courses.map((c) => c.tier))].sort((a, b) => a - b),
    [courses]
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

  // ── Empty / loading / no-major states ──
  if (!selectedMajor) {
    return (
      <div className="prereq-page">
        <div className="prereq-header">
          <h2 className="prereq-title">Course Prerequisite Map</h2>
          <p className="prereq-subtitle">Penn State</p>
        </div>
        <div className="audit-banner audit-banner--note">
          Select your major to see its course prerequisite map. You can set it from the
          major prompt, or just ask ACE in chat.
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="prereq-page">
        <div className="prereq-header">
          <h2 className="prereq-title">Course Prerequisite Map</h2>
          <p className="prereq-subtitle">{programName || selectedMajor}</p>
        </div>
        <div className="audit-banner audit-banner--note">Building your prerequisite map…</div>
      </div>
    );
  }

  if (courses.length === 0) {
    return (
      <div className="prereq-page">
        <div className="prereq-header">
          <h2 className="prereq-title">Course Prerequisite Map</h2>
          <p className="prereq-subtitle">{programName || selectedMajor}</p>
        </div>
        <div className="audit-banner audit-banner--note">
          We don't have a course-level prerequisite map for <strong>{programName || selectedMajor}</strong> yet.
          See your required courses on the <strong>Dashboard</strong> or ask ACE in chat.
        </div>
      </div>
    );
  }

  return (
    <div className="prereq-page">
      <div className="prereq-header">
        <h2 className="prereq-title">Course Prerequisite Map</h2>
        <p className="prereq-subtitle">{programName} &middot; Penn State</p>
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
          {tiers.map((tier) => {
            const tierCourses = courses.filter((c) => c.tier === tier);
            return (
              <div className="prereq-tier" key={tier}>
                <div className="prereq-tier-label">{tierLabels[tier] || `Level ${tier}`}</div>
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
        prerequisites first. Columns follow your major's suggested academic plan where available
        (otherwise prerequisite order); arrows are prerequisites. Always confirm with LionPATH.
      </p>
    </div>
  );
}
