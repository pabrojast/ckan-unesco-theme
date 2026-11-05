import { useEffect, useMemo, useRef, useState } from "react";
import { geoOrthographic, geoPath, geoGraticule10, geoDistance } from "d3-geo";
import { feature } from "topojson-client";
import { Minus, Pause, Play, Plus, RotateCcw } from "lucide-react";
import { countryKey, countryPoints, tally } from "@/lib/coordination";
import { groups } from "@/lib/data";
import { MemberAvatar } from "./member-avatar";
import { optionsFor } from "@/lib/profile-options";

const disclaimer = "The designations employed and the presentation of material on this map do not imply the expression of any opinion whatsoever on the part of UNESCO concerning the legal status of any country, territory, city or area or of its authorities, or concerning the delimitation of its frontiers or boundaries.";
let land110: any = null, land50: any = null;
/** World land only: coastlines, no national borders. The finer outline loads when zooming in. */
async function loadLand(detail: boolean) {
  if (detail) {
    if (!land50) { const t: any = (await import("world-atlas/land-50m.json")).default; land50 = feature(t, t.objects.land); }
    return land50;
  }
  if (!land110) { const t: any = (await import("world-atlas/land-110m.json")).default; land110 = feature(t, t.objects.land); }
  return land110;
}
const graticule = geoGraticule10();
const MIN_K = 1, MAX_K = 4.5, SPIN = 5; // degrees per second
const reduceMotion = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
type Point = { country: string; label: string; coords: [number, number]; count: number; genders?: [string, number][]; color?: string; wg?: number };
/** Working Group of a member for the map: their first appointment or Broad Group badge, otherwise their first interest. */
function memberWg(p: any) {
  const badge = (p.membershipBadges || []).map((b: any) => /^wg([1-5])-/.exec(b.id)?.[1]).find(Boolean);
  return Number(badge || (p.wgs || [])[0] || 0);
}

/**
 * Registered members by country on a rotating globe without national borders.
 * Drag to turn it, zoom with the buttons, a pinch or the wheel (after clicking), click a country to focus on it.
 * Gender appears as totals: for all members from the published totals, or for the profiles shown (UNESCO Secretariat).
 */
