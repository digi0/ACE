import { createContext, useContext, useEffect, useState } from "react";
import { auth } from "./firebase";
import {
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  sendEmailVerification,
  signOut as firebaseSignOut,
} from "firebase/auth";
import { apiFetch } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // undefined = still loading, null = not signed in, object = signed in
  const [user, setUser] = useState(undefined);
  // Server-side state hydrated from /auth/sync. Null until sync completes for
  // the current user, so consumers can distinguish "no major" from "not yet
  // fetched" without racing against the sync insert.
  const [syncData, setSyncData] = useState(null);

  useEffect(() => {
    const syncAndStore = async (firebaseUser) => {
      try {
        const res = await apiFetch("/auth/sync", { method: "POST" });
        const data = await res.json();
        if (auth.currentUser?.uid === firebaseUser.uid) {
          setSyncData(data);
        }
      } catch (e) {
        console.warn("User sync failed:", e);
      }
    };

    // Handle redirect result on mobile after returning from Google
    getRedirectResult(auth).then((result) => {
      if (result?.user) syncAndStore(result.user);
    }).catch(() => {});

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) {
        setSyncData(null);
        setUser(null);
        return;
      }
      // Set user immediately so the app renders; syncData hydrates separately
      // and effects that need server-side state (major, has_doc) gate on it.
      setSyncData(null);
      setUser(firebaseUser);
      syncAndStore(firebaseUser);
    });
    return unsubscribe;
  }, []);

  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  const signInWithGoogle = () => {
    const provider = new GoogleAuthProvider();
    if (isMobile) return signInWithRedirect(auth, provider);
    return signInWithPopup(auth, provider);
  };

  const signInWithEmail = (email, password) =>
    signInWithEmailAndPassword(auth, email, password);

  const signUpWithEmail = async (email, password, name) => {
    const { user } = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(user, { displayName: name });
    await sendEmailVerification(user);
    // Keep the user signed in — App.jsx will show EmailVerificationScreen
    // automatically since emailVerified is false at this point.
  };

  const resendVerification = async (email, password) => {
    const { user } = await signInWithEmailAndPassword(auth, email, password);
    if (!user.emailVerified) {
      await sendEmailVerification(user);
      await firebaseSignOut(auth);
      return { sent: true };
    }
    // Already verified — let them through naturally via onAuthStateChanged
    return { sent: false, alreadyVerified: true };
  };

  const signOut = () => firebaseSignOut(auth);

  return (
    <AuthContext.Provider value={{
      user, syncData, signInWithGoogle, signInWithEmail, signUpWithEmail, signOut,
      resendVerification,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
