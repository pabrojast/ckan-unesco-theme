const map = {
  "firebase/firestore": new URL("../../shims/firestore.js", import.meta.url).href,
  "@firebase/rules-unit-testing": new URL("./rules-unit-testing.js", import.meta.url).href,
};
export async function resolve(specifier, context, next) {
  if (map[specifier]) return { url: map[specifier], shortCircuit: true };
  return next(specifier, context);
}
