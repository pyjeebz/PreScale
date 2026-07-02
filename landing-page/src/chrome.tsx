import { type ReactNode } from "react";
import { motion } from "framer-motion";

/* ── Reveal-on-scroll section (no hover scaling — brutalist) ─────── */
export function Reveal({ children, className = "", id }: { children: ReactNode; className?: string; id?: string }) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={`border-b border-line ${className}`}
    >
      {children}
    </motion.section>
  );
}

/* ── Real links ──────────────────────────────────────────────────── */
export const REPO = "https://github.com/pyjeebz/prescale";
export const RELEASES = "https://github.com/pyjeebz/prescale/releases";
export const PYPI = "https://pypi.org/project/prescale/";

const ext = (href: string) =>
  href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {};

/* ── Nav (shared across pages) ───────────────────────────────────── */
const NAV = [
  { label: "GitHub", href: REPO },
  { label: "Docs", href: "#/docs" },
  { label: "Changelog", href: RELEASES },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-night/85 backdrop-blur-md">
      <div className="flex h-16 items-center justify-between px-8">
        <a href="#/" className="flex items-center gap-2">
          <span className="select-none text-accent">▍</span>
          <span className="font-medium">prescale</span>
        </a>
        <nav className="flex items-center gap-1 text-[0.82rem]">
          {NAV.map((l) => (
            <a
              key={l.label}
              href={l.href}
              {...ext(l.href)}
              className="hidden px-3 py-1.5 text-dim transition-colors hover:text-cream sm:inline-block"
            >
              {l.label}
            </a>
          ))}
          <a
            href="#install"
            className="ml-1 border border-line-strong px-3.5 py-1.5 text-cream transition-colors hover:bg-cream hover:text-night"
          >
            Install
          </a>
        </nav>
      </div>
    </header>
  );
}

/* ── Footer — segmented terminal status bar (shared) ─────────────── */
export function Footer() {
  const cells: [string, string, string, string][] = [
    ["Star on GitHub", "drop a ★, dodge an outage", REPO, "border-b border-line sm:border-b-0 sm:border-r"],
    ["Docs", "read the manual", "#/docs", "border-b border-line sm:border-b-0 sm:border-r"],
    ["Changelog", "what broke, what's fixed", RELEASES, ""],
  ];
  return (
    <footer className="-mt-px border-y border-line">
      <div className="grid grid-cols-1 sm:grid-cols-3">
        {cells.map(([t, sub, href, border]) => (
          <a
            key={t}
            href={href}
            {...ext(href)}
            className={`p-8 transition-colors hover:bg-night-raised ${border}`}
          >
            <span className="block text-[0.85rem] font-medium text-cream">{t}</span>
            <span className="mt-1 block text-[0.72rem] text-faint">{sub}</span>
          </a>
        ))}
      </div>
    </footer>
  );
}
