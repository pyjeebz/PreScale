import { motion } from "motion/react";
import { useInView } from "./hooks/useInView";
import { Database, Cpu, LineChart, ArrowRight } from "lucide-react";

const stages = [
  {
    icon: Database,
    title: "Collect",
    description: "Pluggable agents ingest metrics from any source",
    details: ["System metrics", "Prometheus", "GCP · AWS · Azure", "Custom sources"],
    color: "from-indigo-500 to-indigo-600",
  },
  {
    icon: Cpu,
    title: "Analyze",
    description: "ML models learn your infrastructure patterns",
    details: ["Prophet forecasting", "XGBoost anomalies", "108 features", "Auto-retraining"],
    color: "from-purple-500 to-purple-600",
  },
  {
    icon: LineChart,
    title: "Act",
    description: "Get predictions and scaling recommendations",
    details: ["REST API", "Vue.js dashboard", "CLI tools", "KEDA integration"],
    color: "from-fuchsia-500 to-fuchsia-600",
  },
];

export function Architecture() {
  const [ref, isInView] = useInView({ threshold: 0.2 });

  return (
    <section ref={ref} className="py-24" style={{ backgroundColor: "var(--bg-primary)" }} id="architecture">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 16 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
            Three steps. Zero complexity.
          </h2>
          <p className="text-lg max-w-xl mx-auto" style={{ color: "var(--text-secondary)" }}>
            From raw metrics to actionable intelligence
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {stages.map((stage, index) => (
            <motion.div
              key={stage.title}
              className="relative"
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              transition={{ delay: index * 0.1, duration: 0.5 }}
            >
              <div
                className="h-full rounded-2xl p-6 transition-colors duration-500"
                style={{
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--bg-card)",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-hover)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
              >
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${stage.color} flex items-center justify-center mb-4`}>
                  <stage.icon className="h-5 w-5 text-white" />
                </div>
                <div className="text-xs uppercase tracking-wider font-medium mb-1" style={{ color: "var(--text-muted)" }}>
                  Step {index + 1}
                </div>
                <h3 className="text-xl font-semibold mb-2" style={{ color: "var(--text-primary)" }}>{stage.title}</h3>
                <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>{stage.description}</p>
                <ul className="space-y-1.5">
                  {stage.details.map((detail) => (
                    <li key={detail} className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      <div className="w-1 h-1 rounded-full" style={{ backgroundColor: "var(--text-faint)" }} />
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Arrow connector */}
              {index < stages.length - 1 && (
                <div className="hidden lg:flex absolute top-1/2 -right-2 transform -translate-y-1/2 z-10">
                  <ArrowRight className="h-4 w-4" style={{ color: "var(--text-faint)" }} />
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Storage row */}
        <motion.div
          className="mt-4 rounded-2xl p-6"
          style={{ border: "1px solid var(--border)", backgroundColor: "var(--bg-card)" }}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ delay: 0.4, duration: 0.5 }}
        >
          <div className="flex flex-wrap items-center gap-4 justify-between">
            <div>
              <div className="text-sm font-medium mb-1" style={{ color: "var(--text-primary)" }}>Pluggable Storage</div>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>Choose your preferred backend</div>
            </div>
            <div className="flex gap-2">
              {["In-Memory", "PostgreSQL", "TimescaleDB", "InfluxDB"].map((db) => (
                <span
                  key={db}
                  className="px-3 py-1.5 rounded-lg text-xs font-mono"
                  style={{
                    backgroundColor: "var(--bg-accent)",
                    border: "1px solid var(--border)",
                    color: "var(--text-secondary)",
                  }}
                >
                  {db}
                </span>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
