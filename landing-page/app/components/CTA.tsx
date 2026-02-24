import { motion } from "motion/react";
import { useInView } from "./hooks/useInView";
import { Button } from "./ui/button";
import { ArrowRight, Star } from "lucide-react";
import { useTheme } from "./ThemeProvider";

export function CTA() {
  const [ref, isInView] = useInView({ threshold: 0.3 });
  const { theme } = useTheme();

  return (
    <section ref={ref} className="py-24" style={{ backgroundColor: "var(--bg-primary)" }}>
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          className="relative rounded-2xl p-12 text-center overflow-hidden"
          style={{ border: "1px solid var(--border)", backgroundColor: "var(--bg-card)" }}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.5 }}
        >
          {/* Holographic accent */}
          <div className="absolute inset-0"
            style={{
              opacity: "var(--holo-opacity)",
              background: "radial-gradient(ellipse at top, rgba(129,140,248,0.4) 0%, transparent 60%)",
            }}
          />
          <div className="relative z-10">
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
              Stop reacting. Start predicting.
            </h2>
            <p className="text-lg max-w-md mx-auto mb-8" style={{ color: "var(--text-secondary)" }}>
              Prescale gives your team visibility into what's coming next — before it becomes an incident.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
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
                style={{
                  borderColor: "var(--border)",
                  backgroundColor: "var(--bg-accent)",
                  color: "var(--text-secondary)",
                }}
                onClick={() => window.open('https://github.com/pyjeebz/prescale', '_blank')}
              >
                <Star className="mr-2 h-4 w-4" />
                Star on GitHub
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}