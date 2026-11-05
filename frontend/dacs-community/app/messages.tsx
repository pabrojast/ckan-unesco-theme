import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Flag, LogOut, MessageCircle, Search, Send, Settings2, ShieldCheck, UserRound, Users, X } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { chatIdFor, createGroup, isGroup, isUnread, leaveGroup, markRead, MAX_GROUP, otherMember, reportChat, sendMessage, sendToChat, subscribeMessages, updateGroup, type Chat, type ChatMessage } from "@/lib/chat-store";
import { friendlyError } from "@/lib/store";
import { MemberAvatar } from "./member-avatar";
import { MemberBadges } from "./member-badges";

const time = (s: string) => (s ? new Date(s).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) : "");
const dayLabel = (s: string) => {
  const d = new Date(s), today = new Date();
  const y = new Date(); y.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === y.toDateString()) return "Yesterday";
  return d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: d.getFullYear() === today.getFullYear() ? undefined : "numeric" });
};
const shortWhen = (s: string) => {
  if (!s) return "";
  const d = new Date(s);
  return d.toDateString() === new Date().toDateString() ? time(s) : d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
};
const first = (name: string) => (name || "").split(" ")[0];

export const MONITORING_NOTICE = "Conversations are private between Members. However, to keep the community safe, you may report a conversation to UNESCO Secretariat.";

/** Title and preview of a conversation in lists (Messages and the notification centre). */
export function chatSummary(c: Chat, me: string, people: any[]) {
  const nameOf = (id: string) => people.find((p) => p.id === id)?.name || c.names?.[id] || "Member";
  const title = isGroup(c) ? c.title || "Group conversation" : nameOf(otherMember(c, me));
  const who = c.lastMessage?.from === me ? "You: " : isGroup(c) && c.lastMessage?.from ? first(nameOf(c.lastMessage.from)) + ": " : "";
  const text = c.lastMessage?.text ? who + c.lastMessage.text : isGroup(c) ? `Group created by ${c.createdBy === me ? "you" : nameOf(c.createdBy || "")}` : "";
  return { title, text };
}

