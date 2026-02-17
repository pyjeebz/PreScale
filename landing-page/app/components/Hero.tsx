import { motion } from "motion/react";
import { Button } from "./ui/button";
import { ArrowRight, Github, Terminal } from "lucide-react";
import { useTheme } from "./ThemeProvider";

export function Hero() {
  const { theme } = useTheme();

  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden" style={{ backgroundColor: "var(--bg-primary)" }}>
      {/* Subtle grain texture */}
      <div className="absolute inset-0" style={{
        opacity: "var(--noise-opacity)",
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
      }} />

      {/* Holographic gradient accent — top right */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px]"
        style={{
          opacity: "var(--holo-opacity)",
          background: "radial-gradient(circle at center, rgba(99,102,241,0.4) 0%, rgba(168,85,247,0.2) 40%, transparent 70%)",
        }}
      />

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Tag line chip */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-10"
            style={{ border: "1px solid var(--border)", backgroundColor: "var(--bg-accent)" }}
          >
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
            </span>
            <span className="text-xs tracking-wide uppercase" style={{ color: "var(--text-secondary)" }}>Open Source · Apache 2.0</span>
          </div>
        </motion.div>

        <motion.h1
          className="text-5xl sm:text-6xl lg:text-[4.5rem] font-semibold leading-[1.1] tracking-tight mb-6"
          style={{ color: "var(--text-primary)" }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
        >
          Predict. Detect.{" "}
          <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-fuchsia-400 bg-clip-text text-transparent">
            Scale.
          </span>
        </motion.h1>

        <motion.p
          className="text-lg sm:text-xl mb-12 max-w-2xl mx-auto leading-relaxed"
          style={{ color: "var(--text-secondary)" }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          Helios uses machine learning to forecast traffic, detect anomalies, and
          optimize resource scaling — before your users notice a thing.
        </motion.p>

        <motion.div
          className="flex flex-col sm:flex-row gap-3 justify-center items-center mb-16"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <Button
            size="lg"
            className={`px-6 py-5 text-sm font-medium group rounded-lg ${theme === "dark"
                ? "bg-white text-black hover:bg-neutral-200"
                : "bg-[#0a0a0a] text-white hover:bg-neutral-800"
              }`}
            onClick={() => document.getElementById('installation')?.scrollIntoView({ behavior: 'smooth' })}
          >
            Get Started
            <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="px-6 py-5 text-sm font-medium rounded-lg"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-accent)", color: "var(--text-secondary)" }}
            onClick={() => window.open('https://github.com/pyjeebz/helios', '_blank')}
          >
            <Github className="mr-2 h-4 w-4" />
            Star on GitHub
          </Button>
        </motion.div>

        {/* Inline terminal preview */}
        <motion.div
          className="max-w-xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.6 }}
        >
          <div className="rounded-xl p-1" style={{ border: "1px solid var(--border)", backgroundColor: "var(--bg-card)" }}>
            <div className="flex items-center gap-2 px-4 py-2.5" style={{ borderBottom: "1px solid var(--border)" }}>
              <Terminal className="h-3.5 w-3.5" style={{ color: "var(--text-muted)" }} />
              <span className="text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>Terminal</span>
            </div>
            <div className="px-4 py-4 font-mono text-sm text-left">
              <div style={{ color: "var(--text-muted)" }}>$ pip install helios-agent</div>
              <div className="text-emerald-400 mt-1">✓ Installed helios-agent v0.2.0</div>
              <div style={{ color: "var(--text-muted)" }} className="mt-3">$ helios predict cpu -d api -n prod</div>
              <div className="mt-1" style={{ color: "var(--text-secondary)" }}>
                <span className="text-indigo-400">Forecasting</span> → CPU 67% → 82% in 30min
              </div>
              <div className="text-amber-400 mt-1">⚡ Recommended: scale 3 → 5 replicas</div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}