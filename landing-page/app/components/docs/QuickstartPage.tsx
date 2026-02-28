import { motion } from "motion/react";
import { Link } from "react-router";
import { ChevronRight, Terminal, Copy, Check, FileText } from "lucide-react";
import { useState } from "react";

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    return (
        <button
            className="p-1.5 rounded-md transition-colors hover:bg-[var(--bg-card-hover)]"
            style={{ color: "var(--text-muted)" }}
            onClick={() => {
                navigator.clipboard.writeText(text);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            }}
        >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
    );
}

function CodeBlock({ title, code, language }: { title?: string; code: string; language?: string }) {
    return (
        <div className="rounded-xl border overflow-hidden my-4" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
            {title && (
                <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-2">
                        <Terminal className="h-3.5 w-3.5" style={{ color: "var(--text-muted)" }} />
                        <span className="text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>{title}</span>
                    </div>
                    <CopyButton text={code} />
                </div>
            )}
            <pre className="p-4 text-sm font-mono overflow-x-auto" style={{ color: "var(--text-secondary)" }}>
                <code>{code}</code>
            </pre>
        </div>
    );
}

function StepCard({ step, title, children }: { step: number; title: string; children: React.ReactNode }) {
    return (
        <div className="relative pl-10 pb-10 last:pb-0">
            {/* Vertical line */}
            <div className="absolute left-[15px] top-8 bottom-0 w-px" style={{ backgroundColor: "var(--border)" }} />
            {/* Step number */}
            <div
                className="absolute left-0 top-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border"
                style={{
                    borderColor: "var(--border)",
                    backgroundColor: "var(--bg-accent)",
                    color: "var(--text-primary)",
                }}
            >
                {step}
            </div>
            <h3 className="text-base font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
                {title}
            </h3>
            <div className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {children}
            </div>
        </div>
    );
}

export function QuickstartPage() {
    return (
        <div className="pt-24 pb-20" style={{ backgroundColor: "var(--bg-primary)" }}>
            <div className="max-w-3xl mx-auto px-6">
                {/* Breadcrumb */}
                <motion.div
                    className="flex items-center gap-1.5 mb-8 text-xs"
                    style={{ color: "var(--text-muted)" }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                >
                    <Link to="/docs" className="hover:opacity-80 transition-opacity" style={{ color: "var(--text-secondary)" }}>
                        Docs
                    </Link>
                    <ChevronRight className="h-3 w-3" />
                    <span>Quickstart</span>
                </motion.div>

                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                    className="mb-12"
                >
                    <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
                        Quickstart
                    </h1>
                    <p className="text-base" style={{ color: "var(--text-secondary)" }}>
                        Get Prescale running and making predictions in under 5 minutes.
                    </p>
                </motion.div>

                {/* Steps */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1, duration: 0.4 }}
                >
                    <StepCard step={1} title="Install the Prescale Agent">
                        <p className="mb-2">Install the agent using pip. Python 3.9+ is required.</p>
                        <CodeBlock title="Terminal" code="pip install prescale-agent" />
                        <p className="mt-3">Or use Docker:</p>
                        <CodeBlock title="Terminal" code="docker pull ghcr.io/pyjeebz/prescale:latest" />
                    </StepCard>

                    <StepCard step={2} title="Initialize Configuration">
                        <p className="mb-2">
                            Run the init command to generate a <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>prescale-agent.yaml</code> config file:
                        </p>
                        <CodeBlock
                            title="Terminal"
                            code={`prescale init --source prometheus \\
  --prometheus-url http://prometheus:9090 \\
  --project my-gcp-project`}
                        />
                        <p className="mt-3">This creates a YAML configuration pointing to your Prometheus instance. You can also use <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>--source datadog</code>, <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>--source cloudwatch</code>, or <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>--source azure</code>.</p>
                    </StepCard>

                    <StepCard step={3} title="Configure Monitoring Source">
                        <p className="mb-2">Edit the generated config file to match your environment:</p>
                        <CodeBlock
                            title="prescale-agent.yaml"
                            code={`source: prometheus
prometheus:
  url: http://prometheus:9090
  # Optional: add authentication
  # bearer_token: your-token

gcp:
  project_id: my-project
  region: us-central1

predictions:
  horizon_minutes: 30
  retrain_interval_hours: 6

anomaly_detection:
  enabled: true
  sensitivity: medium   # low | medium | high`}
                        />
                    </StepCard>

                    <StepCard step={4} title="Start the Inference Service">
                        <p className="mb-2">Launch the prediction API server:</p>
                        <CodeBlock title="Terminal" code="prescale serve --port 8001" />
                        <p className="mt-3">Or run with Docker Compose for a full stack deployment:</p>
                        <CodeBlock
                            title="Terminal"
                            code={`# Clone the repo
git clone https://github.com/pyjeebz/prescale.git
cd prescale

# Start all services
docker-compose up -d`}
                        />
                    </StepCard>

                    <StepCard step={5} title="Make Your First Prediction">
                        <p className="mb-2">Use the CLI or API to get resource predictions:</p>
                        <CodeBlock
                            title="CLI"
                            code={`# Predict CPU usage for the next 30 minutes
prescale predict cpu --deployment api-server --namespace prod

# Detect anomalies in memory usage
prescale detect memory --namespace prod

# Get scaling recommendations
prescale recommend --namespace prod`}
                        />
                        <p className="mt-3">Or call the API directly:</p>
                        <CodeBlock
                            title="Terminal"
                            code={`curl http://localhost:8001/predict \\
  -H "Content-Type: application/json" \\
  -d '{
    "metric": "cpu",
    "deployment": "api-server",
    "namespace": "prod",
    "horizon_minutes": 30
  }'`}
                        />
                    </StepCard>

                    <StepCard step={6} title="Open the Dashboard">
                        <p>
                            Visit{" "}
                            <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>
                                http://localhost:8001
                            </code>{" "}
                            to open the Prescale dashboard. You'll see real-time predictions, anomaly alerts, and scaling recommendations.
                        </p>
                    </StepCard>
                </motion.div>

                {/* Next steps */}
                <motion.div
                    className="mt-12 p-6 rounded-xl border"
                    style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2, duration: 0.4 }}
                >
                    <h3 className="text-base font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                        Next Steps
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {[
                            { title: "Configuration Reference", href: "/docs/configuration", icon: FileText },
                            { title: "API Reference", href: "/docs/api", icon: Terminal },
                            { title: "Prometheus Integration", href: "/integrations/prometheus", icon: FileText },
                            { title: "All Integrations", href: "/integrations", icon: FileText },
                        ].map((link) => {
                            const Icon = link.icon;
                            return (
                                <Link
                                    key={link.title}
                                    to={link.href}
                                    className="flex items-center gap-2.5 px-4 py-3 rounded-lg border transition-colors hover:bg-[var(--bg-card-hover)]"
                                    style={{ borderColor: "var(--border)" }}
                                >
                                    <Icon className="h-4 w-4 shrink-0" style={{ color: "var(--text-muted)" }} />
                                    <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                                        {link.title}
                                    </span>
                                    <ChevronRight className="h-3 w-3 ml-auto" style={{ color: "var(--text-muted)" }} />
                                </Link>
                            );
                        })}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
