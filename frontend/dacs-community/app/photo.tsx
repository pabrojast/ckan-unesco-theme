import type { Photo } from "@/lib/imagery";

/** Credit line required on every photograph. */
export function PhotoCredit({ photo, className = "" }: { photo: Photo; className?: string }) {
  return (
    <a
      className={"photo-credit " + className}
      href={photo.creditUrl}
      target="_blank"
      rel="noopener noreferrer"
      title={"Photograph: " + photo.credit}
    >
      {photo.credit}
    </a>
  );
}

/** Background photograph that fills its positioned parent, with its credit in the corner. */
export function PhotoBackdrop({
  photo,
  eager = false,
  credit = true,
  sizes = "(max-width: 800px) 100vw, 1200px",
}: {
  photo: Photo;
  eager?: boolean;
  credit?: boolean;
  sizes?: string;
}) {
  return (
    <>
      <img
        className="photo-backdrop"
        src={photo.src}
        srcSet={`${photo.small} 800w, ${photo.src} 1600w`}
        sizes={sizes}
        alt=""
        loading={eager ? "eager" : "lazy"}
        decoding="async"
        style={{ objectPosition: photo.position }}
      />
      {credit && <PhotoCredit photo={photo} />}
    </>
  );
}
