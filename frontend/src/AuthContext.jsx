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

  useEffect(() => {
    // Handle redirect result on mobile after returning from Google
    getRedirectResult(auth).then(async (result) => {
      if (result?.user) {
        try {
          await apiFetch("/auth/sync", { method: "POST" });
        } catch (e) {
          console.warn("User sync failed:", e);
        }
      }
    }).catch(() => {});

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        // Sync user record to our database (non-blocking)
        try {
          await apiFetch("/auth/sync", { method: "POST" });
        } catch (e) {
          console.warn("User sync failed:", e);
        }
      }
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
      user, signInWithGoogle, signInWithEmail, signUpWithEmail, signOut,
      resendVerification,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
