import { motion } from "motion/react";
import { useInView } from "./hooks/useInView";
import { useState } from "react";
import { Copy, Check, Terminal } from "lucide-react";

const tabs = [
  {
    name: "Docker",
    code: `docker pull ghcr.io/pyjeebz/prescale/inference:latest
docker run -d -p 8080:8080 \\
  ghcr.io/pyjeebz/prescale/inference:latest`,
  },
  {
    name: "Helm",
    code: `helm repo add prescale https://pyjeebz.github.io/prescale
helm install prescale prescale/prescale \\
  --namespace prescale --create-namespace`,
  },
  {
    name: "Local",
    code: `git clone https://github.com/pyjeebz/prescale.git
cd prescale

# Backend
pip install -r ml/inference/requirements.txt
uvicorn ml.inference.app:app --port 8080

# Frontend
cd ml/inference/web && npm install && npm run dev`,
  },
];

const agentInstalls = [
  { name: "Base", cmd: "pip install prescale-agent" },
  { name: "GCP", cmd: "pip install prescale-agent[gcp]" },
  { name: "AWS", cmd: "pip install prescale-agent[aws]" },
  { name: "All", cmd: "pip install prescale-agent[all]" },
];

export function Installation() {
  const [ref, isInView] = useInView({ threshold: 0.1 });
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState<number | null>(null);

  const handleCopy = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <section ref={ref} className="py-24" style={{ backgroundColor: "var(--bg-primary)" }} id="installation">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 16 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
            Up and running in minutes
          </h2>
          <p className="text-lg max-w-xl mx-auto" style={{ color: "var(--text-secondary)" }}>
            Choose your preferred deployment method
          </p>
        </motion.div>

        {/* Tabbed terminal */}
        <motion.div
          className="rounded-2xl overflow-hidden mb-6"
          style={{ border: "1px solid var(--border)", backgroundColor: "var(--bg-card)" }}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ delay: 0.1, duration: 0.5 }}
        >
          <div className="flex items-center" style={{ borderBottom: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 px-4">
              <Terminal className="h-3.5 w-3.5" style={{ color: "var(--text-muted)" }} />
            </div>
            {tabs.map((tab, i) => (
              <button
                key={tab.name}
                className="px-4 py-3 text-xs font-medium transition-colors"
                style={{
                  color: activeTab === i ? "var(--text-primary)" : "var(--text-muted)",
                  borderBottom: activeTab === i ? "1px solid var(--text-primary)" : "1px solid transparent",
                }}
                onClick={() => setActiveTab(i)}
              >
                {tab.name}
              </button>
            ))}
            <div className="flex-1" />
            <button
              className="px-4 py-3 transition-colors"
              style={{ color: "var(--text-muted)" }}
              onClick={() => handleCopy(tabs[activeTab].code, -1)}
            >
              {copied === -1 ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
          <pre className="p-5 overflow-x-auto text-[13px] leading-relaxed min-h-[120px]">
            <code className="font-mono" style={{ color: "var(--text-secondary)" }}>{tabs[activeTab].code}</code>
          </pre>
        </motion.div>

        {/* Agent install row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {agentInstalls.map((agent, i) => (
            <motion.button
              key={agent.name}
              className="group rounded-xl p-4 text-left transition-all duration-300"
              style={{
                border: "1px solid var(--border)",
                backgroundColor: "var(--bg-card)",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              transition={{ delay: 0.2 + i * 0.05, duration: 0.4 }}
              onClick={() => handleCopy(agent.cmd, i)}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{agent.name}</span>
                {copied === i ? (
                  <Check className="h-3 w-3 text-emerald-400" />
                ) : (
                  <Copy className="h-3 w-3" style={{ color: "var(--text-faint)" }} />
                )}
              </div>
              <code className="text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>{agent.cmd}</code>
            </motion.button>
          ))}
        </div>
      </div>
    </section>
  );
}
