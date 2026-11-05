import { useEffect, useRef, useState } from "react";
import { PlayCircle, Volume2 } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { asset } from "@/lib/base";

/**
 * A short narrated tour of the platform, shown once after a member's first sign-in and available again from the account menu.
 * The video tries to start with sound. When the browser blocks sound before an interaction, it plays muted
 * (the subtitles are part of the picture) and offers a button to turn the sound on.
 */
export function WelcomeVideo({ open, onClose, name }: { open: boolean; onClose: () => void; name?: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [silenced, setSilenced] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSilenced(false);
    const timer = window.setTimeout(() => {
      const video = ref.current;
      if (!video) return;
      video.muted = false;
      video.play().catch(() => {
        video.muted = true;
        setSilenced(true);
        video.play().catch(() => undefined);
      });
    }, 150);
    return () => window.clearTimeout(timer);
  }, [open]);

  function unmute() {
    const video = ref.current;
    if (!video) return;
    video.muted = false;
    video.volume = 1;
    if (video.ended || video.currentTime > 2) video.currentTime = 0;
    void video.play().catch(() => undefined);
    setSilenced(false);
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="detail-content welcome-video">
        <DialogTitle><PlayCircle size={20} /> {name ? `Welcome, ${name.split(" ")[0]}!` : "Welcome to DACS Community"}</DialogTitle>
        <DialogDescription>A short narrated tour of the platform. You can watch it again at any time from your account menu.</DialogDescription>
        {open && (
          <div className="welcome-frame">
            <video ref={ref} className="welcome-player" controls playsInline preload="auto" poster={asset("/assets/video/welcome-narrated-poster.jpg")}
              onVolumeChange={(e) => { if (!e.currentTarget.muted) setSilenced(false); }}>
              <source src={asset("/assets/video/welcome-narrated.mp4")} type="video/mp4" />
              <source src={asset("/assets/video/welcome-narrated.webm")} type="video/webm" />
              Your browser cannot play this video.
            </video>
            {silenced && (
              <button type="button" className="welcome-unmute" onClick={unmute}>
                <Volume2 size={18} /> Turn on the sound
              </button>
            )}
          </div>
        )}
        <div className="toolbar welcome-actions">
          <span className="micro">The tour shows sample data. Subtitles are included in the video.</span>
          <button type="button" className="btn primary" onClick={onClose}>Start exploring</button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