/** Messages: the member's conversations and one open conversation. A key "u:<id>" opens a person, "c:<id>" a conversation. */
export function Messages({ me, people, chats, target, onTargetUsed, onOpenProfile }: { me: any; people: any[]; chats: Chat[]; target?: { id?: string; chatId?: string } | null; onTargetUsed?: () => void; onOpenProfile?: (p: any) => void }) {
  const [active, setActive] = useState<string>("");
  const [search, setSearch] = useState(""), [grouping, setGrouping] = useState<Chat | "new" | null>(null);
  useEffect(() => {
    if (!target) return;
    if (target.chatId) setActive("c:" + target.chatId);
    else if (target.id && target.id !== me.id) setActive("u:" + target.id);
    onTargetUsed?.();
  }, [target]);
  const personOf = (id: string, chat?: Chat) => people.find((p) => p.id === id) || { id, name: chat?.names?.[id] || "Member", headline: "" };
  const found = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [];
    return people.filter((p) => p.id !== me.id && !p.banned && [p.name, p.organisation, p.headline].join(" ").toLowerCase().includes(q)).slice(0, 8);
  }, [search, people, me.id]);
  // The open conversation, and for a conversation between two people, the other person.
  const chat = active.startsWith("c:") ? chats.find((c) => c.id === active.slice(2)) : active.startsWith("u:") ? chats.find((c) => c.id === chatIdFor(me.id, active.slice(2))) : undefined;
  const otherId = active.startsWith("u:") ? active.slice(2) : chat && !isGroup(chat) ? otherMember(chat, me.id) : "";
  const keyOf = (c: Chat) => (isGroup(c) ? "c:" + c.id : "u:" + otherMember(c, me.id));
  // A group the member has left, or a conversation not loaded yet, closes the thread.
  const seen = useRef(new Set<string>());
  useEffect(() => {
    if (active.startsWith("c:") && seen.current.has(active.slice(2)) && !chat) setActive("");
    chats.forEach((c) => seen.current.add(c.id));
  }, [chats, active]);
  return (
    <section className={"messages" + (active ? " has-active" : "")} aria-label="Messages">
      <aside className="chat-list glass">
        <div className="chat-list-top">
          <div className="chat-search">
            <Search size={15} />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Find a member to write to" aria-label="Find a member to write to" />
          </div>
          <button type="button" className="btn small" onClick={() => setGrouping("new")} title="Start a conversation with several members"><Users size={14} /> New group</button>
        </div>
        {found.length > 0 && (
          <ul className="chat-found">
            {found.map((p) => (
              <li key={p.id}><button type="button" onClick={() => { setActive("u:" + p.id); setSearch(""); }}>
                <MemberAvatar name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt} />
                <span><strong>{p.name}</strong><small>{p.membershipBadges?.[0]?.label || p.headline || p.organisation}</small></span>
              </button></li>
            ))}
          </ul>
        )}
        <p className="chat-notice"><ShieldCheck size={14} /> {MONITORING_NOTICE}</p>
        {!chats.length && !found.length && (
          <div className="agenda-empty"><MessageCircle size={22} /><p>No conversation yet. Find a member above, open a profile and choose “Send a message”, or start a group.</p></div>
        )}
        <ul className="chat-threads">
          {chats.map((c) => {
            const unread = isUnread(c, me.id), s = chatSummary(c, me.id, people), group = isGroup(c);
            const other = group ? null : personOf(otherMember(c, me.id), c);
            return (
              <li key={c.id}>
                <button type="button" className={(keyOf(c) === active || ("c:" + c.id) === active ? "on " : "") + (unread ? "unread" : "")} onClick={() => setActive(keyOf(c))}>
                  {group ? <span className="group-avatar"><Users size={18} /></span> : <MemberAvatar name={other!.name} uid={other!.id} hasPhoto={other!.hasPhoto} version={other!.updatedAt} />}
                  <span className="chat-thread-text">
                    <span className="chat-thread-top"><strong>{s.title}</strong><small>{shortWhen(c.updatedAt)}</small></span>
                    <span className="chat-thread-role">{group ? `${c.members.length} members` : other!.membershipBadges?.[0]?.label || ""}</span>
                    <span className="chat-thread-preview">{s.text}</span>
                  </span>
                  {unread && <i className="chat-dot" aria-label="Unread" />}
                </button>
              </li>
            );
          })}
        </ul>
      </aside>
      {active ? (
        <Thread key={active} me={me} people={people} chat={chat} other={otherId ? personOf(otherId, chat) : null}
          onBack={() => setActive("")} onOpenProfile={onOpenProfile} onManage={(c) => setGrouping(c)} />
      ) : (
        <div className="chat-thread glass chat-placeholder">
          <MessageCircle size={34} />
          <h2>Your messages</h2>
          <p>Choose a conversation, find a member, or start a group conversation.</p>
        </div>
      )}
      <GroupDialog open={!!grouping} chat={grouping === "new" ? null : grouping} me={me} people={people} onClose={() => setGrouping(null)} onCreated={(id) => setActive("c:" + id)} />
    </section>
  );
}

