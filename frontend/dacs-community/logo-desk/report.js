/* Public activity report page: no sign-in. An applicant files a progress update or a final report
   with the request reference and the reporting code sent by the Secretariat.
   firestore.rules accept the report only if the code matches reportCodes/{ref}; nobody can read reports from here. */
import {collection,doc,setDoc,serverTimestamp} from 'firebase/firestore';
import {db as fs} from '../lib/firebase';
import {decadeGoals} from '../lib/decade-goals';
const MGS=Object.fromEntries(decadeGoals.map(g=>['MG'+g.id,g.title]));
const MAX_FILE = 700 * 1024;
const $ = (s) => document.querySelector(s);
const val = (id) => String($("#" + id).value || "").replace(/ /g, " ").trim();
const num = (id) => { const v = val(id); return v === "" ? null : Math.max(0, Math.round(Number(v))); };

/* theme, shared with the platform */
const store = (k, v) => { try { localStorage.setItem("dacs-desk-" + k, JSON.stringify(v)); } catch (e) {} };
const recall = (k, d) => { try { const v = localStorage.getItem("dacs-desk-" + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } };
function applyTheme(t) { document.documentElement.classList.toggle("light", t === "light"); document.querySelectorAll("[data-theme-btn]").forEach((b) => { b.textContent = t === "light" ? "Dark" : "Bright"; }); }
applyTheme(recall("theme", "dark"));
document.addEventListener("click", (e) => { if (e.target.closest("[data-theme-btn]")) { const t = document.documentElement.classList.contains("light") ? "dark" : "light"; store("theme", t); applyTheme(t); } });

/* main goals as toggles */
$("#f_mgs").innerHTML = Object.keys(MGS).map((k) => `<button type="button" class="chip" data-mg="${k}" aria-pressed="false" title="${MGS[k]}">${k} · ${MGS[k]}</button>`).join("");
$("#f_mgs").addEventListener("click", (e) => { const b = e.target.closest("[data-mg]"); if (b) b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") === "true" ? "false" : "true"); });

/* link from the Secretariat's message: ?ref=…&code=… */
const qs = new URLSearchParams(location.search);
if (qs.get("ref")) $("#f_ref").value = qs.get("ref");
if (qs.get("code")) $("#f_code").value = qs.get("code");
if (qs.get("ref") || qs.get("code")) history.replaceState(null, "", location.pathname);

/* character counters */
document.querySelectorAll(".count[data-for]").forEach((c) => { const t = $("#" + c.dataset.for); const u = () => { c.textContent = `${t.value.length} / ${t.maxLength}`; }; t.addEventListener("input", u); u(); });

/* attachment */
let file = null;
$("#f_file").addEventListener("change", async (e) => {
  const f = e.target.files[0]; const note = $("#f_fileNote"); file = null;
  if (!f) return;
  if (f.size > MAX_FILE) { note.textContent = `${f.name} is ${(f.size / 1024 / 1024).toFixed(1)} MB: the limit is 700 KB. Share it as a link instead.`; note.style.color = "var(--bad)"; e.target.value = ""; return; }
  const data = await new Promise((ok, ko) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(",")[1]); r.onerror = ko; r.readAsDataURL(f); });
  file = { name: f.name.slice(0, 200), type: f.type || "application/octet-stream", size: f.size, data };
  note.textContent = `${f.name} · ${Math.round(f.size / 1024)} KB`; note.style.color = "";
});

function show(msg, bad) { const m = $("#f_msg"); m.hidden = !msg; m.textContent = msg || ""; m.style.background = bad ? "var(--bad-t)" : ""; }

$("#repForm").addEventListener("submit", async (e) => {
  e.preventDefault(); show("");
  if (!fs) { show("The reporting service is not configured yet. Please write to cryosphere@unesco.org.", true); return; }
  const ref = val("f_ref").toUpperCase(), code = val("f_code").toUpperCase();
  const missing = [["f_ref", "request reference"], ["f_code", "reporting code"], ["f_type", "type of report"], ["f_name", "full name"], ["f_email", "e-mail address"], ["f_org", "organisation"], ["f_status", "status of the activity"], ["f_summary", "summary"]].filter(([id]) => !val(id)).map(([, l]) => l);
  if (missing.length) { show("Please complete: " + missing.join(", ") + "."); return; }
  if (!/^DACS-LOGO-\d{4}-\d{3,}$/.test(ref)) { show("The request reference looks like DACS-LOGO-2026-012."); return; }
  if (!/^\S+@\S+\.\S+$/.test(val("f_email"))) { show("Please check the e-mail address."); return; }
  if (val("f_from") && val("f_to") && val("f_to") < val("f_from")) { show("The end of the period is before its start."); return; }
  if (!$("#f_consent").checked) { show("Please tick the confirmation at the bottom of the form."); return; }
  const btn = $("#f_submit"); btn.disabled = true; btn.textContent = "Sending…";
  const id = doc(collection(fs, "logoReports")).id;
  const report = {
    ref, code, type: val("f_type"), periodFrom: val("f_from"), periodTo: val("f_to"),
    name: val("f_name"), email: val("f_email").toLowerCase(), organisation: val("f_org"),
    status: val("f_status"), logoUse: val("f_logo"), summary: val("f_summary"), outcomes: val("f_outcomes"),
    people: num("f_people"), outputs: num("f_outputs"), countries: val("f_countries"),
    mgs: [...document.querySelectorAll("#f_mgs [aria-pressed=true]")].map((b) => b.dataset.mg), contribution: val("f_contrib"),
    links: val("f_links").split(/\s+/).filter((l) => /^https?:\/\/\S+$/i.test(l)).slice(0, 20),
    fileName: file ? file.name : "", fileSize: file ? file.size : 0,
    consent: true, submittedAt: serverTimestamp()
  };
  try {
    await setDoc(doc(fs, "logoReports", id), report);
    if (file) await setDoc(doc(fs, "logoReportFiles", id), { ref, code, name: file.name, type: file.type, size: file.size, data: file.data, submittedAt: serverTimestamp() });
    $("#repForm").hidden = true; $("#done").hidden = false;
    $("#doneText").textContent = `Your ${report.type.toLowerCase()} for ${ref} has been sent to the UNESCO Secretariat (receipt ${id.slice(0, 8).toUpperCase()}). Thank you for contributing to the reporting of the Decade.`;
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    console.error(err);
    show(err && err.code === "permission-denied" ? "The request reference and the reporting code do not match. Please check both, or write to cryosphere@unesco.org." : "The report could not be sent. Check your connection and try again.", true);
  } finally { btn.disabled = false; btn.textContent = "Submit the report"; }
});

$("#another").addEventListener("click", () => {
  const keep = { ref: val("f_ref"), code: val("f_code"), name: val("f_name"), email: val("f_email"), org: val("f_org") };
  $("#repForm").reset(); file = null; $("#f_fileNote").textContent = "PDF, Word or image, 700 KB at most. For larger files, share a link above.";
  document.querySelectorAll("#f_mgs [data-mg]").forEach((b) => b.setAttribute("aria-pressed", "false"));
  $("#f_ref").value = keep.ref; $("#f_code").value = keep.code; $("#f_name").value = keep.name; $("#f_email").value = keep.email; $("#f_org").value = keep.org;
  document.querySelectorAll(".count[data-for]").forEach((c) => { const t = $("#" + c.dataset.for); c.textContent = `${t.value.length} / ${t.maxLength}`; });
  $("#done").hidden = true; $("#repForm").hidden = false; window.scrollTo({ top: 0 });
});
