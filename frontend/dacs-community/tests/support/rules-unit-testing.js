// Stand-in for "@firebase/rules-unit-testing": runs Alexandre's Firestore rules tests against the IHP-WINS
// community API (tests/support/harness.py) instead of the Firebase emulator. Same function names and behaviour.
import { createFirestore } from "../../shims/firestore.js";
import { httpTransport } from "../../shims/transport.js";

const BASE = process.env.DACS_HARNESS || "http://127.0.0.1:8765/api/";

export async function initializeTestEnvironment() {
  const ctx = (headers) => ({ firestore: () => createFirestore(httpTransport(BASE, headers)) });
  return {
    authenticatedContext: (uid, token = {}) => ctx({ "X-Test-Auth": JSON.stringify({ uid, token }) }),
    unauthenticatedContext: () => ctx({}),
    withSecurityRulesDisabled: async (fn) => fn(ctx({ "X-Test-Bypass": "1" })),
    clearFirestore: async () => { await httpTransport(BASE).post("clear", {}); },
    cleanup: async () => {},
  };
}

export async function assertSucceeds(promise) {
  return await promise;
}

export async function assertFails(promise) {
  let result;
  try {
    result = await promise;
  } catch (e) {
    const code = String((e && e.code) || "");
    if (code === "permission-denied" || code === "PERMISSION_DENIED" || /PERMISSION_DENIED/.test(String(e && e.message))) return e;
    throw e;
  }
  throw new Error("Expected request to fail, but it succeeded." + (result === undefined ? "" : ""));
}
