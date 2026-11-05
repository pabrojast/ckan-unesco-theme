import { doc, getDoc } from "firebase/firestore";
import { db } from "./firebase";
const cache = new Map<string, Promise<string>>();
export function getProfilePhoto(uid: string, version = "") {
  const key = uid + ":" + version;
  if (!cache.has(key))
    cache.set(
      key,
      getDoc(doc(db!, "profilePhotos", uid))
        .then((s) => (s.exists() ? s.data().data : ""))
        .catch(() => ""),
    );
  return cache.get(key)!;
}
export function clearPhotoCache(uid: string) {
  for (const key of cache.keys())
    if (key.startsWith(uid + ":")) cache.delete(key);
}
export async function resizePhoto(file: File): Promise<string> {
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type))
    throw Error("Choose a JPEG, PNG or WebP photo.");
  if (file.size > 10 * 1024 * 1024)
    throw Error("Choose a photo smaller than 10 MB.");
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 256;
    const side = Math.min(img.naturalWidth, img.naturalHeight);
    canvas
      .getContext("2d")!
      .drawImage(
        img,
        (img.naturalWidth - side) / 2,
        (img.naturalHeight - side) / 2,
        side,
        side,
        0,
        0,
        256,
        256,
      );
    for (const quality of [0.82, 0.65, 0.45, 0.3]) {
      const data = canvas.toDataURL("image/jpeg", quality);
      if (data.length <= 100000) return data;
    }
    throw Error("This photo is too detailed. Choose another image.");
  } finally {
    URL.revokeObjectURL(url);
  }
}
