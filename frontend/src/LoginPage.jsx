import { useState } from "react";
import { SignIn, SignUp } from "@clerk/clerk-react";
import { AceWordmark } from "./AceMark.jsx";

/**
 * Sign in / sign up.
 *
 * CONVERTED TO TAILWIND + ZERO CHROMA. This page used to be a dark canvas with
 * a ~226 kB animated sparkles field behind a blurred glass card. None of that
 * survives the language: Zero Chroma is flat, square, six greys, no gradients,
 * no shadows, no blur. Dropping SparklesCore also takes tsparticles out of the
 * bundle entirely — see the note in the commit if you want the sparkles back.
 *
 * The period: the Clerk primary button (Continue). It is the one action on the
 * page, so the mark above it drops its dot rather than competing.
 */
export default function LoginPage() {
  const [mode, setMode] = useState("signin");

  // Clerk sizes its own wrapper (.cl-cardBox) to the VIEWPORT — width 25rem with
  // a viewport-based max-width — not to its parent, so inside a padded card it
  // overflows to the right on phones. Pinning rootBox + cardBox + card to
  // width:100% / minWidth:0 / maxWidth:100% makes the widget shrink to the card.
  // cardBox is the one an earlier fix missed: it sits BETWEEN rootBox and card
  // and is the element that actually carries the width.
  const appearance = {
    variables: {
      colorPrimary: "#00875A",          // the period
      colorBackground: "transparent",
      colorText: "#0A0A0A",
      colorTextSecondary: "#666666",
      colorInputBackground: "#FFFFFF",
      colorInputText: "#0A0A0A",
      colorNeutral: "#0A0A0A",
      borderRadius: "0",
      fontFamily: "inherit",
      fontSize: "13px",
    },
    elements: {
      rootBox: { width: "100%", minWidth: 0, maxWidth: "100%" },
      cardBox: { width: "100%", minWidth: 0, maxWidth: "100%", boxShadow: "none", border: "none" },
      card: {
        boxShadow: "none",
        background: "transparent",
        padding: 0,
        width: "100%",
        minWidth: 0,
        maxWidth: "100%",
      },
      headerTitle: { display: "none" },
      headerSubtitle: { display: "none" },
      footer: { display: "none" },
      form: { width: "100%" },
      formFieldRow: { width: "100%" },
      formField: { width: "100%" },
      formFieldInput: { width: "100%", boxSizing: "border-box", borderRadius: 0 },
      // Ink on emerald measures 4.35:1 and fails AA; pure white is 4.55 and passes.
      formButtonPrimary: {
        width: "100%", boxSizing: "border-box", borderRadius: 0,
        color: "#FFFFFF", textTransform: "none", fontWeight: 600,
      },
      socialButtons: { width: "100%" },
      socialButtonsBlockButton: { width: "100%", boxSizing: "border-box", borderRadius: 0 },
      socialButtonsIconButton: { boxSizing: "border-box", borderRadius: 0 },
    },
  };

  return (
    <div className="login-page flex min-h-screen items-center justify-center p-5 font-sans">
      <div className="w-full max-w-[420px]">

        {/* The real wordmark, not a tile plus the letters "ACE" set in the UI
            font — same fix as the app header, dot and all. The period is the
            identity, so it stays part of the lockup wherever the wordmark
            appears; the sidebar carries it too. The "one emerald per view" rule
            governs UI accents beyond the logo — here that budget is spent on
            the Clerk primary button. */}
        <div className="mb-6 text-ink">
          <AceWordmark width={132} />
          <p className="mt-3.5 max-w-[46ch] text-[14.5px] leading-[1.45] text-mute">
            ACE is your Academic Counseling Engine. It reads the degree audit
            Penn State already gave you, then tells you what you still need,
            what you can take next, and what's due.
          </p>
        </div>

        <div className="border border-rule bg-card p-9">
          <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-ink">
            {mode === "signin" ? "welcome back" : "create your account"}
          </h1>
          <p className="mt-2 mb-7 max-w-[52ch] text-[14px] leading-[1.4] text-mute">
            {mode === "signin"
              ? "sign in to pick up where you left off."
              : "sign up and point ace at your degree."}
          </p>

          {mode === "signin" ? (
            <SignIn routing="virtual" appearance={appearance} signUpUrl="#signup" />
          ) : (
            <SignUp routing="virtual" appearance={appearance} signInUrl="#signin" />
          )}

          <p className="mt-6 border-t border-rule pt-5 text-[13px] text-mute">
            {mode === "signin" ? "no account yet?" : "already have an account?"}{" "}
            <button
              type="button"
              className="text-ink underline underline-offset-2"
              onClick={() => setMode((m) => (m === "signin" ? "signup" : "signin"))}
            >
              {mode === "signin" ? "sign up" : "sign in"}
            </button>
          </p>
        </div>

        <p className="mt-5 font-mono text-[11px] uppercase tracking-[0.14em] text-mute">
          Built for Penn State students
        </p>
      </div>
    </div>
  );
}
