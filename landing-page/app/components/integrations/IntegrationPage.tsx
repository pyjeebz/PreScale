import { motion } from "motion/react";
import { Link, useParams } from "react-router";
import { ChevronRight, Terminal, Copy, Check, Activity, BarChart3, Eye, Cloud, Monitor, CheckCircle2 } from "lucide-react";
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

/* ─── platform data ──────────────────────────────────────────── */

interface PlatformData {
    title: string;
    icon: React.ElementType;
    color: string;
    overview: string;
    prerequisites: string[];
    configYaml: string;
    configTitle: string;
    verifyCommand: string;
    verifyOutput: string;
    setupSteps: { title: string; content: string }[];
    docsLink: string;
}

const platforms: Record<string, PlatformData> = {
    prometheus: {
        title: "Prometheus",
        icon: Activity,
        color: "#E6522C",
        overview:
            "Prescale integrates natively with Prometheus to pull CPU, memory, and custom metrics via PromQL queries. The agent automatically discovers services through Kubernetes ServiceMonitor CRDs or static scrape configs.",
        prerequisites: [
            "Prometheus server v2.30+ running and accessible",
            "Prescale Agent installed (pip install prescale-agent)",
            "Network access from Prescale to Prometheus endpoint",
            "Optional: ServiceMonitor CRD for auto-discovery",
        ],
        setupSteps: [
            {
                title: "Ensure Prometheus is Accessible",
                content: "Verify your Prometheus instance is reachable. In a Kubernetes cluster, this is typically at http://prometheus.monitoring.svc:9090",
            },
            {
                title: "Configure Prescale",
                content: "Set Prometheus as your monitoring source in the Prescale agent config:",
            },
            {
                title: "Enable ServiceMonitor (Optional)",
                content: "If using the Kubernetes Operator, deploy the Prescale ServiceMonitor to auto-register metrics scraping.",
            },
        ],
        configYaml: `source: prometheus

prometheus:
  url: http://prometheus.monitoring.svc:9090
  # Authentication (optional)
  bearer_token: ""
  # TLS settings
  tls_skip_verify: false
  ca_file: ""
  # Query settings
  query_timeout: 30s
  scrape_interval: 15s
  # Custom PromQL queries (optional)
  custom_queries:
    cpu: 'rate(container_cpu_usage_seconds_total{namespace="prod"}[5m])'
    memory: 'container_memory_working_set_bytes{namespace="prod"}'`,
        configTitle: "prescale-agent.yaml",
        verifyCommand: `# Test the connection
prescale status --source prometheus

# Run a test prediction
prescale predict cpu --namespace prod --verbose`,
        verifyOutput: `✓ Connected to Prometheus at http://prometheus.monitoring:9090
✓ Found 24 active targets
✓ Query latency: 12ms
✓ Predictions ready`,
        docsLink: "https://prometheus.io/docs/introduction/overview/",
    },
    grafana: {
        title: "Grafana",
        icon: BarChart3,
        color: "#F46800",
        overview:
            "Prescale ships with pre-built Grafana dashboards for visualizing predictions, anomaly alerts, and cost optimization insights. Import them directly or deploy via Helm with the grafana sidecar.",
        prerequisites: [
            "Grafana v9.0+ running and accessible",
            "Prometheus datasource configured in Grafana",
            "Prescale inference service running and exposing /metrics",
        ],
        setupSteps: [
            {
                title: "Import Prescale Dashboards",
                content: "Use the Grafana import feature or sidecar provisioning to load the bundled dashboards:",
            },
            {
                title: "Configure Datasource",
                content: "Ensure your Prometheus datasource points to the instance scraping Prescale metrics.",
            },
        ],
        configYaml: `# Helm values for Grafana sidecar provisioning
grafana:
  enabled: true
  sidecar:
    dashboards:
      enabled: true
      label: grafana_dashboard
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
        - name: prescale
          folder: Prescale
          type: file
          options:
            path: /var/lib/grafana/dashboards/prescale

# Or import manually via Grafana UI:
# 1. Go to Dashboards → Import
# 2. Upload prescale-inference.json
# 3. Select your Prometheus datasource`,
        configTitle: "values.yaml (Helm)",
        verifyCommand: `# Verify Grafana can reach Prescale metrics
curl http://grafana:3000/api/datasources/proxy/1/api/v1/query?query=prescale_cost_requests_total

# Check dashboard provisioning
kubectl logs -l app=grafana -c grafana-sc-dashboard`,
        verifyOutput: `✓ Datasource connected
✓ 2 dashboards provisioned: prescale-inference, prescale-cost
✓ Panels loading with live data`,
        docsLink: "https://grafana.com/docs/grafana/latest/",
    },
    datadog: {
        title: "Datadog",
        icon: Eye,
        color: "#632CA6",
        overview:
            "Prescale ingests metrics from Datadog's Metrics API v2, supporting tag-based filtering, multi-org environments, and real-time metric streaming for ML predictions.",
        prerequisites: [
            "Datadog account with API and Application keys",
            "Datadog Agent collecting infrastructure metrics",
            "Prescale Agent installed",
        ],
        setupSteps: [
            {
                title: "Generate API Keys",
                content: "Create API and Application keys in Datadog → Organization Settings → API Keys.",
            },
            {
                title: "Configure Prescale",
                content: "Set Datadog as your monitoring source:",
            },
        ],
        configYaml: `source: datadog

datadog:
  api_key: \${DD_API_KEY}       # Env var recommended
  app_key: \${DD_APP_KEY}
  site: datadoghq.com          # or datadoghq.eu, ddog-gov.com
  # Metric filtering
  tags:
    - "env:production"
    - "service:api-server"
  # Query settings
  query_interval: 60s
  lookback_minutes: 120`,
        configTitle: "prescale-agent.yaml",
        verifyCommand: `# Set environment variables
export DD_API_KEY=your-api-key
export DD_APP_KEY=your-app-key

# Verify connection
prescale status --source datadog

# Test prediction
prescale predict cpu --tags "service:api-server,env:production"`,
        verifyOutput: `✓ Authenticated with Datadog (org: my-org)
✓ Found 156 metrics matching tags
✓ Data streaming active
✓ Predictions ready`,
        docsLink: "https://docs.datadoghq.com/api/",
    },
    cloudwatch: {
        title: "AWS CloudWatch",
        icon: Cloud,
        color: "#FF9900",
        overview:
            "Prescale connects to AWS CloudWatch to pull metrics from ECS, EKS, EC2, and custom namespaces. Supports IAM role-based and key-based authentication with cross-region queries.",
        prerequisites: [
            "AWS account with CloudWatch access",
            "IAM role or access keys with cloudwatch:GetMetricData permission",
            "Prescale Agent installed",
        ],
        setupSteps: [
            {
                title: "Configure IAM Permissions",
                content: "Create an IAM role or user with the cloudwatch:GetMetricData, cloudwatch:ListMetrics permissions.",
            },
            {
                title: "Configure Prescale",
                content: "Set CloudWatch as your monitoring source:",
            },
        ],
        configYaml: `source: cloudwatch

cloudwatch:
  region: us-east-1
  # Authentication: use env vars or IAM role
  access_key_id: \${AWS_ACCESS_KEY_ID}
  secret_access_key: \${AWS_SECRET_ACCESS_KEY}
  # Or use IAM role (recommended for EKS)
  # role_arn: arn:aws:iam::123456789:role/prescale-read
  namespace: AWS/ECS             # AWS/ECS | AWS/EKS | AWS/EC2 | Custom
  # Metric filtering
  dimensions:
    ClusterName: my-ecs-cluster
    ServiceName: api-service
  period: 300                    # Seconds between data points`,
        configTitle: "prescale-agent.yaml",
        verifyCommand: `# Verify AWS credentials
aws sts get-caller-identity

# Test the connection
prescale status --source cloudwatch

# Run prediction
prescale predict cpu --namespace AWS/ECS --dimension ClusterName=my-cluster`,
        verifyOutput: `✓ AWS credentials valid (account: 123456789012)
✓ CloudWatch accessible in us-east-1
✓ Found 12 metrics in AWS/ECS namespace
✓ Predictions ready`,
        docsLink: "https://docs.aws.amazon.com/cloudwatch/",
    },
    "azure-monitor": {
        title: "Azure Monitor",
        icon: Monitor,
        color: "#0078D4",
        overview:
            "Prescale integrates with Azure Monitor to collect metrics from AKS clusters, Virtual Machines, and other Azure resources. Supports service principal and managed identity authentication.",
        prerequisites: [
            "Azure subscription with Monitor Reader role",
            "Service principal or managed identity for authentication",
            "Prescale Agent installed",
        ],
        setupSteps: [
            {
                title: "Create Service Principal",
                content: "Create a service principal with the Monitoring Reader role on your subscription or resource group.",
            },
            {
                title: "Configure Prescale",
                content: "Set Azure Monitor as your monitoring source:",
            },
        ],
        configYaml: `source: azure

azure:
  subscription_id: \${AZURE_SUBSCRIPTION_ID}
  tenant_id: \${AZURE_TENANT_ID}
  client_id: \${AZURE_CLIENT_ID}
  client_secret: \${AZURE_CLIENT_SECRET}
  # Or use managed identity (recommended for AKS)
  # use_managed_identity: true
  resource_group: my-resource-group
  # Metric targeting
  resources:
    - type: Microsoft.ContainerService/managedClusters
      name: my-aks-cluster
    - type: Microsoft.Compute/virtualMachines
      name: my-vm
  metric_interval: PT5M         # ISO 8601 duration`,
        configTitle: "prescale-agent.yaml",
        verifyCommand: `# Verify Azure credentials
az account show

# Test connection
prescale status --source azure

# Run prediction
prescale predict cpu --resource my-aks-cluster`,
        verifyOutput: `✓ Azure credentials valid (subscription: my-sub)
✓ Monitor API accessible
✓ Found 8 resources in my-resource-group
✓ Predictions ready`,
        docsLink: "https://learn.microsoft.com/en-us/azure/azure-monitor/",
    },
};

