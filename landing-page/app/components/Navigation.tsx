import { motion, AnimatePresence } from "motion/react";
import { useState, useEffect, useRef } from "react";
import { Link, useLocation } from "react-router";
import { Button } from "./ui/button";
import {
  Github, Menu, X, Sun, Moon, ChevronDown,
  BookOpen, Zap, Settings, Code2, ArrowRight,
  Activity, BarChart3, Eye, Cloud, Monitor,
  LayoutDashboard, Cpu, Shield, Users, FileText,
  Gauge, AlertTriangle, TrendingUp, Blocks,
} from "lucide-react";
import { useTheme } from "./ThemeProvider";
import { PreScaleLogo } from "./PreScaleLogo";

/* ─── dropdown data ──────────────────────────────────────────── */

const docsItems = [
  {
    title: "Quickstart",
    description: "Get Prescale running in under 5 minutes",
    href: "/docs/quickstart",
    icon: Zap,
  },
  {
    title: "Configuration",
    description: "YAML config, env vars, and deployment options",
    href: "/docs/configuration",
    icon: Settings,
  },
  {
    title: "API Reference",
    description: "REST endpoints for prediction and detection",
    href: "/docs/api",
    icon: Code2,
  },
  {
    title: "Architecture",
    description: "System design and ML pipeline overview",
    href: "/#architecture",
    icon: Blocks,
  },
];

const integrationItems = [
  {
    title: "Prometheus",
    description: "Pull metrics via PromQL queries",
    href: "/integrations/prometheus",
    icon: Activity,
    color: "#E6522C",
  },
  {
    title: "Grafana",
    description: "Visualize predictions on dashboards",
    href: "/integrations/grafana",
    icon: BarChart3,
    color: "#F46800",
  },
  {
    title: "Datadog",
    description: "Ingest metrics from Datadog API",
    href: "/integrations/datadog",
    icon: Eye,
    color: "#632CA6",
  },
  {
    title: "AWS CloudWatch",
    description: "Connect to AWS monitoring metrics",
    href: "/integrations/cloudwatch",
    icon: Cloud,
    color: "#FF9900",
  },
  {
    title: "Azure Monitor",
    description: "Integrate with Azure monitoring suite",
    href: "/integrations/azure-monitor",
    icon: Monitor,
    color: "#0078D4",
  },
];

const resourceItems = [
  {
    title: "Cost Optimization",
    description: "Reduce infrastructure spend with ML insights",
    href: "/docs#cost",
    icon: TrendingUp,
  },
  {
    title: "Anomaly Detection",
    description: "Detect and alert on usage anomalies",
    href: "/docs#anomaly",
    icon: AlertTriangle,
  },
  {
    title: "Community",
    description: "GitHub Discussions and contributing guide",
    href: "https://github.com/pyjeebz/prescale/discussions",
    icon: Users,
    external: true,
  },
];

/* ─── dropdown panel ─────────────────────────────────────────── */

