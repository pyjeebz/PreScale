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

/* ─── endpoint card ──────────────────────────────────────────── */

function EndpointCard({
    method,
    path,
    description,
    requestBody,
    responseBody,
}: {
    method: string;
    path: string;
    description: string;
    requestBody?: string;
    responseBody: string;
}) {
    const methodColors: Record<string, string> = {
        GET: "text-emerald-400 bg-emerald-400/10",
        POST: "text-indigo-400 bg-indigo-400/10",
        PUT: "text-amber-400 bg-amber-400/10",
        DELETE: "text-red-400 bg-red-400/10",
    };

    return (
        <div className="rounded-xl border overflow-hidden mb-6" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
            {/* Endpoint header */}
            <div className="px-5 py-4 border-b" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center gap-3 mb-2">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold font-mono ${methodColors[method] || ""}`}>
                        {method}
                    </span>
                    <code className="text-sm font-mono font-medium" style={{ color: "var(--text-primary)" }}>
                        {path}
                    </code>
                </div>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    {description}
                </p>
            </div>

            <div className="divide-y" style={{ borderColor: "var(--border)" }}>
                {requestBody && (
                    <div className="px-5 py-3">
                        <div className="text-[11px] font-medium uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
                            Request Body
                        </div>
                        <pre className="text-xs font-mono overflow-x-auto p-3 rounded-lg" style={{ backgroundColor: "var(--bg-accent)", color: "var(--text-secondary)" }}>
                            <code>{requestBody}</code>
                        </pre>
                    </div>
                )}
                <div className="px-5 py-3">
                    <div className="text-[11px] font-medium uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
                        Response
                    </div>
                    <pre className="text-xs font-mono overflow-x-auto p-3 rounded-lg" style={{ backgroundColor: "var(--bg-accent)", color: "var(--text-secondary)" }}>
                        <code>{responseBody}</code>
                    </pre>
                </div>
            </div>
        </div>
    );
}

/* ─── main page ──────────────────────────────────────────────── */

const toc = [
    { id: "predict", label: "/predict" },
    { id: "detect", label: "/detect" },
    { id: "recommend", label: "/recommend" },
    { id: "health", label: "/health" },
    { id: "metrics", label: "/metrics" },
    { id: "cost", label: "/cost/*" },
];

