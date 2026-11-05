// Runs Alexandre's Firestore rules tests (tests/rules.test.mjs) against the IHP-WINS community API:
// starts tests/support/harness.py (same Python code as CKAN, SQLite in memory), then node --test.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("..", import.meta.url));
const rules = fileURLToPath(new URL("../../../ckanext/theme_ejemplo/community_data/dacs.rules", import.meta.url));
const port = process.env.DACS_HARNESS_PORT || "8765";
const harness = spawn("python3", ["tests/support/harness.py", "--port", port, "--rules", rules], { cwd: root, stdio: ["ignore", "pipe", "inherit"] });
await new Promise((resolve, reject) => {
  harness.stdout.on("data", (d) => { if (String(d).includes("listening")) resolve(); });
  harness.on("exit", (code) => reject(new Error("harness exited with " + code)));
});
const test = spawn(process.execPath, ["--import", "./tests/support/loader.mjs", "--test", "tests/rules.test.mjs"], {
  cwd: root, stdio: "inherit", env: { ...process.env, DACS_HARNESS: `http://127.0.0.1:${port}/api/` },
});
test.on("exit", (code) => { harness.kill(); process.exit(code ?? 1); });
