import { useEffect, useId, useMemo, useRef, useState } from "react";
import { AtSign, MessagesSquare, Paperclip, Pencil, Reply, Send, Trash2, UserRound } from "lucide-react";
import { AttachmentList, AttachmentPicker } from "./attachments";
import type { Attachment } from "@/lib/files-store";
import { toast } from "sonner";
import { MemberAvatar } from "./member-avatar";
import { friendlyError } from "@/lib/store";
import {
  activeMentions,
  mentionQuery,
  mentionSuggestions,
  splitMentions,
  threadsFrom,
  timeAgo,
  wasEdited,
  type DiscussionMessage,
} from "@/lib/discussion";
import { DISCUSSION_LIMIT, editMessage, postMessage, removeMessage, subscribeDiscussion } from "@/lib/discussion-store";

type Person = { id: string; name: string; hasPhoto?: boolean; updatedAt?: string; headline?: string };
type Tag = { id: string; name: string };
const VISIBLE_REPLIES = 3;
const fullDate = (iso: string) =>
  iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "";

/** Working Group discussion: topics, replies and @mentions that notify members in the Hub. */
export function GroupDiscussion({
  space,
  label,
  me,
  people,
  moderator,
  focusId,
  onFocused,
  onCreateProfile,
  fileBody = null,
}: {
  space: string;
  label: string;
  me: Person | null;
  people: Person[];
  moderator: boolean;
  focusId?: string;
  onFocused?: () => void;
  onCreateProfile: () => void;
  /** Body under which this member shares files here, or null when they cannot share files. */
  fileBody?: string | null;
}) {
  const [messages, setMessages] = useState<DiscussionMessage[] | null>(null);
  const [capped, setCapped] = useState(false);
  const [error, setError] = useState("");
  const [replyTo, setReplyTo] = useState<{ thread: string; seed: Tag | null; nonce: number } | null>(null);
  const [editing, setEditing] = useState("");
  const [expanded, setExpanded] = useState<string[]>([]);
  const [flash, setFlash] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setMessages(null);
    setError("");
    setReplyTo(null);
    setEditing("");
    if (!me) return;
    return subscribeDiscussion(
      space,
      (m, c) => {
        setMessages(m);
        setCapped(c);
      },
      (e) => setError(friendlyError(e)),
    );
  }, [space, !!me]);

  const threads = useMemo(() => threadsFrom(messages || []), [messages]);
  const byId = useMemo(() => new Map(people.map((p) => [p.id, p])), [people]);
  const nameOf = (id: string) => byId.get(id)?.name || "";

  // Opened from a notification: show the message, highlight it and open a reply to its author.
  useEffect(() => {
    if (!focusId || !messages || !me) return;
    const m = messages.find((x) => x.id === focusId);
    onFocused?.();
    if (!m) {
      toast.info(capped ? `That message is older than the latest ${DISCUSSION_LIMIT} messages.` : "That message has been removed.");
      return;
    }
    const thread = m.parent || m.id;
    setExpanded((e) => (e.includes(thread) ? e : [...e, thread]));
    setEditing("");
    setReplyTo({ thread, seed: m.author !== me.id ? { id: m.author, name: m.author_name } : null, nonce: Date.now() });
    setFlash(m.id);
    window.setTimeout(() => document.getElementById("msg-" + m.id)?.scrollIntoView({ behavior: "smooth", block: "center" }), 120);
  }, [focusId, messages]);
  useEffect(() => {
    if (!flash) return;
    const t = window.setTimeout(() => setFlash(""), 2800);
    return () => window.clearTimeout(t);
  }, [flash]);

  if (!me)
    return (
      <section className="glass discussion" aria-labelledby={space + "-discussion"}>
        <div className="section-title">
          <h2 id={space + "-discussion"}><MessagesSquare size={18} /> Discussion</h2>
        </div>
        <div className="discussion-empty">
          <UserRound size={26} />
          <p>Create your profile to read and join the discussion of {label}.</p>
          <button className="btn primary" onClick={onCreateProfile}>Create my profile</button>
        </div>
      </section>
    );
  const self = me;

  async function run(action: () => Promise<unknown>, done?: string) {
    setBusy(true);
    try {
      await action();
      if (done) toast.success(done);
      return true;
    } catch (e) {
      toast.error(friendlyError(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  const notifiedText = (n: number) => (n ? ` ${n} ${n === 1 ? "member was" : "members were"} notified.` : "");
  const post = (parent: string) => (body: string, mentions: string[], attachments: Attachment[] = []) =>
    run(() => postMessage({ space, parent, body, mentions, authorName: self.name, attachments }), (parent ? "Reply posted." : "Topic posted.") + notifiedText(mentions.length)).then((ok) => {
      if (ok && parent) setReplyTo(null);
      return ok;
    });
  const save = (m: DiscussionMessage) => (body: string, mentions: string[]) => {
    const added = mentions.filter((x) => !m.mentions.includes(x)).length;
    return run(() => editMessage(m, body, mentions, self.name), "Message updated." + notifiedText(added)).then((ok) => {
      if (ok) setEditing("");
      return ok;
    });
  };
  function remove(m: DiscussionMessage, hasReplies: boolean) {
    const own = m.author === self.id;
    if (!window.confirm(own ? "Remove your message?" : `Remove this message by ${m.author_name}?`)) return;
    void run(() => removeMessage(m, hasReplies), "Message removed.");
  }
  function startReply(thread: string, m: DiscussionMessage) {
    setEditing("");
    setExpanded((e) => (e.includes(thread) ? e : [...e, thread]));
    setReplyTo({ thread, seed: m.author !== self.id ? { id: m.author, name: m.author_name } : null, nonce: Date.now() });
  }
  const tagsFor = (m: DiscussionMessage) => m.mentions.map((id) => ({ id, name: nameOf(id) })).filter((t) => t.name);
  const renderBody = (m: DiscussionMessage) =>
    splitMentions(m.body, tagsFor(m).map((t) => t.name)).map((s, i) =>
      s.mention ? (
        <span key={i} className={"mention" + (m.mentions.includes(self.id) && s.text === "@" + self.name ? " me" : "")}>{s.text}</span>
      ) : (
        <span key={i}>{s.text}</span>
      ),
    );
  const message = (m: DiscussionMessage, thread: { topic: DiscussionMessage; replies: DiscussionMessage[] }, isReply: boolean) => {
    const person = byId.get(m.author);
    const own = m.author === self.id;
    const hasReplies = !isReply && thread.replies.length > 0;
    return (
      <div className={"msg" + (isReply ? " reply" : " topic") + (flash === m.id ? " flash" : "") + (m.deleted ? " removed" : "")} id={"msg-" + m.id} key={m.id}>
        <MemberAvatar name={m.author_name} uid={m.author} hasPhoto={person?.hasPhoto} version={person?.updatedAt} />
        <div className="msg-main">
          <div className="msg-head">
            <strong>{m.author_name}</strong>
            {own && <span className="pill">You</span>}
            <time dateTime={m.createdAt} title={fullDate(m.createdAt)}>{timeAgo(m.createdAt)}</time>
            {wasEdited(m) && <span className="micro" title={fullDate(m.updatedAt)}>· edited</span>}
          </div>
          {editing === m.id ? (
            <Composer
              people={people}
              meId={self.id}
              initial={m.body}
              initialTags={tagsFor(m)}
              label="Edit your message"
              submitLabel="Save"
              busy={busy}
              compact
              autoFocus
              onSubmit={save(m)}
              onCancel={() => setEditing("")}
            />
          ) : m.deleted ? (
            <p className="msg-removed">This message was removed.</p>
          ) : (
            <><p className="msg-body">{renderBody(m)}</p><AttachmentList items={m.attachments} compact /></>
          )}
          {!m.deleted && editing !== m.id && (
            <div className="msg-actions">
              {!thread.topic.deleted && (
                <button type="button" className="msg-action" onClick={() => startReply(thread.topic.id, m)}>
                  <Reply size={14} /> Reply
                </button>
              )}
              {own && (
                <button type="button" className="msg-action" onClick={() => { setReplyTo(null); setEditing(m.id); }}>
                  <Pencil size={13} /> Edit
                </button>
              )}
              {(own || moderator) && (
                <button type="button" className="msg-action remove" disabled={busy} onClick={() => remove(m, hasReplies)}>
                  <Trash2 size={13} /> Remove
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };
  return (
    <section className="glass discussion" aria-labelledby={space + "-discussion"}>
      <div className="section-title">
        <h2 id={space + "-discussion"}><MessagesSquare size={18} /> Discussion</h2>
        {messages && threads.length > 0 && <span className="micro">{threads.length} {threads.length === 1 ? "topic" : "topics"}</span>}
      </div>
      <p className="micro discussion-intro">
        Open to all members of the Hub. Type @ to tag a member: they receive a notification in the Hub and can open your message to reply.
      </p>
      <Composer
        people={people}
        meId={self.id}
        label={"New topic for " + label}
        placeholder={"Start a topic for " + label + "…"}
        submitLabel="Post topic"
        busy={busy}
        fileBody={fileBody}
        onSubmit={post("")}
      />
      {error && <p className="error-banner" role="alert">{error}</p>}
      {!messages && !error && <p className="micro discussion-loading">Loading the discussion…</p>}
      {messages && threads.length === 0 && (
        <div className="discussion-empty">
          <MessagesSquare size={26} />
          <p>No topic yet. Ask a question, share a document reference or propose next steps.</p>
        </div>
      )}
      <div className="threads">
        {threads.map((t) => {
          const open = expanded.includes(t.topic.id);
          const hidden = open ? 0 : Math.max(0, t.replies.length - VISIBLE_REPLIES);
          return (
            <article className="thread" key={t.topic.id} aria-label={"Topic by " + t.topic.author_name}>
              {message(t.topic, t, false)}
              {(t.replies.length > 0 || replyTo?.thread === t.topic.id) && (
                <div className="replies">
                  {hidden > 0 && (
                    <button type="button" className="text-button more-replies" onClick={() => setExpanded((e) => [...e, t.topic.id])}>
                      Show {hidden} earlier {hidden === 1 ? "reply" : "replies"}
                    </button>
                  )}
                  {t.replies.slice(hidden).map((r) => message(r, t, true))}
                  {replyTo?.thread === t.topic.id && !t.topic.deleted && (
                    <div className="reply-composer">
                      <Composer
                        key={replyTo.nonce}
                        people={people}
                        meId={self.id}
                        initial={replyTo.seed ? "@" + replyTo.seed.name + " " : ""}
                        initialTags={replyTo.seed ? [replyTo.seed] : []}
                        label={"Reply to " + t.topic.author_name}
                        placeholder="Write a reply…"
                        submitLabel="Reply"
                        busy={busy}
                        compact
                        autoFocus
                        fileBody={fileBody}
                        onSubmit={post(t.topic.id)}
                        onCancel={() => setReplyTo(null)}
                      />
                    </div>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
      {capped && <p className="notice">Showing the latest {DISCUSSION_LIMIT} messages.</p>}
    </section>
  );
}

/** Message box with @mention suggestions. Ctrl or Cmd + Enter sends. */
function Composer({
  people,
  meId,
  initial = "",
  initialTags = [],
  label,
  placeholder,
  submitLabel,
  busy,
  compact = false,
  autoFocus = false,
  fileBody = null,
  onSubmit,
  onCancel,
}: {
  people: Person[];
  meId: string;
  initial?: string;
  initialTags?: Tag[];
  label: string;
  placeholder?: string;
  submitLabel: string;
  busy: boolean;
  compact?: boolean;
  autoFocus?: boolean;
  fileBody?: string | null;
  onSubmit: (body: string, mentions: string[], attachments?: Attachment[]) => Promise<boolean>;
  onCancel?: () => void;
}) {
  const [text, setText] = useState(initial);
  const [files, setFiles] = useState<Attachment[]>([]), [showFiles, setShowFiles] = useState(false);
  const [tags, setTags] = useState<Tag[]>(initialTags);
  const [menu, setMenu] = useState<{ query: string; start: number } | null>(null);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLTextAreaElement>(null);
  const blurTimer = useRef(0);
  const id = useId();
  const suggestions = menu ? mentionSuggestions(people, menu.query, meId) : [];
  useEffect(() => {
    const el = ref.current;
    if (!autoFocus || !el) return;
    el.focus({ preventScroll: true });
    el.setSelectionRange(el.value.length, el.value.length);
  }, [autoFocus]);
  useEffect(() => () => window.clearTimeout(blurTimer.current), []);
  function sync(el: HTMLTextAreaElement) {
    setMenu(mentionQuery(el.value.slice(0, el.selectionStart ?? el.value.length)));
    setActive(0);
  }
  function place(pos: number) {
    requestAnimationFrame(() => {
      const el = ref.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(pos, pos);
    });
  }
  function pick(p: Person) {
    const el = ref.current;
    if (!el || !menu) return;
    const caret = el.selectionStart ?? text.length;
    const insert = "@" + p.name + " ";
    setText(text.slice(0, menu.start) + insert + text.slice(caret).replace(/^ /, ""));
    setTags((t) => (t.some((x) => x.id === p.id) ? t : [...t, { id: p.id, name: p.name }]));
    setMenu(null);
    place(menu.start + insert.length);
  }
  function startTag() {
    const el = ref.current;
    if (!el) return;
    const caret = el.selectionStart ?? text.length;
    const before = text.slice(0, caret);
    const insert = (before && !/\s$/.test(before) ? " " : "") + "@";
    setText(before + insert + text.slice(caret));
    setMenu({ query: "", start: caret + insert.length - 1 });
    setActive(0);
    place(caret + insert.length);
  }
  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    const body = text.trim();
    if (!body || busy) return;
    if (await onSubmit(body, activeMentions(body, tags), files)) {
      setText("");
      setTags([]);
      setMenu(null);
      setFiles([]);
      setShowFiles(false);
    }
  }
  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (menu && suggestions.length) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        setActive((a) => (a + (e.key === "ArrowDown" ? 1 : suggestions.length - 1)) % suggestions.length);
        return;
      }
      if ((e.key === "Enter" && !e.ctrlKey && !e.metaKey) || e.key === "Tab") {
        e.preventDefault();
        pick(suggestions[Math.min(active, suggestions.length - 1)]);
        return;
      }
    }
    if (e.key === "Escape") {
      if (menu) setMenu(null);
      else onCancel?.();
      e.preventDefault();
      return;
    }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      void submit();
    }
  }
  const notified = activeMentions(text, tags)
    .map((x) => tags.find((t) => t.id === x)?.name)
    .filter(Boolean);
  const listId = id + "-mentions";
  return (
    <form className={"msg-composer" + (compact ? " compact" : "")} onSubmit={submit}>
      <div className="msg-composer-field">
        <textarea
          ref={ref}
          value={text}
          maxLength={3000}
          rows={compact ? 2 : 3}
          placeholder={placeholder}
          aria-label={label}
          aria-autocomplete="list"
          aria-controls={menu ? listId : undefined}
          aria-activedescendant={menu && suggestions.length ? `${listId}-${active}` : undefined}
          onChange={(e) => {
            setText(e.target.value);
            sync(e.target);
          }}
          onKeyDown={onKeyDown}
          onKeyUp={(e) => ["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key) && sync(e.currentTarget)}
          onClick={(e) => sync(e.currentTarget)}
          onFocus={() => window.clearTimeout(blurTimer.current)}
          onBlur={() => {
            blurTimer.current = window.setTimeout(() => setMenu(null), 150);
          }}
        />
        {menu && (
          <ul className="mention-menu" role="listbox" id={listId} aria-label="Members you can tag">
            {suggestions.length ? (
              suggestions.map((p, i) => (
                <li
                  key={p.id}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === active}
                  className={i === active ? "active" : undefined}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    pick(p);
                  }}
                  onMouseEnter={() => setActive(i)}
                >
                  <MemberAvatar name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt} />
                  <span>
                    <strong>{p.name}</strong>
                    {p.headline && <small>{p.headline}</small>}
                  </span>
                </li>
              ))
            ) : (
              <li className="empty" role="presentation">
                {menu.query.trim() ? `No member found for “${menu.query.trim()}”.` : "Type a name to find a member."}
              </li>
            )}
          </ul>
        )}
      </div>
      {fileBody !== null && (showFiles || files.length > 0) && <AttachmentPicker value={files} onChange={setFiles} body={fileBody} />}
      <div className="msg-composer-bar">
        <button type="button" className="btn small" onClick={startTag}>
          <AtSign size={14} /> Tag a member
        </button>
        {fileBody !== null && !showFiles && !files.length && (
          <button type="button" className="btn small" onClick={() => setShowFiles(true)}>
            <Paperclip size={14} /> Attach files
          </button>
        )}
        <span className="msg-composer-hint micro" aria-live="polite">
          {notified.length ? "Will notify " + notified.join(", ") : text.length > 2600 ? `${3000 - text.length} characters left` : ""}
        </span>
        {onCancel && (
          <button type="button" className="btn small" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button className="btn small primary" disabled={busy || !text.trim()} title="Ctrl or Cmd + Enter">
          <Send size={14} /> {submitLabel}
        </button>
      </div>
    </form>
  );
}
