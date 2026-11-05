// Drop-in replacement for the parts of "firebase/auth" the DACS Community app uses.
// There is no separate account: members sign in to IHP-WINS (CKAN). The current user comes from the
// community API ("me"), and sign-in, registration, sign-out and password resets open the IHP-WINS pages.

import { config, defaultTransport, FirestoreError } from "./transport.js";

const state = { known: false, user: null, loading: null, listeners: new Set() };

function toUser(info) {
  if (!info || !info.uid) return null;
  return {
    uid: info.uid,
    email: info.email || null,
    emailVerified: true,
    displayName: info.name || info.ckanName || null,
    ckanName: info.ckanName || null,
    platformAdmin: info.platformAdmin === true,
    sysadmin: info.sysadmin === true,
    accountUrl: info.accountUrl || null,
    providerData: [],
    isAnonymous: false,
    async getIdToken() { return ""; },
    async reload() { await loadUser(true); },
  };
}

async function loadUser(force = false) {
  if (state.loading && !force) return state.loading;
  state.loading = (async () => {
    try {
      const me = await defaultTransport.post("me", {});
      state.user = toUser(me && me.user);
    } catch (e) {
      console.error(e);
      state.user = null;
    }
    state.known = true;
    for (const cb of [...state.listeners]) { try { cb(state.user); } catch (e) { console.error(e); } }
    return state.user;
  })();
  return state.loading;
}

const authInstance = {
  get currentUser() { return state.user; },
  app: null,
  name: "[DEFAULT]",
};

export function getAuth() { return authInstance; }
export function connectAuthEmulator() {}

export function onAuthStateChanged(_auth, next) {
  const cb = typeof next === "function" ? next : (next && next.next) || (() => {});
  state.listeners.add(cb);
  if (state.known) queueMicrotask(() => { if (state.listeners.has(cb)) cb(state.user); });
  else void loadUser();
  return () => { state.listeners.delete(cb); };
}

const here = () => (typeof location !== "undefined" ? location.pathname + location.search : config.routeBase);
export const loginUrl = () => config.loginUrl || "/user/login?came_from=" + encodeURIComponent(here());
export const registerUrl = () => config.registerUrl || "/user/register";
export const logoutUrl = () => config.logoutUrl || "/user/_logout";
export const resetUrl = () => config.resetUrl || "/user/reset";

function go(url) {
  if (typeof location !== "undefined") location.assign(url);
  return new Promise(() => {}); // the page is leaving
}

export async function signOut() { return go(logoutUrl()); }
export async function reload() { await loadUser(true); }
export function signInWithEmailAndPassword() { return go(loginUrl()); }
export function createUserWithEmailAndPassword() { return go(registerUrl()); }
export function signInWithPopup() { return go(loginUrl()); }
export function signInWithRedirect() { return go(loginUrl()); }
export class GoogleAuthProvider { setCustomParameters() { return this; } }
export async function sendPasswordResetEmail() { return go(resetUrl()); }

const notOnIhpWins = () => Promise.reject(new FirestoreError("auth/operation-not-allowed", "Account emails are handled by IHP-WINS."));
export const verifyPasswordResetCode = notOnIhpWins;
export const confirmPasswordReset = notOnIhpWins;
export const checkActionCode = notOnIhpWins;
export const applyActionCode = notOnIhpWins;
