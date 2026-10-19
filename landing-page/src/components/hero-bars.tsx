import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { COLORS, checker, sparse } from "./dots";
import { cn } from "./ui";

/*
 * The hero's backdrop: a load-test chart drawn in dot-matrix bars. Each bar
 * runs from sparse dots through a checkerboard into a solid block, and one bar
 * at a time re-measures, so the page looks like something is running.
 * The closing section reuses it mirrored, so the page opens and closes on it.
 */

const ROWS = 22;

/** Deterministic noise in [0, 1), so every visit starts from the same chart. */
const noise = (index: number) => {
  const value = Math.sin(index * 12.9898 + 4.1414) * 43758.5453;
  return value - Math.floor(value);
};

/** Rows level with the headline run behind the text; above and below it they can be any length. */
const behindText = (index: number) => index >= 4 && index <= ROWS - 5;

/**
 * Bars behind the text end in a margin, short on the left or long on the right,
 * so their solid ends and labels stay visible around the headline.
 */
const seed = (index: number, offset: number) => {
  const random = noise(index + offset);
  if (!behindText(index)) return 0.3 + random * 0.62;
  return random < 0.5 ? 0.05 + random * 0.14 : 0.94 + (random - 0.5) * 0.1;
};

const clamp = (index: number, length: number) =>
  behindText(index)
    ? length < 0.5
      ? Math.min(0.13, Math.max(0.04, length))
      : Math.min(0.99, Math.max(0.93, length))
    : Math.min(0.94, Math.max(0.28, length));

const latency = (length: number) => `${Math.round(48 + length * 290)} ms`;

/** `mirror` grows the bars from the right edge; `offset` starts from a different chart. */
export function HeroBars({ mirror = false, offset = 0 }: { mirror?: boolean; offset?: number }) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);
  // Grows in the first time it scrolls into view, not on page load.
  const [seen, setSeen] = useState(false);
  const [lengths, setLengths] = useState(() => Array.from({ length: ROWS }, (_, index) => seed(index, offset)));
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    if (!seen) return;
    const timer = window.setTimeout(() => setSettled(true), 1800);
    return () => window.clearTimeout(timer);
  }, [seen]);

  // Only re-measure while the chart is on screen.
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => {
      setVisible(entry.isIntersecting);
      if (entry.isIntersecting) setSeen(true);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // One bar re-measures at a time: a small, believable change.
  useEffect(() => {
    if (reduced || !visible) return;
    const timer = window.setInterval(() => {
      setLengths((current) => {
        const next = [...current];
        const index = Math.floor(Math.random() * next.length);
        const drift = (Math.random() - 0.5) * (behindText(index) ? 0.05 : 0.12);
        next[index] = clamp(index, next[index] + drift);
        return next;
      });
    }, 1700);
    return () => window.clearInterval(timer);
  }, [reduced, visible]);

  return (
    <div
      ref={ref}
      aria-hidden
      className="pointer-events-none absolute inset-0 flex flex-col justify-center gap-[22px] overflow-hidden opacity-80 [mask-image:linear-gradient(#000_0%,#000_10%,transparent_17%,transparent_86%,#000_93%)] xl:[mask-image:radial-gradient(ellipse_760px_400px_at_50%_50%,transparent_42%,rgb(0_0_0/0.35)_72%,#000_100%)]"
    >
      {lengths.map((length, index) => {
        const color = COLORS[(index + offset) % COLORS.length];
        return (
          <div key={index} className={cn("flex h-3 items-center gap-3", mirror && "flex-row-reverse")}>
            <motion.div
              // Never narrower than the checkerboard and solid end, or they spill onto the label.
              className={cn("flex h-full min-w-[84px] shrink-0", mirror && "flex-row-reverse")}
              initial={reduced ? false : { width: "0%" }}
              animate={{ width: seen || reduced ? `calc((100% - 96px) * ${length})` : "0%" }}
              transition={{
                duration: settled ? 1.2 : 1.1,
                delay: settled ? 0 : index * 0.035,
                ease: [0.23, 1, 0.32, 1],
              }}
            >
              <span className="min-w-0 flex-1" style={{ background: sparse(color) }} />
              <span className="w-[54px] shrink-0" style={{ background: checker(color) }} />
              <span className="w-[30px] shrink-0" style={{ background: color }} />
            </motion.div>
            <motion.span
              className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground"
              initial={reduced ? false : { opacity: 0 }}
              animate={{ opacity: seen || reduced ? 1 : 0 }}
              transition={{ delay: settled ? 0 : 0.6 + index * 0.035, duration: 0.4 }}
            >
              {latency(length)}
            </motion.span>
          </div>
        );
      })}
    </div>
  );
}
