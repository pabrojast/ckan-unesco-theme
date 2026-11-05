import { useEffect, useRef, useState } from "react";

const reducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Header shadow and back-to-top visibility. Re-renders only when a flag changes. */
export function useScrollFlags() {
  const [flags, setFlags] = useState({ scrolled: false, showTop: false });
  useEffect(() => {
    const update = () => {
      const y = window.scrollY;
      setFlags((p) => {
        const next = { scrolled: y > 4, showTop: y > 600 };
        return p.scrolled === next.scrolled && p.showTop === next.showTop ? p : next;
      });
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  return flags;
}

/** Animates a number from its previous value to the target. */
export function useCountUp(target: number, duration = 750) {
  const [value, setValue] = useState(0);
  const current = useRef(0);
  useEffect(() => {
    if (reducedMotion()) {
      current.current = target;
      setValue(target);
      return;
    }
    const from = current.current,
      start = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const k = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - k, 3);
      current.current = Math.round(from + (target - from) * eased);
      setValue(current.current);
      if (k < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);
  return value;
}
