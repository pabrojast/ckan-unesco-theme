// Light is the default, matching the official United Nations web presence.
// Dark mode is used only after a member chooses it with the theme switch (version 3.11 or later);
// choices saved by earlier versions under "dacs-theme" are ignored so everyone starts in light mode.
export type Theme = "light" | "dark";
const KEY = "dacs-theme-v2";
export function storedTheme(): Theme {
  try {
    return localStorage.getItem(KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}
export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.classList.toggle("light", theme === "light");
  root.style.colorScheme = theme;
}
export function saveTheme(theme: Theme) {
  try {
    localStorage.setItem(KEY, theme);
  } catch {}
  applyTheme(theme);
}