export function ApiReferencePage() {
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
                            <span>API Reference</span>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.4 }}
                        >
                            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4" style={{ color: "var(--text-primary)" }}>
                                API Reference
                            </h1>
                            <p className="text-base mb-4" style={{ color: "var(--text-secondary)" }}>
                                REST API endpoints for the Prescale Inference Service running on port <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: "var(--bg-accent)" }}>8001</code>.
                            </p>
                            <div className="text-sm mb-10 px-4 py-3 rounded-lg border" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-accent)", color: "var(--text-muted)" }}>
                                Base URL: <code className="font-mono text-xs" style={{ color: "var(--text-primary)" }}>http://localhost:8001</code> (development) |{" "}
                                <code className="font-mono text-xs" style={{ color: "var(--text-primary)" }}>https://prescale.dev</code> (production)
                            </div>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1, duration: 0.4 }}
                        >
                            {/* Predict */}
                            <section id="predict" className="scroll-mt-24 mb-10">
                                <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                                    Prediction
                                </h2>
                                <EndpointCard
                                    method="POST"
                                    path="/predict"
                                    description="Generate resource usage predictions for a specific deployment and metric."
                                    requestBody={`{
  "metric": "cpu",              // cpu | memory
  "deployment": "api-server",
  "namespace": "production",
  "horizon_minutes": 30
}`}
                                    responseBody={`{
  "prediction": {
    "metric": "cpu",
    "current_value": 0.67,
    "predicted_value": 0.82,
    "horizon_minutes": 30,
    "confidence": 0.91,
    "trend": "increasing",
    "timestamp": "2026-02-24T18:00:00Z"
  },
  "recommendation": {
    "action": "scale_up",
    "current_replicas": 3,
    "recommended_replicas": 5,
    "reason": "CPU predicted to exceed 80% threshold"
  }
}`}
                                />
                            </section>

                            {/* Detect */}
                            <section id="detect" className="scroll-mt-24 mb-10">
                                <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                                    Anomaly Detection
                                </h2>
                                <EndpointCard
                                    method="POST"
                                    path="/detect"
                                    description="Detect anomalies in resource usage patterns."
                                    requestBody={`{
  "metric": "memory",
  "namespace": "production",
  "lookback_minutes": 60
}`}
                                    responseBody={`{
  "anomalies": [
    {
      "timestamp": "2026-02-24T17:45:00Z",
      "metric": "memory",
      "deployment": "worker",
      "value": 0.95,
      "expected_range": [0.40, 0.65],
      "severity": "high",
      "type": "spike"
    }
  ],
  "total": 1,
  "status": "anomalies_detected"
}`}
                                />
                            </section>

                            {/* Recommend */}
                            <section id="recommend" className="scroll-mt-24 mb-10">
                                <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                                    Recommendations
                                </h2>
                                <EndpointCard
                                    method="GET"
                                    path="/recommend?namespace=production"
                                    description="Get scaling and optimization recommendations for all deployments in a namespace."
                                    responseBody={`{
  "recommendations": [
    {
      "deployment": "api-server",
      "namespace": "production",
      "action": "scale_up",
      "current_replicas": 3,
      "recommended_replicas": 5,
      "confidence": 0.89,
      "estimated_savings": null,
      "reason": "Traffic predicted to increase 40% in next 30min"
    },
    {
      "deployment": "batch-worker",
      "namespace": "production",
      "action": "scale_down",
      "current_replicas": 8,
      "recommended_replicas": 4,
      "confidence": 0.93,
      "estimated_savings": "$12.40/day",
      "reason": "Consistently over-provisioned during off-peak hours"
    }
  ]
}`}
                                />
                            </section>

                            {/* Health */}
                            <section id="health" className="scroll-mt-24 mb-10">
                                <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                                    Health & Metrics
                                </h2>
                                <EndpointCard
                                    method="GET"
                                    path="/health"
                                    description="Health check endpoint for liveness and readiness probes."
                                    responseBody={`{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-02-24T18:00:00Z",
  "models_loaded": 2,
  "uptime_seconds": 86400
}`}
                                />
                            </section>

                            {/* Metrics */}
                            <section id="metrics" className="scroll-mt-24 mb-10">
                                <EndpointCard
                                    method="GET"
                                    path="/metrics"
                                    description="Prometheus-compatible metrics endpoint for scraping service telemetry."
                                    responseBody={`# HELP prescale_cost_requests_total Total cost API requests
# TYPE prescale_cost_requests_total counter
prescale_cost_requests_total{endpoint="/predict",method="POST",status="200"} 1547

# HELP prescale_prediction_latency_seconds Prediction latency
# TYPE prescale_prediction_latency_seconds histogram
prescale_prediction_latency_seconds_bucket{le="0.1"} 1200
prescale_prediction_latency_seconds_bucket{le="0.5"} 1500`}
                                />
                            </section>

                            {/* Cost */}
                            <section id="cost" className="scroll-mt-24 mb-10">
                                <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                                    Cost Intelligence
                                </h2>
                                <EndpointCard
                                    method="GET"
                                    path="/cost/summary?period=7d"
                                    description="Get cost breakdown and savings opportunities."
                                    responseBody={`{
  "period": "7d",
  "total_cost": 847.20,
  "currency": "USD",
  "by_namespace": {
    "production": 612.50,
    "staging": 134.70,
    "development": 100.00
  },
  "potential_savings": 186.30,
  "efficiency_score": 0.78
}`}
                                />
                                <EndpointCard
                                    method="GET"
                                    path="/cost/forecast?period=30d"
                                    description="Forecast infrastructure costs for the next period."
                                    responseBody={`{
  "forecast_period": "30d",
  "predicted_cost": 3420.00,
  "confidence_interval": [3100.00, 3750.00],
  "trend": "increasing",
  "cost_drivers": [
    {
      "namespace": "production",
      "resource": "cpu",
      "contribution": 0.45
    }
  ]
}`}
                                />
                            </section>
                        </motion.div>
                    </div>

                    {/* Sticky TOC sidebar */}
                    <div className="hidden lg:block w-44 shrink-0">
                        <div className="sticky top-24">
                            <div className="text-[11px] font-medium uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
                                Endpoints
                            </div>
                            <ul className="space-y-2">
                                {toc.map((item) => (
                                    <li key={item.id}>
                                        <a
                                            href={`#${item.id}`}
                                            className="text-xs font-mono transition-colors hover:opacity-80"
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
