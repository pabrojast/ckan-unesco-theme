import { useEffect, useRef } from "react";
import { Check } from "lucide-react";
import { celebrated, markCelebrated, snowBurst } from "./fx";

/** The six parts of a profile that make it useful to others, each growing one branch of the crystal. */
export function profileParts(p: any) {
  return [
    { k: "photo", label: "Photo", done: !!p?.hasPhoto, hint: "Add a photo" },
    { k: "skills", label: "Expertise", done: (p?.skills || []).length > 0, hint: "Add your expertise" },
    { k: "languages", label: "Languages", done: (p?.languages || []).length > 0, hint: "Add your languages" },
    { k: "cryo", label: "Cryosphere focus", done: (p?.cryosphereTypes || []).length > 0, hint: "Choose your cryosphere focus" },
    { k: "availability", label: "Availability", done: !!p?.availability, hint: "State your availability" },
    { k: "bio", label: "Biography", done: !!(p?.bio || "").trim(), hint: "Write a short biography" },
  ];
}

/** One arm of the crystal, pointing up; rotated for each of the six parts. */
const ARM = "M0 0 V-52 M0 -22 L-11 -33 M0 -22 L11 -33 M0 -36 L-8 -44 M0 -36 L8 -44";

/** A six-branched ice crystal on "My profile": one branch grows for each completed part, and a complete profile shimmers. */
export function ProfileCrystal({ me }: { me: any }) {
  const parts = profileParts(me), n = parts.filter((x) => x.done).length, complete = n === parts.length;
  const ref = useRef<SVGSVGElement>(null);
  useEffect(() => {
    if (!complete || !me?.id || celebrated(me.id).includes("profile-complete")) return;
    markCelebrated(me.id, ["profile-complete"]);
    const r = ref.current?.getBoundingClientRect();
    const t = window.setTimeout(() => snowBurst(["#8ed2ee", "#a0a9ff", "#82d8b7"], { origin: r ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : undefined, count: 70, duration: 3200 }), 900);
    return () => window.clearTimeout(t);
  }, [complete, me?.id]);
  return (
    <div className={"profile-crystal" + (complete ? " complete" : "")}>
      <svg ref={ref} viewBox="-64 -64 128 128" role="img" aria-label={`Profile completed: ${n} of ${parts.length} parts`}>
        <defs>
          <linearGradient id="crystal-ice" x1="0" y1="-1" x2="0" y2="0" gradientUnits="objectBoundingBox">
            <stop offset="0" stopColor="#8ed2ee" /><stop offset="1" stopColor="#0a6eb4" />
          </linearGradient>
        </defs>
        <circle r="60" className="crystal-halo" />
        {parts.map((x, i) => (
          <g key={x.k} transform={`rotate(${i * 60})`} className={"crystal-arm" + (x.done ? " done" : "")} style={{ "--i": i } as React.CSSProperties}>
            <path d={ARM} className="arm-ghost" />
            {x.done && <path d={ARM} className="arm-ice" pathLength={1} />}
          </g>
        ))}
        <polygon points="0,-9 7.8,-4.5 7.8,4.5 0,9 -7.8,4.5 -7.8,-4.5" className="crystal-core" />
        <text y="4" textAnchor="middle" className="crystal-count">{n}</text>
      </svg>
      <div className="crystal-text">
        <strong>{complete ? "Your profile is complete" : `Profile ${n} of ${parts.length}`}</strong>
        <ul>{parts.map((x) => <li key={x.k} className={x.done ? "done" : ""}>{x.done ? <Check size={12} /> : <i />}{x.done ? x.label : x.hint}</li>)}</ul>
      </div>
    </div>
  );
}
