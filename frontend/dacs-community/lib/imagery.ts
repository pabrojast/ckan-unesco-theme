import { BASE } from "./base";
// Photographs used across the Hub. Every display shows its credit.
// To credit a different photographer for one image, change its `credit` and `creditUrl`.
const oceanImageBank = {
  credit: "@greenlandic_explorer / Ocean Image Bank",
  creditUrl: "https://www.instagram.com/greenlandic_explorer/",
};
export type Photo = {
  id: string;
  src: string;
  small: string;
  alt: string;
  position: string;
  credit: string;
  creditUrl: string;
};
const photo = (id: string, alt: string, position = "center"): Photo => ({
  id,
  src: `${BASE}assets/photos/${id}.webp`,
  small: `${BASE}assets/photos/${id}-800.webp`,
  alt,
  position,
  ...oceanImageBank,
});
export const photos = {
  iceCave: photo("ice-cave-blue", "Blue light inside a glacier ice cave", "center 60%"),
  icebergsAerial: photo("icebergs-aerial", "Aerial view of icebergs over turquoise meltwater", "center 55%"),
  blueIce: photo("blue-ice-ripples", "Rippled surface of blue glacier ice", "center"),
  icebergFjord: photo("iceberg-fjord", "Iceberg in a calm polar fjord at dusk", "center 62%"),
  iceCrystal: photo("ice-crystal", "Close-up of clear glacier ice", "center"),
  icebergSpires: photo("iceberg-spires", "Sculpted iceberg spires reflected in the sea", "center 45%"),
  icebergSky: photo("iceberg-sky", "Iceberg under a clear sky", "center 78%"),
};
/** Photograph shown in each Working Group space, chosen to echo its theme. */
export const groupPhotos: Record<number, Photo> = {
  1: photos.icebergsAerial,
  2: photos.blueIce,
  3: photos.icebergSpires,
  4: photos.icebergFjord,
  5: photos.iceCrystal,
};
