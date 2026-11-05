import { ArrowUpRight, Download, ScrollText } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { BASE } from "@/lib/base";

/** Terms of Reference of the Working Groups and governing bodies (PDF, in public/assets/tor). */
export const termsOfReference: Record<string, { title: string; pages: number }> = {
  wg1: { title: "Working Group 1: Global Cryosphere Monitoring", pages: 3 },
  wg2: { title: "Working Group 2: Actionable Cryosphere Projections", pages: 6 },
  wg3: { title: "Working Group 3: Cryospheric Risk Management Solutions", pages: 5 },
  wg4: { title: "Working Group 4: Adaptation to Cryosphere Loss", pages: 5 },
  wg5: { title: "Working Group 5: Amplify the Impact of Cryospheric Science", pages: 5 },
  smc: { title: "Strategic Management Committee", pages: 4 },
  esc: { title: "Executive Steering Committee", pages: 4 },
  cfd: { title: "Cryosphere Finance Dialogue", pages: 4 },
};
export const torUrl = (id: string) => `${BASE}assets/tor/${id}.pdf`;

/** A card that opens the Terms of Reference of a group or body. */
export function TorCard({ body, onOpen }: { body: string; onOpen: () => void }) {
  const t = termsOfReference[body];
  if (!t) return null;
  return (
    <button type="button" className="tor-card" onClick={onOpen}>
      <span className="tor-icon"><ScrollText size={22} /></span>
      <span className="tor-text">
        <small>Terms of Reference</small>
        <strong>{t.title}</strong>
        <span>PDF · {t.pages} pages · mandate, objectives, membership and ways of working</span>
      </span>
      <span className="tor-action">Read</span>
    </button>
  );
}

/** Reads the Terms of Reference inside the platform, with links to open or download the PDF. */
export function TorDialog({ body, onClose }: { body: string | null; onClose: () => void }) {
  const t = body ? termsOfReference[body] : null;
  return (
    <Dialog open={!!t} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="detail-content tor-dialog">
        <DialogTitle><ScrollText size={19} /> Terms of Reference</DialogTitle>
        <DialogDescription>{t?.title} · Decade of Action for Cryospheric Sciences (2025–2034)</DialogDescription>
        {t && body && (
          <>
            <iframe className="tor-frame" src={torUrl(body) + "#view=FitH"} title={"Terms of Reference · " + t.title} />
            <div className="toolbar">
              <a className="btn" href={torUrl(body)} target="_blank" rel="noopener noreferrer">Open in a new tab <ArrowUpRight size={14} /></a>
              <a className="btn" href={torUrl(body)} download={`Terms of Reference - ${t.title.replace(/:/g, " -")}.pdf`}><Download size={14} /> Download</a>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
