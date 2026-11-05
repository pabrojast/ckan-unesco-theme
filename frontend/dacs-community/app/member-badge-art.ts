// Artwork of the member badge shown on the lanyard: front (logo of the Decade, photo, name, role), back and strap.
// Drawn on canvases and handed to the Lanyard as image URLs, so no file is stored for any member.
import { broadGroupBadge, editorialBadgeIds } from "@/lib/member-roles";
import { asset } from "@/lib/base";

const W = 1024, H = 1440; // Same proportions as the portrait card of the Lanyard (1.6 × 2.25).
const NAVY = "#0b2f4e", BLUE = "#0a6eb4", FONT = '"Source Sans 3 Variable", "Source Sans 3", "Segoe UI", system-ui, sans-serif';

const images = new Map<string, Promise<HTMLImageElement | null>>();
function load(src: string) {
  if (!src) return Promise.resolve(null);
  if (!images.has(src))
    images.set(src, new Promise((resolve) => {
      const img = new Image();
      img.decoding = "async";
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    }));
  return images.get(src)!;
}
async function fonts() {
  try { await Promise.all([document.fonts.load(`700 64px ${FONT}`), document.fonts.load(`600 32px ${FONT}`), document.fonts.load(`400 32px ${FONT}`)]); } catch { /* system font */ }
}
function canvas(w: number, h: number) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  return [c, c.getContext("2d")!] as const;
}
/** Draws text on one line, reducing its size until it fits the width. */
function fitText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, max: number, weight: number, size: number, min = 26) {
  let s = size;
  do { ctx.font = `${weight} ${s}px ${FONT}`; s -= 2; } while (ctx.measureText(text).width > max && s > min);
  let t = text;
  while (ctx.measureText(t).width > max && t.length > 4) t = t.slice(0, -2);
  ctx.fillText(t === text ? t : t.trimEnd() + "…", x, y);
}
/** Splits a name over at most two lines, each fitting the width at the given size. */
function nameLines(ctx: CanvasRenderingContext2D, name: string, max: number) {
  for (const size of [76, 70, 64, 58, 52]) {
    ctx.font = `700 ${size}px ${FONT}`;
    if (ctx.measureText(name).width <= max) return { size, lines: [name] };
    const words = name.split(/\s+/);
    for (let i = words.length - 1; i > 0; i--) {
      const a = words.slice(0, i).join(" "), b = words.slice(i).join(" ");
      if (ctx.measureText(a).width <= max && ctx.measureText(b).width <= max) return { size, lines: [a, b] };
    }
  }
  return { size: 52, lines: [name] };
}
function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
}
const initials = (name: string) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("") || "?";

/** The member's role on the badge: their first badge or appointment, as on their profile. */
export function badgeRole(p: any) {
  const b = (p.membershipBadges || []).find((x: any) => !editorialBadgeIds.includes(x.id));
  return b?.label || broadGroupBadge.label;
}

export type BadgeArt = { front: string; back: string; strap: string };