export function MembersMap({ people, genderOf, genderTotals, categories = [], note, focusCountry, onOpenProfile }: {
  people: any[];
  focusCountry?: string;
  onOpenProfile?: (p: any) => void;
  genderOf?: (id: string) => string;
  genderTotals?: { total: number; gender: Record<string, number> } | null;
  categories?: any[];
  note?: string;
}) {
  const [stage, setStage] = useState("");
  const [gender, setGender] = useState("");
  const [hover, setHover] = useState("");
  const [selected, setSelected] = useState("");
  const [spinning, setSpinning] = useState(() => !reduceMotion());
  const [zoom, setZoom] = useState(1);
  const [active, setActive] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null), canvasRef = useRef<HTMLCanvasElement>(null), tipRef = useRef<HTMLDivElement>(null);
  const state = useRef({ rot: [-12, -28, 0] as [number, number, number], k: 1, land: null as any, size: { w: 800, h: 520 }, drag: null as null | { x: number; y: number; moved: boolean }, pinch: null as null | { d: number; k: number }, pointers: new Map<number, { x: number; y: number }>(), resumeAt: 0, fly: null as null | { from: [number, number]; to: [number, number]; start: number }, points: [] as Point[], hover: "", selected: "", spinning: true });
  const stages = optionsFor("careerStages", categories);
  const genders = optionsFor("genders", categories);
  const filtered = useMemo(() => people.filter((p) => (!stage || (p.careerStage || "Not stated") === stage) && (!gender || (genderOf?.(p.id) || "Not stated") === gender)), [people, stage, gender, genderOf]);
  const { points, unplaced } = useMemo((): { points: Point[]; unplaced: [string, number][] } => {
    const base = countryPoints(filtered);
    // Each country glows in the colour of the Working Group most represented among its members.
    const r = { ...base, points: base.points.map((pt) => {
      const counts = new Map<number, number>();
      for (const m of filtered) if (countryKey(m.country || "") === pt.country) { const n = memberWg(m); if (n) counts.set(n, (counts.get(n) || 0) + 1); }
      const wg = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0]?.[0] || 0;
      return { ...pt, wg, color: wg ? groups[wg - 1].color : "#cfe8f5" };
    }) };
    if (!genderOf) return r;
    // UNESCO Secretariat: gender split per country, for the tooltip.
    return { ...r, points: r.points.map((p) => ({ ...p, genders: tally(filtered.filter((m) => countryPoints([m]).points[0]?.country === p.country), (m) => genderOf(m.id), genders) as [string, number][] })) };
  }, [filtered, genderOf]);
  const max = Math.max(1, ...points.map((p) => p.count));
  const stageTotals = tally(filtered, (p) => p.careerStage, stages);
  const genderRows: [string, number][] = genderOf
    ? (tally(filtered, (p) => genderOf(p.id), genders) as [string, number][])
    : genderTotals ? Object.entries(genderTotals.gender).sort((a, b) => (genders.indexOf(a[0]) + 1 || 99) - (genders.indexOf(b[0]) + 1 || 99)) : [];
  const genderTotal = genderRows.reduce((n, r) => n + r[1], 0);
  const pct = (n: number) => (genderTotal ? Math.round((n / genderTotal) * 100) : 0);
  state.current.points = points;
  state.current.hover = hover;
  state.current.selected = selected;
  state.current.spinning = spinning;

  useEffect(() => { loadLand(false).then((l) => { if (!state.current.land) state.current.land = l; }).catch(() => {}); }, []);
  useEffect(() => { if (zoom >= 2) loadLand(true).then((l) => { state.current.land = l; }).catch(() => {}); }, [zoom >= 2]);
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => { const w = el.clientWidth; state.current.size = { w, h: Math.max(340, Math.min(560, Math.round(w * 0.66))) }; });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  /* ---------- drawing loop ---------- */
  useEffect(() => {
    let raf = 0, last = performance.now();
    const still = reduceMotion();
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const s = state.current, c = canvasRef.current;
      if (!c) return;
      const dt = Math.min(64, now - last); last = now;
      const { w, h } = s.size, dpr = Math.min(2, window.devicePixelRatio || 1);
      if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); c.style.height = h + "px"; }
      if (s.fly) {
        const t = Math.min(1, (now - s.fly.start) / 900), e = 1 - Math.pow(1 - t, 3);
        let dl = s.fly.to[0] - s.fly.from[0]; dl = ((dl + 540) % 360) - 180;
        s.rot = [s.fly.from[0] + dl * e, s.fly.from[1] + (s.fly.to[1] - s.fly.from[1]) * e, 0];
        if (t >= 1) s.fly = null;
      } else if (s.spinning && !s.drag && !s.selected && now > s.resumeAt && !still) {
        s.rot = [s.rot[0] + (SPIN * dt) / 1000, s.rot[1], 0];
      }
      const ctx = c.getContext("2d")!;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const r = Math.min(w, h) * 0.43 * s.k;
      const proj = geoOrthographic().translate([w / 2, h / 2]).scale(r).rotate(s.rot).clipAngle(90).precision(0.6);
      const path = geoPath(proj, ctx);
      // atmosphere glow
      const glow = ctx.createRadialGradient(w / 2, h / 2, r * 0.92, w / 2, h / 2, r * 1.18);
      glow.addColorStop(0, "rgba(120, 200, 235, 0.22)"); glow.addColorStop(1, "rgba(120, 200, 235, 0)");
      ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(w / 2, h / 2, r * 1.18, 0, Math.PI * 2); ctx.fill();
      // ocean
      const sea = ctx.createRadialGradient(w / 2 - r * 0.35, h / 2 - r * 0.4, r * 0.1, w / 2, h / 2, r);
      sea.addColorStop(0, "#3d7392"); sea.addColorStop(0.55, "#22506f"); sea.addColorStop(1, "#143553");
      ctx.beginPath(); path({ type: "Sphere" } as any); ctx.fillStyle = sea; ctx.fill();
      // graticule
      ctx.beginPath(); path(graticule); ctx.strokeStyle = "rgba(160, 215, 240, 0.16)"; ctx.lineWidth = 0.8; ctx.stroke();
      // land (coastlines only)
      if (s.land) {
        ctx.beginPath(); path(s.land);
        ctx.fillStyle = "rgba(255, 255, 255, 0.07)"; ctx.fill();
        ctx.strokeStyle = "rgba(235, 247, 252, 0.85)"; ctx.lineWidth = 0.9; ctx.stroke();
      }
      // rim
      ctx.beginPath(); path({ type: "Sphere" } as any); ctx.strokeStyle = "rgba(190, 232, 247, 0.55)"; ctx.lineWidth = 1.3; ctx.stroke();
      // countries
      const center: [number, number] = [-s.rot[0], -s.rot[1]];
      let tipPoint: Point | null = null, tipXY: [number, number] | null = null;
      s.points.forEach((p, i) => {
        if (geoDistance(p.coords, center) > Math.PI / 2 - 0.02) return;
        const xy = proj(p.coords); if (!xy) return;
        const base = Math.min(13, 4 + Math.sqrt(p.count) * 2.1) * (0.85 + 0.15 * s.k);
        const on = p.country === s.hover || p.country === s.selected;
        if (!still) {
          const phase = ((now / 1000 + i * 0.37) % 2.4) / 2.4;
          ctx.beginPath(); ctx.arc(xy[0], xy[1], base * (1.2 + phase * 2.2), 0, Math.PI * 2);
          ctx.globalAlpha = (1 - phase) * (on ? 0.9 : 0.6);
          ctx.strokeStyle = on ? "#f2a54a" : p.color || "#8ed2ee"; ctx.lineWidth = 1.5; ctx.stroke();
          ctx.globalAlpha = 1;
        }
        const halo = ctx.createRadialGradient(xy[0], xy[1], base * 0.6, xy[0], xy[1], base * 2.4);
        halo.addColorStop(0, (on ? "#f2a54a" : p.color || "#8ed2ee") + "88"); halo.addColorStop(1, (on ? "#f2a54a" : p.color || "#8ed2ee") + "00");
        ctx.beginPath(); ctx.arc(xy[0], xy[1], base * 2.4, 0, Math.PI * 2); ctx.fillStyle = halo; ctx.fill();
        ctx.beginPath(); ctx.arc(xy[0], xy[1], base, 0, Math.PI * 2);
        ctx.fillStyle = on ? "#f2a54a" : p.color || "#8ed2ee"; ctx.fill();
        ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2; ctx.stroke();
        if (on) { tipPoint = p; tipXY = xy as [number, number]; }
      });
      const tip = tipRef.current;
      if (tip) {
        if (tipPoint && tipXY) { tip.style.opacity = "1"; tip.style.transform = `translate(${tipXY[0] + 16}px, ${tipXY[1] - 18}px)`; }
        else tip.style.opacity = "0";
      }
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  /* ---------- interaction ---------- */
  const pause = (ms = 3500) => { state.current.resumeAt = performance.now() + ms; };
  function pick(cx: number, cy: number) {
    const s = state.current, c = canvasRef.current!, b = c.getBoundingClientRect();
    const x = cx - b.left, y = cy - b.top, { w, h } = s.size, r = Math.min(w, h) * 0.43 * s.k;
    const proj = geoOrthographic().translate([w / 2, h / 2]).scale(r).rotate(s.rot).clipAngle(90);
    const center: [number, number] = [-s.rot[0], -s.rot[1]];
    let best = "", dist = 1e9;
    for (const p of s.points) {
      if (geoDistance(p.coords, center) > Math.PI / 2 - 0.02) continue;
      const xy = proj(p.coords); if (!xy) continue;
      const d = Math.hypot(xy[0] - x, xy[1] - y), base = Math.min(13, 4 + Math.sqrt(p.count) * 2.1) * (0.85 + 0.15 * s.k);
      if (d < base + 8 && d < dist) { dist = d; best = p.country; }
    }
    return best;
  }
  function flyTo(country: string) {
    const p = points.find((x) => x.country === country);
    if (!p) return;
    const s = state.current;
    s.fly = { from: [s.rot[0], s.rot[1]], to: [-p.coords[0], Math.max(-70, Math.min(70, -p.coords[1]))], start: performance.now() };
    setSelected(country);
    if (s.k < 1.6) { s.k = 1.6; setZoom(1.6); }
  }
  // Opening a member's profile turns the globe to their country.
  useEffect(() => { if (!focusCountry) return; const key = countryKey(focusCountry); if (key && points.some((p) => p.country === key)) flyTo(key); }, [focusCountry]);
  function setK(k: number) { const v = Math.min(MAX_K, Math.max(MIN_K, k)); state.current.k = v; setZoom(v); pause(); }
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const wheel = (e: WheelEvent) => {
      if (!active && !e.ctrlKey && !e.metaKey) return; // the page scrolls until the globe is clicked
      e.preventDefault();
      setK(state.current.k * Math.exp(-e.deltaY * 0.002));
    };
    c.addEventListener("wheel", wheel, { passive: false });
    return () => c.removeEventListener("wheel", wheel);
  }, [active]);
  function onPointerDown(e: React.PointerEvent<HTMLCanvasElement>) {
    setActive(true);
    const s = state.current;
    s.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (s.pointers.size === 2) { const [a, b] = [...s.pointers.values()]; s.pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), k: s.k }; s.drag = null; }
    else s.drag = { x: e.clientX, y: e.clientY, moved: false };
    s.fly = null;
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }
  function onPointerMove(e: React.PointerEvent<HTMLCanvasElement>) {
    const s = state.current;
    if (s.pointers.has(e.pointerId)) s.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (s.pinch && s.pointers.size === 2) { const [a, b] = [...s.pointers.values()]; setK((s.pinch.k * Math.hypot(a.x - b.x, a.y - b.y)) / s.pinch.d); return; }
    if (s.drag) {
      const dx = e.clientX - s.drag.x, dy = e.clientY - s.drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) s.drag.moved = true;
      s.drag.x = e.clientX; s.drag.y = e.clientY;
      const f = 0.32 / s.k;
      s.rot = [s.rot[0] + dx * f, Math.max(-80, Math.min(80, s.rot[1] - dy * f)), 0];
      pause();
      return;
    }
    const found = pick(e.clientX, e.clientY);
    if (found !== s.hover) setHover(found);
    e.currentTarget.style.cursor = found ? "pointer" : "grab";
  }
  function onPointerUp(e: React.PointerEvent<HTMLCanvasElement>) {
    const s = state.current, drag = s.drag;
    s.pointers.delete(e.pointerId);
    if (s.pointers.size < 2) s.pinch = null;
    s.drag = null;
    if (drag && !drag.moved) {
      const found = pick(e.clientX, e.clientY);
      if (found) flyTo(found); else setSelected("");
    }
  }
  const tipCountry = points.find((p) => p.country === (hover || selected));
  return (
    <section className="members-map">
      <div className="map-toolbar">
        <label className="meeting-filter">Professional experience<select value={stage} onChange={(e) => setStage(e.target.value)}><option value="">All levels</option>{stages.map((s) => <option key={s}>{s}</option>)}<option>Not stated</option></select></label>
        {genderOf && <label className="meeting-filter">Gender<select value={gender} onChange={(e) => setGender(e.target.value)}><option value="">All</option>{genders.map((s) => <option key={s}>{s}</option>)}<option>Not stated</option></select></label>}
        <span className="micro map-count"><strong>{filtered.length}</strong> {filtered.length === 1 ? "member" : "members"} · {points.length} {points.length === 1 ? "country" : "countries"}</span>
      </div>
      <div className="map-layout">
        <div className="map-frame">
          <div className={"globe-card" + (active ? " active" : "")} ref={wrapRef} onMouseLeave={() => { setActive(false); setHover(""); }}>
            <canvas ref={canvasRef} role="img" aria-label={`Rotating globe showing ${filtered.length} members in ${points.length} countries: ${points.map((p) => `${p.label} ${p.count}`).join(", ")}`}
              onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}
              onDoubleClick={() => setK(state.current.k * 1.6)} />
            <div className="globe-tip" ref={tipRef} aria-hidden="true">
              {tipCountry && <><strong>{tipCountry.label}</strong><span>{tipCountry.count} {tipCountry.count === 1 ? "member" : "members"}</span>
                {tipCountry.genders && tipCountry.genders.length > 0 && <span className="globe-tip-genders">{tipCountry.genders.map(([g, n]) => `${g} ${n}`).join(" · ")}</span>}</>}
            </div>
            {genderRows.length > 0 && (
              <div className="globe-gender" aria-label="Gender representation">
                <span className="globe-gender-title">Gender representation</span>
                <div className="gender-stack">{genderRows.map(([g, n], i) => <span key={g} className={"g" + (i % 5)} style={{ width: pct(n) + "%" }} />)}</div>
                <ul>{genderRows.map(([g, n], i) => <li key={g}><i className={"g" + (i % 5)} />{g} <b>{pct(n)}%</b></li>)}</ul>
              </div>
            )}
            <div className="globe-controls" role="group" aria-label="Globe controls">
              <button type="button" aria-label={spinning ? "Stop the rotation" : "Rotate the globe"} title={spinning ? "Stop the rotation" : "Rotate"} onClick={() => setSpinning(!spinning)}>{spinning ? <Pause size={16} /> : <Play size={16} />}</button>
              <button type="button" aria-label="Zoom in" title="Zoom in" onClick={() => setK(state.current.k * 1.5)} disabled={zoom >= MAX_K}><Plus size={18} /></button>
              <button type="button" aria-label="Zoom out" title="Zoom out" onClick={() => setK(state.current.k / 1.5)} disabled={zoom <= MIN_K}><Minus size={18} /></button>
              <button type="button" aria-label="Reset the view" title="Reset" onClick={() => { state.current.k = 1; setZoom(1); setSelected(""); state.current.fly = { from: [state.current.rot[0], state.current.rot[1]], to: [-12, -28], start: performance.now() }; }}><RotateCcw size={16} /></button>
            </div>
            <span className="globe-hint">{active ? "Drag to turn · scroll to zoom · click a country to see its members" : "Drag to turn the globe · click a country to see its members"}</span>
          </div>
          <p className="map-disclaimer">{disclaimer}</p>
        </div>
        <aside className="map-side">
          {selected && (() => {
            const here = filtered.filter((m) => countryKey(m.country || "") === selected), label = points.find((p) => p.country === selected)?.label || selected;
            return (
              <div className="map-here">
                <h3>Members in {label}</h3>
                <div className="map-here-list">{here.slice(0, 12).map((m) => (
                  <button key={m.id} type="button" onClick={() => onOpenProfile?.(m)} disabled={!onOpenProfile} title={"Open the profile of " + m.name}>
                    <MemberAvatar name={m.name} uid={m.id} hasPhoto={m.hasPhoto} version={m.updatedAt} />
                    <span><b>{m.name}</b><small>{m.headline || m.organisation || ""}</small></span>
                  </button>))}</div>
                {here.length > 12 && <p className="micro">and {here.length - 12} more</p>}
              </div>
            );
          })()}
          <div className="map-wg-legend" aria-label="Colours of the Working Groups">{groups.map((g) => <span key={g.id}><i style={{ background: g.color }} />WG{g.id}</span>)}</div>
          <h3>Countries</h3>
          <ol className="map-countries">
            {points.slice(0, 12).map((p) => (
              <li key={p.country} className={hover === p.country || selected === p.country ? "on" : ""} onMouseEnter={() => setHover(p.country)} onMouseLeave={() => setHover("")}>
                <button type="button" onClick={() => flyTo(p.country)} title={"Turn the globe to " + p.label}>{p.label}</button>
                <span className="bar"><span style={{ width: (p.count / max) * 100 + "%" }} /></span><b>{p.count}</b>
              </li>
            ))}
          </ol>
          {points.length > 12 && <p className="micro">and {points.length - 12} more countries</p>}
          {unplaced.length > 0 && <p className="micro">Not on the map: {unplaced.map(([c, n]) => `${c} (${n})`).join(", ")}</p>}
          <h3>Gender representation</h3>
          {genderRows.length ? (
            <>
              <ul className="map-stages gender-legend">
                {genderRows.map(([g, n], i) => <li key={g}><span><i className={"g" + (i % 5)} />{g}</span><b>{n} · {pct(n)}%</b></li>)}
              </ul>
              <p className="micro">{genderOf ? "For the profiles shown. Gender answers are private; only totals are displayed." : `All ${genderTotals?.total || genderTotal} registered members, as totals only. Gender answers are private.`}</p>
            </>
          ) : <p className="micro">Totals appear once the UNESCO Secretariat has opened the Dashboard or this map.</p>}
          <h3>Professional experience</h3>
          <ul className="map-stages">{stageTotals.map(([s, n]) => <li key={s}><span>{s}</span><b>{n}</b></li>)}</ul>
          {note && <p className="micro">{note}</p>}
        </aside>
      </div>
    </section>
  );
}
