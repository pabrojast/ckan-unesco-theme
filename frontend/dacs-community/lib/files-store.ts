// Files shared by the leadership of a body or the UNESCO Secretariat: PDF, Word and PowerPoint, up to 10 MB.
// Cloud Storage needs the Blaze plan, so on the Spark plan a file is kept in Firestore: a description in
// files/{id} and its content, in base64, split into parts in files/{id}/chunks/{n}.
import { collection, deleteDoc, doc, getDoc, getDocs, serverTimestamp, setDoc } from "firebase/firestore";
import { auth, db } from "./firebase";

export type Attachment = { id: string; name: string; type: FileKind; size: number; body: string };
export type FileKind = "pdf" | "doc" | "docx" | "ppt" | "pptx";
export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const MAX_ATTACHMENTS = 5;
const CHUNK = 900_000;
export const fileAccept = ".pdf,.doc,.docx,.ppt,.pptx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation";
const mime: Record<FileKind, string> = {
  pdf: "application/pdf",
  doc: "application/msword",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ppt: "application/vnd.ms-powerpoint",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
};
export const kindOf = (name: string): FileKind | null => {
  const ext = name.toLowerCase().split(".").pop() || "";
  return (["pdf", "doc", "docx", "ppt", "pptx"] as const).includes(ext as FileKind) ? (ext as FileKind) : null;
};
export const kindLabel = (k: FileKind) => (k === "pdf" ? "PDF" : k.startsWith("doc") ? "Word" : "PowerPoint");
export const sizeLabel = (n: number) => (n >= 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1] || "");
    r.onerror = () => reject(r.error || Error("The file could not be read."));
    r.readAsDataURL(file);
  });
}

/**
 * Uploads a file. `body` is the body whose leadership shares it ('' for the UNESCO Secretariat);
 * `audience` limits reading to a meeting's audience ('all' for every member).
 */
export async function uploadFile(file: File, body: string, audience: "all" | "leadership" | "core" | "broad", progress?: (p: number) => void): Promise<Attachment> {
  const uid = auth?.currentUser?.uid;
  if (!db || !uid) throw Error("Sign in first.");
  const type = kindOf(file.name);
  if (!type) throw Error("Share PDF, Word (.doc, .docx) or PowerPoint (.ppt, .pptx) files only.");
  if (file.size > MAX_FILE_BYTES) throw Error(`“${file.name}” is larger than 10 MB. Share it through SharePoint and add the link instead.`);
  const data = await toBase64(file);
  const parts = Math.max(1, Math.ceil(data.length / CHUNK));
  const ref = doc(collection(db, "files"));
  const name = file.name.slice(0, 200);
  await setDoc(ref, { name, type, size: file.size, chunks: parts, body, audience, uploadedBy: uid, createdAt: serverTimestamp() });
  try {
    for (let i = 0; i < parts; i++) {
      await setDoc(doc(db, "files", ref.id, "chunks", String(i)), { data: data.slice(i * CHUNK, (i + 1) * CHUNK) });
      progress?.((i + 1) / parts);
    }
  } catch (e) {
    await deleteFile(ref.id, parts).catch(() => {});
    throw e;
  }
  return { id: ref.id, name, type, size: file.size, body };
}

export async function deleteFile(id: string, parts?: number) {
  if (!db) return;
  const n = parts ?? ((await getDoc(doc(db, "files", id))).data() as any)?.chunks ?? 0;
  for (let i = 0; i < n; i++) await deleteDoc(doc(db, "files", id, "chunks", String(i))).catch(() => {});
  await deleteDoc(doc(db, "files", id));
}

/** Opens a PDF in a new tab; downloads Word and PowerPoint files. */
export async function openFile(a: Attachment) {
  if (!db) return;
  const win = a.type === "pdf" ? window.open("", "_blank") : null;
  try {
    const s = await getDocs(collection(db, "files", a.id, "chunks"));
    const data = s.docs.sort((x, y) => Number(x.id) - Number(y.id)).map((d) => (d.data() as any).data).join("");
    const bin = atob(data), bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const url = URL.createObjectURL(new Blob([bytes], { type: mime[a.type] }));
    if (win) win.location.href = url;
    else {
      const link = document.createElement("a");
      link.href = url; link.download = a.name; link.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (e) {
    win?.close();
    throw e;
  }
}

export const cleanAttachments = (v: any): Attachment[] =>
  (Array.isArray(v) ? v : []).filter((a) => a && typeof a.id === "string" && kindOf("x." + a.type)).slice(0, MAX_ATTACHMENTS)
    .map((a) => ({ id: a.id, name: String(a.name).slice(0, 200), type: a.type, size: Number(a.size) || 1, body: String(a.body || "") }));