export async function paintBadge(p: any, accent: { color: string; ink: string }, photo: string): Promise<BadgeArt> {
  await fonts();
  const [logo, unesco, topo, face] = await Promise.all([
    load(asset("assets/logos/decade-logo-en-white.png")), load(asset("assets/unesco-logo-white.webp")), load(asset("assets/topo-lines-white.webp")), load(photo),
  ]);

  // ---- Front ----
  const [front, f] = canvas(W, H);
  f.fillStyle = "#ffffff"; f.fillRect(0, 0, W, H);
  // Header: glacier blue, contour lines, and the logo of the Decade below the slot of the clip.
  const head = 500;
  const g = f.createLinearGradient(0, 0, W, head);
  g.addColorStop(0, NAVY); g.addColorStop(1, BLUE);
  f.fillStyle = g; f.fillRect(0, 0, W, head);
  if (topo) { f.globalAlpha = 0.16; f.drawImage(topo, 0, 0, W, (topo.height / topo.width) * W); f.globalAlpha = 1; }
  if (logo) { const lw = 660, lh = (logo.height / logo.width) * lw; f.drawImage(logo, (W - lw) / 2, 150, lw, lh); }
  // Thin band in the member's Working Group colour.
  f.fillStyle = accent.color; f.fillRect(0, head - 14, W, 14);

  // Photo, or initials, in a white ring.
  const cx = W / 2, cy = head + 40, r = 175;
  f.save();
  f.shadowColor = "rgba(4, 25, 44, 0.28)"; f.shadowBlur = 40; f.shadowOffsetY = 14;
  f.beginPath(); f.arc(cx, cy, r + 16, 0, Math.PI * 2); f.fillStyle = "#ffffff"; f.fill();
  f.restore();
  f.beginPath(); f.arc(cx, cy, r + 16, 0, Math.PI * 2); f.lineWidth = 6; f.strokeStyle = accent.color; f.stroke();
  f.save();
  f.beginPath(); f.arc(cx, cy, r, 0, Math.PI * 2); f.clip();
  if (face) {
    const s = Math.max((2 * r) / face.width, (2 * r) / face.height);
    f.drawImage(face, cx - (face.width * s) / 2, cy - (face.height * s) / 2, face.width * s, face.height * s);
  } else {
    const ig = f.createLinearGradient(cx - r, cy - r, cx + r, cy + r);
    ig.addColorStop(0, "#00afd0"); ig.addColorStop(1, BLUE);
    f.fillStyle = ig; f.fillRect(cx - r, cy - r, 2 * r, 2 * r);
    f.fillStyle = "#ffffff"; f.font = `700 132px ${FONT}`; f.textAlign = "center"; f.textBaseline = "middle";
    f.fillText(initials(p.name || ""), cx, cy + 6);
  }
  f.restore();

  // Name, position and organisation.
  f.textAlign = "center"; f.textBaseline = "alphabetic";
  const n = nameLines(f, p.name || "Member", W - 140);
  let y = cy + r + 40 + n.size;
  f.fillStyle = "#0f1f2e";
  for (const line of n.lines) { f.font = `700 ${n.size}px ${FONT}`; f.fillText(line, cx, y); y += n.size * 1.08; }
  y += 6;
  if (p.headline) { f.fillStyle = "#33475b"; fitText(f, p.headline, cx, y, W - 160, 500, 42); y += 60; }

  // Role, as a pill in the Working Group colour.
  const role = badgeRole(p);
  f.font = `700 40px ${FONT}`;
  const rw = Math.min(f.measureText(role).width + 80, W - 120);
  const ry = Math.max(y + 8, 1010);
  f.fillStyle = accent.color; roundRect(f, cx - rw / 2, ry, rw, 70, 35); f.fill();
  f.fillStyle = accent.ink; f.textBaseline = "middle"; fitText(f, role, cx, ry + 37, rw - 50, 700, 40, 24);
  f.textBaseline = "alphabetic";
  const org = [p.organisation, p.country].filter(Boolean).join(" · ");
  if (org) { f.fillStyle = "#33475b"; fitText(f, org, cx, ry + 135, W - 160, 500, 36, 24); }

  // Footer.
  const foot = H - 150;
  f.fillStyle = NAVY; f.fillRect(0, foot, W, H - foot);
  f.fillStyle = accent.color; f.fillRect(0, foot, W, 8);
  f.fillStyle = "#ffffff"; f.textAlign = "left"; f.font = `700 30px ${FONT}`;
  f.fillText("DACS COMMUNITY", 70, foot + 70);
  f.font = `400 26px ${FONT}`; f.globalAlpha = 0.85;
  f.fillText("Decade of Action for Cryospheric Sciences", 70, foot + 110);
  f.globalAlpha = 1; f.textAlign = "right"; f.font = `700 44px ${FONT}`;
  f.fillText("2025–2034", W - 70, foot + 96);

  // ---- Back ----
  const [back, b] = canvas(W, H);
  const bg = b.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, NAVY); bg.addColorStop(1, "#0a4f86");
  b.fillStyle = bg; b.fillRect(0, 0, W, H);
  if (topo) { b.globalAlpha = 0.14; for (let ty = 0; ty < H; ty += (topo.height / topo.width) * W) b.drawImage(topo, 0, ty, W, (topo.height / topo.width) * W); b.globalAlpha = 1; }
  if (logo) { const lw = 760, lh = (logo.height / logo.width) * lw; b.drawImage(logo, (W - lw) / 2, 470, lw, lh); }
  b.fillStyle = accent.color; b.fillRect((W - 160) / 2, 760, 160, 8);
  b.fillStyle = "#ffffff"; b.textAlign = "center"; b.font = `600 34px ${FONT}`;
  b.fillText("Member of the DACS community", W / 2, 850);
  if (unesco) { const uw = 300, uh = (unesco.height / unesco.width) * uw; b.globalAlpha = 0.95; b.drawImage(unesco, (W - uw) / 2, H - 260, uw, uh); b.globalAlpha = 1; }

  // ---- Strap: the name of the Decade repeated along the band ----
  const [strap, s] = canvas(2400, 192);
  s.fillStyle = NAVY; s.fillRect(0, 0, 2400, 192);
  s.fillStyle = accent.color; s.fillRect(0, 14, 2400, 6); s.fillRect(0, 172, 2400, 6);
  s.fillStyle = "#ffffff"; s.font = `700 64px ${FONT}`; s.textBaseline = "middle";
  const motto = "DECADE OF ACTION FOR CRYOSPHERIC SCIENCES  ·  2025–2034  ·  ";
  for (let x = 30, i = 0; x < 2400 && i < 6; i++) { s.fillText(motto, x, 100); x += s.measureText(motto).width; }

  return { front: front.toDataURL("image/jpeg", 0.9), back: back.toDataURL("image/jpeg", 0.9), strap: strap.toDataURL("image/png") };
}
