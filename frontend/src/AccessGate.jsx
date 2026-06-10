import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const LANDING_URL = "https://acecollege.app";
const ACCESS_EMAIL = "access@acecollege.app";

/**
 * Pilot access gate. ACE is invite-only while we onboard the first cohort:
 * the access code is verified server-side (ACCESS_CODE env var on the
 * backend), and a successful unlock is remembered per-browser.
 *
 * Inline styles only — this screen renders before the app shell, and keeping
 * it self-contained avoids touching the desktop baseline stylesheet.
 */
export default function AccessGate({ onUnlock }) {
  const [code, setCode] = useState("");
  const [state, setState] = useState("idle"); // idle | checking | error
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!code.trim() || state === "checking") return;
    setState("checking");
    setError("");
    try {
      const res = await fetch(`${API}/access/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "That code isn't valid.");
      localStorage.setItem("ace_access_ok", "1");
      onUnlock();
    } catch (err) {
      setError(err.message || "Something went wrong — try again.");
      setState("error");
    }
  };

  const s = {
    page: {
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "#fbfaf7", padding: 20,
      backgroundImage: "radial-gradient(circle, #d8d5cc 1px, transparent 1px)",
      backgroundSize: "26px 26px",
      fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    card: {
      width: "100%", maxWidth: 430, background: "#fff", borderRadius: 18,
      border: "1.5px solid #e4e4e7", boxShadow: "0 30px 70px rgba(20,20,25,0.10)",
      padding: "36px 34px", textAlign: "center",
    },
    mark: {
      width: 52, height: 52, borderRadius: 14, background: "#2563eb",
      display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px",
    },
    h1: { fontSize: 24, fontWeight: 800, color: "#101113", letterSpacing: "-0.5px", margin: "0 0 8px" },
    p: { fontSize: 14.5, color: "#686d76", lineHeight: 1.6, margin: "0 0 22px" },
    input: {
      width: "100%", boxSizing: "border-box", fontSize: 16, padding: "13px 16px",
      border: "1.5px solid #e4e4e7", borderRadius: 12, outline: "none",
      textAlign: "center", letterSpacing: "2px", fontWeight: 600, marginBottom: 10,
    },
    btn: {
      width: "100%", fontSize: 15.5, fontWeight: 700, color: "#fff", background: "#2563eb",
      border: "none", borderRadius: 12, padding: "13px 0",
      cursor: state === "checking" ? "wait" : "pointer", opacity: state === "checking" ? 0.7 : 1,
    },
    err: { color: "#dc2626", fontSize: 13.5, margin: "10px 0 0" },
    foot: { marginTop: 22, paddingTop: 18, borderTop: "1px solid #f0efe9", fontSize: 13.5, color: "#686d76", lineHeight: 1.7 },
    a: { color: "#2563eb", fontWeight: 600, textDecoration: "none" },
  };

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.mark}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
            <path d="M6 12v5c3 3 9 3 12 0v-5" />
          </svg>
        </div>
        <h1 style={s.h1}>ACE is in early access</h1>
        <p style={s.p}>
          We're onboarding the first group of students. Enter your access code
          to continue.
        </p>
        <form onSubmit={submit}>
          <input
            style={s.input}
            type="password"
            placeholder="ACCESS CODE"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            autoFocus
            aria-label="Access code"
          />
          <button style={s.btn} type="submit" disabled={state === "checking"}>
            {state === "checking" ? "Checking…" : "Unlock ACE"}
          </button>
          {error && <p style={s.err}>{error}</p>}
        </form>
        <div style={s.foot}>
          Don't have a code?{" "}
          <a style={s.a} href={LANDING_URL}>Join the waitlist</a>
          {" "}or email{" "}
          <a style={s.a} href={`mailto:${ACCESS_EMAIL}?subject=ACE%20access%20request`}>{ACCESS_EMAIL}</a>
        </div>
      </div>
    </div>
  );
}
