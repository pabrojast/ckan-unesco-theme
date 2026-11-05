import { useEffect, useState } from "react";
import { ExternalLink, KeyRound, Loader2, Trash2, UserX } from "lucide-react";
import { resetUrl } from "firebase/auth";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { MemberAvatar } from "./member-avatar";

// IHP-WINS edition: members sign in with their IHP-WINS account, so passwords and sign-in accounts are managed by
// IHP-WINS (CKAN), not by this platform. The former Firebase Authentication tools (Google OAuth client, reset links,
// account deletion) are replaced by links to the IHP-WINS pages.

const userPage = (member: any) => `/user/${encodeURIComponent(member?.id || "")}`;

/** Explains how a member resets their IHP-WINS password. */
export function ResetPasswordDialog({ member, onClose }: { member: any | null; onClose: () => void }) {
  return (
    <Dialog open={!!member} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="detail-content account-dialog">
        <DialogTitle><KeyRound size={19} /> Reset the password</DialogTitle>
        <DialogDescription>{member?.name || "This member"} signs in with an IHP-WINS account, so the password is reset on IHP-WINS.</DialogDescription>
        {member && <div className="account-person"><MemberAvatar name={member.name} uid={member.id} hasPhoto={member.hasPhoto} version={member.updatedAt} /><span><strong>{member.name}</strong><small>{member.headline}</small></span></div>}
        <div className="account-step">
          <p>Send the member the IHP-WINS password reset page. They enter their email address there and IHP-WINS sends them a link. IHP-WINS administrators can also set a new password from the member's account page.</p>
          <div className="toolbar">
            <a className="btn primary" href={resetUrl()} target="_blank" rel="noopener noreferrer"><KeyRound size={16} /> Open the reset page</a>
            <a className="btn" href={userPage(member)} target="_blank" rel="noopener noreferrer">Open the IHP-WINS account <ExternalLink size={14} /></a>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** Removes a member's data from the community. Their IHP-WINS account stays and is managed by IHP-WINS. */
export function RemoveMemberDialog({ member, onClose, removeData }: { member: any | null; onClose: () => void; removeData: (m: any) => Promise<boolean> }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(""), [typed, setTyped] = useState("");
  useEffect(() => { setError(""); setTyped(""); setBusy(false); }, [member?.id]);
  const confirmed = typed.trim().toLowerCase() === "remove";
  async function run() {
    setError("");
    setBusy(true);
    try {
      const removed = await removeData(member);
      if (removed) onClose();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog open={!!member} onOpenChange={(v) => !v && !busy && onClose()}>
      <DialogContent className="detail-content account-dialog account-danger">
        <DialogTitle><UserX size={19} /> Remove a member</DialogTitle>
        <DialogDescription>This cannot be undone.</DialogDescription>
        {member && <div className="account-person"><MemberAvatar name={member.name} uid={member.id} hasPhoto={member.hasPhoto} version={member.updatedAt} /><span><strong>{member.name}</strong><small>{member.headline}</small></span></div>}
        <ul className="account-list">
          <li>The profile, the private profile answers, the role and badges, the role declaration and the preferences are deleted.</li>
          <li>The member's news, events and contributions are deleted, and the member leaves every mailing list.</li>
          <li>Messages already sent stay in the conversations of the other members.</li>
          <li>The IHP-WINS account is not deleted: the person can still sign in to IHP-WINS and create a new profile. To block them, use Ban, or ask an IHP-WINS administrator to delete the account.</li>
        </ul>
        <label className="action-field">
          <span>Type <strong>remove</strong> to confirm</span>
          <input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
        </label>
        {error && <p role="alert" className="error-banner">{error}</p>}
        <div className="toolbar account-actions">
          <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn danger" disabled={!confirmed || busy} onClick={run}>
            {busy ? <><Loader2 size={16} className="spin" /> Removing…</> : <><Trash2 size={16} /> Remove the member data</>}
          </button>
        </div>
        <a className="micro account-console" href={userPage(member)} target="_blank" rel="noopener noreferrer">Open the member's IHP-WINS account <ExternalLink size={12} /></a>
      </DialogContent>
    </Dialog>
  );
}
