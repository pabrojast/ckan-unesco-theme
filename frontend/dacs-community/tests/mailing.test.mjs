import test from "node:test";
import assert from "node:assert/strict";
import { memberTiers, recipients, mailtoBatches, entryChanges, currentEntries } from "../lib/mailing.ts";
import { badgeFor, nextRequest, claimStatus, cleanClaims, roleName } from "../lib/role-claims.ts";

const gov = [
  { id: "wg1", lead: "a", associateLeads: ["b"], secretariat: ["c"], core: ["d"] },
  { id: "smc", lead: "", associateLeads: [], secretariat: [], core: ["a"] },
];

test("tiers follow appointments and badges; Working Groups selected in a profile do not count", () => {
  assert.deepEqual(memberTiers("a", {}, gov, { wgs: [] }), { wg1: "leadership", smc: "core" });
  assert.deepEqual(memberTiers("d", {}, gov, { wgs: [2] }), { wg1: "core" });
  assert.deepEqual(memberTiers("f", { role: "member", badges: ["wg2-member"] }, gov, { wgs: [2, 4] }), { wg2: "broad" });
  assert.deepEqual(memberTiers("e", { role: "member", badges: ["cfd", "wg3-member"] }, gov, { wgs: [] }), { wg3: "broad", cfd: "broad" });
});

test("the UNESCO Secretariat's global access does not place it in every group", () => {
  const unesco = { role: "unesco-secretariat", admin: true, badges: ["unesco-secretariat"], wgs: [] };
  assert.deepEqual(memberTiers("u", unesco, gov, { wgs: [5] }), {});
  assert.deepEqual(memberTiers("u", { ...unesco, badges: ["unesco-secretariat", "wg5-member"] }, gov, { wgs: [] }), { wg5: "broad" });
});

test("lists are nested and de-duplicated", () => {
  const e = [
    { id: "1", name: "Ana", email: "ana@x.org", tier: "leadership" },
    { id: "2", name: "Ben", email: "ben@x.org", tier: "core" },
    { id: "3", name: "Cy", email: "cy@x.org", tier: "broad" },
    { id: "4", name: "Cy again", email: "CY@x.org", tier: "broad" },
    { id: "5", name: "Bad", email: "not-an-email", tier: "broad" },
  ];
  assert.deepEqual(recipients(e, "leadership").map((x) => x.id), ["1"]);
  assert.deepEqual(recipients(e, "core").map((x) => x.id), ["1", "2"]);
  assert.deepEqual(recipients(e, "broad").map((x) => x.id), ["1", "2", "3"]);
});

test("mailto puts the sender in To, the others in Bcc, and splits long lists", () => {
  const [one] = mailtoBatches("me@x.org", ["me@x.org", "a@x.org", "b@x.org"], "[DACS] ");
  assert.equal(one, "mailto:me%40x.org?subject=%5BDACS%5D%20&bcc=a%40x.org,b%40x.org");
  const many = Array.from({ length: 200 }, (_, i) => `member${i}@example.org`);
  const parts = mailtoBatches("me@x.org", many, "Hello", 1900);
  assert.ok(parts.length > 1);
  assert.ok(parts.every((p) => p.length <= 1900));
  assert.equal(parts.map((p) => p.split("bcc=")[1].split(",").length).reduce((a, b) => a + b, 0), 200);
});

test("entry changes write new or changed tiers and remove lists the member left", () => {
  const r = entryChanges({ wg1: { tier: "broad", email: "a@x.org", name: "A" }, smc: { tier: "core", email: "a@x.org", name: "A" } }, { wg1: "core", decade: "member" }, "a@x.org", "A");
  assert.deepEqual(r.write.map((w) => w.list), ["wg1", "decade"]);
  assert.deepEqual(r.remove, ["smc"]);
});

test("declared roles: badges, names and statuses", () => {
  assert.equal(badgeFor("wg2", "lead"), "wg2-lead");
  assert.equal(badgeFor("wg2", "member"), "wg2-member");
  assert.equal(badgeFor("cfd", "member"), "cfd");
  assert.equal(badgeFor("wg2", "unsure"), "");
  assert.equal(roleName("smc", "associate"), "Vice-chairperson");
  assert.deepEqual(cleanClaims({ wg1: "lead", wg9: "lead", smc: "boss" }), { wg1: "lead" });
  const r = { claims: { wg1: "lead", smc: "apply" }, decisions: { wg1: "associate", smc: "declined" } };
  assert.equal(claimStatus(r, "wg1").label, "Confirmed as Associate Lead");
  assert.equal(claimStatus(r, "smc").state, "declined");
});

test("a new declaration keeps decisions unless a decided role changed", () => {
  const prev = { claims: { wg1: "lead", wg2: "core" }, note: "", decisions: { wg1: "lead" } };
  assert.equal(nextRequest(prev, { wg1: "lead", wg2: "core" }, ""), null);
  assert.deepEqual(nextRequest(prev, { wg1: "lead", wg2: "member" }, "").decisions, { wg1: "lead" });
  assert.deepEqual(nextRequest(prev, { wg1: "core", wg2: "core" }, "").decisions, {});
  assert.equal(nextRequest(null, {}, ""), null);
});

test("list entries are checked against current roles: interested members without the badge are left out", () => {
  const people = [
    { id: "d", role: "member", assignedBadgeIds: [], wgs: [1] },
    { id: "g", role: "member", assignedBadgeIds: ["wg1-member"], wgs: [] },
    { id: "h", role: "member", assignedBadgeIds: [], wgs: [1] },
  ];
  const entries = [
    { id: "d", name: "D", email: "d@x.org", tier: "broad" },
    { id: "g", name: "G", email: "g@x.org", tier: "broad" },
    { id: "h", name: "H", email: "h@x.org", tier: "broad" },
    { id: "gone", name: "Gone", email: "gone@x.org", tier: "broad" },
  ];
  assert.deepEqual(currentEntries("wg1", entries, people, gov).map((e) => [e.id, e.tier]), [["d", "core"], ["g", "broad"]]);
});
