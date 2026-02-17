import { motion } from "motion/react";
import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Github, Menu, X, Sun, Moon } from "lucide-react";
import { useTheme } from "./ThemeProvider";

export function Navigation() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const links = [
    { href: "#features", label: "Features" },
    { href: "#architecture", label: "Architecture" },
    { href: "#installation", label: "Install" },
  ];

  return (
    <motion.nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled
          ? "backdrop-blur-xl border-b"
          : "bg-transparent"
        }`}
      style={scrolled ? { backgroundColor: "var(--nav-bg)", borderColor: "var(--border)" } : {}}
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <motion.a href="#" className="flex items-center gap-2" whileHover={{ opacity: 0.8 }}>
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <span className="text-white font-bold text-xs">H</span>
            </div>
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Helios</span>
          </motion.a>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-6">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-xs hover:opacity-80 transition-opacity"
                style={{ color: "var(--text-secondary)" }}
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-2">
            {/* Theme toggle */}
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
              onClick={() => window.open('https://github.com/pyjeebz/helios', '_blank')}
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
              onClick={() => document.getElementById('installation')?.scrollIntoView({ behavior: 'smooth' })}
            >
              Get Started
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
      {mobileMenuOpen && (
        <motion.div
          className="md:hidden backdrop-blur-xl border-t"
          style={{ backgroundColor: "var(--nav-bg)", borderColor: "var(--border)" }}
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
        >
          <div className="px-6 py-4 space-y-3">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="block text-sm transition-opacity hover:opacity-80 py-1"
                style={{ color: "var(--text-secondary)" }}
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <div className="pt-3 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 text-xs"
                style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
                onClick={() => window.open('https://github.com/pyjeebz/helios', '_blank')}
              >
                <Github className="mr-1.5 h-3.5 w-3.5" />
                GitHub
              </Button>
              <Button
                size="sm"
                className={`flex-1 text-xs ${theme === "dark"
                    ? "bg-white text-black"
                    : "bg-[#0a0a0a] text-white"
                  }`}
                onClick={() => {
                  setMobileMenuOpen(false);
                  document.getElementById('installation')?.scrollIntoView({ behavior: 'smooth' });
                }}
              >
                Get Started
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </motion.nav>
  );
}