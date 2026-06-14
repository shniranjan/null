/**
 * Null — API Client
 *
 * Wraps fetch() with automatic JWT token attachment,
 * 401 handling (redirect to login), and JSON parsing.
 */

const API_BASE = "/api";

let authToken = null;

/** Set the JWT token for all subsequent requests. */
export function setToken(token) {
  authToken = token;
  if (token) {
    localStorage.setItem("xcpng_token", token);
  } else {
    localStorage.removeItem("xcpng_token");
  }
}

/** Get the stored token (from memory or localStorage). */
export function getToken() {
  if (authToken) return authToken;
  authToken = localStorage.getItem("xcpng_token");
  return authToken;
}

/** Base fetch wrapper with auth headers and error handling. */
export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  // Handle 401 — token expired or invalid
  if (res.status === 401) {
    setToken(null);
    // Redirect to login (dispatch custom event so App can react)
    window.dispatchEvent(new CustomEvent("auth:expired"));
    throw new Error("Session expired — please log in again");
  }

  // For 204 No Content, return null
  if (res.status === 204) return null;

  const data = await res.json();

  if (!res.ok) {
    const msg = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data;
}

// ── Convenience methods ───────────────────────────────────────────

export const api = {
  get: (path) => apiFetch(path),
  post: (path, body) =>
    apiFetch(path, { method: "POST", body: JSON.stringify(body) }),
  put: (path, body) =>
    apiFetch(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path) => apiFetch(path, { method: "DELETE" }),
};

// ── Auth ──────────────────────────────────────────────────────────

export async function login(username, password) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function logout() {
  try {
    await api.post("/auth/logout");
  } catch {
    // ignore
  }
  setToken(null);
}

export async function getMe() {
  return api.get("/auth/me");
}
