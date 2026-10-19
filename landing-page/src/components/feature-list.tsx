import {
  AnimatePresence,
  MotionConfig,
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
  useVelocity,
} from "framer-motion";
import { useRef, useState, type ComponentType, type MouseEvent, type ReactNode } from "react";
import {
  AgentPreview,
  DiagnosisPreview,
  LaunchPreview,
  PrCommentPreview,
  PreviewWindow,
  SignoffPreview,
  TerminalPreview,
} from "./feature-previews";
import { CALM } from "./dots";
import { MiniBar } from "./mini-bar";
import { cn } from "./ui";

/** Gap between the cursor and the card, which sits beside it so the row stays readable. */
const GAP = 28;
const EDGE = 12;
const DEFAULT_SIZE = { w: 340, h: 230 };

type Feature = {
  title: string;
  body: ReactNode;
  window: string;
  Preview: ComponentType;
  /** Draws its own windows instead of sitting in the standard frame. */
  bare?: boolean;
  size?: { w: number; h: number };
};

const FEATURES: Feature[] = [
  {
    title: "One command, a real answer",
    body: "Point PreScale at a URL. It ramps virtual users until something gives and tells you how many users you survive, with a confidence band. No scripts to write.",
    window: "~/acme-shop — zsh",
    Preview: TerminalPreview,
  },
  {
    title: "It tells you why",
    body: "When something breaks, PreScale probes the cause, like an exhausted connection pool, a concurrency ceiling or a slow endpoint, then shows the evidence and the fix.",
    window: "Run a41f9c2 · Diagnosis",
    Preview: DiagnosisPreview,
  },
  {
    title: "Capacity on every pull request",
    body: "The GitHub Action tests each preview deploy and keeps one comment on the PR: the change against main, what breaks first, and how to fix it.",
    window: "Pull request #42",
    Preview: PrCommentPreview,
  },
  {
    title: "GO or NO-GO for your launch",
    body: (
      <>
        Launching on Product Hunt, Hacker News or Reddit? Add{" "}
        <code className="whitespace-nowrap font-mono text-[0.92em] text-foreground">--profile product-hunt</code> to ramp past that
        launch&apos;s peak, and Launch Guard gives a clear GO or NO-GO with a checklist behind it.
      </>
    ),
    window: "Launch Guard",
    Preview: LaunchPreview,
  },
  {
    title: "Proof you can share",
    body: "Verify you own the site, sign off a result, and share a page that says so. The README badge turns red on its own if capacity drops.",
    window: "Sign-off · api.acme.dev",
    Preview: SignoffPreview,
  },
  {
    title: "Your coding agent can run it too",
    body: "PreScale ships an MCP server. Ask your agent to load-test the branch it just changed, read the diagnosis and apply the fix, all on your machine.",
    window: "agent session",
    Preview: AgentPreview,
    bare: true,
    size: { w: 420, h: 260 },
  },
];

/** Only real mice get the floating preview; touch keeps a plain list. */
const finePointer = () => window.matchMedia("(hover: hover) and (pointer: fine)").matches;

