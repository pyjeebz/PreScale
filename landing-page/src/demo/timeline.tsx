import { ChangeTag, Surface } from "../components/ui";
import type { Run } from "./data";

/* The dashboard's capacity timeline (web/src/components/target-detail/capacity-timeline.tsx). */

const W = 720;
const H = 250;
const PAD = { left: 40, right: 20, top: 26, bottom: 30 };
const INNER_W = W - PAD.left - PAD.right;
const INNER_H = H - PAD.top - PAD.bottom;

// Each run is a dot-matrix column: sparse from the floor, checkerboard, solid cap at its capacity.
const CAP = 8;
const CHECKER = 16;
const TONES = { brand: "var(--brand)", danger: "var(--danger)", warning: "var(--warning)", muted: "var(--muted-foreground)" } as const;

/** Patterns resolve colour where they're defined, so each tone gets its own. */
function DotPatterns({ id, color }: { id: string; color: string }) {
  return (
    <defs>
      <pattern id={`${id}-sparse`} width="4" height="4" patternUnits="userSpaceOnUse">
        <rect width="2" height="2" fill={color} />
      </pattern>
      <pattern id={`${id}-checker`} width="4" height="4" patternUnits="userSpaceOnUse">
        <rect width="2" height="2" fill={color} />
        <rect x="2" y="2" width="2" height="2" fill={color} />
      </pattern>
    </defs>
  );
}

function niceScale(value: number) {
  const target = Math.max(value, 10) / 5;
  const magnitude = 10 ** Math.floor(Math.log10(target));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= target) ?? target;
  return { max: Math.ceil(value / step) * step, step };
}

