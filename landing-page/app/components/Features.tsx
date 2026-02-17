import { motion } from "motion/react";
import { TrendingUp, AlertCircle, Lightbulb, Cloud, BarChart3, Database } from "lucide-react";
import { useInView } from "./hooks/useInView";

const features = [
  {
    icon: TrendingUp,
    title: "Traffic Forecasting",
    description:
      "Predict CPU, memory, and request rates using ML models including Prophet, XGBoost, and baseline algorithms.",
  },
  {
    icon: AlertCircle,
    title: "Anomaly Detection",
    description:
      "Real-time detection of unusual patterns using machine learning and statistical methods to prevent outages.",
  },
  {
    icon: Lightbulb,
    title: "Scaling Recommendations",
    description:
      "Proactive advice for resource scaling with confidence scores to optimize your infrastructure costs.",
  },
  {
    icon: Cloud,
    title: "Multi-Cloud Support",
    description:
      "GCP Cloud Monitoring, AWS CloudWatch, Azure Monitor, Prometheus, and custom metrics sources.",
  },
  {
    icon: BarChart3,
    title: "Real-Time Dashboard",
    description:
      "Vue.js powered web interface with live charts, agent map, predictions, anomalies, and multi-deployment management.",
  },
  {
    icon: Database,
    title: "Pluggable Storage",
    description:
      "In-memory (dev), PostgreSQL, TimescaleDB, or InfluxDB backends for flexible deployment options.",
  },
];

export function Features() {
  const [ref, isInView] = useInView({ threshold: 0.1 });

  return (
    <section ref={ref} className="py-24 bg-slate-900" id="features">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-4xl font-bold text-white mb-4">
            Powerful Features
          </h2>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Everything you need to manage and optimize your cloud infrastructure
            intelligently
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              className="relative group"
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              transition={{ delay: index * 0.1, duration: 0.6 }}
            >
              <div className="h-full p-8 rounded-2xl bg-slate-800/50 border border-slate-700 hover:border-blue-500/50 transition-all duration-300 group-hover:bg-slate-800/80">
                <motion.div
                  className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-4"
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  transition={{ duration: 0.2 }}
                >
                  <feature.icon className="h-6 w-6 text-white" />
                </motion.div>
                <h3 className="text-xl font-semibold text-white mb-3">
                  {feature.title}
                </h3>
                <p className="text-slate-400 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
