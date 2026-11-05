import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  where,
  limit,
  orderBy,
  setDoc,
  updateDoc,
  deleteDoc,
  writeBatch,
  serverTimestamp,
  Timestamp,
  onSnapshot,
} from "firebase/firestore";
import { auth, db, isPlatformOwner } from "./firebase";
import { languages, regions, normaliseRegion } from "./data";
import { linkedGroups, validGoalSelection } from "./decade-goals";
import {
  categoryKinds,
  normaliseLabel,
  CategoryKind,
  bodies,
  emptyBody,
  bodyTitle,
} from "./profile-options";
import { clearPhotoCache } from "./photos";
import { refreshMemberEntries } from "./mailing-store";
import { logoReviewOptions } from "./meetings";
import { cleanAttachments } from "./files-store";
import { saveOwnRequest, cleanClaims } from "./role-requests";
import { committeeSeatError, applyAppointments, isAppointmentBadge } from "./governance-seats";
import { assignedBadges, canSeeWorkspace, badgeIds, isUnescoSecretariat } from "./member-roles";
// IHP-WINS: the owner is a platform administrator (see isPlatformOwner in firebase.ts), not one email address.
const stamp = (v: any) =>
  v instanceof Timestamp ? v.toDate().toISOString() : v;
const unpack = (d: any): any => ({
  id: d.id,
  ...Object.fromEntries(
    Object.entries(d.data()).map(([k, v]) => [k, k === "region" ? normaliseRegion(String(v || "")) : stamp(v)]),
  ),
});
const unique = (a: any[]) => [...new Map(a.map((x) => [x.id, x])).values()];
const empty = (user: any) => ({
  me: null,
  admin: false,
  people: [],
  opportunities: [],
  contributions: [],
  posts: [],
  follows: [],
  governance: [],
  events: [],
  user: user
    ? { id: user.uid, email: user.email, name: user.displayName || "" }
    : null,
  more: {},
});
function current() {
  if (!auth?.currentUser || !db) throw Error("Sign in before saving.");
  return { u: auth.currentUser, d: db };
}
async function list(name: string, filters: any[] = [], max = 50) {
  if (!db) throw Error("Community unavailable.");
  const s = await getDocs(query(collection(db, name), ...filters, limit(max)));
  return s.docs.map(unpack);
}
async function role(uid: string) {
  if (!db) throw Error("Community unavailable.");
  const s = await getDoc(doc(db, "roles", uid));
  const r = s.exists() ? s.data() : { admin: false, role: "member", wgs: [] };
  if (
    auth?.currentUser?.uid === uid &&
    isPlatformOwner(auth.currentUser) &&
    (!s.exists() ||
      r.admin !== true ||
      r.role !== "unesco-secretariat" ||
      !(r.badges || []).includes("unesco-secretariat"))
  ) {
    await setDoc(doc(db, "roles", uid), {
      admin: true,
      role: "unesco-secretariat",
      wgs: r.wgs || [],
      badges: [...new Set(["unesco-secretariat", ...(r.badges || [])])].slice(
        0,
        20,
      ),
    });
    return {
      admin: true,
      role: "unesco-secretariat",
      wgs: r.wgs || [],
      badges: [...new Set(["unesco-secretariat", ...(r.badges || [])])].slice(
        0,
        20,
      ),
    };
  }
  return {
    ...r,
    admin:
      isUnescoSecretariat(r) ||
      (auth?.currentUser?.uid === uid &&
        isPlatformOwner(auth.currentUser)),
  };
}
const managedGroups = (uid: string, r: any, governance: any[]) => [
  ...new Set([
    ...(r.wgs || []),
    ...governance
      .filter(
        (g) =>
          g.id.startsWith("wg") &&
          (g.lead === uid ||
            [...g.secretariat, ...g.associateLeads, ...g.core].includes(uid)),
      )
      .map((g) => Number(g.id.slice(2))),
  ]),
];
export async function loadCommunity() {
  const u = auth?.currentUser;
  if (!u || !db) return empty(u);
  const [myRole, storedBoards, roles, bans] = await Promise.all([
    role(u.uid),
    list("governance", [], 10),
    list("roles", [], 100),
    list("bans", [], 500).catch(() => []),
  ]);
  const bannedIds = new Set(bans.map((b: any) => b.id));
  const governance = bodies.map((b) => ({
    ...emptyBody,
    ...b,
    ...storedBoards.find((g) => g.id === b.id),
    title: bodyTitle(b.id, storedBoards.find((g) => g.id === b.id)?.title || b.title),
  }));
  const admin = myRole.admin === true,
    managed = managedGroups(u.uid, myRole, governance);
  const [
    directory,
    own,
    ownPrivate,
    open,
    owned,
    managedOps,
    ownCs,
    managedCs,
    posts,
    prefs,
    recentEvents,
  ] = await Promise.all([
    list(
      "profiles",
      admin ? [] : [where("visibility", "==", "community")],
      100,
    ),
    getDoc(doc(db, "profiles", u.uid)),
    getDoc(doc(db, "privateProfiles", u.uid)),
    list("opportunities", [where("status", "==", "open")], 50),
    list("opportunities", [where("owner", "==", u.uid)], 50),
    admin
      ? list("opportunities", [], 100)
      : managed.length
        ? list("opportunities", [where("wg", "in", managed)], 100)
        : Promise.resolve([]),
    list("contributions", [where("member_id", "==", u.uid)], 50),
    admin
      ? list("contributions", [], 100)
      : managed.length
        ? list("contributions", [where("wg", "in", managed)], 100)
        : Promise.resolve([]),
    list("posts", [orderBy("createdAt", "desc")], 25),
    getDoc(doc(db, "preferences", u.uid)),
    list("events", [where("endAt", ">=", Timestamp.fromMillis(Date.now() - 30 * 86400000)), orderBy("endAt")], 100),
  ]);
  // Banned members are hidden from other members; the UNESCO Secretariat still sees them, marked as banned.
  let people = unique([...directory, ...(own.exists() ? [unpack(own)] : [])])
    .filter((p: any) => admin || p.id === u.uid || !bannedIds.has(p.id));
  people = await Promise.all(
    people.map(async (p) => {
      const rr =
        p.id === u.uid
          ? myRole
          : roles.find((x) => x.id === p.id) || {
              role: "member",
              wgs: [],
              admin: false,
            };
      const priv =
        admin || p.id === u.uid
          ? await getDoc(doc(db!, "privateProfiles", p.id))
          : null;
      return {
        ...p,
        ...(priv?.exists() ? unpack(priv) : {}),
        role: rr.role,
        admin: isUnescoSecretariat(rr),
        directWgs: rr.wgs || [],
        logoReview: rr.logoReview || [],
        assignedBadgeIds: rr.badges || [],
        membershipBadges: assignedBadges(p.id, rr, governance),
        managedWgs: managedGroups(p.id, rr, governance),
        banned: bannedIds.has(p.id),
      };
    }),
  );
  const me = people.find((p) => p.id === u.uid) || null;
  return {
    me,
    admin,
    banned: bannedIds.has(u.uid) && !admin,
    canAccessWorkspace: canSeeWorkspace(u.uid, myRole, governance),
    people,
    governance,
    opportunities: unique([...open, ...owned, ...managedOps]).sort((a, b) =>
      String(b.createdAt).localeCompare(String(a.createdAt)),
    ),
    contributions: unique([...ownCs, ...managedCs]),
    posts: posts.map((p) => ({ ...p, created_at: p.createdAt })),
    events: recentEvents,
    follows: prefs.exists() ? prefs.data().wgs : [],
    welcomeSeen: prefs.exists() ? prefs.data().welcomeSeen === true : false,
    user: { id: u.uid, email: u.email, name: u.displayName || "" },
    more: {
      profiles: directory.length === 100,
      opportunities: open.length === 50 || managedOps.length === 100,
      posts: posts.length === 25,
      contributions: ownCs.length === 50 || managedCs.length === 100,
      events: recentEvents.length === 100,
    },
  };
}
export function subscribeCategories(
  next: (r: any[]) => void,
  error: (e: any) => void,
) {
  if (!db) return () => {};
  return onSnapshot(
    collection(db, "categories"),
    (s) => next(s.docs.map(unpack)),
    error,
  );
}
const str = (v: any, max = 1500) =>
  typeof v === "string" ? v.trim().slice(0, max) : "";
