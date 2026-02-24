import { motion } from "motion/react";
import { useInView } from "./hooks/useInView";

const codeExample = `# config.yaml
agent:
  collection_interval: 60

sources:
  - type: system
    enabled: true
  - type: prometheus
    config:
      url: http://prometheus:9090
  - type: gcp
    config:
      project_id: my-project

prescale:
  endpoint: http://prescale:8080`;

const apiExample = `import requests

# Forecast CPU usage
r = requests.post("http://prescale:8080/predict",
  json={"metric": "cpu", "periods": 12})
print(r.json()["predictions"])

# Detect anomalies
r = requests.post("http://prescale:8080/detect",
  json={"deployment": "api-prod"})

# Get scaling advice
r = requests.post("http://prescale:8080/recommend",
  json={"deployment": "api-prod"})
print(r.json()["action"])  # → "scale_out"`;

export function CodeExample() {
  const [ref, isInView] = useInView({ threshold: 0.2 });

  return (
    <section ref={ref} className="py-24" style={{ backgroundColor: "var(--bg-primary)" }}>
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 16 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
            Simple config. Powerful API.
          </h2>
          <p className="text-lg max-w-xl mx-auto" style={{ color: "var(--text-secondary)" }}>
            YAML to configure, REST to integrate
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-4">
          {/* Config */}
          <motion.div
            className="rounded-2xl overflow-hidden"
            style={{ border: "1px solid var(--border)", backgroundColor: "var(--bg-card)" }}
            initial={{ opacity: 0, x: -30 }}
            animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: -30 }}
            transition={{ duration: 0.5 }}
          >
            <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
              <span className="text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>config.yaml</span>
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--border)" }} />
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--border)" }} />
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--border)" }} />
              </div>
            </div>
            <pre className="p-5 overflow-x-auto text-[13px] leading-relaxed">
              <code className="font-mono" style={{ color: "var(--text-secondary)" }}>{codeExample}</code>
            </pre>
          </motion.div>

          {/* API */}
          <motion.div
            className="rounded-2xl overflow-hidden"
            style={{ border: "1px solid var(--border)", backgroundColor: "var(--bg-card)" }}
            initial={{ opacity: 0, x: 30 }}
            animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 30 }}
            transition={{ duration: 0.5 }}
          >
            <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
              <span className="text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>example.py</span>
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--border)" }} />
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--border)" }} />
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--border)" }} />
              </div>
            </div>
            <pre className="p-5 overflow-x-auto text-[13px] leading-relaxed">
              <code className="font-mono" style={{ color: "var(--text-secondary)" }}>{apiExample}</code>
            </pre>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