export function FeatureList() {
  const [active, setActive] = useState<number | null>(null);
  const [hovering, setHovering] = useState(false);
  const reduced = useReducedMotion();

  // Pointer position lives in motion values, so moving the mouse never re-renders React.
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const x = useSpring(mouseX, { stiffness: 150, damping: 18, mass: 0.5 });
  const y = useSpring(mouseY, { stiffness: 150, damping: 18, mass: 0.5 });
  // Lean into fast horizontal moves, settle back to level at rest.
  const velocityX = useVelocity(x);
  const tilt = useTransform(velocityX, [-1600, 0, 1600], [-12, 0, 12], { clamp: true });

  const pointer = useRef({ x: 0, y: 0 });
  const size = useRef(DEFAULT_SIZE);
  const titles = useRef<Array<HTMLSpanElement | null>>([]);
  const activeRef = useRef<number | null>(null);

  /**
   * Right of the cursor and vertically centred on it, but never over the hovered
   * row's title: the card starts past the end of the title text. Stays on screen.
   */
  const place = () => {
    const { w, h } = size.current;
    const { x: cx, y: cy } = pointer.current;
    const title = activeRef.current === null ? null : titles.current[activeRef.current];
    const clearOfTitle = title ? title.getBoundingClientRect().right + GAP : 0;
    const left = Math.max(cx + GAP, clearOfTitle);
    mouseX.set(Math.max(EDGE, Math.min(left, window.innerWidth - w - EDGE)));
    mouseY.set(Math.min(Math.max(EDGE, cy - h / 2), window.innerHeight - h - EDGE));
  };

  const track = (event: MouseEvent) => {
    pointer.current = { x: event.clientX, y: event.clientY };
    place();
  };

  const enter = (event: MouseEvent) => {
    if (!finePointer()) return;
    track(event);
    setHovering(true);
    // Start beside the cursor instead of flying in from the corner. Wait a frame so
    // the hovered row has set its target too; a spring drops targets set right after a jump.
    requestAnimationFrame(() => {
      x.jump(mouseX.get());
      y.jump(mouseY.get());
    });
  };

  const activate = (index: number) => {
    size.current = FEATURES[index].size ?? DEFAULT_SIZE;
    activeRef.current = index;
    place();
    setActive(index);
  };

  const leave = () => {
    setHovering(false);
    setActive(null);
    activeRef.current = null;
  };

  const current = active === null ? null : FEATURES[active];

  return (
    <div onMouseEnter={enter} onMouseMove={track} onMouseLeave={leave} className="border-t border-border">
      <ol>
        {FEATURES.map((feature, index) => (
          <li
            key={feature.title}
            onMouseEnter={() => activate(index)}
            className="grid grid-cols-[48px_minmax(0,1fr)] gap-y-3 border-b border-border py-8 md:grid-cols-[72px_minmax(0,1fr)_340px] md:items-center md:gap-x-12 md:py-10"
          >
            <span className="flex flex-col gap-2.5 self-start pt-1.5 md:self-center md:pt-0">
              <span
                className="font-mono text-[11px] tabular-nums text-muted-foreground transition-colors duration-200"
                style={active === index ? { color: CALM[index % CALM.length] } : undefined}
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              {/* Each row's own bar; it "measures" (grows) while the row is hovered. */}
              <MiniBar
                color={CALM[index % CALM.length]}
                cell={4}
                className="transition-[width] duration-500 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
                style={{ width: active === index ? 64 : 32 }}
              />
            </span>
            <h3
              className={cn(
                "text-[22px] font-medium leading-[1.2] tracking-[-0.025em] transition-colors duration-200 md:text-[30px]",
                active !== null && active !== index ? "text-muted-foreground" : "text-foreground",
              )}
            >
              <span ref={(element) => { titles.current[index] = element; }}>{feature.title}</span>
            </h3>
            <p className="col-start-2 text-sm leading-[1.6] text-muted-foreground md:col-start-3 md:text-[13px]">{feature.body}</p>
          </li>
        ))}
      </ol>

      <MotionConfig reducedMotion="user">
        <AnimatePresence>
          {hovering && current && (
            <motion.div
              aria-hidden
              className="pointer-events-none fixed left-0 top-0 z-50 hidden md:block"
              style={{ x, y, rotate: reduced ? 0 : tilt }}
              initial={{ opacity: 0, scale: 0.85, width: current.size?.w ?? DEFAULT_SIZE.w, height: current.size?.h ?? DEFAULT_SIZE.h }}
              animate={{ opacity: 1, scale: 1, width: current.size?.w ?? DEFAULT_SIZE.w, height: current.size?.h ?? DEFAULT_SIZE.h }}
              exit={{ opacity: 0, scale: 0.85 }}
              transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
            >
              <AnimatePresence mode="popLayout" initial={false}>
                <motion.div
                  key={active}
                  className="absolute inset-0"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18 }}
                >
                  {current.bare ? (
                    <current.Preview />
                  ) : (
                    <PreviewWindow title={current.window}>
                      <current.Preview />
                    </PreviewWindow>
                  )}
                </motion.div>
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </MotionConfig>
    </div>
  );
}
