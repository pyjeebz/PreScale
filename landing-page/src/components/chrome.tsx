import { useEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, MotionConfig, motion, useScroll, useTransform } from "framer-motion";
import { CALM, checker, sparse } from "./dots";
import { Logo, RampLogo } from "./logo";
import { MiniBar } from "./mini-bar";
import { CopyButton, buttonPrimary, buttonSecondary, cn } from "./ui";
import { DOGFOOD, type DogfoodRun } from "../data/dogfood";

export const LINKS = {
  dashboard: "/dashboard",
  docs: "https://github.com/pyjeebz/prescale#readme",
  repo: "https://github.com/pyjeebz/prescale",
  releases: "https://github.com/pyjeebz/prescale/releases",
  action: "https://github.com/pyjeebz/prescale/tree/main/action",
  pypi: "https://pypi.org/project/prescale/",
  mcp: "https://github.com/pyjeebz/prescale#coding-agents-mcp",
  data: "https://github.com/pyjeebz/prescale#what-gets-uploaded",
};

const external = (href: string) => (href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {});

/** Settles in once when scrolled into view. */
export function Reveal({ children, className, id, as = "section" }: { children: ReactNode; className?: string; id?: string; as?: "section" | "div" }) {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const Tag = as;
  return (
    <Tag ref={ref as never} id={id} data-shown={shown ? "" : undefined} className={cn("reveal scroll-mt-20", className)}>
      {children}
    </Tag>
  );
}

/** Big links in the menu, then the smaller developer links beside them. */
const MENU_MAIN = [
  { label: "Product", href: "#product" },
  { label: "Features", href: "#features" },
  { label: "Docs", href: LINKS.docs },
  { label: "Dashboard", href: LINKS.dashboard },
];
const MENU_DEV = [
  { label: "GitHub", href: LINKS.repo },
  { label: "GitHub Action", href: LINKS.action },
  { label: "MCP server", href: LINKS.mcp },
  { label: "PyPI", href: LINKS.pypi },
  { label: "Changelog", href: LINKS.releases },
];

const GITHUB_ICON =
  "M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56 0-.27-.01-1.17-.02-2.12-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.19 1.76 1.19 1.03 1.76 2.69 1.25 3.35.96.1-.75.4-1.25.72-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.78 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.42-2.7 5.4-5.26 5.68.41.35.77 1.05.77 2.12 0 1.53-.01 2.76-.01 3.14 0 .31.21.68.8.56A11.52 11.52 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z";

const SECTIONS = MENU_MAIN.filter((link) => link.href.startsWith("#")).map((link) => link.href.slice(1));

/** The section currently under the nav, so the menu can mark it. */
function useActiveSection() {
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    const visible = new Map<string, boolean>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) visible.set(entry.target.id, entry.isIntersecting);
        // When two sections share the band, the lower one is the one being read.
        setActive(SECTIONS.filter((id) => visible.get(id)).at(-1) ?? null);
      },
      // A band under the nav: a section counts once it reaches the top third of the screen.
      { rootMargin: "-80px 0px -66% 0px" },
    );
    for (const id of SECTIONS) {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, []);
  return active;
}

/** Scroll progress drawn like a load ramp along the menu pill's bottom edge. */
function ScrollRamp() {
  const { scrollYProgress } = useScroll();
  const width = useTransform(scrollYProgress, (progress) => `${progress * 100}%`);
  return (
    <motion.span aria-hidden className="pointer-events-none absolute bottom-0 left-0 flex h-[2px] justify-end overflow-hidden" style={{ width }}>
      <span className="min-w-0 flex-1 shrink-0" style={{ background: sparse(CALM[0], 2) }} />
      <span className="w-6 shrink-0" style={{ background: checker(CALM[0], 2) }} />
      <span className="w-2 shrink-0" style={{ background: CALM[0] }} />
    </motion.span>
  );
}

const EASE = [0.23, 1, 0.32, 1] as const;

/*
 * Three floating glass pills, after spacefs.com: the mark (it widens to show the
 * name on hover), a centred Menu pill that opens in place into the full menu,
 * and the call to action.
 */
