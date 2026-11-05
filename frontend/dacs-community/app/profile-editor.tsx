import { useEffect, useState } from "react";
import { toast } from "sonner";
import { groups, regions } from "@/lib/data";
import { blankProfile, CategoryKind, optionsFor } from "@/lib/profile-options";
import { addCategory, friendlyError } from "@/lib/store";
import { resizePhoto } from "@/lib/photos";
import { MemberAvatar } from "./member-avatar";
import { useMemberAuth } from "./auth";
import { Check, Upload } from "lucide-react";
import { RoleDeclaration } from "./role-requests";
import { getOwnRequest, type RoleRequest } from "@/lib/role-requests";

export function OptionQuestion({
  kind,
  label,
  value,
  onChange,
  categories,
  multiple = false,
  note,
}: {
  kind: CategoryKind;
  label: string;
  value: string | string[];
  onChange: (v: any) => void;
  categories: any[];
  multiple?: boolean;
  note?: string;
}) {
  const [custom, setCustom] = useState(""),
    [busy, setBusy] = useState(false);
  const selected = Array.isArray(value) ? value : value ? [value] : [];
  const options = optionsFor(kind, categories, selected);
  function choose(v: string) {
    if (multiple) {
      if (!selected.includes(v) && selected.length >= 20) {
        toast.info("Choose up to 20 options.");
        return;
      }
      onChange(
        selected.includes(v)
          ? selected.filter((x) => x !== v)
          : [...selected, v],
      );
    } else onChange(v);
  }
  async function add() {
    if (!custom.trim()) return;
    setBusy(true);
    try {
      const existing = options.find(
        (s) => s.toLocaleLowerCase() === custom.trim().toLocaleLowerCase(),
      );
      const label = existing || (await addCategory(kind, custom));
      if (multiple && !selected.includes(label))
        onChange([...selected, label].slice(0, 20));
      else if (!multiple) onChange(label);
      setCustom("");
      toast.success("Option added to the shared choices.");
    } catch (e) {
      toast.error(friendlyError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <fieldset className="option-question">
      <legend>{label}</legend>
      {note && <p className="micro">{note}</p>}
      <div className="tags">
        {options.map((option) => (
          <button
            type="button"
            className={
              "skill-choice " + (selected.includes(option) ? "selected" : "")
            }
            aria-pressed={selected.includes(option)}
            key={option}
            onClick={() => choose(option)}
          >
            {option}
          </button>
        ))}
      </div>
      <div className="category-add">
        <input
          aria-label={"Add an option for " + label}
          maxLength={100}
          value={custom}
          placeholder="Add another option…"
          onChange={(e) => setCustom(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
        />
        <button
          type="button"
          className="btn small"
          disabled={busy || !custom.trim()}
          onClick={add}
        >
          {busy ? "Adding…" : "Add option"}
        </button>
      </div>
    </fieldset>
  );
}
export function ProfileEditor({
  initial,
  categories,
  onSave,
  saving = false,
  onboarding = false,
  adminEditing = false,
}: {
  initial: any;
  categories: any[];
  onSave: (p: any) => Promise<boolean>;
  saving?: boolean;
  onboarding?: boolean;
  adminEditing?: boolean;
}) {
  const { user } = useMemberAuth();
  const [draft, setDraft] = useState<any>({
      ...blankProfile,
      ...initial,
      name: initial?.name || user?.displayName || "",
    }),
    [step, setStep] = useState(0),
    [photoBusy, setPhotoBusy] = useState(false),
    [request, setRequest] = useState<RoleRequest | null>(null);
  // Roles declared by the member. The Secretariat assigns roles directly when editing another member.
  const declares = !adminEditing;
  useEffect(() => {
    if (!declares || !user?.uid) return;
    let live = true;
    getOwnRequest(user.uid).then((r) => {
      if (!live) return;
      setRequest(r);
      setDraft((d: any) => ({ ...d, roleClaims: d.roleClaims ?? r?.claims ?? {}, roleNote: d.roleNote ?? r?.note ?? "" }));
    }).catch(() => live && setDraft((d: any) => ({ ...d, roleClaims: d.roleClaims ?? {}, roleNote: d.roleNote ?? "" })));
    return () => { live = false; };
  }, [declares, user?.uid]);
  const update = (key: string, value: any) =>
    setDraft((d: any) => ({ ...d, [key]: value }));
  function field(
    key: string,
    label: string,
    area = false,
    max = 160,
    required = false,
  ) {
    return (
      <div className={"field " + (area ? "full" : "")}>
        <label htmlFor={"edit-" + key}>
          {label}
          {required ? " *" : ""}
        </label>
        {area ? (
          <textarea
            id={"edit-" + key}
            maxLength={max}
            value={draft[key] || ""}
            onChange={(e) => update(key, e.target.value)}
          />
        ) : (
          <input
            id={"edit-" + key}
            maxLength={max}
            required={required}
            value={draft[key] || ""}
            onChange={(e) => update(key, e.target.value)}
          />
        )}
      </div>
    );
  }
  const question = (
    kind: CategoryKind,
    key: string,
    label: string,
    multiple = false,
    note?: string,
  ) => (
    <OptionQuestion
      kind={kind}
      label={label}
      value={draft[key]}
      onChange={(v) => update(key, v)}
      categories={categories}
      multiple={multiple}
      note={note}
    />
  );
  async function upload(file?: File) {
    if (!file) return;
    setPhotoBusy(true);
    try {
      update("photoData", await resizePhoto(file));
    } catch (e) {
      toast.error(friendlyError(e));
    } finally {
      setPhotoBusy(false);
    }
  }
  const keys = ["who", "expertise", ...(declares ? ["role"] : []), "career", "contribution", "consent"];
  const key = keys[step], last = keys.length - 1;
  function next() {
    if (key === "who" && !draft.name.trim()) {
      toast.info("Enter your full name.");
      return;
    }
    if (key === "expertise" && (!draft.skills.length || !draft.languages.length)) {
      toast.info("Select at least one skill and a working language.");
      return;
    }
    setStep((s) => s + 1);
  }
  const titleOf: Record<string, string> = {
    who: "Who you are",
    expertise: "Your expertise",
    role: "Your role",
    career: "Career and background",
    contribution: "Your contribution",
    consent: "Visibility and consent",
  };
  const titles = keys.map((k) => titleOf[k]);
  return (
    <form
      className="profile-editor"
      onSubmit={async (e) => {
        e.preventDefault();
        if (onboarding && step < last) {
          next();
          return;
        }
        await onSave(draft);
      }}
    >
      <ol
        className="wizard-steps"
        aria-label="Profile setup progress"
        style={{ "--progress": step / (titles.length - 1), "--steps": titles.length } as React.CSSProperties}
      >
        {titles.map((title, i) => {
          const state = i === step ? "current" : i < step ? "done" : "";
          const dot = <span className="step-dot">{i < step && onboarding ? <Check size={16} /> : i + 1}</span>;
          return (
            <li key={title} className={state}>
              {onboarding ? (
                <span aria-current={i === step ? "step" : undefined}>
                  {dot}
                  <span className="step-label">{title}</span>
                </span>
              ) : (
                <button
                  type="button"
                  aria-label={title}
                  aria-current={i === step ? "step" : undefined}
                  onClick={() => setStep(i)}
                >
                  {dot}
                  <span className="step-label">{title}</span>
                </button>
              )}
            </li>
          );
        })}
      </ol>
      {key === "who" && (
        <section className="profile-section">
          <h2>Who you are</h2>
          <div className="photo-edit">
            <MemberAvatar
              name={draft.name}
              uid={initial?.id}
              hasPhoto={draft.photoData === null ? false : initial?.hasPhoto}
              version={initial?.updatedAt}
              photo={draft.photoData || undefined}
              large
            />
            <div className="stack">
              <label className="btn small photo-button">
                <Upload size={14} />
                {photoBusy ? "Preparing photo…" : "Add profile photo"}
                <input
                  aria-label="Profile photo"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  disabled={photoBusy}
                  onChange={(e) => upload(e.target.files?.[0])}
                />
              </label>
              <small className="micro">Optional · JPEG, PNG or WebP</small>
              {(draft.photoData || initial?.hasPhoto) &&
                draft.photoData !== null && (
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => update("photoData", null)}
                  >
                    Remove photo
                  </button>
                )}
            </div>
          </div>
          <div className="form-grid">
            {field("name", "Full name", false, 120, true)}
            {field("headline", "Professional headline")}
            {field("organisation", "Organisation / affiliation")}
            {field("country", "Country", false, 100)}
            <div className="field">
              <label htmlFor="edit-region">Regional experience</label>
              <select
                id="edit-region"
                value={draft.region}
                onChange={(e) => update("region", e.target.value)}
              >
                <option value="">Choose a region</option>
                {regions.map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </div>
            {field("website", "Professional link", false, 500)}
            {field("bio", "Tell us about your work", true, 1500)}
          </div>
        </section>
      )}
      {key === "expertise" && (
        <section className="profile-section">
          <h2>Your expertise and interests</h2>
          {question(
            "skills",
            "skills",
            "Which skills could you contribute? *",
            true,
          )}
          {question(
            "cryosphereTypes",
            "cryosphereTypes",
            "Which parts of the cryosphere do you work on?",
            true,
          )}
          {question(
            "languages",
            "languages",
            "Which working languages do you use? *",
            true,
          )}
          <fieldset className="option-question">
            <legend>Which Working Groups interest you?</legend>
            <div className="choice-grid">
              {groups.map((g) => (
                <label className="choice" key={g.id}>
                  <input
                    type="checkbox"
                    checked={draft.wgs.includes(g.id)}
                    onChange={(e) =>
                      update(
                        "wgs",
                        e.target.checked
                          ? [...draft.wgs, g.id]
                          : draft.wgs.filter((n: number) => n !== g.id),
                      )
                    }
                  />
                  WG{g.id} · {g.short}
                </label>
              ))}
            </div>
            <p className="micro">
              You can participate across the Decade without selecting a group.
            </p>
          </fieldset>
        </section>
      )}
      {key === "role" && (
        <section className="profile-section">
          <h2>Your role in the Decade</h2>
          <RoleDeclaration
            claims={draft.roleClaims || {}}
            note={draft.roleNote || ""}
            request={request}
            onChange={(c) => update("roleClaims", c)}
            onNote={(n) => update("roleNote", n)}
          />
        </section>
      )}
      {key === "career" && (
        <section className="profile-section">
          <h2>Career and background</h2>
          {question(
            "careerStages",
            "careerStage",
            "What is your current career stage?",
          )}
          {question(
            "educationLevels",
            "educationLevel",
            "What is your highest level of education?",
          )}
          {question(
            "genders",
            "gender",
            "How do you describe your gender?",
            false,
            "Optional. Excluded from member searches and matching. It appears on your profile only if you choose so in the last step.",
          )}
        </section>
      )}
      {key === "contribution" && (
        <section className="profile-section">
          <h2>Your contribution to the Decade</h2>
          {field("motivation", "What brings you to the Decade?", true, 1500)}
          {field("contribution", "What could you contribute?", true, 1500)}
          <div className="field">
            <label htmlFor="edit-availability">Indicative availability</label>
            <select
              id="edit-availability"
              value={draft.availability}
              onChange={(e) => update("availability", e.target.value)}
            >
              {[
                "2–4 hours / month",
                "4–8 hours / month",
                "8+ hours / month",
                "Project-based",
                "Currently unavailable",
              ].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="edit-sentiment">
              How do you feel about the Decade?
            </label>
            <select
              id="edit-sentiment"
              value={draft.sentiment}
              onChange={(e) => update("sentiment", e.target.value)}
            >
              <option value="">Prefer not to answer</option>
              {[
                "Enthusiastic and ready to contribute",
                "Interested; looking for a clear role",
                "Need more information",
                "Concerned about time or resources",
              ].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </div>
          {field(
            "feedback",
            "What support would help you participate?",
            true,
            1500,
          )}
          <p className="micro">
            How you feel about the Decade can appear on your profile if you
            choose so in the last step. Your feedback stays visible only to you
            and the Secretariat.
          </p>
        </section>
      )}
      {key === "consent" && (
        <section className="profile-section">
          <h2>Visibility and consent</h2>
          <div className="field">
            <label htmlFor="edit-visibility">Who can see your profile?</label>
            <select
              id="edit-visibility"
              value={draft.visibility}
              onChange={(e) => update("visibility", e.target.value)}
            >
              <option value="community">Signed-in community members</option>
              <option value="private">Only me and the Secretariat</option>
            </select>
          </div>
          <label className="checkline">
            <input
              type="checkbox"
              checked={draft.contactConsent}
              onChange={(e) => update("contactConsent", e.target.checked)}
            />
            Display my sign-in email on my visible profile.
          </label>
          {adminEditing &&
            draft.contactConsent &&
            field("contact", "Member contact email", false, 254)}
          <label className="checkline">
            <input
              type="checkbox"
              checked={!!draft.showBackground}
              onChange={(e) => update("showBackground", e.target.checked)}
            />
            Show my gender and how I feel about the Decade on my profile, to
            signed-in members.
          </label>
          <label className="checkline">
            <input
              type="checkbox"
              checked={draft.consent}
              onChange={(e) => update("consent", e.target.checked)}
            />
            I agree to store my profile for member discovery and Decade
            participation. I can edit my answers and visibility. Appointments
            are assigned separately by the Secretariat.
          </label>
          <p className="micro">
            Your sign-in email is not shown to other members. It is added to the
            mailing lists of the groups you belong to, which their leadership and
            Core Group, and the UNESCO Secretariat, use to write to you about the
            Decade.
          </p>
          <p className="micro">
            Profile photos follow your profile visibility. Gender and private
            feedback are excluded from the directory and matching.
          </p>
        </section>
      )}
      <div className="wizard-actions">
        <span className="step-count">
          Step {step + 1} of {keys.length} · {titles[step]}
        </span>
        {step > 0 && (
          <button
            className="btn"
            type="button"
            disabled={saving}
            onClick={() => setStep((s) => s - 1)}
          >
            Back
          </button>
        )}
        {onboarding && step < last ? (
          <button className="btn primary" type="button" onClick={next}>
            Continue
          </button>
        ) : (
          <button
            className="btn primary"
            type="submit"
            disabled={saving || photoBusy || !draft.consent}
          >
            {saving
              ? "Saving…"
              : onboarding
                ? "Save profile and enter community"
                : "Save profile"}
          </button>
        )}
      </div>
    </form>
  );
}
