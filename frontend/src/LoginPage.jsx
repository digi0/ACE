import { useState } from "react";
import { SignIn, SignUp } from "@clerk/clerk-react";
import { dark } from "@clerk/themes";
import SparklesCore from "./SparklesCore";

export default function LoginPage() {
  const [mode, setMode] = useState("signin");

  // Always dark on this page — Sparkles needs a dark canvas.
  // The Clerk widget must fit inside the .login-card. Clerk sizes its own
  // wrapper (.cl-cardBox) to the *viewport* — width 25rem with a viewport-based
  // max-width — not to its parent, so inside our padded glass card it overflows
  // to the right on phones. Pinning rootBox + cardBox + card to width:100% /
  // minWidth:0 / maxWidth:100% makes the widget shrink to the card. cardBox is
  // the wrapper the original fix missed: it sits BETWEEN rootBox and card and is
  // the element that actually carries the width.
  const appearance = {
    baseTheme: dark,
    variables: {
      colorPrimary: "#3b82f6",
      colorBackground: "transparent",
      colorInputBackground: "rgba(255,255,255,0.06)",
      colorInputText: "#fff",
      borderRadius: "8px",
      fontFamily: "inherit",
      fontSize: "13px",
    },
    elements: {
      rootBox: { width: "100%", minWidth: 0, maxWidth: "100%" },
      cardBox: { width: "100%", minWidth: 0, maxWidth: "100%" },
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
      formFieldInput: { width: "100%", boxSizing: "border-box" },
      formButtonPrimary: { width: "100%", boxSizing: "border-box" },
      socialButtons: { width: "100%" },
      socialButtonsBlockButton: { width: "100%", boxSizing: "border-box" },
      socialButtonsIconButton: { boxSizing: "border-box" },
    },
  };

  return (
    <div className="login-page">
      <SparklesCore
        background="transparent"
        minSize={0.8}
        maxSize={2}
        particleDensity={180}
        particleColor="#ffffff"
        className="login-sparkles-bg"
      />

      <div className="login-center">
        {/* Brand */}
        <div className="login-brand">
          <div className="login-logo">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="#ffffff" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round"
              aria-hidden>
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <span className="login-brand-name">ACE</span>
        </div>
        <p className="login-brand-sub">Academic Counseling Engine</p>

        {/* Card */}
        <div className="login-card">
          <h2 className="login-card-title">
            {mode === "signin" ? "Welcome back" : "Create your account"}
          </h2>
          <p className="login-card-subtitle">
            {mode === "signin"
              ? "Sign in to access your academic advisor"
              : "Sign up to get started with ACE"}
          </p>

          {mode === "signin" ? (
            <SignIn routing="virtual" appearance={appearance} signUpUrl="#signup" />
          ) : (
            <SignUp routing="virtual" appearance={appearance} signInUrl="#signin" />
          )}

          <p className="login-switch">
            {mode === "signin" ? "Don't have an account?" : "Already have an account?"}
            {" "}
            <button
              className="login-switch-btn"
              onClick={() => setMode((m) => (m === "signin" ? "signup" : "signin"))}
              type="button"
            >
              {mode === "signin" ? "Sign up" : "Sign in"}
            </button>
          </p>
        </div>

        <p className="login-footer">Built for Penn State students</p>
      </div>
    </div>
  );
}