/* ─── main component ─────────────────────────────────────────── */

export function IntegrationPage() {
    const { platform } = useParams();
    const data = platforms[platform || ""];

    if (!data) {
        return (
            <div className="pt-24 pb-20 text-center" style={{ backgroundColor: "var(--bg-primary)" }}>
                <div className="max-w-3xl mx-auto px-6">
                    <h1 className="text-2xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                        Integration not found
                    </h1>
                    <Link to="/integrations" className="text-sm underline" style={{ color: "var(--text-secondary)" }}>
                        View all integrations
                    </Link>
                </div>
            </div>
        );
    }

    const Icon = data.icon;

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
                    <Link to="/integrations" className="hover:opacity-80 transition-opacity" style={{ color: "var(--text-secondary)" }}>
                        Integrations
                    </Link>
                    <ChevronRight className="h-3 w-3" />
                    <span>{data.title}</span>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
                    {/* Header */}
                    <div className="flex items-start gap-4 mb-8">
                        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl" style={{ backgroundColor: `${data.color}15` }}>
                            <Icon className="h-7 w-7" style={{ color: data.color }} />
                        </div>
                        <div>
                            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-2" style={{ color: "var(--text-primary)" }}>
                                {data.title}
                            </h1>
                            <p className="text-base" style={{ color: "var(--text-secondary)" }}>
                                {data.overview}
                            </p>
                        </div>
                    </div>

                    {/* Prerequisites */}
                    <section className="mb-10">
                        <h2 className="text-lg font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
                            Prerequisites
                        </h2>
                        <ul className="space-y-2">
                            {data.prerequisites.map((prereq, i) => (
                                <li key={i} className="flex items-start gap-2.5 text-sm" style={{ color: "var(--text-secondary)" }}>
                                    <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0 text-emerald-400" />
                                    {prereq}
                                </li>
                            ))}
                        </ul>
                    </section>

                    {/* Setup steps */}
                    <section className="mb-10">
                        <h2 className="text-lg font-semibold mb-5" style={{ color: "var(--text-primary)" }}>
                            Setup
                        </h2>
                        {data.setupSteps.map((step, i) => (
                            <div key={i} className="mb-6">
                                <h3 className="text-base font-medium mb-2" style={{ color: "var(--text-primary)" }}>
                                    {i + 1}. {step.title}
                                </h3>
                                <p className="text-sm mb-2" style={{ color: "var(--text-secondary)" }}>
                                    {step.content}
                                </p>
                            </div>
                        ))}
                    </section>

                    {/* Configuration */}
                    <section className="mb-10">
                        <h2 className="text-lg font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
                            Configuration
                        </h2>
                        <CodeBlock title={data.configTitle} code={data.configYaml} />
                    </section>

                    {/* Verification */}
                    <section className="mb-10">
                        <h2 className="text-lg font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
                            Verify
                        </h2>
                        <CodeBlock title="Terminal" code={data.verifyCommand} />
                        <div
                            className="rounded-xl border p-4 mt-3 font-mono text-sm"
                            style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
                        >
                            {data.verifyOutput.split("\n").map((line, i) => (
                                <div key={i} className={line.startsWith("✓") ? "text-emerald-400" : ""} style={!line.startsWith("✓") ? { color: "var(--text-secondary)" } : {}}>
                                    {line}
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Platform docs link */}
                    <div
                        className="rounded-xl border p-5 flex items-center justify-between"
                        style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
                    >
                        <div>
                            <div className="text-sm font-medium mb-1" style={{ color: "var(--text-primary)" }}>
                                Official {data.title} Documentation
                            </div>
                            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                                Learn more about {data.title} configuration and best practices.
                            </div>
                        </div>
                        <a
                            href={data.docsLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs font-medium px-4 py-2 rounded-lg border transition-colors hover:bg-[var(--bg-card-hover)]"
                            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
                        >
                            View Docs →
                        </a>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
