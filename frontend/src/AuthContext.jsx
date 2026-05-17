import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useUser, useAuth as useClerkAuth } from "@clerk/clerk-react";
import { apiFetch } from "./api.js";

const AuthContext = createContext(null);

/**
 * Thin wrapper around Clerk's hooks that preserves the shape App.jsx already
 * consumes: { user, syncData, signOut }.
 *
 * - `user`: undefined while Clerk is loading, null if signed out, an object
 *   ({ uid, email, displayName }) when signed in. Mirrors the Firebase shape
 *   minus provider-specific bits.
 * - `syncData`: server-side state from /auth/sync ({ major, has_doc }). Null
 *   until sync resolves for the current user — kept so the major-modal
 *   effect can distinguish "no major" from "not yet fetched."
 */
export function AuthProvider({ children }) {
  const { isLoaded, isSignedIn, user: clerkUser } = useUser();
  const { signOut: clerkSignOut } = useClerkAuth();

  const [syncData, setSyncData] = useState(null);

  const user = useMemo(() => {
    if (!isLoaded) return undefined;
    if (!isSignedIn || !clerkUser) return null;
    return {
      uid: clerkUser.id,
      email: clerkUser.primaryEmailAddress?.emailAddress || null,
      displayName: clerkUser.fullName || clerkUser.username || null,
    };
  }, [isLoaded, isSignedIn, clerkUser]);

  // Sync on login; reset on logout.
  useEffect(() => {
    if (!user?.uid) {
      setSyncData(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch("/auth/sync", { method: "POST" });
        const data = await res.json();
        if (!cancelled) setSyncData(data);
      } catch (e) {
        console.warn("User sync failed:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [user?.uid]);

  const signOut = () => clerkSignOut();

  return (
    <AuthContext.Provider value={{ user, syncData, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
