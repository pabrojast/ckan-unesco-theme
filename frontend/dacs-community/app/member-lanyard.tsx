import { lazy, Suspense, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Hand } from "lucide-react";
import { getProfilePhoto } from "@/lib/photos";
import { paintBadge, type BadgeArt } from "./member-badge-art";

// three.js is loaded only when a profile is opened on a wide screen.
const Lanyard = lazy(() => import("@/components/lanyard/Lanyard"));

/** Wide screens only: the badge needs the space to the right of the profile window. */
const WIDE = "(min-width: 1200px)";
export function useLanyardSpace() {
  const [wide, setWide] = useState(() => typeof window !== "undefined" && window.matchMedia(WIDE).matches);
  useEffect(() => {
    const m = window.matchMedia(WIDE), on = () => setWide(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return wide;
}

/**
 * Horizontal position of the strap, as a share of the screen width: the middle of the space to the right of the
 * profile window. Keep in line with --member-w and the left margin of .member-sheet.with-lanyard in globals.css.
 */
function useBadgeAnchor() {
  const at = () => { const w = window.innerWidth, sheet = Math.min(1000, w - 380); return Math.min(0.92, (32 + sheet + w) / 2 / w); };
  const [x, setX] = useState(at);
  useEffect(() => { const on = () => setX(at()); window.addEventListener("resize", on); return () => window.removeEventListener("resize", on); }, []);
  return x;
}

/** The member's badge hanging from a lanyard on the right of their profile: logo of the Decade, photo, name and role. */
export function MemberLanyard({ person, accent, anchorX, className = "", hint = true }: { person: any; accent: { color: string; ink: string }; anchorX?: number; className?: string; hint?: boolean }) {
  const [art, setArt] = useState<BadgeArt | null>(null);
  const auto = useBadgeAnchor(), anchor = anchorX ?? auto;
  useEffect(() => {
    let live = true;
    setArt(null);
    (person.hasPhoto ? getProfilePhoto(person.id, person.updatedAt || "") : Promise.resolve(""))
      .catch(() => "")
      .then((photo) => paintBadge(person, accent, photo))
      .then((a) => live && setArt(a))
      .catch(() => {});
    return () => { live = false; };
  }, [person.id, person.name, person.headline, person.organisation, person.country, person.updatedAt, person.hasPhoto, accent.color, (person.membershipBadges || []).map((b: any) => b.id).join()]);
  return createPortal(
    <div className={"member-lanyard " + className} aria-hidden="true">
      {art && (
        <Suspense fallback={null}>
          <Lanyard key={person.id} frontImage={art.front} backImage={art.back} strapImage={art.strap}
            imageFit="cover" cardColor="#ffffff" orientation="portrait" finish="glossy" cornerRadius={0.3}
            size={0.38} anchorX={anchor} passThrough strapLength={0.5} strapColor="#0b2f4e" strapWidth={0.65} metal="silver"
            gravity={1} damping={0.5} elasticity={0.5} breeze={0.5} interactive intro />
        </Suspense>
      )}
      {art && hint && <p className="member-lanyard-hint" style={{ left: `${anchor * 100}%` }}><Hand size={13} /> Drag the badge</p>}
    </div>,
    document.body,
  );
}