function Thread({ me, people, chat, other, onBack, onOpenProfile, onManage }: { me: any; people: any[]; chat?: Chat; other: any | null; onBack: () => void; onOpenProfile?: (p: any) => void; onManage: (c: Chat) => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]), [text, setText] = useState(""), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [report, setReport] = useState<{ messageId: string } | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const exists = !!chat, group = isGroup(chat);
  const nameOf = (id: string) => people.find((p) => p.id === id)?.name || chat?.names?.[id] || "Member";
  useEffect(() => {
    setError("");
    if (!exists) { setMessages([]); return; }
    return subscribeMessages(chat!.id, setMessages, (e) => setError(friendlyError(e)));
  }, [exists, chat?.id]);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages.length]);
  useEffect(() => { if (chat && isUnread(chat, me.id)) markRead(chat.id, me.id).catch(() => {}); }, [chat?.updatedAt]);
  async function send() {
    if (!text.trim() || busy) return;
    setBusy(true); setError("");
    try {
      if (chat) await sendToChat(chat, me, text);
      else if (other) await sendMessage({ id: me.id, name: me.name }, { id: other.id, name: other.name }, text);
      setText("");
    } catch (e: any) {
      setError(e?.code === "permission-denied" ? "Your message could not be sent. Reload the page and try again; if it persists, contact the UNESCO Secretariat." : friendlyError(e));
    }
    finally { setBusy(false); }
  }
  async function leave() {
    if (!chat || !window.confirm(`Leave “${chat.title}”? You will no longer see this conversation.`)) return;
    try { await leaveGroup(chat, me.id); toast.success("You have left the group."); onBack(); } catch (e) { toast.error(friendlyError(e)); }
  }
  const label = group ? chat!.title || "Group conversation" : other?.name || "Member";
  let lastDay = "";
  return (
    <div className="chat-thread glass">
      <header className="chat-head">
        <button type="button" className="btn small icon-only chat-back" onClick={onBack} aria-label="Back to conversations"><ArrowLeft size={16} /></button>
        {group ? <span className="group-avatar"><Users size={18} /></span> : <MemberAvatar name={other?.name} uid={other?.id} hasPhoto={other?.hasPhoto} version={other?.updatedAt} />}
        <div className="chat-head-name">
          <strong>{label}</strong>
          {group ? (
            <small>{chat!.members.map((m) => (m === me.id ? "You" : first(nameOf(m)))).join(", ")}</small>
          ) : (
            <MemberBadges badges={other?.membershipBadges} compact />
          )}
        </div>
        {!group && onOpenProfile && other?.createdAt && <button type="button" className="btn small" onClick={() => onOpenProfile(other)} aria-label="Open the profile"><UserRound size={14} /><span className="btn-label"> Profile</span></button>}
        {group && chat!.createdBy === me.id && <button type="button" className="btn small" onClick={() => onManage(chat!)} aria-label="Manage the group"><Settings2 size={14} /><span className="btn-label"> Manage</span></button>}
        {group && <button type="button" className="btn small" onClick={leave} aria-label="Leave the group"><LogOut size={14} /><span className="btn-label"> Leave</span></button>}
        {exists && <button type="button" className="btn small" onClick={() => setReport({ messageId: "" })} aria-label="Report this conversation"><Flag size={14} /><span className="btn-label"> Report</span></button>}
      </header>
      <div className="chat-body" aria-live="polite">
        {!messages.length && <p className="chat-empty">{exists && chat!.lastMessage?.text ? "Loading…" : group ? "Write the first message to the group." : `Write your first message to ${first(label)}.`}</p>}
        {messages.map((m, i) => {
          const d = m.createdAt ? new Date(m.createdAt).toDateString() : "";
          const sep = d && d !== lastDay ? ((lastDay = d), <div className="chat-day" key={"d" + m.id}><span>{dayLabel(m.createdAt)}</span></div>) : null;
          const mine = m.from === me.id, showName = group && !mine && messages[i - 1]?.from !== m.from;
          return [sep, (
            <div key={m.id} className={"chat-msg " + (mine ? "mine" : "theirs") + (m.removed ? " removed" : "")}>
              {showName && <span className="chat-author">{nameOf(m.from)}</span>}
              <div className="chat-bubble">{m.removed ? "This message was removed by a moderator." : m.text}</div>
              <span className="chat-meta">{time(m.createdAt)}{!mine && !m.removed && <button type="button" className="text-button" onClick={() => setReport({ messageId: m.id })}>Report</button>}</span>
            </div>
          )];
        })}
        <div ref={end} />
      </div>
      {error && <p className="error-banner" role="alert">{error}</p>}
      <form className="chat-composer" onSubmit={(e) => { e.preventDefault(); void send(); }}>
        <textarea rows={1} maxLength={4000} value={text} placeholder={group ? `Message ${label}` : `Message ${first(label)}`} aria-label={`Message ${label}`}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }} />
        <button className="btn primary" disabled={busy || !text.trim()} aria-label="Send"><Send size={16} /></button>
      </form>
      <ReportDialog open={!!report} onClose={() => setReport(null)} chatId={chat?.id || ""} messageId={report?.messageId || ""} reporterName={me.name} />
    </div>
  );
}