const strings = (v: any, max = 20) =>
  Array.isArray(v)
    ? [
        ...new Set(
          v
            .filter((x) => typeof x === "string")
            .map((x) => normaliseLabel(x).slice(0, 100))
            .filter(Boolean),
        ),
      ].slice(0, max)
    : [];
const groups = (v: any) =>
  Array.isArray(v)
    ? [...new Set(v.filter((x) => Number.isInteger(x) && x >= 1 && x <= 5))]
    : [];
const times = [
  "2–4 hours / month",
  "4–8 hours / month",
  "8+ hours / month",
  "Project-based",
  "Currently unavailable",
];
export async function addCategory(kind: CategoryKind, label: string) {
  const { u, d } = current();
  const clean = normaliseLabel(label);
  if (!categoryKinds.includes(kind) || !clean || clean.length > 100)
    throw Error("Enter a category between 1 and 100 characters.");
  const normalized = clean.toLocaleLowerCase();
  const hash = Array.from(
    new Uint8Array(
      await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(kind + ":" + normalized),
      ),
    ),
  )
    .map((n) => n.toString(16).padStart(2, "0"))
    .join("");
  const ref = doc(d, "categories", hash),
    existing = await getDoc(ref);
  if (existing.exists()) {
    if (existing.data().enabled === false)
      throw Error("This option was retired by the Secretariat.");
    return existing.data().label as string;
  }
  try {
    await setDoc(ref, {
      kind,
      label: clean,
      normalized,
      enabled: true,
      createdBy: u.uid,
      createdAt: serverTimestamp(),
    });
  } catch (e) {
    const raced = await getDoc(ref);
    if (!raced.exists() || raced.data().enabled === false) throw e;
    return raced.data().label as string;
  }
  return clean;
}
async function deleteWithChildren(
  collectionName: string,
  id: string,
  children: [string, string, string][],
) {
  const { d } = current();
  const sets = await Promise.all(
    children.map(([name, key, value]) =>
      list(name, [where(key, "==", value)], 450),
    ),
  );
  if (
    sets.some((a) => a.length === 450) ||
    sets.reduce((n, a) => n + a.length, 0) > 450
  )
    throw Error(
      "This record has too many linked records for one removal. Remove those records first.",
    );
  const batch = writeBatch(d);
  sets.forEach((a, i) =>
    a.forEach((x) => batch.delete(doc(d, children[i][0], x.id))),
  );
  batch.delete(doc(d, collectionName, id));
  if (collectionName === "profiles") {
    for (const name of [
      "privateProfiles",
      "profilePhotos",
      "preferences",
      "roles",
    ])
      batch.delete(doc(d, name, id));
    const boards = await list("governance", [], 10);
    for (const board of boards) {
      if (
        board.lead === id ||
        [...board.secretariat, ...board.associateLeads, ...board.core].includes(
          id,
        )
      )
        batch.update(doc(d, "governance", board.id), {
          lead: board.lead === id ? "" : board.lead,
          secretariat: board.secretariat.filter((uid: string) => uid !== id),
          associateLeads: board.associateLeads.filter(
            (uid: string) => uid !== id,
          ),
          core: board.core.filter((uid: string) => uid !== id),
          updatedAt: serverTimestamp(),
        });
    }
  }
  await batch.commit();
}
export async function saveCommunity(b: any) {
  const { u, d } = current();
  const r = await role(u.uid);
  const boards = await list("governance", [], 10);
  const managed = managedGroups(
    u.uid,
    r,
    bodies.map((x) => ({
      ...emptyBody,
      ...x,
      ...boards.find((g) => g.id === x.id),
    })),
  );
  const canManage = (wg: number) => r.admin === true || managed.includes(wg);
  if (b.action === "profile") {
    const p = b.profile,
      target = b.id || u.uid;
    if (target !== u.uid && !r.admin)
      throw Error("UNESCO Secretariat access is required.");
    if (
      !p?.name?.trim() ||
      !p.consent ||
      !p.skills?.length ||
      !p.languages?.length
    )
      throw Error(
        "Enter your name, at least one skill and a language, then accept the profile notice.",
      );
    const ref = doc(d, "profiles", target),
      existing = await getDoc(ref);
    const publicData = {
      name: str(p.name, 120),
      headline: str(p.headline, 160),
      organisation: str(p.organisation, 160),
      country: str(p.country, 100),
      region: regions.includes(normaliseRegion(p.region)) ? normaliseRegion(p.region) : "",
      languages: strings(p.languages),
      skills: strings(p.skills),
      wgs: groups(p.wgs),
      bio: str(p.bio),
      motivation: str(p.motivation),
      contribution: str(p.contribution),
      availability: times.includes(p.availability) ? p.availability : times[0],
      website: str(p.website, 500),
      visibility: p.visibility === "private" ? "private" : "community",
      contactConsent: !!p.contactConsent,
      // Gender and feeling about the Decade, shown on the profile only when the member chooses to.
      showBackground: !!p.showBackground,
      publicGender: p.showBackground ? str(p.gender, 100) : "",
      publicSentiment: p.showBackground ? str(p.sentiment, 100) : "",
      contact: p.contactConsent
        ? target === u.uid
          ? u.email || ""
          : str(p.contact, 254)
        : "",
      consent: true,
      careerStage: str(p.careerStage, 100) || "Prefer not to say",
      educationLevel: str(p.educationLevel, 100) || "Prefer not to say",
      cryosphereTypes: strings(p.cryosphereTypes),
      hasPhoto:
        p.photoData === null
          ? false
          : p.photoData
            ? true
            : existing.exists()
              ? existing.data().hasPhoto === true
              : false,
      onboardingVersion: 2,
      createdAt: existing.exists()
        ? existing.data().createdAt
        : serverTimestamp(),
      updatedAt: serverTimestamp(),
    };
    const batch = writeBatch(d);
    batch.set(ref, publicData);
    batch.set(doc(d, "privateProfiles", target), {
      sentiment: str(p.sentiment, 100),
      feedback: str(p.feedback),
      gender: str(p.gender, 100) || "Prefer not to say",
      updatedAt: serverTimestamp(),
    });
    if (p.photoData === null) batch.delete(doc(d, "profilePhotos", target));
    else if (typeof p.photoData === "string")
      batch.set(doc(d, "profilePhotos", target), {
        data: p.photoData,
        updatedAt: serverTimestamp(),
      });
    await batch.commit();
    clearPhotoCache(target);
    // Roles the member declared, for the UNESCO Secretariat to confirm.
    if (target === u.uid && p.roleClaims !== undefined)
      await saveOwnRequest(u.uid, publicData.name, cleanClaims(p.roleClaims), str(p.roleNote, 1000));
    return {};
  }
  if (
    [
      "role",
      "ban",
      "unban",
      "governance",
      "categoryStatus",
      "adminEdit",
      "adminDelete",
    ].includes(b.action)
  ) {
    if (!r.admin) throw Error("UNESCO Secretariat access is required.");
    if (b.action === "role") {
      const existingRole = await getDoc(doc(d, "roles", b.id));
      const unesco = b.role === "unesco-secretariat";
      if (b.id === u.uid && isPlatformOwner(u) && !unesco)
        throw Error("The project Secretariat account must retain UNESCO access.");
      const ticked = (b.badges === undefined
        ? existingRole.data()?.badges || [] : strings(b.badges, 80))
        .filter((id: string) => badgeIds.includes(id) && id !== "unesco-secretariat");
      // Lead, Associate Lead, Secretariat and Core Group roles are stored as Governance appointments,
      // so the member appears under Governance and on the group's page. Other badges stay on the role.
      const selected = b.badges === undefined ? ticked : ticked.filter((id: string) => !isAppointmentBadge(id));
      const badges = unesco ? ["unesco-secretariat", ...selected] : selected;
      if (badges.length > 20) throw Error("Select at most 20 badges.");
      const batch = writeBatch(d);
      // Logo review access (Working Groups 1 to 5, SMC, ESC) is kept unless the dialog sends a new choice.
      const logoReview = (b.logoReview === undefined ? existingRole.data()?.logoReview || [] : strings(b.logoReview, 10))
        .filter((x: string) => logoReviewOptions.includes(x));
      batch.set(doc(d, "roles", b.id), {
        admin: unesco,
        role: b.role,
        wgs: b.wgs === undefined ? groups(existingRole.data()?.wgs) : groups(b.wgs),
        badges,
        ...(logoReview.length ? { logoReview: [...new Set(logoReview)] } : {}),
      });
      if (b.badges !== undefined) {
        const current = (await getDocs(collection(d, "governance"))).docs.map((x) => ({ id: x.id, ...x.data() }));
        for (const g of applyAppointments(b.id, ticked, current, bodies))
          batch.set(doc(d, "governance", g.id), {
            title: str(g.title, 160) || g.id,
            description: str(g.description),
            lead: g.lead,
            secretariat: g.secretariat,
            associateLeads: g.associateLeads,
            core: g.core,
            updatedAt: serverTimestamp(),
          });
      }
      await batch.commit();
      await refreshMemberEntries(b.id).catch(() => {});
      return {};
    }
    if (b.action === "ban" || b.action === "unban") {
      if (b.id === u.uid) throw Error("You cannot ban your own account.");
      if (b.action === "unban") { await deleteDoc(doc(d, "bans", b.id)); return {}; }
      const target = await getDoc(doc(d, "roles", b.id));
      if (target.exists() && isUnescoSecretariat(target.data()))
        throw Error("Remove this member's UNESCO Secretariat access before banning the account.");
      await setDoc(doc(d, "bans", b.id), { by: u.uid, at: serverTimestamp() });
      // A banned member leaves the mailing lists.
      await Promise.all([...bodies.map((x) => x.id), "decade"].map((l) => deleteDoc(doc(d, "mailingLists", l, "entries", b.id)).catch(() => {})));
      return {};
    }
    if (b.action === "governance") {
      const base = bodies.find((x) => x.id === b.id);
      if (!base) throw Error("Unknown Decade body.");
      const seatError = committeeSeatError(b.id, b.body);
      if (seatError) throw Error(seatError);
      const before = await getDoc(doc(d, "governance", b.id));
      const seated = (g: any) => [g?.lead, ...(g?.secretariat || []), ...(g?.associateLeads || []), ...(g?.core || [])].filter(Boolean);
      const affected = [...new Set([...seated(before.data()), ...seated(b.body)])];
      await setDoc(doc(d, "governance", b.id), {
        title: str(b.body.title, 160) || base.title,
        description: str(b.body.description),
        lead: str(b.body.lead, 128),
        secretariat: strings(b.body.secretariat),
        associateLeads: strings(b.body.associateLeads),
        core: strings(b.body.core),
        updatedAt: serverTimestamp(),
      });
      await Promise.all(affected.map((id) => refreshMemberEntries(id).catch(() => {})));
      return {};
    }
    if (b.action === "categoryStatus") {
      await updateDoc(doc(d, "categories", b.id), {
        enabled: b.enabled === true,
      });
      return {};
    }
    if (
      !["profiles", "opportunities", "posts", "contributions"].includes(
        b.collection,
      )
    )
      throw Error("Unknown content type.");
    if (b.action === "adminDelete") {
      if (b.collection === "profiles") {
        if (b.id === u.uid) throw Error("You cannot remove your own account.");
        await deleteWithChildren("profiles", b.id, [
          ["contributions", "member_id", b.id],
          ["posts", "author", b.id],
          ["events", "owner", b.id],
        ]);
        // The member's other records: private answers, role, role declaration, preferences and mailing-list entries.
        await Promise.all([
          ...["privateProfiles", "roles", "roleRequests", "preferences"].map((c) => deleteDoc(doc(d, c, b.id)).catch(() => {})),
          ...[...bodies.map((x) => x.id), "decade"].map((l) => deleteDoc(doc(d, "mailingLists", l, "entries", b.id)).catch(() => {})),
        ]);
      }
      else if (b.collection === "opportunities")
        await deleteWithChildren("opportunities", b.id, [
          ["contributions", "opportunity_id", b.id],
        ]);
      else await deleteDoc(doc(d, b.collection, b.id));
      return {};
    }
    if (b.collection === "posts")
      await updateDoc(doc(d, "posts", b.id), {
        body: str(b.record.body, 3000),
        wg: Number(b.record.wg),
        updatedAt: serverTimestamp(),
      });
    if (b.collection === "opportunities") {
      const existing = await getDoc(doc(d, "opportunities", b.id));
      const nextGroup = Number(b.record.wg);
      const nextTitle = str(b.record.title, 160);
      const goalIds = b.record.mgs || [];
      if (!validGoalSelection(goalIds) || (goalIds.length && !linkedGroups(goalIds).includes(nextGroup)))
        throw Error("Choose valid main goals and a reviewing group linked to them.");
      const linked =
        existing.exists() &&
        (existing.data().wg !== nextGroup ||
          existing.data().title !== nextTitle)
          ? await list(
              "contributions",
              [where("opportunity_id", "==", b.id)],
              450,
            )
          : [];
      if (linked.length === 450)
        throw Error(
          "This activity has too many linked contributions for one title or group change.",
        );
      const batch = writeBatch(d);
      batch.update(doc(d, "opportunities", b.id), {
        wg: nextGroup,
        mgs: goalIds,
        title: nextTitle,
        description: str(b.record.description, 3000),
        skills: strings(b.record.skills),
        region: normaliseRegion(b.record.region),
        language: str(b.record.language, 100),
        commitment: b.record.commitment,
        deadline: str(b.record.deadline, 10),
        type: normaliseLabel(b.record.type || ""),
        status: b.record.status,
      });
      linked.forEach((c) =>
        batch.update(doc(d, "contributions", c.id), {
          wg: nextGroup,
          opportunity_title: nextTitle,
          updatedAt: serverTimestamp(),
        }),
      );
      await batch.commit();
    }
    if (b.collection === "contributions")
      await updateDoc(doc(d, "contributions", b.id), {
        message: str(b.record.message, 2000),
        status: b.record.status,
        updatedAt: serverTimestamp(),
      });
    return {};
  }
  const member = await getDoc(doc(d, "profiles", u.uid));
  if (!member.exists()) throw Error("Create your member profile first.");
  if (b.action === "follow") {
    const wg = Number(b.wg);
    if (!Number.isInteger(wg) || wg < 1 || wg > 5)
      throw Error("Invalid group.");
    const pref = doc(d, "preferences", u.uid),
      existing = await getDoc(pref),
      prev = existing.exists() ? existing.data().wgs : [];
    await setDoc(pref, {
      wgs: b.follow
        ? groups([...prev, wg])
        : prev.filter((x: number) => x !== wg),
      ...(existing.exists() && existing.data().welcomeSeen === true ? { welcomeSeen: true } : {}),
    });
    return {};
  }
  if (b.action === "welcomeSeen") {
    const pref = doc(d, "preferences", u.uid), existing = await getDoc(pref);
    await setDoc(pref, { wgs: existing.exists() ? existing.data().wgs || [] : [], welcomeSeen: true });
    return {};
  }
  if (b.action === "post") {
    if (!validGoalSelection(b.mgs || [])) throw Error("Select valid main goals.");
    const body = str(b.body, 3000);
    if (!body) throw Error("Write an update.");
    await setDoc(doc(collection(d, "posts")), {
      author: u.uid,
      author_name: member.data().name,
      wg: Number(b.wg) || 0,
      mgs: b.mgs || [],
      body,
      attachments: cleanAttachments(b.attachments),
      createdAt: serverTimestamp(),
    });
    return {};
  }
  if (b.action === "opportunity") {
    const p = b.opportunity,
      wg = Number(p.wg);
    if (!p.title?.trim() || !p.description?.trim())
      throw Error("Complete the title and description.");
    if (!Number.isInteger(wg) || wg < 1 || wg > 5)
      throw Error("Choose a reviewing Working Group.");
    if (!validGoalSelection(p.mgs) || !p.mgs.length || !linkedGroups(p.mgs).includes(wg))
      throw Error("Select at least one main goal and its reviewing Working Group.");
    const type = normaliseLabel(p.type || "");
    if (!type || type.length > 100) throw Error("Choose a contribution type up to 100 characters.");
    const pending = !canManage(wg);
    await setDoc(doc(collection(d, "opportunities")), {
      owner: u.uid,
      wg,
      mgs: p.mgs,
      title: str(p.title, 160),
      description: str(p.description, 3000),
      skills: strings(p.skills),
      region: regions.includes(normaliseRegion(p.region)) ? normaliseRegion(p.region) : "Global",
      language: str(p.language, 100) || languages[0],
      commitment: times.includes(p.commitment) ? p.commitment : times[0],
      deadline: str(p.deadline, 10),
      type,
      status: pending ? "pending" : "open",
      attachments: cleanAttachments(p.attachments),
      ...(p.project ? { project: str(p.project, 128) } : {}),
      createdAt: serverTimestamp(),
    });
    return { pending };
  }
  if (b.action === "apply") {
    const o = await getDoc(doc(d, "opportunities", b.opportunityId));
    if (!o.exists() || o.data().status !== "open")
      throw Error("This opportunity is not open.");
    if (
      o.data().deadline &&
      o.data().deadline < new Date().toISOString().slice(0, 10)
    )
      throw Error("The deadline has passed.");
    const message = str(b.message, 2000);
    if (!message) throw Error("Describe your proposed contribution.");
    const ref = doc(d, "contributions", b.opportunityId + "_" + u.uid),
      existing = await getDoc(ref);
    if (existing.exists()) throw Error("You have already recorded interest.");
    await setDoc(ref, {
      opportunity_id: b.opportunityId,
      member_id: u.uid,
      member_name: member.data().name,
      opportunity_title: o.data().title,
      wg: o.data().wg,
      message,
      status: "Interested",
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp(),
    });
    return {};
  }
  if (b.action === "opportunityEdit" || b.action === "opportunityDelete") {
    const ref = doc(d, "opportunities", b.id), o = await getDoc(ref);
    if (!o.exists()) throw Error("This activity no longer exists.");
    const cur = o.data();
    if (!r.admin && cur.owner !== u.uid) throw Error("Only the person who proposed this activity or the UNESCO Secretariat can change it.");
    if (b.action === "opportunityDelete") {
      if (r.admin) await deleteWithChildren("opportunities", b.id, [["contributions", "opportunity_id", b.id]]);
      else await deleteDoc(ref);
      return {};
    }
    const p = b.opportunity, wg = r.admin ? Number(p.wg) : Number(cur.wg);
    if (!p.title?.trim() || !p.description?.trim()) throw Error("Complete the title and description.");
    if (!Number.isInteger(wg) || wg < 1 || wg > 5) throw Error("Choose a reviewing Working Group.");
    if (!validGoalSelection(p.mgs) || !p.mgs.length || !linkedGroups(p.mgs).includes(wg))
      throw Error(r.admin ? "Select at least one main goal and its reviewing Working Group." : `Select at least one main goal of WG${wg}, the Working Group that reviews this activity.`);
    const type = normaliseLabel(p.type || "");
    if (!type || type.length > 100) throw Error("Choose a contribution type up to 100 characters.");
    await updateDoc(ref, {
      wg,
      mgs: p.mgs,
      title: str(p.title, 160),
      description: str(p.description, 3000),
      skills: strings(p.skills),
      region: regions.includes(normaliseRegion(p.region)) ? normaliseRegion(p.region) : "Global",
      language: str(p.language, 100) || languages[0],
      commitment: times.includes(p.commitment) ? p.commitment : times[0],
      deadline: str(p.deadline, 10),
      type,
      attachments: cleanAttachments(p.attachments),
      project: str(p.project || "", 128),
    });
    return {};
  }
  if (b.action === "opportunityStatus") {
    await updateDoc(doc(d, "opportunities", b.id), { status: b.status });
    return {};
  }
  if (b.action === "contributionStatus") {
    await updateDoc(doc(d, "contributions", b.id), {
      status: b.status,
      updatedAt: serverTimestamp(),
    });
    return {};
  }
  throw Error("Unknown action.");
}
export function friendlyError(e: any) {
  const code = String(e?.code || "");
  if (code.includes("permission-denied"))
    return "This change needs the relevant member or Working Group permission. Contact the UNESCO Secretariat.";
  if (code.includes("resource-exhausted"))
    return "The free-plan quota is currently exhausted. Please try again after the quota resets.";
  if (code.includes("unavailable"))
    return "The community is temporarily unavailable. Your entries are still here; please try again.";
  return e?.message || "The change could not be saved.";
}
