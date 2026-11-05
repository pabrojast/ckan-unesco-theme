// Spaces of the governing bodies, shown under Governance.
// Descriptions follow the Decade governance model (DACS synthesis, pp. 14–15). A description entered by the
// UNESCO Secretariat in the appointments of a body replaces the default text.
import { photos, type Photo } from "./imagery";
export type BodySpace = { id: string; short: string; title: string; description: string; photo: Photo; folder: string; color: string };
export const bodySpaces: BodySpace[] = [
  {
    id: "unesco",
    color: "#009edb",
    short: "UNESCO–IHP",
    title: "UNESCO–IHP Secretariat",
    description: "UNESCO–IHP hosts the Secretariat of the Decade and supports its management.",
    photo: photos.blueIce,
    folder: "general",
  },
  {
    id: "esc",
    color: "#0a6eb4",
    short: "ESC",
    title: "Executive Steering Committee",
    description: "The Strategic Management Committee reports to the Executive Steering Committee and to UNESCO–IHP.",
    photo: photos.icebergSky,
    folder: "esc",
  },
  {
    id: "smc",
    color: "#00afd0",
    short: "SMC",
    title: "Strategic Management Committee",
    description: "Coordinates the five Working Groups, receives reports from the Cryosphere Finance Dialogue and liaises with other initiatives. Reports to the Executive Steering Committee and UNESCO–IHP.",
    photo: photos.icebergFjord,
    folder: "smc",
  },
  {
    id: "cfd",
    color: "#599c41",
    short: "CFD",
    title: "Cryosphere Finance Dialogue",
    description: "Reports to the Strategic Management Committee.",
    photo: photos.iceCrystal,
    folder: "cfd",
  },
  {
    id: "alliance",
    color: "#3fa58a",
    short: "Alliance",
    title: "Alliance for the Cryosphere",
    description: "Supports the Decade together with Indigenous advice and liaison with other initiatives.",
    photo: photos.icebergSpires,
    folder: "alliance",
  },
  {
    id: "iac",
    color: "#8a9bb0",
    short: "IAC",
    title: "Indigenous Advisory Committee",
    description: "Provides Indigenous advice to the Decade. Its exact role and placement are subject to consultation.",
    photo: photos.iceCave,
    folder: "",
  },
];
export const bodySpace = (id: string) => bodySpaces.find((b) => b.id === id);
