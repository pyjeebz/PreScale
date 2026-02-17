import { motion } from "motion/react";
import { useInView } from "./hooks/useInView";
import { CheckCircle2, GitPullRequest, Users, Package } from "lucide-react";

const milestones = [
  {
    icon: CheckCircle2,
    title: "Production Ready",
    description: "Stable API with comprehensive testing",
  },
  {
    icon: GitPullRequest,
    title: "Active Development",
    description: "Regular updates and improvements",
  },
  {
    icon: Users,
    title: "Community Driven",
    description: "Open source and welcoming contributors",
  },
  {
    icon: Package,
    title: "Easy Deployment",
    description: "Docker, Helm, and local installation options",
  },
];

export function ProjectBadges() {
  const [ref, isInView] = useInView({ threshold: 0.2 });

  return (
    <section ref={ref} className="py-16 bg-slate-950 border-t border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">


        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {milestones.map((milestone, index) => (
            <motion.div
              key={milestone.title}
              className="text-center"
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              transition={{ delay: index * 0.1 + 0.2, duration: 0.5 }}
            >
              <div className="flex justify-center mb-3">
                <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center">
                  <milestone.icon className="h-6 w-6 text-blue-400" />
                </div>
              </div>
              <h4 className="text-white font-semibold mb-2">
                {milestone.title}
              </h4>
              <p className="text-sm text-slate-400">{milestone.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
