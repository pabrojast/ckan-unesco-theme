// Removes the previous build output (bundles and HTML pages) from the CKAN public folder,
// leaving the static assets (assets/, favicon.png) in place.
import { rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
const out = fileURLToPath(new URL("../../../ckanext/theme_ejemplo/public/dacs-community/", import.meta.url));
for (const p of ["bundle", "index.html", "logo-desk"]) rmSync(out + p, { recursive: true, force: true });
console.log("Cleaned the previous build in", out);
