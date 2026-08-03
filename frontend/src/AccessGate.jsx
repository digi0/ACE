import { useState } from "react";
import { AceTile } from "./AceMark.jsx";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const LANDING_URL = "https://acecollege.app";
const ACCESS_EMAIL = "access@acecollege.app";

/**
 * Pilot access gate. ACE is invite-only while we onboard the first cohort:
 * the access code is verified server-side (ACCESS_CODE env var on the
 * backend), and a successful unlock is remembered per-browser.
 *
 * FIRST SCREEN CONVERTED TO TAILWIND + ZERO CHROMA. It was the right pilot
 * because it carried no index.css rules at all (it was inline-styled), so
 * there is no unlayered CSS competing with the utilities here.
 *
 * The period: the unlock button. That is the one thing this view exists to do,
 * so the mark above it drops its dot rather than competing for the accent.
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

  return (
    <div className="flex min-h-screen items-center justify-center bg-ground p-5 font-sans">
      {/* Cards sit LIGHTER than the page and are never raised by shadow. */}
      <div className="w-full max-w-[430px] border border-rule bg-card p-9">

        {/* Logo tile — the one place radius is allowed (20%). */}
        <AceTile size={52} period={false} className="mb-6" />

        <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-ink">
          ace is in early access
        </h1>
        <p className="mt-2 max-w-[52ch] text-[14px] leading-[1.4] text-mute">
          we're onboarding the first group of students. enter your access code
          to continue.
        </p>

        <form onSubmit={submit} className="mt-7">
          <label
            htmlFor="access-code"
            className="mb-2 block font-mono text-[11px] uppercase tracking-[0.14em] text-mute"
          >
            Access code
          </label>
          <input
            id="access-code"
            type="password"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            autoFocus
            aria-invalid={state === "error" || undefined}
            aria-describedby={error ? "access-error" : undefined}
            className="w-full border border-rule bg-card px-4 py-3 font-mono text-[16px]
                       tracking-[0.12em] text-ink outline-none
                       transition-colors duration-200 ease-ace
                       placeholder:text-ghost focus:border-ink
                       aria-invalid:border-ink"
          />

          {/* The period. Measured against #00875A: pure white is 4.55:1 (AA, by
              0.05), ink is 4.35 and paper #F6F6F6 is 4.21 — both fail. The
              emerald has almost no contrast headroom, so this stays #FFFFFF and
              is the one place the app uses pure white. */}
          <button
            type="submit"
            disabled={state === "checking"}
            className="mt-3 w-full bg-period py-3 text-center text-[15px] font-semibold text-white
                       transition-opacity duration-200 ease-ace
                       hover:opacity-90 disabled:cursor-wait disabled:opacity-60"
          >
            {state === "checking" ? "checking…" : "unlock ace"}
          </button>

          {/* Zero Chroma has no alert red — the error carries by weight and a
              mono label, the same way the field label does. */}
          {error && (
            <p id="access-error" role="alert" className="mt-3 flex gap-2 text-[13px] text-ink">
              <span className="font-mono uppercase tracking-[0.14em] text-mute">Error</span>
              <span>{error}</span>
            </p>
          )}
        </form>

        <div className="mt-6 border-t border-rule pt-5 text-[13px] leading-[1.4] text-mute">
          no code yet?{" "}
          <a className="text-ink underline underline-offset-2" href={LANDING_URL}>
            join the waitlist
          </a>
          {" "}or email{" "}
          <a
            className="text-ink underline underline-offset-2"
            href={`mailto:${ACCESS_EMAIL}?subject=ACE%20access%20request`}
          >
            {ACCESS_EMAIL}
          </a>
        </div>
      </div>
    </div>
  );
}
