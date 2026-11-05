import { broadGroupBadge, editorialBadgeIds } from "@/lib/member-roles";
import {groups} from '@/lib/data';

export function MemberBadges({
  badges = [],
  compact = false,
}: {
  badges?: { id: string; label: string; group: string }[];
  compact?: boolean;
}) {
  const publicBadges = [...new Map(badges.filter((b) => !editorialBadgeIds.includes(b.id)).map((b) => [b.label, b])).values()];
  const all = publicBadges.length ? publicBadges : [broadGroupBadge];
  const shown = compact ? all.slice(0, 3) : all;
  return (
    <div className="member-badges" aria-label="Secretariat-assigned badges">
      {shown.map((b) => {
        const group=groups.find(g=>b.id.startsWith(`wg${g.id}-`));
        const framed=!!group && /-(lead|associate|core)$/.test(b.id);
        const broad=!!group && b.id.endsWith("-member");
        return (
        <span
          key={b.id}
          className={
            "member-badge " +
            (b.id === "unesco-secretariat" ? "unesco" : b.id === broadGroupBadge.id ? "neutral" : b.id.startsWith("wg") ? b.id.slice(0, 3) : "committee") + (framed ? " wg-frame" : "") + (broad ? " wg-broad" : "") + (b.id.endsWith("-core") ? " wg-core" : "")
          }
          title={group ? `${b.label} · ${group.title}` : undefined}
          style={group?{'--wg-color':group.color,'--wg-ink':group.ink} as React.CSSProperties:undefined}
        >
          {b.label}
        </span>
      );})}
      {compact && all.length > 3 && (
        <span
          className="member-badge neutral"
          title={all
            .slice(3)
            .map((b) => b.label)
            .join(", ")}
        >
          +{all.length - 3}
        </span>
      )}
    </div>
  );
}
