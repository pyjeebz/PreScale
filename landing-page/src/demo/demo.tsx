import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Logo } from "../components/logo";
import { cn } from "../components/ui";
import { TARGETS } from "./data";
import {
  ConnectView,
  DemoContext,
  LaunchGuardView,
  Overview,
  RunView,
  RunsView,
  TargetView,
  TargetsView,
  useHot,
  viewPath,
  type View,
} from "./views";

/**
 * The dashboard, embedded. A scripted cursor walks through the story; move
 * the mouse in (or tap) and it hands over, so visitors click around the real
 * screens with mock data. It resumes a few seconds after they leave.
 */

const DESIGN_W = 1200;
const DESIGN_H = 760;
const MIN_SCALE = 0.56;

type Step = {
  /** data-demo id the cursor moves to. */
  to: string;
  /** Ms to rest after arriving (and after the click, if any). */
  rest: number;
  click?: View;
  point?: string;
};

const TOUR: Step[] = [
  { to: "nav-overview", rest: 900, click: { name: "overview" } },
  { to: "row-shop", rest: 600, click: { name: "target", id: "shop" } },
  { to: "point-shop-a41f9c2", rest: 2600, point: "shop-a41f9c2" },
  { to: "point-shop-a41f9c2", rest: 900, click: { name: "run", id: "shop-a41f9c2" } },
  { to: "fix-0", rest: 2600 },
  { to: "nav-launch", rest: 1800, click: { name: "launch", target: "api", profile: "product-hunt" } },
  { to: "profile-hn-frontpage", rest: 2000, click: { name: "launch", target: "api", profile: "hn-frontpage" } },
  { to: "profile-black-friday", rest: 2000, click: { name: "launch", target: "api", profile: "black-friday" } },
  { to: "profile-product-hunt", rest: 1200, click: { name: "launch", target: "api", profile: "product-hunt" } },
  { to: "signoff", rest: 2600 },
];

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      window.clearTimeout(timer);
      reject(new DOMException("aborted", "AbortError"));
    });
  });