export function Nav() {
  const active = useActiveSection();
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);

  // Escape and a click anywhere outside close the menu.
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    const onPointer = (event: PointerEvent) => {
      if (menu.current && !menu.current.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <MotionConfig reducedMotion="user">
      <header className="pointer-events-none fixed inset-x-0 top-0 z-50">
        {/* A soft blur under the pills that fades out downward, so content passing beneath stays calm. */}
        <div
          aria-hidden
          className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-background/70 to-transparent backdrop-blur-[6px] [mask-image:linear-gradient(#000_45%,transparent)]"
        />
        <div className="relative flex h-20 items-center justify-between px-4 sm:px-8 lg:px-10">
          <a
            href="#top"
            aria-label="PreScale home"
            onClick={close}
            className="glass-control group pointer-events-auto flex h-12 items-center rounded-full px-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            {/* Hovering the mark runs a tiny load test: the bars ramp out. */}
            <RampLogo />
          </a>

          <div
            ref={menu}
            className={cn(
              // z-20: the open panel covers the right-hand buttons on narrow screens.
              "pointer-events-auto absolute top-2.5 z-20 sm:left-1/2 sm:-translate-x-1/2",
              // Phones have no room for a centred pill next to the right-hand actions.
              open ? "left-4" : "left-[76px]",
            )}
          >
            <div
              className={cn(
                "relative rounded-[28px] p-1.5 transition-[width] duration-[450ms] ease-[var(--ease-out)] motion-reduce:transition-none",
                open ? "w-[min(520px,calc(100vw-32px))]" : "w-[60px] sm:w-[128px]",
              )}
            >
              <motion.div
                aria-hidden
                className="glass-strong pointer-events-none absolute inset-0 rounded-[28px]"
                initial={false}
                animate={{ opacity: open ? 1 : 0 }}
                transition={{ duration: 0.25 }}
              />
              <div className="relative">
                <div className="glass-control relative flex h-12 items-center justify-center overflow-hidden rounded-full px-1.5">
                  <button
                    type="button"
                    aria-expanded={open}
                    aria-controls="site-menu"
                    aria-label={open ? "Close menu" : "Open menu"}
                    onClick={() => setOpen((value) => !value)}
                    className="flex items-center gap-2.5 rounded-full px-3.5 py-1.5 text-sm font-medium transition-opacity duration-150 hover:opacity-80"
                  >
                    <span aria-hidden className="relative grid h-4 w-4 place-items-center">
                      <span
                        className="col-start-1 row-start-1 h-[1.5px] w-[15px] rounded-full bg-current transition-transform duration-300 ease-[var(--ease-out)]"
                        style={{ transform: open ? "rotate(45deg)" : "translateY(-3px)" }}
                      />
                      <span
                        className="col-start-1 row-start-1 h-[1.5px] w-[15px] rounded-full bg-current transition-transform duration-300 ease-[var(--ease-out)]"
                        style={{ transform: open ? "rotate(-45deg)" : "translateY(3px)" }}
                      />
                    </span>
                    <span className="hidden min-w-[5ch] text-left sm:inline">{open ? "Close" : "Menu"}</span>
                  </button>
                  {!open && <ScrollRamp />}
                </div>

                <AnimatePresence initial={false}>
                  {open && (
                    <motion.nav
                      id="site-menu"
                      aria-label="Site"
                      className="overflow-hidden"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.4, ease: EASE }}
                    >
                      <div className="grid max-h-[calc(100svh-9rem)] gap-7 overflow-y-auto overscroll-contain px-4 pb-4 pt-7 [scrollbar-width:none] sm:grid-cols-2 sm:gap-6">
                        <MenuGroup label="Explore">
                          {MENU_MAIN.map((link, index) => {
                            const current = link.href === `#${active}`;
                            return (
                              <MenuItem key={link.label} index={index}>
                                <a
                                  href={link.href}
                                  {...external(link.href)}
                                  onClick={close}
                                  aria-current={current ? "location" : undefined}
                                  className="flex w-fit items-center gap-3 text-[24px] font-medium leading-tight tracking-[-0.025em] transition-colors duration-150 hover:text-muted-foreground"
                                >
                                  {link.label}
                                  {current && <MiniBar color={CALM[0]} />}
                                </a>
                              </MenuItem>
                            );
                          })}
                        </MenuGroup>
                        <MenuGroup label="Developers">
                          {MENU_DEV.map((link, index) => (
                            <MenuItem key={link.label} index={index + 2}>
                              <a
                                href={link.href}
                                {...external(link.href)}
                                onClick={close}
                                className="w-fit text-[15px] text-muted-foreground transition-colors duration-150 hover:text-foreground"
                              >
                                {link.label}
                              </a>
                            </MenuItem>
                          ))}
                        </MenuGroup>
                      </div>
                      <div className="mx-4 flex items-center justify-between border-t border-border/70 py-3.5 text-[13px] text-muted-foreground">
                        <span className="flex items-center gap-4">
                          <a href={LINKS.dashboard} onClick={close} className="font-medium text-foreground sm:hidden">
                            Log in
                          </a>
                          <a href={LINKS.data} onClick={close} className="transition-colors duration-150 hover:text-foreground">
                            What gets uploaded
                          </a>
                        </span>
                        <span className="font-mono text-[11px]">Apache-2.0</span>
                      </div>
                    </motion.nav>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>

          <div className="pointer-events-auto flex items-center gap-2">
            {/* Open source and free: say so in the bar, not only in the menu. */}
            <a
              href={LINKS.repo}
              {...external(LINKS.repo)}
              aria-label="PreScale on GitHub (open source)"
              className="glass-control inline-flex h-10 items-center gap-2 rounded-full px-3 text-sm font-medium transition-[transform,opacity] duration-150 ease-[var(--ease-out)] active:scale-[.97] md:px-4 [@media(hover:hover)]:hover:opacity-85"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden>
                <path d={GITHUB_ICON} />
              </svg>
              <span className="hidden md:inline">GitHub</span>
            </a>
            <a
              href={LINKS.dashboard}
              className="hidden h-10 items-center rounded-full px-3 text-sm font-medium text-muted-foreground transition-colors duration-150 hover:text-foreground sm:inline-flex"
            >
              Log in
            </a>
            <a
              href={LINKS.dashboard}
              className="inline-flex h-10 items-center rounded-full bg-foreground px-4 text-sm font-medium text-background shadow-[inset_0_1px_0_rgb(255_255_255/0.5),0_8px_20px_-10px_rgb(0_0_0/0.8)] transition-[background-color,transform] duration-150 ease-[var(--ease-out)] active:scale-[.97] [@media(hover:hover)]:hover:bg-white"
            >
              Get started
            </a>
          </div>
        </div>
      </header>
    </MotionConfig>
  );
}

function MenuGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="mb-1 font-mono text-[11px] text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

/** Menu items rise in one after another as the menu opens. */
function MenuItem({ index, children }: { index: number; children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.08 + index * 0.035, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

const INSTALL = [
  { key: "macOS / Linux", command: "curl -fsSL https://prescale.dev/install | sh" },
  { key: "Windows", command: "irm https://prescale.dev/install.ps1 | iex" },
  { key: "pip", command: "pip install prescale" },
] as const;

export function InstallBox({ className }: { className?: string }) {
  const [tab, setTab] = useState<(typeof INSTALL)[number]["key"]>("macOS / Linux");
  const active = INSTALL.find((option) => option.key === tab)!;
  return (
    <div className={cn("w-full max-w-[520px] overflow-hidden rounded-[10px] border border-border bg-background text-left", className)}>
      <div role="tablist" aria-label="Install command" className="flex border-b border-border px-1.5">
        {INSTALL.map((option) => (
          <button
            key={option.key}
            role="tab"
            aria-selected={option.key === tab}
            onClick={() => setTab(option.key)}
            className={cn(
              "-mb-px border-b px-2.5 py-2 text-xs font-[450] transition-colors duration-150",
              option.key === tab ? "border-foreground text-foreground" : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {option.key}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 py-2 pl-4 pr-2">
        <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap font-mono text-[13px] [scrollbar-width:none]">
          <span className="select-none text-muted-foreground">$ </span>
          {active.command}
        </code>
        <CopyButton text={active.command} label="Copy install command" />
      </div>
    </div>
  );
}

export function Ctas({ className }: { className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-center justify-center gap-2", className)}>
      <a href={LINKS.dashboard} className={cn(buttonPrimary, "h-9 px-4 text-sm")}>
        Get started
      </a>
      <a href={LINKS.docs} className={cn(buttonSecondary, "h-9 px-4 text-sm")}>
        Read the docs
      </a>
    </div>
  );
}

const FOOTER: Array<[string, Array<[string, string]>]> = [
  [
    "Product",
    [
      ["Dashboard", LINKS.dashboard],
      ["Docs", LINKS.docs],
      ["Changelog", LINKS.releases],
      ["What gets uploaded", LINKS.data],
    ],
  ],
  [
    "Developers",
    [
      ["GitHub", LINKS.repo],
      ["GitHub Action", LINKS.action],
      ["MCP server", LINKS.mcp],
      ["PyPI", LINKS.pypi],
      ["License (Apache-2.0)", `${LINKS.repo}/blob/main/LICENSE`],
    ],
  ],
];

/*
 * The footer wordmark, drawn like one of the hero's bars: sparse dots, then a
 * checkerboard, then solid. Three stacked copies of the word, each clipped to
 * its stretch. Kept grey so the hero stays the page's one colourful moment.
 */
const WORD_COLOR = "#3a3a3a";
const dots = (cell: string) => `conic-gradient(${WORD_COLOR} 25%, transparent 0) 0 0 / ${cell} ${cell}`;
const checks = (cell: string) =>
  `conic-gradient(${WORD_COLOR} 25%, transparent 0 50%, ${WORD_COLOR} 0 75%, transparent 0) 0 0 / ${cell} ${cell}`;

/*
 * With a real run on prescale.dev (data/dogfood.ts), the word is our own load
 * test instead: one vertical slice per ramp stage, left to right, filled by that
 * stage's p95 on a log scale from the run's fastest stage to its slowest.
 */
function dogfoodLayers(run: DogfoodRun, cell: string): Array<[string, string]> {
  const p95s = run.stages.map((stage) => stage.p95);
  const low = Math.log(Math.min(...p95s));
  const span = Math.log(Math.max(...p95s)) - low || 1;
  const width = 100 / run.stages.length;
  return run.stages.map((stage, index) => {
    const t = (Math.log(stage.p95) - low) / span;
    const fill = t < 1 / 3 ? dots(cell) : t < 2 / 3 ? checks(cell) : WORD_COLOR;
    // A hair of overlap so neighbouring slices don't leave a seam.
    const left = Math.max(index * width - 0.05, 0);
    const right = Math.max(100 - (index + 1) * width - 0.05, 0);
    return [fill, `inset(0 ${right.toFixed(2)}% 0 ${left.toFixed(2)}%)`];
  });
}

function DotWordmark() {
  const cell = "var(--cell)";
  const layers: Array<[string, string]> = DOGFOOD
    ? dogfoodLayers(DOGFOOD, cell)
    : [
        [dots(cell), "inset(0 46% 0 0)"],
        [checks(cell), "inset(0 20% 0 54%)"],
        [WORD_COLOR, "inset(0 0 0 80%)"],
      ];
  return (
    <div
      aria-hidden
      className="relative mt-10 select-none text-center text-[clamp(88px,22vw,300px)] font-semibold leading-[0.78] tracking-[-0.06em] [--cell:4px] lg:[--cell:6px]"
    >
      <span className="invisible">PreScale</span>
      {layers.map(([background, clip]) => (
        <span
          key={clip}
          className="absolute inset-0 bg-clip-text text-transparent"
          style={{ background, WebkitBackgroundClip: "text", backgroundClip: "text", clipPath: clip }}
        >
          PreScale
        </span>
      ))}
    </div>
  );
}

const ms = (value: number) => (value >= 1000 ? `${(value / 1000).toFixed(1)}s` : `${value}ms`);

/** Says where the wordmark's dots come from, and links to the run. */
function DogfoodCaption({ run }: { run: DogfoodRun }) {
  const p95s = run.stages.map((stage) => stage.p95);
  const date = new Date(run.measuredAt).toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" });
  const text = `The wordmark below is our own load test: p95 per stage on ${run.host}, ${ms(Math.min(...p95s))} to ${ms(Math.max(...p95s))}, ${date}.`;
  return (
    <p className="text-xs text-muted-foreground">
      {text}
      {run.report && (
        <>
          {" "}
          <a href={run.report} className="underline decoration-border underline-offset-4 transition-colors duration-150 hover:text-foreground">
            See the run
          </a>
        </>
      )}
    </p>
  );
}

export function Footer() {
  return (
    <footer className="overflow-hidden border-t border-border">
      <div className="mx-auto grid max-w-[1200px] gap-10 px-4 py-14 sm:grid-cols-[2fr_1fr_1fr] sm:px-8">
        <div>
          <div className="flex items-center gap-2.5">
            <Logo />
            <span className="text-sm font-medium">PreScale</span>
          </div>
          <p className="mt-4 max-w-[260px] text-sm leading-relaxed text-muted-foreground">
            Know how much traffic every deploy can take, why it breaks, and how to fix it.
          </p>
        </div>
        {FOOTER.map(([heading, links]) => (
          <div key={heading}>
            <h3 className="text-sm font-medium">{heading}</h3>
            <ul className="mt-3 flex flex-col gap-2">
              {links.map(([label, href]) => (
                <li key={label}>
                  <a href={href} {...external(href)} className="text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground">
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mx-auto flex max-w-[1200px] flex-wrap justify-between gap-x-8 gap-y-2 px-4 sm:px-8">
        <p className="text-xs text-muted-foreground">© 2026 PreScale. The CLI is open source under Apache-2.0.</p>
        {DOGFOOD && <DogfoodCaption run={DOGFOOD} />}
      </div>
      <DotWordmark />
    </footer>
  );
}
