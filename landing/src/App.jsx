import {useEffect, useRef, useState} from 'react';

const API = import.meta.env.VITE_API_URL || 'https://web-production-7ffe.up.railway.app';
const APP_URL = import.meta.env.VITE_APP_URL || 'https://app.acecollege.app';

/* ── Waitlist form ──────────────────────────────────────────────────────────── */
function WaitlistForm({compact = false}) {
  const [email, setEmail] = useState('');
  const [state, setState] = useState('idle'); // idle | sending | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim() || state === 'sending') return;
    setState('sending');
    setError('');
    try {
      const referral = new URLSearchParams(window.location.search).get('ref') || 'landing';
      const res = await fetch(`${API}/waitlist`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email: email.trim(), referral}),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Something went wrong.');
      setResult(data);
      setState('done');
    } catch (err) {
      setError(err.message || 'Something went wrong — try again.');
      setState('error');
    }
  };

  if (state === 'done' && result) {
    return (
      <div className="wl-done" role="status">
        <span className="wl-done-check">✓</span>
        {result.already ? (
          <span>
            You're already on the list — <strong>#{result.position}</strong>. We'll be in touch soon.
          </span>
        ) : (
          <span>
            You're in! You're <strong>#{result.position}</strong> on the waitlist.
            {result.position <= 100 ? ' That puts you in the early-access group. 🎉' : " We'll email you when your spot opens."}
          </span>
        )}
      </div>
    );
  }

  return (
    <form className={`wl-form${compact ? ' wl-form--compact' : ''}`} onSubmit={submit}>
      <input
        className="wl-input"
        type="email"
        required
        placeholder="you@psu.edu"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        aria-label="Email address"
      />
      <button className="wl-btn" type="submit" disabled={state === 'sending'}>
        {state === 'sending' ? 'Joining…' : 'Join the waitlist'}
      </button>
      {state === 'error' && <p className="wl-error">{error}</p>}
    </form>
  );
}

/* ── Page ───────────────────────────────────────────────────────────────────── */
const FEATURES = [
  {
    icon: '💬',
    title: 'Ask anything',
    desc: 'Course requirements, policies, deadlines, "what should I take next semester?" — real answers in seconds, grounded in your college\'s actual policies and catalog. Not next week. Now.',
  },
  {
    icon: '📊',
    title: 'Know where you stand',
    desc: 'Upload your What-If Report or Degree Audit and ACE turns it into a live dashboard — credits earned, requirements left, and exactly what changes if you switch majors.',
  },
  {
    icon: '🗺️',
    title: 'Plan your whole degree',
    desc: 'Prerequisite maps, gen-ed tracking with double-dip finder, and your college\'s suggested semester-by-semester plan — for any of 749 majors, not just a few.',
  },
  {
    icon: '🧭',
    title: 'All of campus, one place',
    desc: 'Tutoring, counseling, career services, advising offices, key dates — every campus resource you didn\'t know existed, surfaced when you actually need it.',
  },
];

const STEPS = [
  {n: '1', title: 'Pick your major', desc: 'ACE supports all 749 Penn State programs — your answers are tailored to yours from the first question.'},
  {n: '2', title: 'Upload your audit', desc: 'Optional, but powerful: drop in your What-If or Degree Audit PDF and everything becomes personal.'},
  {n: '3', title: 'Just ask', desc: 'Plan semesters, check prereqs, track gen eds, find deadlines — like texting an advisor who always has time.'},
];

export default function App() {
  const videoRef = useRef(null);

  // Pause the film when it scrolls out of view
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const obs = new IntersectionObserver(
      ([e]) => (e.isIntersecting ? v.play().catch(() => {}) : v.pause()),
      {threshold: 0.25},
    );
    obs.observe(v);
    return () => obs.disconnect();
  }, []);

  return (
    <div className="page">
      {/* Nav */}
      <nav className="nav">
        <div className="nav-brand">
          <span className="nav-logo" aria-hidden>🎓</span>
          <span className="nav-name">ACE</span>
          <span className="nav-sub">Academic Counseling Engine</span>
        </div>
        <a className="nav-cta" href={APP_URL}>
          Open ACE →
        </a>
      </nav>

      {/* Hero */}
      <header className="hero">
        <div className="hero-badge">🚀 Launching at Penn State · first 100 students get early access</div>
        <h1 className="hero-title">
          Never feel <span className="accent">lost</span> in college again.
        </h1>
        <p className="hero-sub">
          ACE is the AI academic counselor that knows <em>your</em> major — real answers about courses,
          prereqs, gen eds, and deadlines. In seconds, not in six days.
        </p>
        <WaitlistForm />
        <p className="hero-note">Free for students. No spam — one email when your access opens.</p>

        {/* The launch film */}
        <div className="film-wrap">
          <video
            ref={videoRef}
            className="film"
            src="/ace-launch.mp4"
            autoPlay
            muted
            loop
            playsInline
            controls
          />
        </div>
      </header>

      {/* Problem strip */}
      <section className="strip">
        <p>
          It's 2 a.m. Registration opens tomorrow. Your advisor's next slot is <strong>in six days</strong>.
          <br />
          <span className="strip-accent">College doesn't come with a manual — so we built one.</span>
        </p>
      </section>

      {/* Features */}
      <section className="section" id="features">
        <h2 className="section-title">What ACE does</h2>
        <div className="features">
          {FEATURES.map((f) => (
            <div className="feature" key={f.title}>
              <div className="feature-icon" aria-hidden>{f.icon}</div>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="section section--alt" id="how">
        <h2 className="section-title">How it works</h2>
        <div className="steps">
          {STEPS.map((s) => (
            <div className="step" key={s.n}>
              <div className="step-n">{s.n}</div>
              <h3 className="step-title">{s.title}</h3>
              <p className="step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="section cta">
        <h2 className="cta-title">Be one of the first 100.</h2>
        <p className="cta-sub">
          We're opening ACE to a small early-access group before the fall semester. Grab a spot.
        </p>
        <WaitlistForm compact />
      </section>

      {/* Footer */}
      <footer className="footer">
        <p>
          ACE is an independent student-built planning tool and is <strong>not affiliated with or endorsed by
          Penn State University</strong>. Always confirm academic decisions with your academic adviser.
        </p>
        <p className="footer-links">
          <a href={APP_URL}>Open ACE</a> · <a href="mailto:mrmalpani25@gmail.com">Contact</a>
        </p>
      </footer>
    </div>
  );
}