function DropdownPanel({
  items,
  wide,
  onClose,
}: {
  items: typeof docsItems | typeof integrationItems;
  wide?: boolean;
  onClose: () => void;
}) {
  return (
    <motion.div
      className="absolute top-full left-1/2 pt-2"
      style={{ transform: "translateX(-50%)" }}
      initial={{ opacity: 0, y: 4, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 4, scale: 0.98 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
    >
      <div
        className={`rounded-xl border shadow-2xl overflow-hidden ${wide ? "w-[520px]" : "w-[380px]"}`}
        style={{
          backgroundColor: "var(--bg-card)",
          borderColor: "var(--border)",
          boxShadow: "0 20px 60px -12px rgba(0,0,0,0.4)",
        }}
      >
        <div className={`p-2 ${wide ? "grid grid-cols-2 gap-0.5" : "space-y-0.5"}`}>
          {items.map((item) => {
            const Icon = item.icon;
            const isExternal = "external" in item && item.external;
            const Comp = isExternal ? "a" : Link;
            const extraProps = isExternal
              ? { href: item.href, target: "_blank", rel: "noopener noreferrer" }
              : { to: item.href };

            return (
              <Comp
                key={item.title}
                {...(extraProps as any)}
                className="flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-[var(--bg-card-hover)] group"
                onClick={onClose}
              >
                <div
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border"
                  style={{
                    borderColor: "var(--border)",
                    backgroundColor: "var(--bg-accent)",
                  }}
                >
                  <Icon
                    className="h-4 w-4"
                    style={{ color: "color" in item ? (item as any).color : "var(--text-secondary)" }}
                  />
                </div>
                <div className="min-w-0">
                  <div className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>
                    {item.title}
                  </div>
                  <div className="text-[11px] leading-snug mt-0.5" style={{ color: "var(--text-muted)" }}>
                    {item.description}
                  </div>
                </div>
              </Comp>
            );
          })}
        </div>

        {/* Bottom bar with "View all" link */}
        <div
          className="px-4 py-2.5 border-t flex items-center justify-between"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-accent)" }}
        >
          <Link
            to={items === integrationItems ? "/integrations" : "/docs"}
            className="text-[11px] font-medium flex items-center gap-1 transition-colors hover:opacity-80"
            style={{ color: "var(--text-secondary)" }}
            onClick={onClose}
          >
            View all {items === integrationItems ? "integrations" : "documentation"}
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>
    </motion.div>
  );
}

/* ─── nav link with dropdown ─────────────────────────────────── */

function NavDropdown({
  label,
  items,
  wide,
  activeDropdown,
  setActiveDropdown,
}: {
  label: string;
  items: typeof docsItems;
  wide?: boolean;
  activeDropdown: string | null;
  setActiveDropdown: (v: string | null) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isOpen = activeDropdown === label;

  return (
    <div
      className="relative"
      ref={ref}
      onMouseEnter={() => setActiveDropdown(label)}
      onMouseLeave={() => setActiveDropdown(null)}
    >
      <button
        className="flex items-center gap-1 text-xs transition-colors py-2 px-1"
        style={{ color: isOpen ? "var(--text-primary)" : "var(--text-secondary)" }}
        onClick={() => setActiveDropdown(isOpen ? null : label)}
      >
        {label}
        <ChevronDown
          className={`h-3 w-3 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        />
      </button>
      <AnimatePresence>{isOpen && <DropdownPanel items={items} wide={wide} onClose={() => setActiveDropdown(null)} />}</AnimatePresence>
    </div>
  );
}

/* ─── mobile section ─────────────────────────────────────────── */

function MobileSection({
  title,
  items,
  onClose,
}: {
  title: string;
  items: typeof docsItems;
  onClose: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <button
        className="flex items-center justify-between w-full py-2 text-sm"
        style={{ color: "var(--text-primary)" }}
        onClick={() => setExpanded(!expanded)}
      >
        {title}
        <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`} />
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pl-2 pb-2 space-y-1">
              {items.map((item) => {
                const Icon = item.icon;
                const isExternal = "external" in item && item.external;
                const Comp = isExternal ? "a" : Link;
                const extraProps = isExternal
                  ? { href: item.href, target: "_blank", rel: "noopener noreferrer" }
                  : { to: item.href };

                return (
                  <Comp
                    key={item.title}
                    {...(extraProps as any)}
                    className="flex items-center gap-2.5 py-2 px-2 rounded-lg transition-colors hover:bg-[var(--bg-card-hover)]"
                    onClick={onClose}
                  >
                    <Icon
                      className="h-4 w-4 shrink-0"
                      style={{ color: "color" in item ? (item as any).color : "var(--text-muted)" }}
                    />
                    <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                      {item.title}
                    </span>
                  </Comp>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── main navigation ────────────────────────────────────────── */

export function Navigation() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Close mobile menu on navigation
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const isLanding = location.pathname === "/";

  return (
    <motion.nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled || !isLanding ? "backdrop-blur-xl border-b" : "bg-transparent"
        }`}
      style={
        scrolled || !isLanding
          ? { backgroundColor: "var(--nav-bg)", borderColor: "var(--border)" }
          : {}
      }
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <Link to="/" className="flex items-center hover:opacity-80 transition-opacity">
            <PreScaleLogo size="sm" />
          </Link>

          {/* Desktop nav links */}
          <div className="hidden md:flex items-center gap-5">
            {isLanding && (
              <a
                href="#features"
                className="text-xs hover:opacity-80 transition-opacity py-2"
                style={{ color: "var(--text-secondary)" }}
              >
                Features
              </a>
            )}
            <NavDropdown
              label="Docs"
              items={docsItems}
              activeDropdown={activeDropdown}
              setActiveDropdown={setActiveDropdown}
            />
            <NavDropdown
              label="Integrations"
              items={integrationItems}
              wide
              activeDropdown={activeDropdown}
              setActiveDropdown={setActiveDropdown}
            />
            <NavDropdown
              label="Resources"
              items={resourceItems}
              activeDropdown={activeDropdown}
              setActiveDropdown={setActiveDropdown}
            />
          </div>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg transition-colors hover:bg-[var(--bg-card-hover)]"
              style={{ color: "var(--text-muted)" }}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>

            <Button
              variant="ghost"
              size="sm"
              className="hover:bg-[var(--bg-card-hover)] text-xs h-8 px-3"
              style={{ color: "var(--text-secondary)" }}
              onClick={() => window.open("https://github.com/pyjeebz/prescale", "_blank")}
            >
              <Github className="mr-1.5 h-3.5 w-3.5" />
              GitHub
            </Button>
            <Button
              size="sm"
              className={`text-xs h-8 px-4 rounded-lg font-medium ${theme === "dark"
                ? "bg-white text-black hover:bg-neutral-200"
                : "bg-[#0a0a0a] text-white hover:bg-neutral-800"
                }`}
              asChild
            >
              <Link to="/docs/quickstart">Get Started</Link>
            </Button>
          </div>

          {/* Mobile toggle */}
          <div className="md:hidden flex items-center gap-1">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-md transition-colors"
              style={{ color: "var(--text-muted)" }}
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button
              className="p-1.5 rounded-md transition-colors"
              style={{ color: "var(--text-secondary)" }}
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            className="md:hidden backdrop-blur-xl border-t overflow-y-auto"
            style={{
              backgroundColor: "var(--nav-bg)",
              borderColor: "var(--border)",
              maxHeight: "calc(100vh - 56px)",
            }}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-6 py-4 space-y-1">
              {isLanding && (
                <a
                  href="#features"
                  className="block text-sm py-2 transition-opacity hover:opacity-80"
                  style={{ color: "var(--text-secondary)" }}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Features
                </a>
              )}

              <MobileSection title="Docs" items={docsItems} onClose={() => setMobileMenuOpen(false)} />
              <MobileSection title="Integrations" items={integrationItems} onClose={() => setMobileMenuOpen(false)} />
              <MobileSection title="Resources" items={resourceItems} onClose={() => setMobileMenuOpen(false)} />

              <div className="pt-3 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-xs"
                  style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
                  onClick={() => window.open("https://github.com/pyjeebz/prescale", "_blank")}
                >
                  <Github className="mr-1.5 h-3.5 w-3.5" />
                  GitHub
                </Button>
                <Button
                  size="sm"
                  className={`flex-1 text-xs ${theme === "dark" ? "bg-white text-black" : "bg-[#0a0a0a] text-white"
                    }`}
                  asChild
                >
                  <Link to="/docs/quickstart" onClick={() => setMobileMenuOpen(false)}>
                    Get Started
                  </Link>
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}