export function CapacityTimeline({
  points,
  baselineBranch,
  active,
  onActive,
  onOpen,
}: {
  points: Run[];
  baselineBranch: string;
  active: string | null;
  onActive: (id: string | null) => void;
  onOpen: (id: string) => void;
}) {
  const { max, step } = niceScale(Math.max(...points.map((point) => point.high)) * 1.08);
  const colW = Math.max(4, Math.min(20, Math.floor(((INNER_W / points.length) * 0.55) / 4) * 4));
  const x = (index: number) => PAD.left + colW / 2 + (index / Math.max(points.length - 1, 1)) * (INNER_W - colW);
  const y = (value: number) => PAD.top + INNER_H - (value / max) * INNER_H;

  const onLine = (point: Run) => point.branch === baselineBranch;
  const line = points.map((point, index) => ({ point, index })).filter(({ point }) => onLine(point));
  const linePath = line.map(({ point, index }) => `${x(index)},${y(point.survives)}`).join(" ");

  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step);
  const dateTicks = [0, Math.floor((points.length - 1) / 2), points.length - 1];
  const activeIndex = points.findIndex((point) => point.id === active);
  const activePoint = activeIndex >= 0 ? points[activeIndex] : null;
  const lastLine = line[line.length - 1];

  return (
    <Surface title="Capacity timeline" hint={`Survives-users, one column per run · trend follows ${baselineBranch}`}>
      <div className="relative px-4 pb-2 pt-3">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full"
          role="img"
          aria-label={`Capacity over ${points.length} runs. Latest ${baselineBranch} run survives about ${lastLine?.point.survives} users.`}
          onPointerLeave={() => onActive(null)}
        >
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(tick)} y2={y(tick)} stroke="var(--muted)" strokeWidth="1" />
              <text x={PAD.left - 8} y={y(tick) + 3} textAnchor="end" fontSize="10" fill="var(--muted-foreground)" className="font-mono tabular-nums">
                {tick}
              </text>
            </g>
          ))}
          {dateTicks.map((index) => (
            <text
              key={index}
              x={x(index)}
              y={H - 8}
              textAnchor={index === 0 ? "start" : index === points.length - 1 ? "end" : "middle"}
              fontSize="10"
              fill="var(--muted-foreground)"
              className="font-mono"
            >
              {points[index].date}
            </text>
          ))}

          {Object.entries(TONES).map(([key, color]) => (
            <DotPatterns key={key} id={`demo-${key}`} color={color} />
          ))}
          <polyline points={linePath} fill="none" stroke="var(--brand)" strokeOpacity="0.35" strokeWidth="1" strokeDasharray="2 3" />

          {activePoint && (
            <line x1={x(activeIndex)} x2={x(activeIndex)} y1={PAD.top - 6} y2={PAD.top + INNER_H} stroke="var(--border-strong)" strokeWidth="1" />
          )}

          {points.map((point, index) => {
            const cx = x(index);
            const cy = y(point.survives);
            const regression = point.change?.kind === "regressed" || point.change?.kind === "possible";
            const offLine = !onLine(point);
            const tone: keyof typeof TONES =
              point.change?.kind === "regressed" ? "danger" : point.change?.kind === "possible" ? "warning" : offLine ? "muted" : "brand";
            const total = Math.max(y(0) - cy, 2);
            const cap = Math.min(CAP, total);
            const checker = Math.min(CHECKER, total - cap);
            const left = cx - colW / 2;
            const dimmed = active !== null && active !== point.id;
            return (
              <g
                key={point.id}
                data-demo={`point-${point.id}`}
                role="link"
                tabIndex={0}
                aria-label={`${point.date}: survives ~${point.survives} users, commit ${point.commit}${point.change ? `, ${point.change.pct} vs ${point.change.against}` : ""}. Open run.`}
                className="cursor-pointer outline-none"
                style={{ color: TONES[tone] }}
                onPointerEnter={() => onActive(point.id)}
                onFocus={() => onActive(point.id)}
                onBlur={() => onActive(null)}
                onClick={() => onOpen(point.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onOpen(point.id);
                  }
                }}
              >
                <rect x={cx - Math.max(colW, 28) / 2} y={PAD.top - 6} width={Math.max(colW, 28)} height={INNER_H + 6} fill="transparent" />
                <g
                  className="transition-opacity duration-150 motion-safe:animate-[column-rise_700ms_var(--ease-out)_both]"
                  style={{ opacity: dimmed ? 0.45 : offLine ? 0.7 : 1, transformBox: "fill-box", transformOrigin: "bottom", animationDelay: `${index * 30}ms` }}
                >
                  {total - cap - checker > 0 && (
                    <rect x={left} y={cy + cap + checker} width={colW} height={total - cap - checker} fill={`url(#demo-${tone}-sparse)`} />
                  )}
                  {checker > 0 && <rect x={left} y={cy + cap} width={colW} height={checker} fill={`url(#demo-${tone}-checker)`} />}
                  <rect x={left} y={cy} width={colW} height={cap} fill="currentColor" />
                  {/* Confidence band: a bracket beside the cap (as in the dashboard's bar.tsx). */}
                  <g stroke="currentColor" strokeOpacity={0.6} strokeWidth={1}>
                    <line x1={left + colW + 3} x2={left + colW + 3} y1={y(point.high)} y2={Math.max(y(point.low), y(point.high) + 1)} />
                    <line x1={left + colW + 1} x2={left + colW + 5} y1={y(point.high)} y2={y(point.high)} />
                    <line x1={left + colW + 1} x2={left + colW + 5} y1={Math.max(y(point.low), y(point.high) + 1)} y2={Math.max(y(point.low), y(point.high) + 1)} />
                  </g>
                </g>
                {regression && (
                  <text x={cx} y={y(point.high) - 8} textAnchor="middle" fontSize="10" fill="var(--foreground)" className="font-mono">
                    {point.change!.pct} {point.commit}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {activePoint && (
          <div
            className="pointer-events-none absolute top-2 z-10 w-[230px] rounded-[8px] border border-border bg-background px-3 py-2.5 shadow-[0_8px_24px_rgba(0,0,0,.5)]"
            style={
              x(activeIndex) / W > 0.55
                ? { right: `calc(${100 - (x(activeIndex) / W) * 100}% + 4px)` }
                : { left: `calc(${(x(activeIndex) / W) * 100}% + 20px)` }
            }
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[15px] font-semibold tabular-nums">
                ~{activePoint.survives}
                <span className="ml-1 text-[11px] font-normal text-muted-foreground">
                  users ({activePoint.low}–{activePoint.high})
                </span>
              </span>
              <ChangeTag change={activePoint.change} />
            </div>
            <p className="mt-1 font-mono text-[11px] text-muted-foreground">
              {activePoint.commit} · {activePoint.branch}
              {activePoint.preview ? " · preview" : ""}
            </p>
            <p className="mt-1 text-[11.5px] text-muted-foreground">
              {activePoint.culprit
                ? `Breaks at ${activePoint.culprit}${activePoint.cause ? ` · ${activePoint.cause}` : ""}`
                : "Held to the max tested"}
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {activePoint.date} · {activePoint.source} · {activePoint.when}
            </p>
          </div>
        )}

        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-2 bg-[var(--brand)]" aria-hidden />
            {baselineBranch}: solid top = capacity, bracket = confidence band
          </span>
          {points.some((point) => !onLine(point)) && (
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-2 bg-muted-foreground opacity-70" aria-hidden />
              pull request previews
            </span>
          )}
          {points.some((point) => point.change?.kind === "regressed") && (
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-2 bg-[var(--danger)]" aria-hidden />
              regression (&gt;20% drop)
            </span>
          )}
        </div>
      </div>
    </Surface>
  );
}
