import { useAuth } from "./AuthContext";

export default function EmailVerificationScreen({ user }) {
  const { signOut } = useAuth();

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      height: "100vh", background: "#fafafa",
      fontFamily: "'Plus Jakarta Sans', -apple-system, system-ui, sans-serif",
    }}>
      <div style={{
        maxWidth: 420, padding: 40, background: "white",
        borderRadius: 12, border: "1px solid #e4e4e7",
        boxShadow: "0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)",
        textAlign: "center",
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12,
          background: "#eff6ff", display: "flex",
          alignItems: "center", justifyContent: "center",
          margin: "0 auto 16px",
        }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
            stroke="#3b82f6" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
          </svg>
        </div>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: "#09090b", letterSpacing: "-0.3px" }}>
          Check your email
        </h2>
        <p style={{ fontSize: 13, color: "#71717a", lineHeight: 1.6, marginBottom: 24 }}>
          We sent a verification link to{" "}
          <strong style={{ color: "#09090b" }}>{user.email}</strong>.
          Click the link in the email to activate your account.
        </p>
        <button
          onClick={() => window.location.reload()}
          style={{
            width: "100%", padding: "10px 16px", borderRadius: 8,
            background: "#09090b", color: "white", border: "none",
            fontSize: 13, fontWeight: 600, cursor: "pointer",
            fontFamily: "inherit", marginBottom: 8,
          }}
        >
          I've verified my email
        </button>
        <button
          onClick={() => signOut()}
          style={{
            width: "100%", padding: "10px 16px", borderRadius: 8,
            background: "transparent", color: "#71717a", border: "1px solid #e4e4e7",
            fontSize: 13, fontWeight: 500, cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          Sign out and try again
        </button>
      </div>
    </div>
  );
}