/** Creates a group conversation, or lets its creator rename it and change its members. */
function GroupDialog({ open, chat, me, people, onClose, onCreated }: { open: boolean; chat: Chat | null; me: any; people: any[]; onClose: () => void; onCreated: (id: string) => void }) {
  const [title, setTitle] = useState(""), [picked, setPicked] = useState<any[]>([]), [search, setSearch] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    setTitle(chat?.title || ""); setSearch("");
    setPicked(chat ? chat.members.filter((m) => m !== me.id).map((id) => people.find((p) => p.id === id) || { id, name: chat.names[id] || "Member" }) : []);
  }, [open, chat?.id]);
  const options = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? people.filter((p) => p.id !== me.id && !p.banned && !picked.some((x) => x.id === p.id) && [p.name, p.organisation].join(" ").toLowerCase().includes(q)).slice(0, 6) : [];
  }, [search, people, picked, me.id]);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (picked.length < 2) { toast.info("Choose at least two other members."); return; }
    setBusy(true);
    try {
      if (chat) { await updateGroup(chat, title, [me, ...picked]); toast.success("Group updated."); }
      else { const id = await createGroup({ id: me.id, name: me.name }, picked, title); onCreated(id); toast.success("Group created."); }
      onClose();
    } catch (err) { toast.error(friendlyError(err)); } finally { setBusy(false); }
  }
  return (
    <Dialog open={open} onOpenChange={(v) => !v && !busy && onClose()}>
      <DialogContent className="detail-content auth-dialog group-dialog">
        <DialogTitle>{chat ? "Manage the group" : "New group conversation"}</DialogTitle>
        <DialogDescription>{chat ? "Rename the group, or add and remove members." : `Write to several members at once, up to ${MAX_GROUP} people.`}</DialogDescription>
        <form className="stack" onSubmit={save}>
          <label className="field-label">Name of the group<input required maxLength={80} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="For example: WG4 case studies team" /></label>
          <label className="field-label">Members<input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Type a name to add a member" /></label>
          {options.length > 0 && (
            <ul className="chat-found">
              {options.map((p) => (
                <li key={p.id}><button type="button" onClick={() => { setPicked([...picked, p].slice(0, MAX_GROUP - 1)); setSearch(""); }}>
                  <MemberAvatar name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt} />
                  <span><strong>{p.name}</strong><small>{p.membershipBadges?.[0]?.label || p.organisation}</small></span>
                </button></li>
              ))}
            </ul>
          )}
          <div className="group-picked">
            <span className="group-chip me">You</span>
            {picked.map((p) => <span key={p.id} className="group-chip">{p.name}<button type="button" aria-label={`Remove ${p.name}`} onClick={() => setPicked(picked.filter((x) => x.id !== p.id))}><X size={12} /></button></span>)}
          </div>
          <div className="toolbar"><button className="btn primary" disabled={busy || picked.length < 2 || !title.trim()}>{busy ? "Saving…" : chat ? "Save" : "Create the group"}</button><button type="button" className="btn" onClick={onClose}>Cancel</button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ReportDialog({ open, onClose, chatId, messageId, reporterName }: { open: boolean; onClose: () => void; chatId: string; messageId: string; reporterName: string }) {
  const [reason, setReason] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => { if (open) setReason(""); }, [open]);
  return (
    <Dialog open={open} onOpenChange={(v) => !v && !busy && onClose()}>
      <DialogContent className="detail-content auth-dialog">
        <DialogTitle>{messageId ? "Report this message" : "Report this conversation"}</DialogTitle>
        <DialogDescription>Your report goes to the UNESCO Secretariat, which can then read the conversation. The other members are not notified.</DialogDescription>
        <form className="stack" onSubmit={async (e) => {
          e.preventDefault(); setBusy(true);
          try { await reportChat(chatId, messageId, reason, reporterName); toast.success("Report sent to the UNESCO Secretariat."); onClose(); }
          catch (err) { toast.error(friendlyError(err)); }
          finally { setBusy(false); }
        }}>
          <label className="field-label">What is the problem?<textarea required maxLength={1000} rows={4} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="For example: harassment, spam, inappropriate content." /></label>
          <div className="toolbar"><button className="btn danger" disabled={busy || !reason.trim()}><Flag size={14} /> {busy ? "Sending…" : "Send the report"}</button><button type="button" className="btn" onClick={onClose}>Cancel</button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
