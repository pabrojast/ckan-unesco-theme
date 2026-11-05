// Maps the Firebase imports of the rules tests to the IHP-WINS client and the test stand-in.
import { register } from "node:module";
register("./hooks.mjs", import.meta.url);