const reducedMotion = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function DashboardDemo() {
  const frameRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const mainRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const scaleRef = useRef(1);
  const [view, setView] = useState<View>(() =>
    reducedMotion() ? { name: "target", id: "shop" } : { name: "overview" },
  );
  const [hovered, setHovered] = useState<string | null>(null);
  const [activePoint, setActivePoint] = useState<string | null>(null);
  const [cursor, setCursor] = useState({ x: DESIGN_W * 0.6, y: DESIGN_H * 0.7, shown: false, pressed: false });
  const [visible, setVisible] = useState(false);
  const [userHere, setUserHere] = useState(false);
  const resumeTimer = useRef<number | undefined>(undefined);

  const go = useCallback((next: View) => {
    setView(next);
    setActivePoint(null);
    mainRef.current?.scrollTo({ top: 0 });
  }, []);

  // Fit the fixed-size dashboard into whatever width the page gives it.
  useLayoutEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const fit = () => {
      // Phones keep it readable and let visitors swipe across instead of shrinking it to a thumbnail.
      const next = Math.min(1, Math.max(frame.clientWidth / DESIGN_W, MIN_SCALE));
      scaleRef.current = next;
      setScale(next);
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(frame);
    return () => observer.disconnect();
  }, []);

  // Only play while on screen.
  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0.35 });
    observer.observe(frame);
    return () => observer.disconnect();
  }, []);

  const pointAt = useCallback((id: string) => {
    const canvas = canvasRef.current;
    const element = canvas?.querySelector<HTMLElement | SVGElement>(`[data-demo="${id}"]`);
    if (!canvas || !element) return null;
    const box = canvas.getBoundingClientRect();
    const rect = element.getBoundingClientRect();
    const circle = element.querySelector("circle");
    const anchor = circle ? circle.getBoundingClientRect() : rect;
    const s = scaleRef.current;
    const x = (anchor.left + Math.min(anchor.width / 2, 60) - box.left) / s;
    const y = (anchor.top + anchor.height / 2 - box.top) / s;
    return { x, y };
  }, []);

  const playing = visible && !userHere && !reducedMotion();

  useEffect(() => {
    if (!playing) return;
    const controller = new AbortController();
    const { signal } = controller;

    (async () => {
      try {
        await sleep(500, signal);
        for (;;) {
          for (const step of TOUR) {
            const at = pointAt(step.to);
            if (!at) continue;
            setHovered(null);
            // On phones the window is wider than the screen: keep the cursor in view.
            const frame = frameRef.current;
            if (frame && frame.scrollWidth > frame.clientWidth) {
              frame.scrollTo({ left: Math.max(0, at.x * scaleRef.current - frame.clientWidth / 2), behavior: "smooth" });
            }
            setCursor((current) => ({ ...current, ...at, shown: true }));
            await sleep(950, signal);
            setHovered(step.to);
            if (step.point) setActivePoint(step.point);
            if (step.click) {
              await sleep(260, signal);
              setCursor((current) => ({ ...current, pressed: true }));
              await sleep(140, signal);
              setCursor((current) => ({ ...current, pressed: false }));
              setHovered(null);
              go(step.click);
            }
            await sleep(step.rest, signal);
          }
        }
      } catch {
        /* stopped: the visitor took over or scrolled away */
      }
    })();

    return () => {
      controller.abort();
      setHovered(null);
    };
  }, [playing, pointAt, go]);

  const takeOver = () => {
    window.clearTimeout(resumeTimer.current);
    setUserHere(true);
    setCursor((current) => ({ ...current, shown: false }));
  };
  const handBack = (delay: number) => {
    window.clearTimeout(resumeTimer.current);
    resumeTimer.current = window.setTimeout(() => setUserHere(false), delay);
  };
  useEffect(() => () => window.clearTimeout(resumeTimer.current), []);

  const context = useMemo(() => ({ go, hovered, activePoint, setActivePoint }), [go, hovered, activePoint]);

  let screen: ReactNode;
  switch (view.name) {
    case "overview":
      screen = <Overview />;
      break;
    case "targets":
      screen = <TargetsView />;
      break;
    case "runs":
      screen = <RunsView />;
      break;
    case "connect":
      screen = <ConnectView />;
      break;
    case "target":
      screen = <TargetView id={view.id} />;
      break;
    case "run":
      screen = <RunView id={view.id} />;
      break;
    case "launch":
      screen = <LaunchGuardView targetId={view.target} profileName={view.profile} />;
      break;
  }

  return (
    <div
      ref={frameRef}
      className="relative w-full select-none overflow-x-auto overflow-y-hidden [scrollbar-width:none]"
      style={{ height: DESIGN_H * scale }}
      onPointerEnter={(event) => event.pointerType === "mouse" && takeOver()}
      onPointerLeave={(event) => event.pointerType === "mouse" && handBack(2500)}
      onPointerDown={(event) => {
        if (event.pointerType !== "mouse") {
          takeOver();
          handBack(12000);
        }
      }}
    >
      <div className="relative" style={{ width: DESIGN_W * scale, height: DESIGN_H * scale }}>
      <div
        ref={canvasRef}
        className="absolute left-0 top-0 origin-top-left overflow-hidden rounded-[12px] border border-border bg-background text-foreground"
        style={{ width: DESIGN_W, height: DESIGN_H, transform: `scale(${scale})` }}
      >
        <DemoContext.Provider value={context}>
          <div className="flex h-9 items-center justify-center border-b border-border">
            <span className="rounded-[6px] bg-muted/60 px-3 py-0.5 font-mono text-[11.5px] text-muted-foreground">
              prescale.dev/dashboard{viewPath(view)}
            </span>
          </div>
          <div className="flex" style={{ height: DESIGN_H - 36 }}>
            <Sidebar view={view} />
            <div ref={mainRef} className="min-w-0 flex-1 overflow-y-auto px-7 py-6 [scrollbar-width:none]">
              {screen}
            </div>
          </div>
        </DemoContext.Provider>

        <div
          aria-hidden
          className="demo-cursor pointer-events-none absolute left-0 top-0 z-20"
          data-pressed={cursor.pressed ? "" : undefined}
          style={{ transform: `translate(${cursor.x}px, ${cursor.y}px)`, opacity: cursor.shown && playing ? 1 : 0 }}
        >
          <svg width="20" height="22" viewBox="0 0 20 22">
            <path d="M3 2.5 L3 17.5 L7 13.8 L9.8 20 L12.6 18.8 L9.9 12.7 L15.2 12.7 Z" fill="#fff" stroke="#000" strokeWidth="1.2" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      </div>
    </div>
  );
}

