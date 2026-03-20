import { createContext, useContext, useEffect, useState } from "react";
import { auth } from "./firebase";
import {
  onAuthStateChanged,
  signInWithPopup,
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  signOut as firebaseSignOut,
} from "firebase/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // undefined = still loading, null = not signed in, object = signed in
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, setUser);
    return unsubscribe;
  }, []);

  const signInWithGoogle = () =>
    signInWithPopup(auth, new GoogleAuthProvider());

  const signInWithEmail = (email, password) =>
    signInWithEmailAndPassword(auth, email, password);

  const signUpWithEmail = async (email, password, name) => {
    const { user } = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(user, { displayName: name });
    // Refresh the user object so displayName is immediately available
    setUser({ ...user, displayName: name });
  };

  const signOut = () => firebaseSignOut(auth);

  return (
    <AuthContext.Provider value={{ user, signInWithGoogle, signInWithEmail, signUpWithEmail, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
