// Transport to the IHP-WINS (CKAN) community API.
// The page served by CKAN sets window.__DACS__ (routeBase, apiBase, login/register/logout URLs).
// Static pages (the logo desk, opened in a frame) fall back to the build-time default.

const pageConfig = (typeof window !== "undefined" && window.__DACS__) || {};
const env = (import.meta && import.meta.env) || {};

export const config = {
  apiBase: pageConfig.apiBase || env.VITE_DACS_API_BASE || "/group/dacs/community-of-practice/api/",
  routeBase: pageConfig.routeBase || env.VITE_DACS_ROUTE_BASE || "/group/dacs/community-of-practice/",
  ...pageConfig,
};

/** Error with a Firestore error code, so the app's `e.code === "permission-denied"` checks keep working. */
export class FirestoreError extends Error {
  constructor(code, message) {
    super(message || code);
    this.code = code;
    this.name = "FirebaseError";
  }
}

/**
 * POST transport. `headers` lets tests act as a given user (the local harness reads them; CKAN ignores them).
 * The custom header and JSON body make every call a same-origin request that a cross-site form cannot forge.
 */
let csrfPromise = null;
/** CKAN's CSRF token: from the page, from the parent page (logo desk frame), or asked once from the API. */
function csrfToken(root) {
  if (typeof window === "undefined") return Promise.resolve("");
  if (config.csrfToken) return Promise.resolve(config.csrfToken);
  try {
    const parent = window.parent && window.parent !== window && window.parent.__DACS__;
    if (parent && parent.csrfToken) return Promise.resolve(parent.csrfToken);
  } catch { /* other origin */ }
  if (!csrfPromise) {
    csrfPromise = fetch(root + "csrf", { credentials: "same-origin", headers: { "X-DACS-Request": "1" } })
      .then((r) => (r.ok ? r.json() : {}))
      .then((j) => (j && j.token) || "")
      .catch(() => "");
  }
  return csrfPromise;
}

export function httpTransport(base = config.apiBase, headers = {}) {
  const root = base.endsWith("/") ? base : base + "/";
  return {
    async post(action, body) {
      let res;
      try {
        const token = await csrfToken(root);
        res = await fetch(root + action, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-DACS-Request": "1", ...(token ? { "X-CSRFToken": token } : {}), ...headers },
          body: JSON.stringify(body || {}),
        });
      } catch (e) {
        throw new FirestoreError("unavailable", "The community service could not be reached. Check the connection and try again.");
      }
      let json = null;
      try { json = await res.json(); } catch { /* not JSON */ }
      if (!res.ok || (json && json.error)) {
        const err = (json && json.error) || {};
        throw new FirestoreError(err.code || (res.status === 403 ? "permission-denied" : res.status === 404 ? "not-found" : "internal"),
          err.message || `Request failed (${res.status}).`);
      }
      return json;
    },
  };
}

export const defaultTransport = httpTransport();
