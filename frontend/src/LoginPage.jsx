import { useState } from "react";
import { useAuth } from "./AuthContext";
import AnimatedShaderBackground from "./AnimatedShaderBackground";

/* ── Icons ──────────────────────────────────────────── */
function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
      <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908C16.658 14.013 17.64 11.706 17.64 9.2z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" />
      <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" />
    </svg>
  );
}

function GradCapIcon({ size = 36 }) {
  const iconSize = Math.round(size * 0.52);
  const radius = Math.round(size * 0.22);
  return (
    <div className="ace-logo-box" style={{ width: size, height: size, borderRadius: radius }}>
      <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
        <path d="M6 12v5c3 3 9 3 12 0v-5" />
      </svg>
    </div>
  );
}

/* ── Friendly error messages ────────────────────────── */
function friendlyError(code) {
  switch (code) {
    case "auth/invalid-email":            return "Invalid email address.";
    case "auth/user-not-found":           return "No account found with this email.";
    case "auth/wrong-password":           return "Incorrect password.";
    case "auth/invalid-credential":       return "Invalid email or password.";
    case "auth/email-already-in-use":     return "An account with this email already exists.";
    case "auth/weak-password":            return "Password must be at least 6 characters.";
    case "auth/popup-closed-by-user":     return "Google sign-in was cancelled.";
    case "auth/network-request-failed":   return "Network error. Check your connection.";
    case "auth/too-many-requests":        return "Too many attempts. Please try again later.";
    default:                              return "Something went wrong. Please try again.";
  }
}

/* ── LoginPage ──────────────────────────────────────── */
export default function LoginPage() {
  const { signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();

  const [mode, setMode] = useState("signin"); // "signin" | "signup"
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGoogle = async () => {
    setError("");
    setLoading(true);
    try {
      await signInWithGoogle();
    } catch (e) {
      setError(friendlyError(e.code));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (mode === "signup" && !name.trim()) {
      setError("Please enter your full name.");
      return;
    }
    setLoading(true);
    try {
      if (mode === "signin") {
        await signInWithEmail(email, password);
      } else {
        await signUpWithEmail(email, password, name.trim());
      }
    } catch (e) {
      setError(friendlyError(e.code));
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode((m) => (m === "signin" ? "signup" : "signin"));
    setError("");
    setName("");
    setEmail("");
    setPassword("");
  };

  return (
    <div className="login-page">
      <AnimatedShaderBackground />

      {/* ── Left hero panel ─────────────────────── */}
      <div className="login-hero">
        <div className="login-hero-content">
          <GradCapIcon size={64} />
          <h1 className="login-hero-title">ACE</h1>
          <p className="login-hero-subtitle">Academic Counselling Engine</p>
          <p className="login-hero-desc">
            Your AI-powered academic advisor for Penn State Computer Science.
            Get personalized course planning, degree progress insights, and
            academic guidance — all in one place.
          </p>
          <span className="login-hero-badge">Penn State University</span>
        </div>
      </div>

      {/* ── Right form panel ────────────────────── */}
      <div className="login-form-panel">
        <div className="login-card">

          <h2 className="login-card-title">
            {mode === "signin" ? "Welcome back" : "Create your account"}
          </h2>
          <p className="login-card-subtitle">
            {mode === "signin"
              ? "Sign in to access your academic advisor"
              : "Sign up to get started with ACE"}
          </p>

          {/* Google */}
          <button
            className="login-google-btn"
            onClick={handleGoogle}
            disabled={loading}
            type="button"
          >
            <GoogleIcon />
            Continue with Google
          </button>

          <div className="login-divider"><span>or</span></div>

          {/* Email / Password form */}
          <form onSubmit={handleSubmit} className="login-form" noValidate>
            {mode === "signup" && (
              <div className="login-field">
                <label className="login-label" htmlFor="lp-name">Full Name</label>
                <input
                  id="lp-name"
                  className="login-input"
                  type="text"
                  placeholder="Jane Smith"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                  required
                />
              </div>
            )}

            <div className="login-field">
              <label className="login-label" htmlFor="lp-email">Email</label>
              <input
                id="lp-email"
                className="login-input"
                type="email"
                placeholder="xyz1234@psu.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </div>

            <div className="login-field">
              <label className="login-label" htmlFor="lp-password">Password</label>
              <input
                id="lp-password"
                className="login-input"
                type="password"
                placeholder={mode === "signup" ? "At least 6 characters" : "••••••••"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                required
              />
            </div>

            {error && <p className="login-error" role="alert">{error}</p>}

            <button
              className="login-submit-btn"
              type="submit"
              disabled={loading}
            >
              {loading
                ? "Please wait…"
                : mode === "signin" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <p className="login-switch">
            {mode === "signin" ? "Don't have an account?" : "Already have an account?"}
            {" "}
            <button className="login-switch-btn" onClick={switchMode} type="button">
              {mode === "signin" ? "Sign up" : "Sign in"}
            </button>
          </p>

        </div>
      </div>
    </div>
  );
}
