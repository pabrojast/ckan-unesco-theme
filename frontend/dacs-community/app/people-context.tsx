import { createContext, useContext } from "react";
import { MemberAvatar } from "./member-avatar";

/** Profiles loaded for the signed-in member, shared with components that only need a name. */
export const PeopleContext = createContext<any[]>([]);
export const usePeople = () => useContext(PeopleContext);
export function usePerson(uid?: string) {
  const people = usePeople();
  return uid ? people.find((p) => p.id === uid) : undefined;
}

const when = (v?: string) => {
  if (!v) return "";
  const d = new Date(v.length === 10 ? v + "T12:00:00Z" : v);
  return Number.isFinite(d.getTime()) ? d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";
};

/** "Created by …" line with the person's avatar, used on news, events, polls, activities, tasks and projects. */
export function CreatedBy({ uid, verb = "Created by", at, compact = false, fallback = "a member" }: { uid?: string; verb?: string; at?: string; compact?: boolean; fallback?: string }) {
  const p = usePerson(uid);
  const name = p?.name || fallback;
  return (
    <span className={"created-by" + (compact ? " compact" : "")} title={`${verb} ${name}${at ? " · " + when(at) : ""}`}>
      <MemberAvatar name={name} uid={uid} hasPhoto={p?.hasPhoto} version={p?.updatedAt} />
      <span>{verb} <b>{name}</b>{at && !compact ? <> · {when(at)}</> : null}</span>
    </span>
  );
}
