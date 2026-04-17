import { auth } from "./firebase";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/**
 * Wrapper around fetch that automatically attaches the Firebase ID token
 * as a Bearer token in the Authorization header.
 */
export async function apiFetch(path, options = {}) {
  const user = auth.currentUser;
  const headers = { ...(options.headers || {}) };

  if (user) {
    const token = await user.getIdToken();
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options.body && typeof options.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    console.warn("API returned 401 — user may need to re-authenticate");
  }

  return res;
}

/**
 * For SSE streaming endpoints. Returns the raw Response for manual stream reading.
 */
export async function apiStream(path, body) {
  const user = auth.currentUser;
  const headers = { "Content-Type": "application/json" };

  if (user) {
    const token = await user.getIdToken();
    headers["Authorization"] = `Bearer ${token}`;
  }

  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
}
