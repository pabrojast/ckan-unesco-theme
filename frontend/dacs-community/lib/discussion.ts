// Pure helpers for Working Group discussions and @mentions.
export type DiscussionMessage = {
  id: string; space: string; parent: string; author: string; author_name: string;
  body: string; mentions: string[]; deleted: boolean; createdAt: string; updatedAt: string;
  attachments?: { id: string; name: string; type: 'pdf' | 'doc' | 'docx' | 'ppt' | 'pptx'; size: number; body: string }[];
};
export const discussionSpaces = ['wg1', 'wg2', 'wg3', 'wg4', 'wg5'];
export const fold = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
/** The @query being typed just before the caret, if any. */
export function mentionQuery(beforeCaret: string): { query: string; start: number } | null {
  const m = /(^|[\s([{"'“])@([^@\n]{0,40})$/u.exec(beforeCaret);
  if (!m) return null;
  const query = m[2];
  if ((query.match(/ /g) || []).length > 3) return null;
  return { query, start: beforeCaret.length - query.length - 1 };
}
export function mentionSuggestions<T extends { id: string; name: string }>(people: T[], query: string, exclude: string, max = 6) {
  const q = fold(query.trim());
  return people
    .filter((p) => p.id !== exclude && p.name && (!q || fold(p.name).split(/\s+/).some((w) => w.startsWith(q)) || fold(p.name).startsWith(q) || fold(p.name).includes(q)))
    .sort((a, b) => Number(!fold(a.name).startsWith(q)) - Number(!fold(b.name).startsWith(q)) || a.name.localeCompare(b.name))
    .slice(0, max);
}
/** Mentioned people whose @Name is still present in the text, without duplicates (at most 20). */
export function activeMentions(text: string, tagged: { id: string; name: string }[]) {
  return [...new Set(tagged.filter((t) => t.name && text.includes('@' + t.name)).map((t) => t.id))].slice(0, 20);
}
/** Splits a message into plain text and @Name segments for the given names. */
export function splitMentions(text: string, names: string[]) {
  const list = [...new Set(names.filter(Boolean))].sort((a, b) => b.length - a.length);
  if (!list.length) return [{ text, mention: false }];
  const re = new RegExp('(' + list.map((n) => '@' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')', 'g');
  return text.split(re).filter((s) => s !== '').map((s) => ({ text: s, mention: list.some((n) => s === '@' + n) }));
}
/** Topics newest first; replies oldest first under their topic. Replies whose topic is missing are dropped. */
export function threadsFrom(messages: DiscussionMessage[]) {
  const at = (m: DiscussionMessage) => String(m.createdAt || '9999'); // a message still being saved is the newest
  const topics = messages.filter((m) => !m.parent).sort((a, b) => at(b).localeCompare(at(a)));
  const replies = (id: string) => messages.filter((m) => m.parent === id).sort((a, b) => at(a).localeCompare(at(b)));
  return topics.map((t) => ({ topic: t, replies: replies(t.id) })).filter((t) => !t.topic.deleted || t.replies.length > 0);
}
/** True when a message was changed noticeably after it was posted. */
export const wasEdited = (m: Pick<DiscussionMessage, 'createdAt' | 'updatedAt' | 'deleted'>) =>
  !m.deleted && Date.parse(m.updatedAt) - Date.parse(m.createdAt) > 5000;
export function timeAgo(iso: string, now = Date.now()) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return 'just now';
  const s = Math.round((t - now) / 1000), a = Math.abs(s), rtf = new Intl.RelativeTimeFormat('en-GB', { numeric: 'auto' });
  if (a < 45) return 'just now';
  if (a < 3600) return rtf.format(Math.round(s / 60), 'minute');
  if (a < 86400) return rtf.format(Math.round(s / 3600), 'hour');
  if (a < 604800) return rtf.format(Math.round(s / 86400), 'day');
  return new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}
