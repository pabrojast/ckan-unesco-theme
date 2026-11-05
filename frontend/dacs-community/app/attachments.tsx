import { useRef, useState } from "react";
import { FileText, Loader2, Paperclip, Presentation, X } from "lucide-react";
import { toast } from "sonner";
import { canOrganise, leadershipBodies, type MeetingAccess } from "@/lib/meetings";
import { deleteFile, fileAccept, kindLabel, MAX_ATTACHMENTS, openFile, sizeLabel, uploadFile, type Attachment } from "@/lib/files-store";
import { friendlyError } from "@/lib/store";

/**
 * The body under which a member shares files on a piece of content, or null when they cannot share files.
 * Files are shared by the leadership of a body (Lead, Associate Lead, Secretariat) and by the UNESCO Secretariat.
 */
export function shareBody(access: MeetingAccess, preferred = ""): string | null {
  if (access.admin) return preferred;
  if (preferred && canOrganise(access, preferred)) return preferred;
  return leadershipBodies(access)[0]?.id ?? null;
}

const Icon = ({ a }: { a: Pick<Attachment, "type"> }) => (a.type.startsWith("ppt") ? <Presentation size={16} /> : <FileText size={16} />);

/** Files attached to news, an event, an activity or a discussion message. */
export function AttachmentList({ items, compact = false }: { items?: Attachment[]; compact?: boolean }) {
  const [busy, setBusy] = useState("");
  if (!items?.length) return null;
  return (
    <ul className={"attachments" + (compact ? " compact" : "")} aria-label="Attached files">
      {items.map((a) => (
        <li key={a.id}>
          <button type="button" className={"attachment " + a.type.slice(0, 3)} disabled={busy === a.id} title={`Open ${a.name}`}
            onClick={async () => {
              setBusy(a.id);
              try { await openFile(a); } catch (e) { toast.error(friendlyError(e)); } finally { setBusy(""); }
            }}>
            <span className="attachment-icon">{busy === a.id ? <Loader2 size={16} className="spin" /> : <Icon a={a} />}</span>
            <span className="attachment-text"><strong>{a.name}</strong><small>{kindLabel(a.type)} · {sizeLabel(a.size)}</small></span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Adds PDF, Word or PowerPoint files to a form. Files are uploaded as soon as they are chosen. */
export function AttachmentPicker({ value, onChange, body, audience = "all", disabled = false, saved = [] }: { value: Attachment[]; onChange: (v: Attachment[]) => void; body: string; audience?: "all" | "leadership" | "core" | "broad"; disabled?: boolean; saved?: string[] }) {
  const input = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<{ name: string; p: number } | null>(null);
  async function add(files: FileList | null) {
    if (!files?.length) return;
    let next = [...value];
    for (const f of Array.from(files)) {
      if (next.length >= MAX_ATTACHMENTS) { toast.info(`Attach at most ${MAX_ATTACHMENTS} files.`); break; }
      setProgress({ name: f.name, p: 0 });
      try {
        const a = await uploadFile(f, body, audience, (p) => setProgress({ name: f.name, p }));
        next = [...next, a];
        onChange(next);
      } catch (e) {
        toast.error(friendlyError(e));
      }
    }
    setProgress(null);
    if (input.current) input.current.value = "";
  }
  return (
    <div className="attach-picker">
      <div className="attach-head">
        <span className="field-label-text"><Paperclip size={14} /> Files</span>
        <button type="button" className="btn small" disabled={disabled || !!progress || value.length >= MAX_ATTACHMENTS} onClick={() => input.current?.click()}>Attach PDF, Word or PowerPoint</button>
        <input ref={input} type="file" multiple hidden accept={fileAccept} onChange={(e) => add(e.target.files)} />
      </div>
      {progress && <div className="attach-progress" role="status"><Loader2 size={14} className="spin" /> Uploading {progress.name} · {Math.round(progress.p * 100)}%<i style={{ width: `${Math.round(progress.p * 100)}%` }} /></div>}
      {value.length > 0 && (
        <ul className="attachments compact">
          {value.map((a) => (
            <li key={a.id}>
              <span className={"attachment " + a.type.slice(0, 3)}>
                <span className="attachment-icon"><Icon a={a} /></span>
                <span className="attachment-text"><strong>{a.name}</strong><small>{kindLabel(a.type)} · {sizeLabel(a.size)}</small></span>
                <button type="button" className="attachment-remove" aria-label={`Remove ${a.name}`} disabled={disabled} onClick={() => { onChange(value.filter((x) => x.id !== a.id)); if (!saved.includes(a.id)) deleteFile(a.id).catch(() => {}); }}><X size={14} /></button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="micro">Up to {MAX_ATTACHMENTS} files of 10 MB each. For larger files, add a SharePoint link.</p>
    </div>
  );
}
