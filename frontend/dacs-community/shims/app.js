// Drop-in replacement for "firebase/app": IHP-WINS needs no Firebase project.
export function initializeApp(options = {}) { return { name: "[DEFAULT]", options }; }
export function getApp() { return { name: "[DEFAULT]", options: {} }; }
export function getApps() { return []; }
