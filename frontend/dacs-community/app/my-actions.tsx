import { useState } from "react";
import { Check, ClipboardCheck } from "lucide-react";
import { toast } from "sonner";
import { friendlyError } from "@/lib/store";
import { sortActions, type ActionItem } from "@/lib/coordination";
import { setActionStatus } from "@/lib/coordination-store";
import { ActionStateChip } from "./meeting-minutes";

/** Open action items assigned to the member, on the home page. */
export function MyActions({ actions, onOpenMeeting }: { actions: ActionItem[]; onOpenMeeting: (eventId: string) => void }) {
  const [busy, setBusy] = useState("");
  const open = sortActions(actions.filter((a) => a.status === "open"));
  async function done(a: ActionItem) {
    setBusy(a.id);
    try {
      await setActionStatus(a.id, "done");
      toast.success("Action marked as done.");
    } catch (e) {
      toast.error(friendlyError(e));
    } finally {
      setBusy("");
    }
  }
  return (
    <section className="glass panel my-actions">
      <div className="section-title"><h2><ClipboardCheck size={18} /> My actions</h2><span className="pill">{open.length}</span></div>
      <ul className="action-list">
        {open.slice(0, 6).map((a) => (
          <li key={a.id} className="action-row">
            <button type="button" className="action-check" disabled={busy === a.id} aria-label={"Mark as done: " + a.title} onClick={() => done(a)}><Check size={14} className="ghost" /></button>
            <div className="action-text">
              <strong>{a.title}</strong>
              <span className="micro">{a.body.toUpperCase()}{a.due ? " · due " + new Date(a.due + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : ""} · <button className="text-button inline" onClick={() => onOpenMeeting(a.eventId)}>Meeting and minutes</button></span>
              <span><ActionStateChip action={a} /></span>
            </div>
          </li>
        ))}
      </ul>
      {open.length > 6 && <p className="micro">and {open.length - 6} more in the bell.</p>}
    </section>
  );
}
