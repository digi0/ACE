import { useState } from "react";
import { SignIn, SignUp } from "@clerk/clerk-react";
import { dark } from "@clerk/themes";
import SparklesCore from "./SparklesCore";

export default function LoginPage() {
  const [mode, setMode] = useState("signin");

  // Always dark on this page — Sparkles needs a dark canvas.
  // Sized to fit inside the .login-card (max-width 420 minus 56 padding = 364
  // available). minWidth: 0 + width: 100% on rootBox/card overrides Clerk's
  // default minimum that otherwise blows out the input boxes.
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
      rootBox: { width: "100%", minWidth: 0 },
      card: {
        boxShadow: "none",
        background: "transparent",
        padding: 0,
        width: "100%",
        minWidth: 0,
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
