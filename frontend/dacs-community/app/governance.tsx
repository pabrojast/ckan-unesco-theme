import { useState } from "react";
import { ArrowRight, Ban, ChevronRight, FolderOpen, KeyRound, ShieldCheck, Trash2, Users } from "lucide-react";
import { RemoveMemberDialog, ResetPasswordDialog } from "./account-tools";
import { GovernanceChart } from "./governance-chart";
import { PhotoBackdrop } from "./photo";
import { bodySpaces } from "@/lib/body-spaces";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { appointmentSeats, appointmentIds, appointmentBadge, isAppointmentBadge, singleSeat } from "@/lib/governance-seats";
import { bodies, emptyBody } from "@/lib/profile-options";
import { ProfileEditor, OptionQuestion } from "./profile-editor";
import { MemberBadges } from "./member-badges";
import { badgeOptions } from "@/lib/member-roles";
import { MemberAvatar } from "./member-avatar";
import { useMemberAuth } from "./auth";
import { isPlatformOwner } from "@/lib/firebase";
import {groups,regions} from '@/lib/data';
import {GoalPicker} from './goal-picker';
import {linkedGroups} from '@/lib/decade-goals';
import { bodyLabel, logoReviewOptions } from "@/lib/meetings";
const logoLabel = (b: string) => (/^wg[1-5]$/.test(b) ? `WG${b.slice(2)} · ${groups[Number(b.slice(2)) - 1].title}` : bodyLabel(b));
type Mutate = (payload: any, success: string) => Promise<boolean>;
const seatPosition: Record<string, string> = { lead: "lead", associateLeads: "associate", secretariat: "secretariat", core: "core" };
/** Appointments of a body. Includes members appointed in Governance and members given the role in the Secretariat panel. */
export function GovernanceSeats({
  body,
  people,
  onOpenProfile,
}: {
  body: any;
  people: any[];
  onOpenProfile?: (person: any) => void;
}) {
  const group=groups.find(g=>body.id===`wg${g.id}`);
  return (
    <div className={'governance-seats seat-grid '+(group?'wg-seats':'')} style={group?{'--wg-color':group.color} as React.CSSProperties:undefined}>
      {appointmentSeats(body.id).map((seat) => {
        const badge = `${body.id}-${seatPosition[seat.field]}`;
        const ids = [...new Set([...(appointmentIds(body, seat) as string[]),
          ...people.filter((p) => (p.assignedBadgeIds || []).includes(badge)).map((p) => p.id)])];
        return (
        <div className={"seat-box seat-" + seat.field + (ids.length ? "" : " empty")} key={seat.field}>
          <div className="seat-label"><strong>{seat.label}</strong>{ids.length > 1 && <span className="seat-count">{ids.length}</span>}</div>
          {ids.length ? (
            <div className="seat-people">{ids.map((uid) => {
              const person = people.find((p) => p.id === uid);
              const inner = <>
                <MemberAvatar name={person?.name || "?"} uid={person?.id} hasPhoto={person?.hasPhoto} version={person?.updatedAt} />
                <span className="seat-person-text"><strong>{person?.name || "Member profile is private"}</strong>{person && (person.headline || person.organisation) && <small>{[person.headline, person.organisation].filter(Boolean).join(" · ")}</small>}</span>
              </>;
              return person && onOpenProfile
                ? <button type="button" className="seat-person" key={uid} onClick={() => onOpenProfile(person)} aria-label={"View the profile of " + person.name}>{inner}<ChevronRight size={15} className="seat-chevron" aria-hidden="true" /></button>
                : <div className={"seat-person" + (person ? "" : " private")} key={uid}>{inner}</div>;
            })}</div>
          ) : (
            <span className="seat-empty">Appointment pending</span>
          )}
        </div>
      );})}
    </div>
  );
}
/** Community-visible profiles holding UNESCO Secretariat access. */
export function UnescoMembers({ people, onOpenProfile }: { people: any[]; onOpenProfile?: (person: any) => void }) {
  const members = people.filter((p: any) => p.admin);
  return <div className="seat-people unesco-people">{members.map((p:any)=>{
    const inner=<><MemberAvatar name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt}/>
      <span className="seat-person-text"><strong>{p.name}</strong><small>{[p.headline,p.organisation].filter(Boolean).join(" · ")}</small></span></>;
    return onOpenProfile
      ? <button type="button" className="seat-person" key={p.id} onClick={()=>onOpenProfile(p)} aria-label={"View the profile of "+p.name}>{inner}<ChevronRight size={15} className="seat-chevron" aria-hidden="true"/></button>
      : <div className="seat-person" key={p.id}>{inner}</div>;
  })}{!members.length&&<p className="micro">No community-visible UNESCO Secretariat profiles.</p>}</div>;
}
const seatCount = (g: any) => (g?.lead ? 1 : 0) + (g?.secretariat?.length || 0) + (g?.associateLeads?.length || 0) + (g?.core?.length || 0);
/** Cards opening the space of each governing body. */
function BodySpaceCards({ data, canDocs, onOpenSpace }: { data: any; canDocs: boolean; onOpenSpace: (id: string) => void }) {
  return <section className="body-spaces" aria-labelledby="body-spaces-title">
    <div className="section-title">
      <h2 id="body-spaces-title">Spaces of the governing bodies</h2>
      {canDocs && <span className="micro">Each space links to its working documents on SharePoint.</span>}
    </div>
    <div className="group-cards body-cards">{bodySpaces.map((b) => {
      const g = data.governance?.find((x: any) => x.id === b.id);
      const count = b.id === "unesco" ? data.people.filter((p: any) => p.admin).length : seatCount(g);
      return <section className="glass group-card body-card clickable-card" key={b.id} style={{ "--wg-color": b.color, "--wg-ink": b.color } as React.CSSProperties}>
        <div className="group-card-band has-photo">
          <PhotoBackdrop photo={b.photo} sizes="(max-width: 800px) 100vw, 480px" />
          <span className="wg-label"><small>{b.id === "unesco" ? "Host of the Secretariat" : "Governing body"}</small><span className="big-number">{b.short}</span></span>
          {canDocs && b.folder && <span className="docs-chip"><FolderOpen size={12} />Working documents</span>}
        </div>
        <h2>{b.title}</h2>
        <p>{g?.description || b.description}</p>
        <div className="card-footer">
          <span>
            <Users size={14} />{count} {b.id === "unesco" ? (count === 1 ? "member" : "members") : count === 1 ? "appointment" : "appointments"}
          </span>
          <button className="text-button arrow stretch" onClick={() => onOpenSpace(b.id)} aria-label={"Open the space of the " + b.title}>
            Open space <ArrowRight size={14} />
          </button>
        </div>
      </section>;
    })}</div>
  </section>;
}
export function GovernanceDirectory({
  data,
  mutate,
  saving,
  onManageUnesco,
  onOpenSpace,
  onOpenProfile,
}: {
  data: any;
  mutate: Mutate;
  saving: boolean;
  onManageUnesco: () => void;
  onOpenSpace: (id: string) => void;
  onOpenProfile: (person: any) => void;
}) {
  const [edit, setEdit] = useState<any>(null);
  const [selected, setSelected] = useState("smc");
  function selection(key: string, label: string, multiple = true) {
    const listField = key !== "lead";
    const selectedValue = multiple ? edit[key] : listField ? edit[key]?.[0] || "" : edit[key];
    return (
      <div className="field">
        <label htmlFor={"board-" + key}>{label}</label>
        <select
          id={"board-" + key}
          multiple={multiple}
          value={selectedValue}
          onChange={(e) =>
            setEdit({
              ...edit,
              [key]: multiple
                ? Array.from(e.target.selectedOptions).map((x) => x.value)
                : listField ? (e.target.value ? [e.target.value] : []) : e.target.value,
            })
          }
        >
          {!multiple && <option value="">Appointment pending</option>}
          {data.people.map((p: any) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        {multiple && (
          <small>Use Ctrl or Command to select more than one member.</small>
        )}
      </div>
    );
  }
  return (
    <>
      <GovernanceChart selected={selected} onSelect={setSelected} />
      <section className={'glass panel governance-appointments '+(selected.startsWith('wg')?'wg-appointments':'')} style={selected.startsWith('wg')?{'--wg-color':groups[Number(selected.slice(2))-1]?.color} as React.CSSProperties:undefined}>
        <label className="field">
          <span>Appointments</span>
          <select aria-label="Governance body" value={selected} onChange={e=>setSelected(e.target.value)}>
            <option value="unesco">UNESCO Secretariat</option>
            {bodies.map(b=><option key={b.id} value={b.id}>{b.title}</option>)}
          </select>
        </label>
        {selected === "unesco" ? <>
          <div className="section-title"><h2>UNESCO Secretariat</h2>
            <div className="row">
              {data.admin && <button className="btn small" onClick={onManageUnesco}>Manage UNESCO access</button>}
              <button className="btn small" onClick={() => onOpenSpace("unesco")}>Open space <ArrowRight size={14} /></button>
            </div>
          </div>
          <p className="micro">UNESCO–IHP hosts the Secretariat. These members hold full platform editing access.</p>
          <UnescoMembers people={data.people} onOpenProfile={onOpenProfile} />
        </> : bodies.filter(base=>base.id===selected).map(base=>{
          const body={...emptyBody,...base,...data.governance?.find((x:any)=>x.id===base.id)};
          return <div key={base.id}>
            <div className="section-title"><h2>{body.title}</h2><div className="row">{data.admin&&<button className="btn small" onClick={()=>setEdit(body)}>Edit appointments</button>}<button className="btn small" onClick={()=>onOpenSpace(base.id)}>Open space <ArrowRight size={14} /></button></div></div>
            {body.description&&<p>{body.description}</p>}
            <GovernanceSeats body={body} people={data.people} onOpenProfile={onOpenProfile}/>
          </div>;
        })}
      </section>
      <BodySpaceCards data={data} canDocs={data.canAccessWorkspace === true} onOpenSpace={onOpenSpace} />
      <Dialog open={!!edit} onOpenChange={(v) => !v && setEdit(null)}>
        <DialogContent className="detail-content">
          <DialogTitle>Edit {edit?.title}</DialogTitle>
          <DialogDescription>
            Assign registered members. Working Group appointments grant access
            to review that group’s activities and contributions. UNESCO Secretariat
            editing access is assigned separately.
          </DialogDescription>
          {edit && (
            <form
              className="stack"
              onSubmit={async (e) => {
                e.preventDefault();
                if (
                  await mutate(
                    { action: "governance", id: edit.id, body: edit },
                    "Appointments saved.",
                  )
                )
                  setEdit(null);
              }}
            >
              <div className="field">
                <label htmlFor="board-title">Title</label>
                <input
                  id="board-title"
                  value={edit.title}
                  maxLength={160}
                  onChange={(e) => setEdit({ ...edit, title: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="board-description">Description</label>
                <textarea
                  id="board-description"
                  value={edit.description}
                  maxLength={1500}
                  onChange={(e) =>
                    setEdit({ ...edit, description: e.target.value })
                  }
                />
              </div>
              {appointmentSeats(edit.id).map((seat) => <div key={seat.field}>{selection(seat.field, seat.label, seat.multiple)}</div>)}
              <button className="btn primary" disabled={saving}>
                Save appointments
              </button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
export function SecretariatPanel({
  data,
  categories,
  mutate,
  saving,
}: {
  data: any;
  categories: any[];
  mutate: Mutate;
  saving: boolean;
}) {
  const { user } = useMemberAuth();
  const [tab, setTab] = useState("members"),
    [profile, setProfile] = useState<any>(null),
    [edit, setEdit] = useState<any>(null),
    [search, setSearch] = useState(""),
    [access, setAccess] = useState<any>(null),
    [bannedOnly, setBannedOnly] = useState(false),
    [resetFor, setResetFor] = useState<any>(null),
    [removeFor, setRemoveFor] = useState<any>(null);
  const bannedCount = data.people.filter((p: any) => p.banned).length;
  const tabs = [
    "members",
    "activities",
    "updates",
    "contributions",
    "categories",
  ];
  const all =
    tab === "members"
      ? data.people
      : tab === "activities"
        ? data.opportunities
        : tab === "updates"
          ? data.posts
          : tab === "contributions"
            ? data.contributions
            : categories;
  const records = all.filter((r: any) => (tab !== "members" || !bannedOnly || r.banned)).filter((r: any) =>
    [r.name, r.title, r.body, r.label, r.member_name, r.opportunity_title]
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  // Groups holding a role open when the dialog opens.
  function openAccess(a: any, _initial: boolean) {
    setAccess({ ...a, openGroups: badgeOptions.filter((b) => a.badges.includes(b.id)).map((b) => b.group) });
  }
  async function remove(collection: string, r: any) {
    if (
      window.confirm(
        "Remove this record and its linked community data? This cannot be undone.",
      )
    )
      await mutate(
        { action: "adminDelete", collection, id: r.id },
        "Record removed.",
      );
  }
  function editField(key: string, label: string, area = false, max = 3000) {
    return (
      <div className="field">
        <label htmlFor={"content-" + key}>{label}</label>
        {area ? (
          <textarea
            id={"content-" + key}
            value={edit.record[key] || ""}
            maxLength={max}
            onChange={(e) =>
              setEdit({
                ...edit,
                record: { ...edit.record, [key]: e.target.value },
              })
            }
          />
        ) : (
          <input
            id={"content-" + key}
            value={edit.record[key] || ""}
            maxLength={max}
            onChange={(e) =>
              setEdit({
                ...edit,
                record: { ...edit.record, [key]: e.target.value },
              })
            }
          />
        )}
      </div>
    );
  }
  function editSelect(key: string, label: string, values: string[]) {
    return (
      <div className="field">
        <label htmlFor={"content-" + key}>{label}</label>
        <select
          id={"content-" + key}
          value={edit.record[key]}
          onChange={(e) =>
            setEdit({
              ...edit,
              record: { ...edit.record, [key]: e.target.value },
            })
          }
        >
          {values.map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </div>
    );
  }
  return (
    <section className="glass panel">
      <ResetPasswordDialog member={resetFor} onClose={() => setResetFor(null)} />
      <RemoveMemberDialog member={removeFor} onClose={() => setRemoveFor(null)}
        removeData={(m) => mutate({ action: "adminDelete", collection: "profiles", id: m.id }, (m.name || "The member") + "'s data has been removed.")} />
      <div
        className="toolbar admin-tabs"
        role="tablist"
        aria-label="Content types"
      >
        {tabs.map((t) => (
          <button
            className={"btn small " + (tab === t ? "primary" : "")}
            role="tab"
            aria-selected={tab === t}
            key={t}
            onClick={() => {
              setTab(t);
              setSearch("");
            }}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="field">
        <label htmlFor="admin-search">Search loaded records</label>
        <input
          id="admin-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {tab === "members" && (
        <label className="checkline banned-filter">
          <input type="checkbox" checked={bannedOnly} onChange={(e) => setBannedOnly(e.target.checked)} />
          Show banned accounts only ({bannedCount})
        </label>
      )}
      {records.map((r: any) => (
        <article className="admin-row" key={r.id}>
          <h3>
            {r.name ||
              r.title ||
              r.label ||
              r.opportunity_title ||
              r.author_name}
          </h3>
          {tab === "members" ? (
            <>
              <div className="row">
                <MemberAvatar
                  name={r.name}
                  uid={r.id}
                  hasPhoto={r.hasPhoto}
                  version={r.updatedAt}
                />
                <span className="micro">{r.headline}</span>
                <button className="btn small" onClick={() => setProfile(r)}>
                  Edit profile
                </button>
                <button className="btn small" disabled={saving} onClick={() => setResetFor(r)} title="Create a password reset link to send to this member">
                  <KeyRound size={14} /> Reset password
                </button>
                <button
                  className="text-button danger"
                  disabled={saving || r.id === user?.uid}
                  onClick={() => setRemoveFor(r)}
                >
                  <Trash2 size={14} /> Remove member
                </button>
                {r.banned ? (
                  <button className="btn small" disabled={saving} onClick={() => mutate({ action: "unban", id: r.id }, r.name + " can use the platform again.")}>
                    <ShieldCheck size={14} /> Unban
                  </button>
                ) : (
                  <button className="btn small ban-button" disabled={saving || r.id === user?.uid || r.admin}
                    title={r.admin ? "Remove UNESCO Secretariat access before banning this account" : "Suspend this account"}
                    onClick={() => window.confirm(`Ban ${r.name}? The account will lose access to the platform, including messages, until you unban it. The member is hidden from other members and removed from the mailing lists.`) && mutate({ action: "ban", id: r.id }, r.name + " has been banned.")}>
                    <Ban size={14} /> Ban
                  </button>
                )}
              </div>
              {r.banned && <p className="banned-flag"><Ban size={13} /> Banned · no access to the platform and hidden from other members</p>}
              <MemberBadges badges={r.membershipBadges} compact />
              <button
                className="btn small access-button"
                onClick={() =>
                  openAccess({
                    ...r,
                    // Appointments made in Governance show as ticked roles and can be changed here.
                    badges: [...new Set([...(r.assignedBadgeIds || []),
                      ...(r.membershipBadges || []).map((b: any) => b.id).filter(isAppointmentBadge)])],
                    wgs: r.directWgs || [],
                    logoReview: r.logoReview || [],
                  }, true)
                }
              >
                Manage access & badges
              </button>
            </>
          ) : tab === "categories" ? (
            <div className="row">
              <span className="pill">{r.kind}</span>
              <span>{r.enabled ? "Available" : "Retired"}</span>
              <button
                className="btn small"
                disabled={saving}
                onClick={() =>
                  mutate(
                    { action: "categoryStatus", id: r.id, enabled: !r.enabled },
                    "Shared option updated.",
                  )
                }
              >
                {r.enabled ? "Retire option" : "Restore option"}
              </button>
            </div>
          ) : (
            <>
              <p>{r.body || r.description || r.message}</p>
              <div className="row">
                <span className="pill">{r.status || "Published update"}</span>
                <button
                  className="btn small"
                  onClick={() =>
                    setEdit({
                      collection:
                        tab === "activities"
                          ? "opportunities"
                          : tab === "updates"
                            ? "posts"
                            : "contributions",
                      record: { ...r },
                    })
                  }
                >
                  Edit
                </button>
                <button
                  className="text-button danger"
                  disabled={saving}
                  onClick={() =>
                    remove(
                      tab === "activities"
                        ? "opportunities"
                        : tab === "updates"
                          ? "posts"
                          : "contributions",
                      r,
                    )
                  }
                >
                  Remove
                </button>
              </div>
            </>
          )}
        </article>
      ))}
      {!records.length && (
        <p className="empty-state">No records in this view.</p>
      )}
      <Dialog open={!!access} onOpenChange={(v) => !v && setAccess(null)}>
        <DialogContent className="detail-content access-dialog">
          <DialogTitle>Access & badges · {access?.name}</DialogTitle>
          <DialogDescription>
            Tick a role to appoint this member. Lead, Associate Lead, Secretariat
            and Core Group roles are added to the appointments under Governance
            and on the group's page; unticking removes them.
          </DialogDescription>
          {access && (
            <form
              className="stack"
              onSubmit={async (e) => {
                e.preventDefault();
                const before = data.people.find((p: any) => p.id === access.id);
                if (
                  access.role === "unesco-secretariat" &&
                  !before?.admin &&
                  !window.confirm(
                    "Assign UNESCO Secretariat with full editing access to " +
                      access.name +
                      "?",
                  )
                )
                  return;
                if (
                  await mutate(
                    {
                      action: "role",
                      id: access.id,
                      role: access.role || "member",
                      wgs: access.wgs,
                      admin: access.admin,
                      badges: access.badges,
                      logoReview: access.logoReview || [],
                    },
                    "Access and badges saved.",
                  )
                )
                  setAccess(null);
              }}
            >
              <div className="access-fields">
                <label>
                  Editorial access role
                  <select
                    aria-label={"Editorial access role for " + access.name}
                    value={access.role || "member"}
                    disabled={access.id === user?.uid && isPlatformOwner(user)}
                    onChange={(e) => {
                      const unesco=e.target.value === "unesco-secretariat";
                      setAccess({ ...access, role: e.target.value, admin: unesco,
                        badges: unesco ? [...new Set(["unesco-secretariat", ...access.badges])] : access.badges.filter((id:string)=>id!=="unesco-secretariat") });
                    }}
                  >
                    {[
                      ["member", "Member"],
                      ["core", "Core Group"],
                      ["lead", "Lead"],
                      ["associate", "Associate Lead"],
                      ["secretariat", "WG / body Secretariat"],
                      ["unesco-secretariat", "UNESCO Secretariat · full editing"],
                    ].map(([id, label]) => (
                      <option key={id} value={id}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="micro">Only UNESCO Secretariat receives full editing. WG and body Secretariats retain scoped access.</p>
              </div>
              <section className="badge-editor">
                <h3>Official Decade badges</h3>
                {[...new Set(badgeOptions.map((b) => b.group))].map((group) => (
                  <details key={group} className="badge-group" open={(access.openGroups || []).includes(group) || undefined}>
                    <summary>{group}</summary>
                    <div className="badge-choices">
                      {badgeOptions
                        .filter((b) => b.group === group)
                        .map((b) => {
                          const seat = appointmentBadge(b.id);
                          const record = seat ? { ...(data.governance || []).find((g: any) => g.id === seat.body) } : null;
                          const holders = seat && record ? (seat.field === "lead" ? [record.lead].filter(Boolean) : record[seat.field] || []) : [];
                          const others = holders.filter((id: string) => id !== access.id);
                          const replaces = seat && singleSeat(seat.body, seat.field) && access.badges.includes(b.id) && others.length > 0;
                          const nameOf = (id: string) => data.people.find((p: any) => p.id === id)?.name || "a member with a private profile";
                          return (
                            <label className={"checkline" + (seat ? " appointment" : "")} key={b.id}>
                              <input
                                type="checkbox"
                                aria-label={b.label}
                                checked={access.badges.includes(b.id)}
                                disabled={
                                  saving || b.id === "unesco-secretariat"
                                }
                                onChange={(e) => {
                                  if (
                                    e.target.checked && !isAppointmentBadge(b.id) &&
                                    access.badges.filter((id: string) => !isAppointmentBadge(id)).length >= 20
                                  )
                                    return;
                                  setAccess({
                                    ...access,
                                    badges: e.target.checked
                                      ? [...access.badges, b.id]
                                      : access.badges.filter(
                                          (id: string) => id !== b.id,
                                        ),
                                  });
                                }}
                              />
                              <span>
                                {b.label}{b.id === "esc-lead" ? " · seat 1" : b.id === "esc-associate" ? " · seat 2" : ""}
                                {seat && <span className="appointment-tag">Appointment</span>}
                                {replaces && <small className="seat-note">Replaces {others.map(nameOf).join(", ")} in this seat</small>}
                                {seat && !replaces && others.length > 0 && !access.badges.includes(b.id) && singleSeat(seat.body, seat.field) && (
                                  <small className="seat-note muted">Currently {others.map(nameOf).join(", ")}</small>
                                )}
                              </span>
                            </label>
                          );
                        })}
                    </div>
                  </details>
                ))}
                <p className="micro">
                  Core Group, Lead, Associate Lead and Secretariat roles can see
                  workspace links. Review permissions are separate.
                </p>
              </section>
              <details className="badge-group" open={(access.logoReview || []).length > 0 || undefined}>
                <summary>Logo review access</summary>
                <div className="badge-choices">
                  <p className="micro">
                    Lets this member open “Logo review” and give the opinion of the body ticked below on the logo requests
                    assigned to it. Appointments in Governance do not grant this access: it is given here only.
                  </p>
                  {logoReviewOptions.map((b) => (
                    <label className="checkline" key={b}>
                      <input
                        type="checkbox"
                        checked={(access.logoReview || []).includes(b)}
                        onChange={(e) =>
                          setAccess({
                            ...access,
                            logoReview: e.target.checked
                              ? [...new Set([...(access.logoReview || []), b])]
                              : (access.logoReview || []).filter((x: string) => x !== b),
                          })
                        }
                      />
                      {logoLabel(b)}
                    </label>
                  ))}
                </div>
              </details>
              {access.wgs?.length > 0 && (
                <div className="legacy-access">
                  <p className="micro">
                    This member still holds the former “Working Group review access” for {access.wgs.map((n: number) => "WG" + n).join(", ")}.
                    It lets them publish the activities of {access.wgs.length === 1 ? "this group" : "these groups"} and,
                    with a Lead, Associate Lead, Secretariat or Core Group role above, gives them that role in {access.wgs.length === 1 ? "it" : "them"}.
                  </p>
                  <button type="button" className="btn small" onClick={() => setAccess({ ...access, wgs: [] })}>Remove the former access</button>
                </div>
              )}
              <button className="btn primary" disabled={saving}>
                Save access & badges
              </button>
            </form>
          )}
        </DialogContent>
      </Dialog>
      <Dialog open={!!profile} onOpenChange={(v) => !v && setProfile(null)}>
        <DialogContent className="detail-content">
          <DialogTitle>Edit {profile?.name}</DialogTitle>
          <DialogDescription>
            UNESCO Secretariat changes are subject to the same profile validation and
            visibility settings.
          </DialogDescription>
          {profile && (
            <ProfileEditor
              key={profile.id}
              initial={profile}
              categories={categories}
              saving={saving}
              adminEditing
              onSave={async (p) => {
                const success = await mutate(
                  { action: "profile", id: profile.id, profile: p },
                  "Member profile saved.",
                );
                if (success) setProfile(null);
                return success;
              }}
            />
          )}
        </DialogContent>
      </Dialog>
      <Dialog open={!!edit} onOpenChange={(v) => !v && setEdit(null)}>
        <DialogContent className="detail-content">
          <DialogTitle>Edit community record</DialogTitle>
          <DialogDescription>
            Save corrections to this record.
          </DialogDescription>
          {edit && (
            <form
              className="stack"
              onSubmit={async (e) => {
                e.preventDefault();
                if (
                  await mutate(
                    {
                      action: "adminEdit",
                      collection: edit.collection,
                      id: edit.record.id,
                      record: edit.record,
                    },
                    "Record saved.",
                  )
                )
                  setEdit(null);
              }}
            >
              {edit.collection === "posts" ? (
                <>
                  {editField("body", "Update", true)}
                  {editSelect("wg", "Working Group", [
                    "0",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                  ])}
                </>
              ) : edit.collection === "contributions" ? (
                <>
                  {editField("message", "Contribution", true, 2000)}
                  {editSelect("status", "Status", [
                    "Interested",
                    "Shortlisted",
                    "Selected",
                    "In progress",
                    "Completed",
                    "Not selected",
                    "Withdrawn",
                  ])}
                </>
              ) : (
                <>
                  {editField("title", "Title", false, 160)}
                  {editField("description", "Description", true)}
                  <OptionQuestion
                    kind="skills"
                    label="Requested skills"
                    value={edit.record.skills}
                    onChange={(v) =>
                      setEdit({
                        ...edit,
                        record: { ...edit.record, skills: v },
                      })
                    }
                    categories={categories}
                    multiple
                  />
                  {editSelect("status", "Status", [
                    "pending",
                    "open",
                    "closed",
                  ])}
                  <GoalPicker value={edit.record.mgs || []} onChange={mgs=>{
                    const linked=linkedGroups(mgs);
                    setEdit({...edit,record:{...edit.record,mgs,wg:linked.includes(Number(edit.record.wg))?Number(edit.record.wg):linked[0] || Number(edit.record.wg)}});
                  }}/>
                  {editSelect("wg", "Reviewing Working Group", (edit.record.mgs?.length?linkedGroups(edit.record.mgs):[1,2,3,4,5]).map(String))}
                  {editSelect("region", "Region", regions)}
                  {editField("language", "Working language", false, 100)}
                  {editSelect("commitment", "Time commitment", [
                    "2–4 hours / month",
                    "4–8 hours / month",
                    "8+ hours / month",
                    "Project-based",
                    "Currently unavailable",
                  ])}
                  {editField("deadline", "Deadline (YYYY-MM-DD)", false, 10)}
                  <OptionQuestion kind="contributionTypes" label="Contribution type" value={edit.record.type} onChange={type=>setEdit({...edit,record:{...edit.record,type}})} categories={categories}/>
                </>
              )}
              <button className="btn primary" disabled={saving}>
                Save record
              </button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}