const icons: Record<string, ReactNode> = {
  overview: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
    </>
  ),
  targets: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" />
    </>
  ),
  runs: <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />,
  launch: (
    <>
      <path d="M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6l7-3z" />
      <polyline points="9 12 11 14 15 10" />
    </>
  ),
  connect: (
    <>
      <path d="M9 2v6" />
      <path d="M15 2v6" />
      <path d="M6 8h12v4a6 6 0 0 1-12 0V8z" />
      <path d="M12 18v4" />
    </>
  ),
  docs: (
    <>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </>
  ),
};

function Sidebar({ view }: { view: View }) {
  const hot = useHot();
  const section = view.name === "target" ? "targets" : view.name === "run" ? "runs" : view.name;
  const items: Array<{ id: string; label: string; to: View; count?: number }> = [
    { id: "overview", label: "Overview", to: { name: "overview" } },
    { id: "targets", label: "Targets", to: { name: "targets" }, count: TARGETS.length },
    { id: "runs", label: "Runs", to: { name: "runs" } },
    { id: "launch", label: "Launch Guard", to: { name: "launch", target: "api", profile: "product-hunt" } },
    { id: "connect", label: "Connect", to: { name: "connect" } },
  ];
  return (
    <DemoContext.Consumer>
      {({ go }) => (
        <aside className="flex w-[210px] shrink-0 flex-col border-r border-border px-2 py-2.5">
          <div className="flex items-center gap-2.5 px-2 pb-4">
            <Logo />
            <span className="text-sm font-medium">PreScale</span>
          </div>
          <div className="px-2 pb-1 pt-3 text-[11px] font-[450] text-muted-foreground/60">Workspace</div>
          <ul className="flex flex-col gap-0.5">
            {items.map((item) => {
              const active = section === item.id;
              return (
                <li key={item.id}>
                  <button
                    {...hot(`nav-${item.id}`)}
                    onClick={() => go(item.to)}
                    className={cn(
                      "flex h-8 w-full items-center gap-2.5 rounded-[6px] px-2 text-left text-[13px] font-[450] transition duration-150",
                      active
                        ? "bg-muted font-medium text-foreground"
                        : "text-muted-foreground data-[hover]:bg-muted data-[hover]:text-foreground [@media(hover:hover)]:hover:bg-muted [@media(hover:hover)]:hover:text-foreground",
                    )}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-[15px] w-[15px] shrink-0">
                      {icons[item.id]}
                    </svg>
                    {item.label}
                    {item.count !== undefined && <span className="ml-auto font-mono text-[10.5px] text-muted-foreground/70">{item.count}</span>}
                    {item.id === "targets" && <span className="ml-1.5 h-[5px] w-[5px] rounded-full bg-danger" />}
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="mx-2 mb-1 mt-3 text-[11px] font-[450] text-muted-foreground/60">Resources</div>
          <a
            href="https://github.com/pyjeebz/prescale#readme"
            target="_blank"
            rel="noreferrer"
            className="flex h-8 items-center gap-2.5 rounded-[6px] px-2 text-[13px] font-[450] text-muted-foreground transition duration-150 [@media(hover:hover)]:hover:bg-muted [@media(hover:hover)]:hover:text-foreground"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-[15px] w-[15px] shrink-0">
              {icons.docs}
            </svg>
            Docs
          </a>
          <div className="mt-auto border-t border-border pt-2">
            <div className="flex h-9 items-center gap-2.5 px-2">
              <span className="flex h-[22px] w-[22px] items-center justify-center rounded-full bg-[#2a2a2a] font-mono text-[9px] font-medium text-muted-foreground">
                AC
              </span>
              <span className="min-w-0">
                <span className="block truncate text-xs font-[450] leading-[1.3]">Acme</span>
                <span className="block truncate text-[11px] text-muted-foreground">acme-dev</span>
              </span>
            </div>
          </div>
        </aside>
      )}
    </DemoContext.Consumer>
  );
}
