import { useState, type ReactNode } from "react";
import type { Change, TargetStatus } from "../demo/data";

/* Ported from the dashboard (web/src/components/ui): same look, no app data. */

export const cn = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ");

const buttonBase =
  "inline-flex items-center justify-center gap-1.5 rounded-[7px] font-[450] transition-[background-color,border-color,color,transform] duration-150 ease-[var(--ease-out)] active:scale-[.97] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

export const buttonPrimary = `${buttonBase} bg-foreground text-background [@media(hover:hover)]:hover:bg-white`;
export const buttonSecondary = `${buttonBase} border border-border bg-background [@media(hover:hover)]:hover:border-border-strong [@media(hover:hover)]:hover:bg-muted`;

export function Surface({
  title,
  hint,
  action,
  children,
  className,
}: {
  title?: string;
  hint?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("overflow-hidden rounded-[9px] border border-border bg-card", className)}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="min-w-0">
            <h3 className="truncate text-[13px] font-medium">{title}</h3>
            {hint && <p className="mt-0.5 truncate text-xs text-muted-foreground">{hint}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

const statusTone = {
  pass: "text-success-foreground [&>span]:bg-success",
  watch: "text-warning-foreground [&>span]:bg-warning",
  fail: "text-danger-foreground [&>span]:bg-danger",
  info: "text-accent [&>span]:bg-accent",
  muted: "text-muted-foreground [&>span]:bg-border-strong",
} as const;

export type StatusTone = keyof typeof statusTone;

export function Status({ tone, children, className }: { tone: StatusTone; children: ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-[450]", statusTone[tone], className)}>
      <span className="h-[5px] w-[5px] shrink-0 rounded-full" />
      {children}
    </span>
  );
}

const targetTone = { healthy: "pass", watch: "watch", critical: "fail" } as const;
const targetLabel = { healthy: "Healthy", watch: "Watch", critical: "Regressed" } as const;

export function TargetStatusLabel({ status }: { status: TargetStatus }) {
  return <Status tone={targetTone[status]}>{targetLabel[status]}</Status>;
}

const changeTone = {
  regressed: "text-danger-foreground",
  possible: "text-warning-foreground",
  improved: "text-success-foreground",
  steady: "text-muted-foreground",
  inconclusive: "text-muted-foreground",
} as const;

export const changeLabel = {
  regressed: "Regressed",
  possible: "Possible regression",
  improved: "Improved",
  steady: "Steady",
  inconclusive: "Inconclusive",
} as const;

export function ChangeTag({
  change,
  showAgainst = false,
  className,
}: {
  change: Change | null;
  showAgainst?: boolean;
  className?: string;
}) {
  if (!change) return <span className={cn("text-xs text-muted-foreground", className)}>first run</span>;
  const flat = change.kind === "steady" || change.kind === "inconclusive";
  const down = change.kind === "regressed" || change.kind === "possible";
  return (
    <span
      className={cn("inline-flex items-center gap-1 font-mono text-[12px] tabular-nums", changeTone[change.kind], className)}
      title={`${changeLabel[change.kind]}: ${change.arrow} users vs ${change.against}`}
    >
      <svg viewBox="0 0 12 12" className={cn("h-2.5 w-2.5", down && "rotate-180")} aria-hidden>
        {flat ? (
          <line x1="2" y1="6" x2="10" y2="6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        ) : (
          <path d="M6 2.5v7M3 5.5l3-3 3 3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>
      {change.pct}
      <span className="sr-only">{changeLabel[change.kind]}</span>
      {showAgainst && <span className="font-sans text-[11.5px] text-muted-foreground">vs {change.against}</span>}
    </span>
  );
}

const sparkColor = { healthy: "var(--success)", watch: "var(--warning)", critical: "var(--danger)" } as const;
const SPARK_MUTED = "#6b6b6b";

/**
 * The dashboard's sparkline (web/src/components/ui/sparkline.tsx): tiny dotted
 * columns, the latest in the target's status colour.
 */
export function Sparkline({ points, status }: { points: number[]; status: TargetStatus }) {
  const recent = points.slice(-12);
  const max = Math.max(...recent, 1);
  const width = recent.length * 6 - 2;
  const latest = sparkColor[status];
  const pattern = (id: string, color: string) => (
    <defs>
      <pattern id={`${id}-sparse`} width="2" height="2" patternUnits="userSpaceOnUse">
        <rect width="1" height="1" fill={color} />
      </pattern>
      <pattern id={`${id}-checker`} width="2" height="2" patternUnits="userSpaceOnUse">
        <rect width="1" height="1" fill={color} />
        <rect x="1" y="1" width="1" height="1" fill={color} />
      </pattern>
    </defs>
  );
  return (
    <svg viewBox={`0 0 ${Math.max(width, 1)} 20`} width={width} height={20} className="inline-block overflow-visible" aria-hidden>
      {pattern("spark-muted", SPARK_MUTED)}
      {pattern(`spark-${status}`, latest)}
      {recent.map((value, index) => {
        const last = index === recent.length - 1;
        const height = Math.max((value / max) * 18, 3);
        const top = 20 - height;
        const id = last ? `spark-${status}` : "spark-muted";
        const cap = Math.min(2, height);
        const checker = Math.min(4, height - cap);
        return (
          <g key={index}>
            <rect x={index * 6} y={top + cap + checker} width={4} height={Math.max(height - cap - checker, 0)} fill={`url(#${id}-sparse)`} />
            <rect x={index * 6} y={top + cap} width={4} height={checker} fill={`url(#${id}-checker)`} />
            <rect x={index * 6} y={top} width={4} height={cap} fill={last ? latest : SPARK_MUTED} />
          </g>
        );
      })}
    </svg>
  );
}

export function CodeBlock({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <pre
      className={cn(
        "overflow-x-auto rounded-[7px] border border-border bg-muted/50 px-3 py-2.5 font-mono text-[12px] leading-[1.6] text-foreground",
        className,
      )}
    >
      {children}
    </pre>
  );
}

export function CopyButton({ text, label = "Copy", className }: { text: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard blocked: the command is still selectable */
    }
  };
  return (
    <button
      type="button"
      onClick={copy}
      aria-label={copied ? "Copied" : label}
      title={copied ? "Copied" : label}
      className={cn(
        "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] text-muted-foreground transition duration-150 ease-[var(--ease-out)] active:scale-[.97] [@media(hover:hover)]:hover:bg-muted [@media(hover:hover)]:hover:text-foreground",
        className,
      )}
    >
      {copied ? (
        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <rect x="9" y="9" width="12" height="12" rx="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )}
    </button>
  );
}
