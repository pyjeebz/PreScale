import { motion } from "motion/react";
import { Link } from "react-router";
import {
    Zap, Settings, Code2, Activity, BarChart3, Eye, Cloud, Monitor,
    BookOpen, ArrowRight, Terminal, FileText,
} from "lucide-react";
import { useTheme } from "../ThemeProvider";

const quickstartCards = [
    {
        title: "Quickstart",
        description: "Install the agent and get predictions in under 5 minutes",
        href: "/docs/quickstart",
        icon: Zap,
        gradient: "from-emerald-500/20 to-teal-500/20",
    },
    {
        title: "Configuration",
        description: "Configure YAML, environment variables, and deployment options",
        href: "/docs/configuration",
        icon: Settings,
        gradient: "from-indigo-500/20 to-purple-500/20",
    },
    {
        title: "API Reference",
        description: "REST API endpoints for prediction, detection, and recommendations",
        href: "/docs/api",
        icon: Code2,
        gradient: "from-amber-500/20 to-orange-500/20",
    },
];

const integrationCards = [
    { title: "Prometheus", href: "/integrations/prometheus", icon: Activity, color: "#E6522C" },
    { title: "Grafana", href: "/integrations/grafana", icon: BarChart3, color: "#F46800" },
    { title: "Datadog", href: "/integrations/datadog", icon: Eye, color: "#632CA6" },
    { title: "CloudWatch", href: "/integrations/cloudwatch", icon: Cloud, color: "#FF9900" },
    { title: "Azure Monitor", href: "/integrations/azure-monitor", icon: Monitor, color: "#0078D4" },
];

export function DocsHome() {
    const { theme } = useTheme();

    return (
        <div className="pt-24 pb-20" style={{ backgroundColor: "var(--bg-primary)" }}>
            <div className="max-w-5xl mx-auto px-6">
                {/* Header */}
                <motion.div
                    className="mb-16"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                >
                    <div className="flex items-center gap-2 mb-4">
                        <BookOpen className="h-5 w-5" style={{ color: "var(--text-muted)" }} />
                        <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                            Documentation
                        </span>
                    </div>
                    <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
                        Learn Prescale
                    </h1>
                    <p className="text-lg max-w-2xl" style={{ color: "var(--text-secondary)" }}>
                        Everything you need to set up predictive infrastructure intelligence.
                        From installation to production deployment.
                    </p>
                </motion.div>

                {/* Quickstart cards */}
                <motion.div
                    className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-16"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1, duration: 0.4 }}
                >
                    {quickstartCards.map((card) => {
                        const Icon = card.icon;
                        return (
                            <Link
                                key={card.title}
                                to={card.href}
                                className="group relative rounded-xl border p-6 transition-all duration-200 hover:border-[var(--border-active)]"
                                style={{
                                    borderColor: "var(--border)",
                                    backgroundColor: "var(--bg-card)",
                                }}
                            >
                                <div className={`absolute inset-0 rounded-xl bg-gradient-to-br ${card.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />
                                <div className="relative">
                                    <div
                                        className="flex h-10 w-10 items-center justify-center rounded-lg border mb-4"
                                        style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-accent)" }}
                                    >
                                        <Icon className="h-5 w-5" style={{ color: "var(--text-secondary)" }} />
                                    </div>
                                    <h3 className="text-base font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                                        {card.title}
                                    </h3>
                                    <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                                        {card.description}
                                    </p>
                                    <div className="flex items-center gap-1 mt-4 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                                        Read more
                                        <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
                                    </div>
                                </div>
                            </Link>
                        );
                    })}
                </motion.div>

                {/* Quick install preview */}
                <motion.div
                    className="mb-16"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2, duration: 0.4 }}
                >
                    <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                        Quick Install
                    </h2>
                    <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
                        <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: "var(--border)" }}>
                            <Terminal className="h-3.5 w-3.5" style={{ color: "var(--text-muted)" }} />
                            <span className="text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>Terminal</span>
                        </div>
                        <div className="p-4 font-mono text-sm space-y-3">
                            <div>
                                <span style={{ color: "var(--text-muted)" }}>$ </span>
                                <span style={{ color: "var(--text-primary)" }}>pip install prescale-agent</span>
                            </div>
                            <div>
                                <span style={{ color: "var(--text-muted)" }}>$ </span>
                                <span style={{ color: "var(--text-primary)" }}>prescale init --source prometheus</span>
                            </div>
                            <div className="text-emerald-400">✓ Config written to prescale-agent.yaml</div>
                            <div>
                                <span style={{ color: "var(--text-muted)" }}>$ </span>
                                <span style={{ color: "var(--text-primary)" }}>prescale predict cpu --namespace prod</span>
                            </div>
                            <div style={{ color: "var(--text-secondary)" }}>
                                <span className="text-indigo-400">Forecasting</span> → CPU will reach 82% in 30min
                            </div>
                            <div className="text-amber-400">⚡ Recommendation: scale api-server 3 → 5 replicas</div>
                        </div>
                    </div>
                </motion.div>

                {/* Integrations section */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3, duration: 0.4 }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
                            Integrations
                        </h2>
                        <Link
                            to="/integrations"
                            className="text-xs font-medium flex items-center gap-1 hover:opacity-80 transition-opacity"
                            style={{ color: "var(--text-secondary)" }}
                        >
                            View all <ArrowRight className="h-3 w-3" />
                        </Link>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                        {integrationCards.map((card) => {
                            const Icon = card.icon;
                            return (
                                <Link
                                    key={card.title}
                                    to={card.href}
                                    className="group flex flex-col items-center gap-2 rounded-xl border p-4 transition-all duration-200 hover:border-[var(--border-active)]"
                                    style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
                                >
                                    <Icon className="h-6 w-6" style={{ color: card.color }} />
                                    <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                                        {card.title}
                                    </span>
                                </Link>
                            );
                        })}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
