import type { CSSProperties } from "react";
import { checker, sparse } from "./dots";
import { cn } from "./ui";

/** A small dot-matrix bar, the hero chart's mark at label size. Sized by its cell; pass a width to stretch it. */
export function MiniBar({ color, cell = 3, className, style }: { color: string; cell?: number; className?: string; style?: CSSProperties }) {
  return (
    <span aria-hidden className={cn("flex shrink-0", className)} style={{ width: cell * 10, height: cell * 2, ...style }}>
      <span className="min-w-0 flex-1" style={{ background: sparse(color, cell) }} />
      <span className="shrink-0" style={{ width: cell * 4, background: checker(color, cell) }} />
      <span className="shrink-0" style={{ width: cell * 2, background: color }} />
    </span>
  );
}
