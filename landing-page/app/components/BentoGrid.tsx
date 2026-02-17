import { motion } from "motion/react";
import { useInView } from "./hooks/useInView";
import {
    TrendingUp,
    AlertTriangle,
    ArrowUpRight,
    Cpu,
    Activity,
    Server,
    Gauge,
} from "lucide-react";

function BentoCard({
    children,
    className = "",
    delay = 0,
    isInView,
}: {
    children: React.ReactNode;
    className?: string;
    delay?: number;
    isInView: boolean;
}) {
    return (
        <motion.div
            className={`rounded-2xl overflow-hidden group transition-colors duration-500 ${className}`}
            style={{
                border: "1px solid var(--border)",
                backgroundColor: "var(--bg-card)",
            }}
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
            transition={{ delay, duration: 0.5 }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-hover)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
        >
            {children}
        </motion.div>
    );
}

// Mini chart component for the traffic graph
function MiniChart() {
    const points = [32, 28, 35, 42, 38, 55, 62, 58, 72, 68, 78, 82];
    const max = Math.max(...points);
    const min = Math.min(...points);
    const width = 280;
    const height = 80;
    const padding = 4;

    const pathData = points
        .map((p, i) => {
            const x = padding + (i / (points.length - 1)) * (width - padding * 2);
            const y = height - padding - ((p - min) / (max - min)) * (height - padding * 2);
            return `${i === 0 ? "M" : "L"} ${x} ${y}`;
        })
        .join(" ");

    const areaPath = `${pathData} L ${width - padding} ${height} L ${padding} ${height} Z`;

    return (
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-20">
            <defs>
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="rgb(129,140,248)" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="rgb(129,140,248)" stopOpacity="0" />
                </linearGradient>
            </defs>
            <path d={areaPath} fill="url(#chartGrad)" />
            <path d={pathData} fill="none" stroke="rgb(129,140,248)" strokeWidth="2" />
        </svg>
    );
}

