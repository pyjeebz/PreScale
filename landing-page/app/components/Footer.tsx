import { Github } from "lucide-react";

export function Footer() {
  return (
    <footer style={{ backgroundColor: "var(--bg-primary)", borderTop: "1px solid var(--border)" }}>
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="flex flex-col md:flex-row justify-between gap-8">
          {/* Logo + description */}
          <div className="max-w-xs">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <span className="text-white font-bold text-xs">P</span>
              </div>
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Prescale</span>
            </div>
            <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Open-source predictive infrastructure intelligence.
              Apache 2.0 licensed.
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-16">
            <div>
              <div className="text-xs font-medium mb-3 uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>Resources</div>
              <ul className="space-y-2">
                {[
                  { label: "Documentation", href: "https://github.com/pyjeebz/prescale/tree/main/docs" },
                  { label: "API Reference", href: "https://github.com/pyjeebz/prescale/tree/main/docs" },
                  { label: "Architecture", href: "https://github.com/pyjeebz/prescale/blob/main/docs/architecture/ARCHITECTURE.md" },
                ].map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs transition-opacity hover:opacity-80"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs font-medium mb-3 uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>Community</div>
              <ul className="space-y-2">
                {[
                  { label: "GitHub", href: "https://github.com/pyjeebz/prescale" },
                  { label: "Discussions", href: "https://github.com/pyjeebz/prescale/discussions" },
                  { label: "Contributing", href: "https://github.com/pyjeebz/prescale/blob/main/CONTRIBUTING.md" },
                ].map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs transition-opacity hover:opacity-80"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between mt-12 pt-6" style={{ borderTop: "1px solid var(--border-subtle)" }}>
          <span className="text-[11px]" style={{ color: "var(--text-faint)" }}>
            © {new Date().getFullYear()} Prescale Contributors
          </span>
          <a
            href="https://github.com/pyjeebz/prescale"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-opacity hover:opacity-80"
            style={{ color: "var(--text-faint)" }}
          >
            <Github className="h-4 w-4" />
          </a>
        </div>
      </div>
    </footer>
  );
}