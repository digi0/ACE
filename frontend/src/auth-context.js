import { createContext, useContext } from "react";

/**
 * The auth context and its hook, kept OUT of AuthContext.jsx.
 *
 * react-refresh only preserves component state across edits when a module
 * exports components and nothing else. AuthContext.jsx exporting both
 * <AuthProvider> and useAuth meant every edit to it did a full remount instead
 * of a hot update. Splitting the non-component exports here fixes that; the
 * provider file now exports one component and nothing more.
 */
export const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);
