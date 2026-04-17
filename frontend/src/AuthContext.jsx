import { createContext, useContext, useEffect, useState } from "react";
import { auth } from "./firebase";
import {
  onAuthStateChanged,
  signInWithPopup,
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

  const signInWithGoogle = () =>
    signInWithPopup(auth, new GoogleAuthProvider());

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
