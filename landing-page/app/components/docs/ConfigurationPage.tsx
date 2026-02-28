import { motion } from "motion/react";
import { Link } from "react-router";
import { ChevronRight, Terminal, Copy, Check } from "lucide-react";
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

function CodeBlock({ title, code }: { title: string; code: string }) {
    return (
        <div className="rounded-xl border overflow-hidden my-4" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
            <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center gap-2">
                    <Terminal className="h-3.5 w-3.5" style={{ color: "var(--text-muted)" }} />
                    <span className="text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>{title}</span>
                </div>
                <CopyButton text={code} />
            </div>
            <pre className="p-4 text-sm font-mono overflow-x-auto" style={{ color: "var(--text-secondary)" }}>
                <code>{code}</code>
            </pre>
        </div>
    );
}

function ConfigSection({ title, id, children }: { title: string; id: string; children: React.ReactNode }) {
    return (
        <section id={id} className="scroll-mt-24 mb-12">
            <h2 className="text-xl font-semibold mb-4 pb-2 border-b" style={{ color: "var(--text-primary)", borderColor: "var(--border)" }}>
                {title}
            </h2>
            <div className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {children}
            </div>
        </section>
    );
}

const toc = [
    { id: "agent-config", label: "Agent Configuration" },
    { id: "monitoring-sources", label: "Monitoring Sources" },
    { id: "env-vars", label: "Environment Variables" },
    { id: "kubernetes", label: "Kubernetes Deployment" },
    { id: "advanced", label: "Advanced Settings" },
];

