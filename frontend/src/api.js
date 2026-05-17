const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/**
 * Get a session token from Clerk. Uses the global `window.Clerk` instance
 * exposed by ClerkProvider so plain modules (non-React) can attach auth
 * without going through hooks.
 */
async function getClerkToken() {
  const clerk = typeof window !== "undefined" ? window.Clerk : null;
  if (!clerk?.session) return null;
  try {
    return await clerk.session.getToken();
  } catch {
    return null;
  }
}

/**
 * Wrapper around fetch that automatically attaches a Clerk session token
 * as a Bearer token in the Authorization header.
 */
export async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };

  const token = await getClerkToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

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
  const headers = { "Content-Type": "application/json" };

  const token = await getClerkToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
}
