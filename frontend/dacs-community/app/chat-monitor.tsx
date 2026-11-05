import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, Eye, Flag, MessagesSquare, ShieldCheck, Trash2, UserPlus, X } from "lucide-react";
import { toast } from "sonner";
import { removeMessage, resolveReport, saveMonitors, subscribeAllChats, subscribeMessages, type Chat, type ChatMessage, type ChatReport } from "@/lib/chat-store";
import { friendlyError } from "@/lib/store";
import { MemberAvatar } from "./member-avatar";

const when = (s: string) => (s ? new Date(s).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "");

/** Moderation of private conversations: reports, every conversation, and (for the owner account) the moderators. */
export function ChatMonitor({ people, reports, monitors, owner, meId }: { people: any[]; reports: ChatReport[]; monitors: string[]; owner: boolean; meId: string }) {
  const [tab, setTab] = useState<"reports" | "chats" | "team">("reports");
  const [chats, setChats] = useState<Chat[]>([]), [error, setError] = useState("");
  const [open, setOpen] = useState<{ chatId: string; messageId?: string } | null>(null);
  useEffect(() => subscribeAllChats(setChats, (e) => setError(friendlyError(e))), []);
  const name = (id: string, c?: Chat) => people.find((p) => p.id === id)?.name || c?.names?.[id] || "Member";
  const pending = reports.filter((r) => r.status === "open");
  const shown = open ? chats.find((c) => c.id === open.chatId) : undefined;
  return (
    <section className="monitor" aria-label="Chat moderation">
      <div className="mailing-intro">
        <div>
          <p><b>Moderation of private messages.</b> Reports from members arrive here. You can read any conversation, remove a message and record how a report was handled. Members are told that conversations are private between them and that they may report a conversation to the UNESCO Secretariat.</p>
        </div>
      </div>
      <div className="toolbar admin-tabs" role="tablist" aria-label="Moderation">
        <button role="tab" aria-selected={tab === "reports"} className={"btn small " + (tab === "reports" ? "primary" : "")} onClick={() => setTab("reports")}><Flag size={14} /> Reports {pending.length > 0 && <span className="nav-count inline">{pending.length}</span>}</button>
        <button role="tab" aria-selected={tab === "chats"} className={"btn small " + (tab === "chats" ? "primary" : "")} onClick={() => setTab("chats")}><MessagesSquare size={14} /> Conversations ({chats.length})</button>
        <button role="tab" aria-selected={tab === "team"} className={"btn small " + (tab === "team" ? "primary" : "")} onClick={() => setTab("team")}><ShieldCheck size={14} /> Moderators</button>
      </div>
      {error && <p className="error-banner" role="alert">{error}</p>}
      <div className={"monitor-layout" + (shown ? " with-thread" : "")}>
        <div className="monitor-main">
          {tab === "reports" && (
            reports.length ? reports.map((r) => <ReportCard key={r.id} report={r} chat={chats.find((c) => c.id === r.chatId)} name={name} onOpen={() => setOpen({ chatId: r.chatId, messageId: r.messageId })} active={open?.chatId === r.chatId} />)
              : <div className="agenda-empty glass"><CheckCircle2 size={22} /><p>No report has been received.</p></div>
          )}
          {tab === "chats" && (
            <ul className="monitor-chats glass">
              {!chats.length && <li className="micro">No conversation yet.</li>}
              {chats.map((c) => (
                <li key={c.id}>
                  <button type="button" className={open?.chatId === c.id ? "on" : ""} onClick={() => setOpen({ chatId: c.id })}>
                    <span className="monitor-pair">{c.members.map((m) => <MemberAvatar key={m} name={name(m, c)} uid={m} hasPhoto={people.find((p) => p.id === m)?.hasPhoto} />)}</span>
                    <span className="chat-thread-text">
                      <span className="chat-thread-top"><strong>{c.members.map((m) => name(m, c)).join(" · ")}</strong><small>{when(c.updatedAt)}</small></span>
                      <span className="chat-thread-preview">{c.lastMessage?.text}</span>
                    </span>
                    {reports.some((r) => r.chatId === c.id && r.status === "open") && <span className="pill amber">Reported</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {tab === "team" && <Moderators people={people} monitors={monitors} owner={owner} meId={meId} />}
        </div>
        {shown && <ReadOnlyThread key={shown.id} chat={shown} highlight={open?.messageId} name={(id) => name(id, shown)} onClose={() => setOpen(null)} />}
      </div>
    </section>
  );
}

function ReportCard({ report: r, chat, name, onOpen, active }: { report: ChatReport; chat?: Chat; name: (id: string, c?: Chat) => string; onOpen: () => void; active: boolean }) {
  const [note, setNote] = useState(""), [busy, setBusy] = useState(false);
  const others = chat ? chat.members.filter((m) => m !== r.reporter).map((m) => name(m, chat)) : [];
  return (
    <article className={"report-card glass" + (r.status === "open" ? " open" : "") + (active ? " active" : "")}>
      <header>
        <span className={"pill " + (r.status === "open" ? "amber" : "green")}>{r.status === "open" ? "Open" : "Resolved"}</span>
        <strong>{r.reporterName}</strong>
        <span className="micro">reported {r.messageId ? "a message from" : "the conversation with"} {others.join(", ") || "another member"} · {when(r.createdAt)}</span>
      </header>
      <blockquote className="request-note">{r.reason}</blockquote>
      {r.status === "resolved" && <p className="micro">Resolved {when(r.resolvedAt || "")}{r.resolution ? ` · ${r.resolution}` : ""}</p>}
      <div className="toolbar">
        <button type="button" className="btn small" onClick={onOpen}><Eye size={14} /> Read the conversation</button>
        {r.status === "open" && (
          <>
            <input className="report-note-input" value={note} maxLength={1000} onChange={(e) => setNote(e.target.value)} placeholder="How was it handled? (optional)" aria-label="How the report was handled" />
            <button type="button" className="btn small primary" disabled={busy} onClick={async () => {
              setBusy(true);
              try { await resolveReport(r.id, note); toast.success("Report marked as resolved."); } catch (e) { toast.error(friendlyError(e)); } finally { setBusy(false); }
            }}><CheckCircle2 size={14} /> Mark as resolved</button>
          </>
        )}
      </div>
    </article>
  );
}

function ReadOnlyThread({ chat, highlight, name, onClose }: { chat: Chat; highlight?: string; name: (id: string) => string; onClose: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]), [error, setError] = useState("");
  const mark = useRef<HTMLDivElement>(null);
  useEffect(() => subscribeMessages(chat.id, setMessages, (e) => setError(friendlyError(e))), [chat.id]);
  useEffect(() => { mark.current?.scrollIntoView({ block: "center" }); }, [messages.length, highlight]);
  const [a] = chat.members;
  return (
    <aside className="chat-thread glass monitor-thread" aria-label="Conversation">
      <header className="chat-head">
        <div className="chat-head-name"><strong>{chat.members.map(name).join(" · ")}</strong><small>Read-only · moderator view</small></div>
        <button type="button" className="btn small icon-only" onClick={onClose} aria-label="Close the conversation"><X size={15} /></button>
      </header>
      <div className="chat-body">
        {error && <p className="error-banner">{error}</p>}
        {messages.map((m) => (
          <div key={m.id} ref={m.id === highlight ? mark : undefined} className={"chat-msg " + (m.from === a ? "theirs" : "mine") + (m.removed ? " removed" : "") + (m.id === highlight ? " flagged" : "")}>
            <span className="chat-author">{name(m.from)}</span>
            <div className="chat-bubble">{m.removed ? "Removed by a moderator." : m.text}</div>
            <span className="chat-meta">{when(m.createdAt)}
              {!m.removed && <button type="button" className="text-button danger" onClick={async () => {
                if (!window.confirm("Remove this message? Both members will see that a moderator removed it.")) return;
                try { await removeMessage(chat.id, m.id); toast.success("Message removed."); } catch (e) { toast.error(friendlyError(e)); }
              }}><Trash2 size={12} /> Remove</button>}
            </span>
          </div>
        ))}
      </div>
    </aside>
  );
}

function Moderators({ people, monitors, owner, meId }: { people: any[]; monitors: string[]; owner: boolean; meId: string }) {
  const [pick, setPick] = useState(""), [busy, setBusy] = useState(false);
  const options = useMemo(() => people.filter((p) => !monitors.includes(p.id) && p.id !== meId).sort((x, y) => x.name.localeCompare(y.name)), [people, monitors, meId]);
  async function save(next: string[], done: string) {
    setBusy(true);
    try { await saveMonitors(next); toast.success(done); setPick(""); } catch (e) { toast.error(friendlyError(e)); } finally { setBusy(false); }
  }
  return (
    <div className="glass moderators">
      <p className="micro">The administrators of this community on IHP-WINS are always moderators. {owner ? "You can appoint other members as moderators, and remove them." : "Only they can appoint or remove moderators."}</p>
      <ul>
        <li><ShieldCheck size={16} /><strong>IHP-WINS administrators</strong><span className="micro">Sysadmins and admins of the group</span></li>
        {monitors.map((id) => {
          const p = people.find((x) => x.id === id);
          return (
            <li key={id}>
              <MemberAvatar name={p?.name || "Member"} uid={id} hasPhoto={p?.hasPhoto} />
              <strong>{p?.name || "Member"}</strong><span className="micro">{p?.headline || ""}</span>
              {owner && <button type="button" className="text-button danger" disabled={busy} onClick={() => save(monitors.filter((x) => x !== id), "Moderator removed.")}>Remove</button>}
            </li>
          );
        })}
      </ul>
      {owner && (
        <div className="row moderator-add">
          <select value={pick} onChange={(e) => setPick(e.target.value)} aria-label="Member to appoint as moderator">
            <option value="">Choose a member</option>
            {options.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button type="button" className="btn small primary" disabled={!pick || busy || monitors.length >= 20} onClick={() => save([...monitors, pick], "Moderator appointed.")}><UserPlus size={14} /> Appoint as moderator</button>
        </div>
      )}
    </div>
  );
}