export function ConfigurationPage() {
    return (
        <div className="pt-24 pb-20" style={{ backgroundColor: "var(--bg-primary)" }}>
            <div className="max-w-5xl mx-auto px-6">
                <div className="flex gap-12">
                    {/* Main content */}
                    <div className="flex-1 min-w-0 max-w-3xl">
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
                            <span>Configuration</span>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.4 }}
                        >
                            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
                                Configuration
                            </h1>
                            <p className="text-base mb-10" style={{ color: "var(--text-secondary)" }}>
                                Complete reference for configuring the Prescale agent, monitoring sources, and deployment options.
                            </p>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1, duration: 0.4 }}
                        >
                            <ConfigSection title="Agent Configuration" id="agent-config">
                                <p className="mb-3">
                                    The Prescale agent is configured via a YAML file. By default, the agent looks for{" "}
                                    <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>
                                        prescale-agent.yaml
                                    </code>{" "}
                                    in the current directory or <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>/etc/prescale/agent.yaml</code>.
                                </p>
                                <CodeBlock
                                    title="prescale-agent.yaml"
                                    code={`# Prescale Agent Configuration
# Full reference: https://github.com/pyjeebz/prescale/docs

source: prometheus          # prometheus | datadog | cloudwatch | azure

# GCP Project settings (required for GKE integration)
gcp:
  project_id: my-project-id
  region: us-central1
  zone: us-central1-a

# Prediction engine settings
predictions:
  horizon_minutes: 30       # How far ahead to predict
  retrain_interval_hours: 6 # How often models retrain
  confidence_threshold: 0.85

# Anomaly detection
anomaly_detection:
  enabled: true
  sensitivity: medium       # low | medium | high
  alert_cooldown_minutes: 15

# Cost intelligence (optional)
cost_intelligence:
  enabled: true
  currency: USD
  budget_alert_threshold: 0.8  # Alert at 80% of budget`}
                                />
                            </ConfigSection>

                            <ConfigSection title="Monitoring Sources" id="monitoring-sources">
                                <p className="mb-3">Prescale supports multiple monitoring backends. Configure the one matching your infrastructure:</p>

                                <h3 className="text-base font-semibold mt-6 mb-2" style={{ color: "var(--text-primary)" }}>Prometheus</h3>
                                <CodeBlock
                                    title="prescale-agent.yaml"
                                    code={`source: prometheus
prometheus:
  url: http://prometheus.monitoring:9090
  bearer_token: ""           # Optional auth token
  tls_skip_verify: false
  query_timeout: 30s
  scrape_interval: 15s`}
                                />

                                <h3 className="text-base font-semibold mt-6 mb-2" style={{ color: "var(--text-primary)" }}>Datadog</h3>
                                <CodeBlock
                                    title="prescale-agent.yaml"
                                    code={`source: datadog
datadog:
  api_key: \${DD_API_KEY}     # Use env var
  app_key: \${DD_APP_KEY}
  site: datadoghq.com        # or datadoghq.eu`}
                                />

                                <h3 className="text-base font-semibold mt-6 mb-2" style={{ color: "var(--text-primary)" }}>AWS CloudWatch</h3>
                                <CodeBlock
                                    title="prescale-agent.yaml"
                                    code={`source: cloudwatch
cloudwatch:
  region: us-east-1
  access_key_id: \${AWS_ACCESS_KEY_ID}
  secret_access_key: \${AWS_SECRET_ACCESS_KEY}
  namespace: AWS/ECS          # or AWS/EKS, AWS/EC2`}
                                />

                                <h3 className="text-base font-semibold mt-6 mb-2" style={{ color: "var(--text-primary)" }}>Azure Monitor</h3>
                                <CodeBlock
                                    title="prescale-agent.yaml"
                                    code={`source: azure
azure:
  subscription_id: \${AZURE_SUBSCRIPTION_ID}
  tenant_id: \${AZURE_TENANT_ID}
  client_id: \${AZURE_CLIENT_ID}
  client_secret: \${AZURE_CLIENT_SECRET}
  resource_group: my-rg`}
                                />
                            </ConfigSection>

                            <ConfigSection title="Environment Variables" id="env-vars">
                                <p className="mb-3">All configuration values can be overridden with environment variables using the <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>PRESCALE_</code> prefix:</p>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm border-collapse">
                                        <thead>
                                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                                <th className="text-left py-2 pr-4 font-medium" style={{ color: "var(--text-primary)" }}>Variable</th>
                                                <th className="text-left py-2 pr-4 font-medium" style={{ color: "var(--text-primary)" }}>Default</th>
                                                <th className="text-left py-2 font-medium" style={{ color: "var(--text-primary)" }}>Description</th>
                                            </tr>
                                        </thead>
                                        <tbody className="font-mono text-xs">
                                            {[
                                                ["PRESCALE_SOURCE", "prometheus", "Monitoring source backend"],
                                                ["PRESCALE_PROMETHEUS_URL", "http://localhost:9090", "Prometheus server URL"],
                                                ["PRESCALE_GCP_PROJECT_ID", "—", "GCP project ID"],
                                                ["PRESCALE_HORIZON_MINUTES", "30", "Prediction horizon"],
                                                ["PRESCALE_RETRAIN_HOURS", "6", "Model retrain interval"],
                                                ["PRESCALE_ANOMALY_ENABLED", "true", "Enable anomaly detection"],
                                                ["PRESCALE_COST_ENABLED", "false", "Enable cost intelligence"],
                                                ["PRESCALE_LOG_LEVEL", "info", "Log verbosity"],
                                                ["PRESCALE_PORT", "8001", "API server port"],
                                            ].map(([name, def, desc]) => (
                                                <tr key={name} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                                                    <td className="py-2 pr-4" style={{ color: "var(--text-primary)" }}>{name}</td>
                                                    <td className="py-2 pr-4" style={{ color: "var(--text-muted)" }}>{def}</td>
                                                    <td className="py-2 font-sans" style={{ color: "var(--text-secondary)" }}>{desc}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </ConfigSection>

                            <ConfigSection title="Kubernetes Deployment" id="kubernetes">
                                <p className="mb-3">Deploy Prescale via the official Helm chart:</p>
                                <CodeBlock
                                    title="Terminal"
                                    code={`helm repo add prescale https://pyjeebz.github.io/prescale
helm repo update

helm install prescale prescale/prescale \\
  --namespace prescale --create-namespace \\
  --set gcp.projectId=my-project \\
  --set prometheus.enabled=true \\
  --set grafana.enabled=true`}
                                />
                                <p className="mt-3 mb-3">Or with a custom values file:</p>
                                <CodeBlock
                                    title="values.yaml"
                                    code={`inference:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: "1"
      memory: 1Gi

costIntelligence:
  enabled: true
  replicas: 1

prometheus:
  enabled: true

grafana:
  enabled: true
  dashboards:
    default:
      prescale-inference:
        file: dashboards/prescale-inference.json`}
                                />
                            </ConfigSection>

                            <ConfigSection title="Advanced Settings" id="advanced">
                                <p className="mb-3">Fine-tune model behavior, storage, and performance:</p>
                                <CodeBlock
                                    title="prescale-agent.yaml"
                                    code={`# Storage backend
storage:
  backend: sqlite            # sqlite | gcs
  sqlite:
    path: ./prescale.db
  gcs:
    bucket: prescale-models-\${PROJECT_ID}
    prefix: models/

# Model tuning
models:
  xgboost:
    n_estimators: 100
    max_depth: 6
    learning_rate: 0.1
  prophet:
    changepoint_prior_scale: 0.05
    seasonality_mode: multiplicative

# API server
server:
  host: 0.0.0.0
  port: 8001
  cors_origins: ["*"]
  rate_limit: 100/minute
  workers: 4`}
                                />
                            </ConfigSection>
                        </motion.div>
                    </div>

                    {/* Sticky TOC sidebar (desktop only) */}
                    <div className="hidden lg:block w-48 shrink-0">
                        <div className="sticky top-24">
                            <div className="text-[11px] font-medium uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
                                On this page
                            </div>
                            <ul className="space-y-2">
                                {toc.map((item) => (
                                    <li key={item.id}>
                                        <a
                                            href={`#${item.id}`}
                                            className="text-xs transition-colors hover:opacity-80"
                                            style={{ color: "var(--text-secondary)" }}
                                        >
                                            {item.label}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
