import {useEffect, useRef, useState} from 'react';

const API = import.meta.env.VITE_API_URL || 'https://web-production-7ffe.up.railway.app';
const APP_URL = import.meta.env.VITE_APP_URL || 'https://app.acecollege.app';

/* ── tiny scroll-reveal hook: adds .in when the element enters the viewport ── */
function useReveal() {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => e.isIntersecting && (el.classList.add('in'), obs.disconnect()),
      {threshold: 0.25},
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

/* ── shared SVG bits ── */
const CapIcon = ({stroke = '#fff'}) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
    <path d="M6 12v5c3 3 9 3 12 0v-5" />
  </svg>
);

/* hand-drawn marker stroke (under "chaos") */
const MarkerStroke = () => (
  <svg viewBox="0 0 200 20" preserveAspectRatio="none" aria-hidden>
    <path
      d="M4 13 C40 7, 75 16, 108 11 S 170 6, 196 12"
      fill="none" stroke="#dc2626" strokeWidth="7" strokeLinecap="round" opacity="0.85"
    />
  </svg>
);

/* hand-drawn circle (around "first 100") */
const MarkerCircle = () => (
  <svg viewBox="0 0 120 44" preserveAspectRatio="none" aria-hidden>
    <path
      d="M14 24 C12 10, 48 4, 72 6 C100 8, 116 16, 112 26 C108 38, 70 42, 42 39 C20 37, 8 32, 14 22"
      fill="none" stroke="#2563eb" strokeWidth="3" strokeLinecap="round" opacity="0.9"
    />
  </svg>
);

/* ── Waitlist form ── */
function WaitlistForm() {
  const [email, setEmail] = useState('');
  const [state, setState] = useState('idle');
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

  return (
    <div className="wl-zone">
      {state === 'done' && result ? (
        <div className="wl-done" role="status">
          <span className="wl-done-check">✓</span>
          {result.already ? (
            <span>Already on the list — you're <strong>#{result.position}</strong>. We'll be in touch.</span>
          ) : (
            <span>
              You're in — <strong>#{result.position}</strong> on the list.
              {result.position <= 100 ? ' Early-access group. 🎉' : " We'll email you when your spot opens."}
            </span>
          )}
        </div>
      ) : (
        <form className="wl-form" onSubmit={submit}>
          <input
            className="wl-input" type="email" required placeholder="you@psu.edu"
            value={email} onChange={(e) => setEmail(e.target.value)} aria-label="Email address"
          />
          <button className="wl-btn" type="submit" disabled={state === 'sending'}>
            {state === 'sending' ? 'Joining…' : 'Join the waitlist'}
          </button>
          {state === 'error' && <p className="wl-error">{error}</p>}
        </form>
      )}
      <p className="wl-note">
        Free for students. No spam.
        <span className="wl-100">
          <MarkerCircle />
          first 100 get early access
        </span>
      </p>
    </div>
  );
}

/* ── Hero sticky-note chaos ── */
const NOTES = [
  {cls: 'note-amber', style: {top: '6%', right: '4%', '--rot': '3deg', animationDelay: '-1s'},
   body: <><span>NEXT ADVISOR SLOT</span><b>— in 6 days</b></>},
  {cls: 'note-red', style: {top: '38%', left: '2%', '--rot': '-4deg', animationDelay: '-3s'}, body: 'prereq not met??'},
  {cls: 'note-ink', style: {top: '56%', right: '12%', '--rot': '2deg', animationDelay: '-5s'}, body: 'what even is a GS credit'},
  {cls: 'note-blue', style: {top: '20%', left: '22%', '--rot': '-2deg', animationDelay: '-2s'}, body: 'waitlisted. again.'},
  {cls: 'note-ink', style: {bottom: '4%', left: '14%', '--rot': '-3deg', animationDelay: '-4s'}, body: 'can I still graduate on time?'},
];

/* ── Live chat demo (film scene 4, interactive) ── */
const DEMO_Q = "Can I still graduate by Spring '27?";
const DEMO_CHIPS = ['CMPSC 311 → Fall', 'MATH 220 → Fall', 'GEN ED ×2 → Spring', '15 cr / sem · balanced ✓'];

