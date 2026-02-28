import { motion } from "motion/react";
import { Link } from "react-router";
import { Activity, BarChart3, Eye, Cloud, Monitor, ArrowRight, ChevronRight } from "lucide-react";
import { useTheme } from "../ThemeProvider";

const integrations = [
    {
        slug: "prometheus",
        title: "Prometheus",
        description: "Pull metrics from Prometheus via PromQL queries for real-time predictions and anomaly detection.",
        icon: Activity,
        color: "#E6522C",
        features: ["PromQL query support", "ServiceMonitor CRD", "Auto-discovery", "TLS and bearer token auth"],
    },
    {
        slug: "grafana",
        title: "Grafana",
        description: "Visualize Prescale predictions and anomaly alerts directly on Grafana dashboards.",
        icon: BarChart3,
        color: "#F46800",
        features: ["Pre-built dashboards", "Custom panels", "Alert integration", "Annotation support"],
    },
    {
        slug: "datadog",
        title: "Datadog",
        description: "Ingest metrics from Datadog's API for ML-powered predictions across your infrastructure.",
        icon: Eye,
        color: "#632CA6",
        features: ["Metrics API v2", "Tag-based filtering", "Multi-org support", "Real-time streaming"],
    },
    {
        slug: "cloudwatch",
        title: "AWS CloudWatch",
        description: "Connect to AWS CloudWatch metrics for ECS, EKS, and EC2 resource prediction.",
        icon: Cloud,
        color: "#FF9900",
        features: ["EC2/ECS/EKS metrics", "IAM role auth", "Cross-region", "Custom namespaces"],
    },
    {
        slug: "azure-monitor",
        title: "Azure Monitor",
        description: "Integrate with Azure Monitor for AKS and VM resource forecasting and optimization.",
        icon: Monitor,
        color: "#0078D4",
        features: ["AKS metrics", "Service principal auth", "Log Analytics", "Resource groups"],
    },
];

export function IntegrationsHome() {
    const { theme } = useTheme();

    return (
        <div className="pt-24 pb-20" style={{ backgroundColor: "var(--bg-primary)" }}>
            <div className="max-w-5xl mx-auto px-6">
                {/* Header */}
                <motion.div
                    className="mb-14"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                >
                    <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
                        Integrations
                    </h1>
                    <p className="text-lg max-w-2xl" style={{ color: "var(--text-secondary)" }}>
                        Prescale connects to your existing monitoring stack. Choose your platform below for setup instructions.
                    </p>
                </motion.div>

                {/* Integration cards */}
                <div className="space-y-4">
                    {integrations.map((integration, i) => {
                        const Icon = integration.icon;
                        return (
                            <motion.div
                                key={integration.slug}
                                initial={{ opacity: 0, y: 16 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.05 * i, duration: 0.4 }}
                            >
                                <Link
                                    to={`/integrations/${integration.slug}`}
                                    className="group flex flex-col sm:flex-row items-start gap-5 p-6 rounded-xl border transition-all duration-200 hover:border-[var(--border-active)]"
                                    style={{
                                        borderColor: "var(--border)",
                                        backgroundColor: "var(--bg-card)",
                                    }}
                                >
                                    {/* Icon */}
                                    <div
                                        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl"
                                        style={{ backgroundColor: `${integration.color}15` }}
                                    >
                                        <Icon className="h-6 w-6" style={{ color: integration.color }} />
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1.5">
                                            <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                                                {integration.title}
                                            </h3>
                                            <ArrowRight
                                                className="h-4 w-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all"
                                                style={{ color: "var(--text-muted)" }}
                                            />
                                        </div>
                                        <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
                                            {integration.description}
                                        </p>
                                        <div className="flex flex-wrap gap-2">
                                            {integration.features.map((feature) => (
                                                <span
                                                    key={feature}
                                                    className="px-2 py-0.5 rounded-full text-[11px]"
                                                    style={{
                                                        backgroundColor: "var(--bg-accent)",
                                                        color: "var(--text-muted)",
                                                        border: "1px solid var(--border)",
                                                    }}
                                                >
                                                    {feature}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </Link>
                            </motion.div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
