import { useEffect, useState } from "react";
import { applyActionCode, checkActionCode, verifyPasswordResetCode, confirmPasswordReset, reload } from "firebase/auth";
import { AlertTriangle, ArrowRight, Check, CheckCircle2, Eye, EyeOff, KeyRound, Loader2, MailCheck, ShieldCheck } from "lucide-react";
import { auth } from "@/lib/firebase";
import { emailError } from "@/lib/email-actions";
import { asset, HOME } from "@/lib/base";

type State = "checking" | "reset" | "saving" | "complete" | "error";

/**
 * Page opened from the links in Firebase Authentication emails (password reset, email verification, email recovery).
 * It has a fixed return path and never redirects to a continue URL supplied in the link.
 */
export function EmailAction() {
  const params = new URLSearchParams(window.location.search), mode = params.get("mode") || "", code = params.get("oobCode");
  const [state, setState] = useState<State>("checking"), [error, setError] = useState(""), [email, setEmail] = useState("");
  const [password, setPassword] = useState(""), [confirm, setConfirm] = useState(""), [show, setShow] = useState(false);
  useEffect(() => {
    let active = true;
    async function run() {
      try {
        if (!auth || !code) throw Error("This link is incomplete. Request a new email from the sign-in page.");
        if (mode === "resetPassword") {
          const address = await verifyPasswordResetCode(auth, code);
          if (active) { setEmail(address); setState("reset"); }
          return;
        }
        if (!["verifyEmail", "recoverEmail"].includes(mode)) throw Error("This link is not supported. Return to DACS Community.");
        // Validate before consuming the one-use code.
        const info = await checkActionCode(auth, code);
        await applyActionCode(auth, code);
        if (auth.currentUser && auth.currentUser.email === info.data.email) {
          await reload(auth.currentUser);
          await auth.currentUser.getIdToken(true);
          window.dispatchEvent(new Event("dacs-auth-refresh"));
        }
        if (active) { setEmail(info.data.email || ""); setState("complete"); }
      } catch (e) {
        if (active) { setError(emailError(e)); setState("error"); }
      }
    }
    void run();
    return () => { active = false; };
  }, [mode, code]);

  const long = password.length >= 8, same = !!password && password === confirm;
  const title = state === "checking" ? "Checking your link"
    : state === "error" ? "This link cannot be used"
    : state === "reset" || state === "saving" ? "Choose a new password"
    : mode === "verifyEmail" ? "Your email address is verified"
    : mode === "recoverEmail" ? "Your email address is restored"
    : "Your password has been updated";
  const Icon = state === "error" ? AlertTriangle : state === "complete" ? (mode === "resetPassword" ? CheckCircle2 : MailCheck) : state === "checking" ? Loader2 : KeyRound;

  return (
    <main className="action-page">
      <header className="action-brand">
        <img src={asset("/assets/decade-logo-white.webp")} alt="Decade of Action for Cryospheric Sciences 2025–2034" />
        <i aria-hidden="true" />
        <img src={asset("/assets/unesco-logo-white.webp")} alt="UNESCO" />
      </header>
      <section className={"action-card " + state} aria-live="polite">
        <span className={"action-icon " + state}><Icon size={26} className={state === "checking" ? "spin" : undefined} /></span>
        <p className="action-eyebrow">DACS Community</p>
        <h1>{title}</h1>

        {state === "checking" && <p>Please wait a moment.</p>}

        {state === "error" && (
          <>
            <p>{error}</p>
            <p className="micro">Links in these emails can be used once and expire after a short time. On the sign-in page, choose “Forgot your password?” to receive a new one.</p>
            <a className="btn primary action-main" href={HOME}>Go to the sign-in page <ArrowRight size={16} /></a>
          </>
        )}

        {(state === "reset" || state === "saving") && (
          <form className="action-form" onSubmit={async (e) => {
            e.preventDefault();
            if (!long || !same) return;
            setError(""); setState("saving");
            try { await confirmPasswordReset(auth!, code!, password); setPassword(""); setConfirm(""); setState("complete"); }
            catch (err) { setError(emailError(err)); setState("reset"); }
          }}>
            <p>Enter a new password for <strong>{email}</strong>.</p>
            <label className="action-field">
              <span>New password</span>
              <span className="action-input">
                <input type={show ? "text" : "password"} required minLength={8} autoComplete="new-password" autoFocus value={password} onChange={(e) => setPassword(e.target.value)} disabled={state === "saving"} />
                <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Hide the password" : "Show the password"}>{show ? <EyeOff size={17} /> : <Eye size={17} />}</button>
              </span>
            </label>
            <label className="action-field">
              <span>Confirm the new password</span>
              <span className="action-input">
                <input type={show ? "text" : "password"} required autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} disabled={state === "saving"} />
              </span>
            </label>
            <ul className="action-rules">
              <li className={long ? "ok" : ""}>{long ? <Check size={14} /> : <i />}At least 8 characters</li>
              <li className={same ? "ok" : ""}>{same ? <Check size={14} /> : <i />}Both passwords match</li>
            </ul>
            {error && <p role="alert" className="error-banner">{error}</p>}
            <button className="btn primary action-main" disabled={!long || !same || state === "saving"}>
              {state === "saving" ? <><Loader2 size={16} className="spin" /> Saving…</> : "Save the new password"}
            </button>
          </form>
        )}

        {state === "complete" && (
          <>
            <p>{mode === "resetPassword" ? "You can now sign in with your new password." : `${email ? email + " · " : ""}You can continue to DACS Community.`}</p>
            <a className="btn primary action-main" href={HOME}>{mode === "resetPassword" ? "Sign in" : "Continue to DACS Community"} <ArrowRight size={16} /></a>
          </>
        )}
      </section>
      <footer className="action-foot">
        <ShieldCheck size={14} />
        <span>If you did not ask for this email, you can ignore it: your account has not changed.</span>
      </footer>
      <p className="action-legal">DACS Community connects the people contributing to the United Nations Decade of Action for Cryospheric Sciences 2025-2034. The Decade Secretariat is hosted by UNESCO’s Intergovernmental Hydrological Programme.</p>
    </main>
  );
}
