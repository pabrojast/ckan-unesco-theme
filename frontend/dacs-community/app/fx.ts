// Small visual effects shared across the platform. Every effect is skipped when the member's device asks to reduce motion.

export const reducedMotion = () => {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
};

/** Draws a six-branched ice crystal centred on (0, 0). */
export function drawCrystal(ctx: CanvasRenderingContext2D, r: number) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i, c = Math.cos(a), s = Math.sin(a);
    ctx.moveTo(0, 0); ctx.lineTo(c * r, s * r);
    // Two small side branches on each arm.
    const bx = c * r * 0.55, by = s * r * 0.55, b = r * 0.32;
    ctx.moveTo(bx, by); ctx.lineTo(bx + Math.cos(a + 0.7) * b, by + Math.sin(a + 0.7) * b);
    ctx.moveTo(bx, by); ctx.lineTo(bx + Math.cos(a - 0.7) * b, by + Math.sin(a - 0.7) * b);
  }
  ctx.stroke();
}

type Flake = { x: number; y: number; vx: number; vy: number; r: number; a: number; va: number; color: string; life: number };

/**
 * A burst of snow crystals over the whole page, in the given colours.
 * `origin` is a point in the viewport (default: the top centre); crystals spread from it and drift down.
 */
export function snowBurst(colors: string[], opts: { origin?: { x: number; y: number }; count?: number; duration?: number } = {}) {
  if (typeof document === "undefined" || reducedMotion()) return;
  const canvas = document.createElement("canvas");
  canvas.className = "fx-snow";
  canvas.setAttribute("aria-hidden", "true");
  const dpr = Math.min(window.devicePixelRatio || 1, 2), W = window.innerWidth, H = window.innerHeight;
  canvas.width = W * dpr; canvas.height = H * dpr;
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx) { canvas.remove(); return; }
  ctx.scale(dpr, dpr);
  const o = opts.origin || { x: W / 2, y: H * 0.18 }, n = opts.count ?? 90, duration = opts.duration ?? 3800;
  const palette = [...colors, "#ffffff", "#dff3fb"];
  const flakes: Flake[] = Array.from({ length: n }, () => {
    const angle = Math.random() * Math.PI * 2, speed = 2 + Math.random() * 7;
    return { x: o.x, y: o.y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed - 3, r: 4 + Math.random() * 9, a: Math.random() * Math.PI, va: (Math.random() - 0.5) * 0.12, color: palette[Math.floor(Math.random() * palette.length)], life: 0 };
  });
  const start = performance.now();
  let last = start;
  const tick = (now: number) => {
    const dt = Math.min(2, (now - last) / 16.7); last = now;
    const t = (now - start) / duration;
    ctx.clearRect(0, 0, W, H);
    for (const f of flakes) {
      f.vx *= 0.985 ** dt; f.vy = f.vy * 0.985 ** dt + 0.09 * dt; // air drag, then a gentle fall
      f.vx += Math.sin((now / 600) + f.r) * 0.02 * dt; // breeze
      f.x += f.vx * dt; f.y += f.vy * dt; f.a += f.va * dt;
      ctx.save();
      ctx.globalAlpha = Math.max(0, 1 - Math.max(0, t - 0.65) / 0.35);
      ctx.translate(f.x, f.y); ctx.rotate(f.a);
      ctx.strokeStyle = f.color; ctx.lineWidth = Math.max(1.2, f.r / 6); ctx.lineCap = "round";
      ctx.shadowColor = "rgba(10, 40, 70, 0.25)"; ctx.shadowBlur = 2;
      drawCrystal(ctx, f.r);
      ctx.restore();
    }
    if (t < 1) requestAnimationFrame(tick); else canvas.remove();
  };
  requestAnimationFrame(tick);
}

/** Remembers, per member and on this device, which moments were already celebrated. */
export function celebrated(key: string): string[] {
  try { return JSON.parse(localStorage.getItem("dacs-celebrated-" + key) || "[]"); } catch { return []; }
}
export function markCelebrated(key: string, ids: string[]) {
  try { localStorage.setItem("dacs-celebrated-" + key, JSON.stringify([...new Set([...celebrated(key), ...ids])].slice(-100))); } catch { /* storage unavailable */ }
}

/** An aurora that sweeps across the screen, used when switching between the bright and dark themes. */
export function auroraSweep() {
  if (typeof document === "undefined" || reducedMotion()) return;
  const el = document.createElement("div");
  el.className = "fx-aurora";
  el.setAttribute("aria-hidden", "true");
  el.innerHTML = "<i></i><i></i><i></i>";
  document.body.appendChild(el);
  window.setTimeout(() => el.remove(), 2200);
}
