/*
 * The PreScale mark: the hero chart in miniature. Three bars run from sparse
 * dots through a checkerboard into a solid end; the cyan one goes furthest.
 * Drawn on a pixel grid so it stays crisp: 24×24 for the full mark, and a
 * simpler 16×16 cut for favicon sizes, where single sparse dots would vanish.
 */

import type { CSSProperties } from "react";

const CYAN = "#3FD3DE";
type Run = { x: number; y: number; w: number; cyan: boolean };

/** 1 = sparse, 2 = checkerboard, 3 = solid: the same patterns as the hero's bars. */
const lit = (x: number, y: number, level: number) =>
  level === 3 || (level === 2 && (x + y) % 2 === 0) || (level === 1 && x % 2 === 0 && y % 2 === 0);

function draw(bars: Array<{ y: number; height: number; length: number; cyan?: boolean }>, x0: number, sparseUntil: number) {
  const runs: Run[] = [];
  for (const bar of bars) {
    for (let y = bar.y; y < bar.y + bar.height; y++) {
      let start = -1;
      for (let x = x0; x <= x0 + bar.length; x++) {
        const t = (x - x0) / bar.length;
        const level = t < sparseUntil ? 1 : t < 0.75 ? 2 : 3;
        const on = x < x0 + bar.length && lit(x, y, level);
        if (on && start < 0) start = x;
        if (!on && start >= 0) {
          runs.push({ x: start, y, w: x - start, cyan: Boolean(bar.cyan) });
          start = -1;
        }
      }
    }
  }
  return runs;
}

const FULL = draw(
  [
    { y: 3, height: 4, length: 11 },
    { y: 10, height: 4, length: 20, cyan: true },
    { y: 17, height: 4, length: 15 },
  ],
  2,
  0.45,
);

const SMALL = draw(
  [
    { y: 2, height: 3, length: 7 },
    { y: 7, height: 3, length: 14, cyan: true },
    { y: 12, height: 3, length: 10 },
  ],
  1,
  0.3,
);

/** White parts follow the text colour, so the mark works on dark and light. */
export function Logo({ size = 24, className }: { size?: number; className?: string }) {
  const small = size <= 16;
  const grid = small ? 16 : 24;
  return (
    <svg
      aria-hidden
      viewBox={`0 0 ${grid} ${grid}`}
      width={size}
      height={size}
      shapeRendering="crispEdges"
      className={className}
      style={{ flexShrink: 0 }}
    >
      {(small ? SMALL : FULL).map((run) => (
        <rect key={`${run.x},${run.y}`} x={run.x} y={run.y} width={run.w} height={1} fill={run.cyan ? CYAN : "currentColor"} />
      ))}
    </svg>
  );
}

/*
 * The mark as a live chart for the nav: at rest it matches the static mark; when
 * its `group` is hovered or focused, the bars ramp out one after another, the
 * cyan one furthest, the way the hero's bars grow. Sparse dots stretch while
 * the checkerboard and the solid end ride outward.
 */
const RAMP = [
  { top: 3, rest: 11, out: 34, checker: 4, end: 2, color: "currentColor", delay: 0 },
  { top: 10, rest: 20, out: 64, checker: 6, end: 5, color: CYAN, delay: 60 },
  { top: 17, rest: 15, out: 48, checker: 5, end: 3, color: "currentColor", delay: 120 },
];
/** Rest and ramped-out widths of the whole mark, including its 2px margins. */
const RAMP_WIDTH = { rest: 24, out: 68 };

const dots = (color: string) => `conic-gradient(${color} 25%, transparent 0) 0 0 / 2px 2px`;
const checks = (color: string) => `conic-gradient(${color} 25%, transparent 0 50%, ${color} 0 75%, transparent 0) 0 0 / 2px 2px`;

export function RampLogo() {
  return (
    <span
      aria-hidden
      className="relative block h-6 w-[var(--rest)] shrink-0 transition-[width] duration-500 ease-[var(--ease-out)] group-hover:w-[var(--out)] group-focus-visible:w-[var(--out)] motion-reduce:transition-none"
      style={{ "--rest": `${RAMP_WIDTH.rest}px`, "--out": `${RAMP_WIDTH.out}px` } as CSSProperties}
    >
      {RAMP.map((bar) => (
        <span
          key={bar.top}
          className="absolute left-0.5 flex h-1 w-[var(--rest)] transition-[width] duration-500 ease-[var(--ease-out)] group-hover:w-[var(--out)] group-focus-visible:w-[var(--out)] motion-reduce:transition-none"
          style={
            {
              top: bar.top,
              "--rest": `${bar.rest}px`,
              "--out": `${bar.out}px`,
              transitionDelay: `${bar.delay}ms`,
            } as CSSProperties
          }
        >
          <span className="min-w-0 flex-1" style={{ background: dots(bar.color) }} />
          <span className="shrink-0" style={{ width: bar.checker, background: checks(bar.color) }} />
          <span className="shrink-0" style={{ width: bar.end, background: bar.color }} />
        </span>
      ))}
    </span>
  );
}
