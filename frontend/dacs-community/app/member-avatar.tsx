import { useEffect, useState } from "react";
import { getProfilePhoto } from "@/lib/photos";
export function MemberAvatar({
  name,
  large = false,
  uid,
  hasPhoto = false,
  version = "",
  photo,
}: {
  name: string;
  large?: boolean;
  uid?: string;
  hasPhoto?: boolean;
  version?: string;
  photo?: string;
}) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    let active = true;
    setSrc("");
    if (uid && hasPhoto)
      getProfilePhoto(uid, version).then((v) => {
        if (active) setSrc(v);
      });
    return () => {
      active = false;
    };
  }, [uid, hasPhoto, version]);
  const initials = (name || "?")
    .split(" ")
    .slice(0, 2)
    .map((x) => x[0])
    .join("")
    .toUpperCase();
  return (
    <div className={"avatar " + (large ? "large" : "")} aria-hidden="true">
      {photo || src ? <img src={photo || src} alt="" /> : initials}
    </div>
  );
}