function ChatDemo() {
  const ref = useRef(null);
  const [typed, setTyped] = useState('');
  const [phase, setPhase] = useState('idle'); // idle → typing → answer → chips → stamp

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        setPhase('typing');
        obs.disconnect();
      }
    }, {threshold: 0.4});
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (phase !== 'typing') return;
    let i = 0;
    const iv = setInterval(() => {
      i += 1;
      setTyped(DEMO_Q.slice(0, i));
      if (i >= DEMO_Q.length) {
        clearInterval(iv);
        setTimeout(() => setPhase('answer'), 450);
      }
    }, 38);
    return () => clearInterval(iv);
  }, [phase]);

  useEffect(() => {
    if (phase === 'answer') {
      const t = setTimeout(() => setPhase('chips'), 600);
      return () => clearTimeout(t);
    }
    if (phase === 'chips') {
      const t = setTimeout(() => setPhase('stamp'), DEMO_CHIPS.length * 160 + 300);
      return () => clearTimeout(t);
    }
  }, [phase]);

  const answered = phase === 'answer' || phase === 'chips' || phase === 'stamp';

  return (
    <div className="demo-wrap" ref={ref}>
      <div className="demo">
        <div className="demo-bar">
          <span className="demo-dot" /><span className="demo-dot" /><span className="demo-dot" />
          <span className="demo-title">app.acecollege.app</span>
        </div>
        <div className="demo-body">
          <div className="bubble-q">
            {typed || ' '}
            {phase === 'typing' && <span className="caret" />}
          </div>
          <div className={`bubble-a${answered ? ' show' : ''}`}>
            <div className="bubble-a-head">
              <span className="bubble-a-mark"><CapIcon /></span>
              <span className="bubble-a-name">ACE</span>
            </div>
            <p className="bubble-a-text">
              <strong>Yes — here's your path.</strong> Based on your audit, you need 27 more credits.
              Here's a balanced two-semester plan that clears every remaining requirement:
            </p>
            <div className="plan-chips">
              {DEMO_CHIPS.map((c, i) => (
                <span
                  key={c}
                  className={`plan-chip${phase === 'chips' || phase === 'stamp' ? ' show' : ''}`}
                  style={{transitionDelay: `${i * 0.16}s`}}
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
          <span className={`demo-stamp${phase === 'stamp' ? ' show' : ''}`}>ANSWERED IN 4 SECONDS</span>
        </div>
      </div>
      <p className="demo-caption">↑ a real ACE answer — grounded in your college's actual requirements</p>
    </div>
  );
}

/* ── Bento vignettes ── */
function RingCell() {
  const ref = useReveal();
  return (
    <div className="cell cell-5 rv" ref={ref}>
      <span className="cell-kicker">Upload your audit</span>
      <h3 className="cell-title">Know exactly where you stand</h3>
      <p className="cell-desc">Drop in your What-If or Degree Audit PDF — ACE parses it into a live dashboard.</p>
      <div className="cell-art vg-ring">
        <svg className="ring" viewBox="0 0 110 110">
          <circle className="track" cx="55" cy="55" r="47" />
          <circle className="fill" cx="55" cy="55" r="47" />
          <text className="ring-label" x="55" y="63" textAnchor="middle">55%</text>
        </svg>
        <div className="vg-stats">
          <span className="vg-stat"><b>66.49</b> credits earned</span>
          <span className="vg-stat"><b>53.51</b> remaining</span>
          <span className="vg-badge">38 COURSES PARSED ✓</span>
        </div>
      </div>
    </div>
  );
}

function NodesCell() {
  const ref = useReveal();
  return (
    <div className="cell cell-7 rv rv-d1" ref={ref}>
      <span className="cell-kicker">Plan every semester</span>
      <h3 className="cell-title">Prereqs mapped, registration-ready</h3>
      <p className="cell-desc">
        See your whole degree as a map — what unlocks what, what to take when, for any of 749 majors.
      </p>
      <div className="cell-art">
        <svg className="vg-nodes" viewBox="0 0 520 120">
          <path className="edge edge-hl" d="M96 38 C150 38, 150 38, 204 38" fill="none" />
          <path className="edge" d="M96 38 C160 38, 160 86, 224 86" fill="none" />
          <path className="edge edge-hl" d="M300 38 C354 38, 354 38, 408 38" fill="none" />
          <rect className="nd nd-done" x="20" y="20" width="76" height="36" rx="9" />
          <text x="58" y="42" textAnchor="middle">CMPSC 221</text>
          <rect className="nd nd-done" x="204" y="20" width="96" height="36" rx="9" />
          <text x="252" y="42" textAnchor="middle">CMPSC 311 ✓</text>
          <rect className="nd" x="224" y="68" width="86" height="36" rx="9" />
          <text x="267" y="90" textAnchor="middle">MATH 220</text>
          <rect className="nd" x="408" y="20" width="92" height="36" rx="9" />
          <text x="454" y="42" textAnchor="middle">CMPSC 483W</text>
          <text className="vg-met" x="320" y="22">PREREQ MET ✓</text>
        </svg>
      </div>
    </div>
  );
}

function DipCell() {
  const ref = useReveal();
  return (
    <div className="cell cell-6 rv" ref={ref}>
      <span className="cell-kicker">Master your gen eds</span>
      <h3 className="cell-title">Double-dips, found for you</h3>
      <p className="cell-desc">ACE tracks every category and spots courses that count twice.</p>
      <div className="cell-art vg-dip">
        <div className="vg-dip-row"><span>GS · Social Sciences</span><span className="vg-check">✓</span></div>
        <div className="vg-dip-row"><span>GH · Humanities</span><span className="vg-check">✓</span></div>
        <div className="vg-dip-row"><span>GN · Natural Sciences</span><span>2 left</span></div>
        <span className="vg-dip-flag">ECON 102 covers GS + Major → saves 3 credits</span>
      </div>
    </div>
  );
}

function ResCell() {
  const ref = useReveal();
  const tiles = [
    ['Tutoring', 'M12 6v12M6 12h12'],
    ['Advising', 'M12 3a9 9 0 1 0 9 9M12 7v5l3 3'],
    ['Career', 'M4 7h16v13H4zM8 7V4h8v3'],
    ['Wellness', 'M12 21C7 16 3 12.5 3 8.8 3 6 5 4 7.5 4c1.7 0 3.4 1 4.5 2.6C13.1 5 14.8 4 16.5 4 19 4 21 6 21 8.8c0 3.7-4 7.2-9 12.2z'],
    ['Deadlines', 'M5 5h14v15H5zM5 9h14M9 3v4M15 3v4'],
    ['Aid', 'M12 2v20M17 6H9.5a3 3 0 0 0 0 6h5a3 3 0 0 1 0 6H6'],
  ];
  return (
    <div className="cell cell-6 rv rv-d1" ref={ref}>
      <span className="cell-kicker">All of campus, one place</span>
      <h3 className="cell-title">Every resource you didn't know existed</h3>
      <p className="cell-desc">Tutoring, advising offices, career services, key dates — surfaced when you need them.</p>
      <div className="cell-art vg-res">
        {tiles.map(([label, d]) => (
          <span className="vg-res-tile" key={label}>
            <svg viewBox="0 0 24 24" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d={d} />
            </svg>
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Mantras ── */
function Mantra({children, delay}) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        setTimeout(() => el.classList.add('in'), delay);
        obs.disconnect();
      }
    }, {threshold: 0.6});
    obs.observe(el);
    return () => obs.disconnect();
  }, [delay]);
  return <p className="mantra" ref={ref}>{children}<span className="dot">.</span></p>;
}

/* ── Page ── */
export default function App() {
  const videoRef = useRef(null);
  const heroRef = useReveal();
  const demoTitleRef = useReveal();
  const featTitleRef = useReveal();
  const filmTitleRef = useReveal();
  const ctaRef = useReveal();

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const obs = new IntersectionObserver(
      ([e]) => (e.isIntersecting ? v.play().catch(() => {}) : v.pause()),
      {threshold: 0.3},
    );
    obs.observe(v);
    return () => obs.disconnect();
  }, []);

  return (
    <div className="board">
      <nav className="nav">
        <a className="nav-brand" href="/">
          <span className="nav-mark"><CapIcon /></span>
          <span className="nav-name">ACE</span>
          <span className="nav-tag">your AI academic counselor</span>
        </a>
        <a className="nav-cta" href={APP_URL}>Open ACE →</a>
      </nav>

      {/* Hero */}
      <header className="hero rv in" ref={heroRef}>
        <div>
          <span className="hero-eyebrow">for every Penn State student —</span>
          <h1 className="hero-h1">
            Degree planning is{' '}
            <span className="chaos">
              chaos
              <MarkerStroke />
            </span>
            <span className="meet">Meet ACE.</span>
          </h1>
          <p className="hero-sub">
            The AI academic counselor that knows <strong>your major</strong> — real answers about
            courses, prereqs, gen eds and deadlines. <strong>In seconds, not in six days.</strong>
          </p>
          <WaitlistForm />
        </div>
        <div className="chaos-cluster" aria-hidden>
          {NOTES.map((n, i) => (
            <span key={i} className={`note ${n.cls}`} style={n.style}>{n.body}</span>
          ))}
        </div>
      </header>

      {/* Live demo */}
      <section className="sec" style={{paddingTop: 0}}>
        <div style={{textAlign: 'center', marginBottom: 36}} className="rv" ref={demoTitleRef}>
          <p className="sec-eyebrow">Ask anything</p>
          <h2 className="sec-title" style={{margin: '0 auto'}}>Watch it answer</h2>
        </div>
        <ChatDemo />
      </section>

      {/* Features bento */}
      <section className="sec" id="features">
        <div className="rv" ref={featTitleRef}>
          <p className="sec-eyebrow">What ACE does</p>
          <h2 className="sec-title">One tool for the whole maze</h2>
          <p className="sec-sub">
            Grounded in your college's actual policies, catalog, and your own audit — not vibes.
          </p>
        </div>
        <div className="bento">
          <RingCell />
          <NodesCell />
          <DipCell />
          <ResCell />
        </div>
      </section>

      {/* Film */}
      <section className="sec film-sec">
        <div className="rv" ref={filmTitleRef}>
          <p className="sec-eyebrow">60 seconds</p>
          <h2 className="sec-title" style={{margin: '0 auto'}}>See the whole story</h2>
        </div>
        <div className="film-frame">
          <span className="tape tape-tl" /><span className="tape tape-tr" />
          <video ref={videoRef} src="/ace-launch.mp4" poster="/poster.jpg" preload="metadata" muted loop playsInline controls />
        </div>
      </section>

      {/* Mantras */}
      <section className="mantras">
        <div className="mantras-inner">
          <Mantra delay={0}>Every credit counted</Mantra>
          <Mantra delay={350}>Every deadline tracked</Mantra>
          <Mantra delay={700}>Zero guesswork</Mantra>
        </div>
      </section>

      {/* CTA */}
      <section className="sec cta-sec rv" ref={ctaRef}>
        <p className="sec-eyebrow">Early access</p>
        <h2 className="sec-title" style={{margin: '0 auto'}}>Be one of the first 100.</h2>
        <p className="sec-sub" style={{margin: '14px auto 0'}}>
          We're opening ACE to a small early-access group before the fall semester. Grab a spot.
        </p>
        <WaitlistForm />
      </section>

      <footer className="footer">
        <p>
          ACE is an independent student-built planning tool and is <strong>not affiliated with or
          endorsed by Penn State University</strong>. Always confirm academic decisions with your adviser.
        </p>
        <p className="footer-links">
          <a href={APP_URL}>Open ACE</a> · <a href="mailto:mrmalpani25@gmail.com">Contact</a>
        </p>
      </footer>
    </div>
  );
}
