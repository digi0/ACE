import { useState, useEffect } from 'react';
import { apiFetch } from './api.js';

/**
 * Suggested Academic Plan — renders the college's recommended semester-by-
 * semester course sequence for the student's selected major, pulled live from
 * programs.json via /suggested-plan. Works for any of the 749 programs.
 *
 * Styling is inline + CSS variables so it themes (light/dark) automatically and
 * touches no shared stylesheet.
 */
export default function SuggestedPlan({ selectedMajor }) {
  const [plans, setPlans] = useState([]);
  const [programName, setProgramName] = useState('');
  const [totalCredits, setTotalCredits] = useState(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!selectedMajor) {
      setPlans([]);
      setProgramName('');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setActiveIdx(0);
    apiFetch(`/suggested-plan?major=${encodeURIComponent(selectedMajor)}`)
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        setPlans(Array.isArray(data?.plans) ? data.plans : []);
        setProgramName(data?.program_name || selectedMajor);
        setTotalCredits(data?.total_credits ?? null);
      })
      .catch(() => {
        if (!cancelled) { setPlans([]); setProgramName(selectedMajor); }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedMajor]);

  const wrap = (body) => (
    <div className="prereq-page">
      <div className="prereq-header">
        <h2 className="prereq-title">Suggested Academic Plan</h2>
        <p className="prereq-subtitle">
          {programName || selectedMajor || 'Penn State'}
          {totalCredits ? ` · ${totalCredits} credits` : ''}
        </p>
      </div>
      {body}
    </div>
  );

  if (!selectedMajor) {
    return wrap(
      <div className="audit-banner">
        Select your major to see its college-recommended semester-by-semester plan.
      </div>
    );
  }
  if (loading) return wrap(<div className="audit-banner">Loading your suggested plan…</div>);
  if (plans.length === 0) {
    return wrap(
      <div className="audit-banner">
        We don't have a published suggested plan for <strong>{programName || selectedMajor}</strong> yet.
        Check your required courses on the <strong>Dashboard</strong> or ask ACE in chat.
      </div>
    );
  }

  const plan = plans[Math.min(activeIdx, plans.length - 1)];

  const card = {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg, 12px)',
    boxShadow: 'var(--shadow-sm)',
    padding: '0.9rem 1rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  };

  return wrap(
    <>
      {/* Plan-variant selector (campus options) */}
      {plans.length > 1 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.9rem' }}>
          {plans.map((p, i) => (
            <button
              key={p.label || i}
              onClick={() => setActiveIdx(i)}
              style={{
                fontSize: 'var(--text-xs, 0.75rem)',
                padding: '0.35rem 0.7rem',
                borderRadius: 'var(--radius-full, 999px)',
                cursor: 'pointer',
                border: '1px solid var(--border)',
                background: i === activeIdx ? 'var(--accent)' : 'var(--bg-card)',
                color: i === activeIdx ? '#fff' : 'var(--text-secondary, var(--text))',
                fontWeight: i === activeIdx ? 600 : 500,
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))',
          gap: '0.85rem',
          alignItems: 'start',
        }}
      >
        {plan.semesters.map((sem) => (
          <div key={sem.key} style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ fontWeight: 700, color: 'var(--text)', fontSize: 'var(--text-sm, 0.85rem)' }}>
                {sem.label}
              </span>
              {sem.total_credits ? (
                <span style={{ fontSize: 'var(--text-xs, 0.72rem)', color: 'var(--text-muted)' }}>
                  {sem.total_credits} cr
                </span>
              ) : null}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              {sem.courses.map((c, ci) => (
                <div
                  key={ci}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: '0.5rem',
                    fontSize: 'var(--text-xs, 0.78rem)',
                    color: 'var(--text-secondary, var(--text))',
                    paddingBottom: '0.3rem',
                    borderBottom: ci < sem.courses.length - 1 ? '1px solid var(--border-subtle, var(--border))' : 'none',
                  }}
                >
                  <span>{c.description}</span>
                  <span style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {c.credits != null ? `${c.credits}` : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="prereq-disclaimer">
        This is the college's recommended sequence. Your actual plan may vary with placement,
        transfer credit, and advisor guidance — always confirm in LionPATH and with your adviser.
      </p>
    </>
  );
}