// Animated anomaly pulse
function AnomalyPulse() {
    return (
        <div className="flex items-center gap-3">
            <motion.div
                className="w-3 h-3 rounded-full bg-amber-500"
                animate={{ scale: [1, 1.4, 1], opacity: [1, 0.5, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
            />
            <div>
                <div className="text-amber-400 text-sm font-medium">Anomaly Detected</div>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>CPU spike at 14:32 UTC</div>
            </div>
        </div>
    );
}

export function BentoGrid() {
    const [ref, isInView] = useInView({ threshold: 0.1 });

    return (
        <section ref={ref} className="py-24" style={{ backgroundColor: "var(--bg-primary)" }} id="features">
            <div className="max-w-6xl mx-auto px-6">
                <motion.div
                    className="text-center mb-16"
                    initial={{ opacity: 0, y: 16 }}
                    animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
                    transition={{ duration: 0.5 }}
                >
                    <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
                        Your infrastructure, at a glance
                    </h2>
                    <p className="text-lg max-w-xl mx-auto" style={{ color: "var(--text-secondary)" }}>
                        Modular, real-time intelligence — every box is a window into your systems.
                    </p>
                </motion.div>

                {/* Bento Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

                    {/* Box 1: Traffic Forecast — wide */}
                    <BentoCard className="lg:col-span-2" delay={0.1} isInView={isInView}>
                        <div className="p-6">
                            <div className="flex items-center gap-2 mb-1">
                                <TrendingUp className="h-4 w-4 text-indigo-400" />
                                <span className="text-xs uppercase tracking-wider font-medium" style={{ color: "var(--text-muted)" }}>Traffic Forecast</span>
                            </div>
                            <div className="flex items-baseline gap-2 mb-4">
                                <span className="text-3xl font-semibold" style={{ color: "var(--text-primary)" }}>82%</span>
                                <span className="text-sm" style={{ color: "var(--text-muted)" }}>predicted CPU in 30 min</span>
                                <span className="ml-auto flex items-center text-xs text-emerald-400">
                                    <ArrowUpRight className="h-3 w-3 mr-0.5" />
                                    +15%
                                </span>
                            </div>
                            <MiniChart />
                            <div className="flex justify-between text-[10px] mt-1 font-mono" style={{ color: "var(--text-faint)" }}>
                                <span>12:00</span>
                                <span>13:00</span>
                                <span>14:00</span>
                                <span>Now</span>
                            </div>
                        </div>
                    </BentoCard>

                    {/* Box 2: Server Health */}
                    <BentoCard delay={0.15} isInView={isInView}>
                        <div className="p-6">
                            <div className="flex items-center gap-2 mb-4">
                                <Server className="h-4 w-4 text-emerald-400" />
                                <span className="text-xs uppercase tracking-wider font-medium" style={{ color: "var(--text-muted)" }}>Server Health</span>
                            </div>
                            <div className="space-y-3">
                                {[
                                    { name: "api-prod-1", cpu: 42, status: "healthy" },
                                    { name: "api-prod-2", cpu: 67, status: "healthy" },
                                    { name: "api-prod-3", cpu: 89, status: "warning" },
                                    { name: "worker-1", cpu: 23, status: "healthy" },
                                ].map((node) => (
                                    <div key={node.name} className="flex items-center gap-3">
                                        <div className={`w-1.5 h-1.5 rounded-full ${node.status === "warning" ? "bg-amber-400" : "bg-emerald-400"}`} />
                                        <span className="text-xs font-mono flex-1" style={{ color: "var(--text-secondary)" }}>{node.name}</span>
                                        <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "var(--border)" }}>
                                            <div
                                                className={`h-full rounded-full ${node.cpu > 80 ? "bg-amber-400" : "bg-indigo-400"}`}
                                                style={{ width: `${node.cpu}%` }}
                                            />
                                        </div>
                                        <span className="text-[10px] font-mono w-8 text-right" style={{ color: "var(--text-muted)" }}>{node.cpu}%</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </BentoCard>

                    {/* Box 3: Anomaly Detection */}
                    <BentoCard delay={0.2} isInView={isInView}>
                        <div className="p-6">
                            <div className="flex items-center gap-2 mb-4">
                                <AlertTriangle className="h-4 w-4 text-amber-400" />
                                <span className="text-xs uppercase tracking-wider font-medium" style={{ color: "var(--text-muted)" }}>Anomaly Detection</span>
                            </div>
                            <AnomalyPulse />
                            <div className="mt-4 p-3 rounded-lg" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)" }}>
                                <div className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>Severity</div>
                                <div className="flex gap-1">
                                    {["Low", "Medium", "High", "Critical"].map((level, i) => (
                                        <div
                                            key={level}
                                            className="flex-1 h-1.5 rounded-full"
                                            style={{ backgroundColor: i <= 1 ? "rgba(251,191,36,0.6)" : "var(--border)" }}
                                        />
                                    ))}
                                </div>
                                <div className="flex justify-between text-[10px] mt-1" style={{ color: "var(--text-faint)" }}>
                                    <span>Low</span>
                                    <span>Critical</span>
                                </div>
                            </div>
                            <div className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
                                <span className="font-mono" style={{ color: "var(--text-primary)" }}>0.69%</span> anomaly rate · XGBoost
                            </div>
                        </div>
                    </BentoCard>

                    {/* Box 4: Scaling Recommendation */}
                    <BentoCard delay={0.25} isInView={isInView}>
                        <div className="p-6">
                            <div className="flex items-center gap-2 mb-4">
                                <Gauge className="h-4 w-4 text-purple-400" />
                                <span className="text-xs uppercase tracking-wider font-medium" style={{ color: "var(--text-muted)" }}>Scaling</span>
                            </div>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between p-3 rounded-lg bg-purple-500/[0.06] border border-purple-500/[0.1]">
                                    <div>
                                        <div className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Scale Out</div>
                                        <div className="text-xs" style={{ color: "var(--text-secondary)" }}>3 → 5 replicas</div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-sm text-purple-400 font-mono">87%</div>
                                        <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>confidence</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                                    <Activity className="h-3 w-3" />
                                    Predicted utilization exceeds 80% threshold
                                </div>
                            </div>
                        </div>
                    </BentoCard>

                    {/* Box 5: ML Models — wide */}
                    <BentoCard className="lg:col-span-2" delay={0.3} isInView={isInView}>
                        <div className="p-6">
                            <div className="flex items-center gap-2 mb-4">
                                <Cpu className="h-4 w-4 text-indigo-400" />
                                <span className="text-xs uppercase tracking-wider font-medium" style={{ color: "var(--text-muted)" }}>ML Pipeline</span>
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                {[
                                    { name: "Baseline", metric: "2.6%", label: "MAPE", desc: "Moving Average + Trend" },
                                    { name: "Prophet", metric: "46.9%", label: "Coverage", desc: "Seasonality-aware" },
                                    { name: "XGBoost", metric: "0.69%", label: "Anomaly Rate", desc: "Gradient boosting" },
                                ].map((model) => (
                                    <div key={model.name} className="p-3 rounded-lg" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)" }}>
                                        <div className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>{model.name}</div>
                                        <div className="text-2xl font-semibold mb-0.5" style={{ color: "var(--text-primary)" }}>{model.metric}</div>
                                        <div className="text-[10px] text-indigo-400 mb-1">{model.label}</div>
                                        <div className="text-[10px]" style={{ color: "var(--text-faint)" }}>{model.desc}</div>
                                    </div>
                                ))}
                            </div>
                            <div className="mt-4 flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
                                <span><span className="font-mono" style={{ color: "var(--text-primary)" }}>108</span> engineered features</span>
                                <span style={{ color: "var(--text-faint)" }}>·</span>
                                <span><span className="font-mono" style={{ color: "var(--text-primary)" }}>7</span> raw metrics</span>
                                <span style={{ color: "var(--text-faint)" }}>·</span>
                                <span>Auto-retraining enabled</span>
                            </div>
                        </div>
                    </BentoCard>
                </div>
            </div>
        </section>
    );
}
