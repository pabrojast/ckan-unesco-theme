import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { ArrowRight, BadgeCheck } from "lucide-react";
import { groups } from "@/lib/data";
import type { Application } from "@/lib/applications";
import { MemberLanyard, useLanyardSpace } from "./member-lanyard";
import { snowBurst } from "./fx";

/**
 * Shown once, at the member's next visit, after their application to a Broad Group was approved: their badge drops in
 * on its lanyard, the new Broad Group badge is stamped, and snow crystals fall in the colour of the Working Group.
 */
export function ApprovalCelebration({ person, app, onClose, onOpenGroup }: { person: any; app: Application; onClose: () => void; onOpenGroup: (n: number) => void }) {
  const n = Number(app.body.slice(2)), g = groups[n - 1] || groups[0];
  const wide = useLanyardSpace(), card = useRef<HTMLDivElement>(null), first = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    first.current?.focus();
    const t = window.setTimeout(() => {
      const r = card.current?.getBoundingClientRect();
      snowBurst([g.color, g.ink], { origin: r ? { x: r.left + r.width / 2, y: r.top + 150 } : undefined, count: 110 });
    }, 650);
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", key);
    return () => { window.clearTimeout(t); window.removeEventListener("keydown", key); };
  }, []);
  return createPortal(
    <div className={"celebrate" + (wide ? " wide" : "")} style={{ "--wg-color": g.color, "--wg-ink": g.ink } as React.CSSProperties}>
      <div className="celebrate-backdrop" onClick={onClose} />
      <div className="celebrate-card" ref={card} role="dialog" aria-modal="true" aria-labelledby="celebrate-title">
        <span className="celebrate-kicker"><BadgeCheck size={15} /> Application approved</span>
        <h2 id="celebrate-title">Welcome to the WG{n} Broad Group</h2>
        <p className="celebrate-group">{g.title}</p>
        <div className="celebrate-stamp" aria-hidden="true"><span className="stamp-ring" /><span className="stamp-badge">Broad Group member of WG{n}</span></div>
        <p>Your application has been approved. You now appear in the Broad Group of the Working Group and receive its Broad Group emails.</p>
        <div className="celebrate-actions">
          <button ref={first} type="button" className="btn primary" onClick={() => { onClose(); onOpenGroup(n); }}>Open the WG{n} page <ArrowRight size={15} /></button>
          <button type="button" className="btn" onClick={onClose}>Close</button>
        </div>
      </div>
      {wide && <MemberLanyard person={person} accent={{ color: g.color, ink: g.ink }} anchorX={0.74} className="celebrate-lanyard" hint={false} />}
    </div>,
    document.body,
  );
}
