"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { PageLoader } from "@/components/ui/Loader";
import { Zap } from "lucide-react";

export default function AuthLayout({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  // ── If already logged in → go to dashboard ──────────────────────────────
  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return <PageLoader message="Loading..." />;
  }

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {/* ── Left panel: Branding ─────────────────────────────────────────── */}
      <div
        className="hidden lg:flex flex-col justify-between w-[45%] 
                    bg-linear-to-br from-slate-900 to-slate-950
                    border-r border-slate-800 p-10 relative overflow-hidden"
      >
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {/* Large glow */}
          <div
            className="absolute top-[-20%] left-[-20%] w-[70%] h-[70%] 
                          rounded-full bg-yellow-500/5 blur-3xl"
          />
          <div
            className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] 
                          rounded-full bg-orange-500/5 blur-3xl"
          />

          {/* Grid pattern */}
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage: `linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), 
                                linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)`,
              backgroundSize: "40px 40px",
            }}
          />
        </div>

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div
            className="w-11 h-11 rounded-xl bg-linear-to-br from-yellow-500 
                          to-orange-500 flex items-center justify-center
                          shadow-lg shadow-yellow-500/25"
          >
            <Zap className="w-6 h-6 text-black" fill="black" />
          </div>
          <div>
            <p className="font-bold text-white">EnergyOptimizer</p>
            <p className="text-xs text-slate-500">Smart Energy Management</p>
          </div>
        </div>

        {/* Center content */}
        <div className="relative space-y-6">
          <div>
            <h2 className="text-4xl font-bold text-white leading-tight mb-4">
              Optimize your{" "}
              <span className="bg-linear-to-br from-yellow-400 to-orange-500 bg-clip-text text-transparent">
                energy costs
              </span>{" "}
              intelligently
            </h2>
            <p className="text-slate-400 text-base leading-relaxed">
              Use AI-powered optimization to reduce your electricity bills with
              solar generation, battery storage, and smart grid management.
            </p>
          </div>

          {/* Feature highlights */}
          <div className="space-y-3">
            {[
              {
                icon: "☀️",
                title: "Solar Optimization",
                desc: "Maximize solar generation efficiency",
              },
              {
                icon: "🔋",
                title: "Battery Management",
                desc: "Smart charge and discharge cycles",
              },
              {
                icon: "📊",
                title: "Cost Analytics",
                desc: "Real-time savings and ROI tracking",
              },
              {
                icon: "🤖",
                title: "AI Predictions",
                desc: "Continuous energy use optimization",
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="flex items-center gap-3 p-3 rounded-xl 
                           bg-white/5 border border-white/5"
              >
                <span className="text-xl">{feature.icon}</span>
                <div>
                  <p className="text-sm font-medium text-slate-200">
                    {feature.title}
                  </p>
                  <p className="text-xs text-slate-500">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom stats */}
        <div className="relative grid grid-cols-3 gap-4">
          {[
            { value: "35%", label: "Avg Savings" },
            { value: "4yr", label: "Avg ROI" },
            { value: "2k+", label: "Users" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="text-center p-3 rounded-xl bg-white/5 border border-white/5"
            >
              <p className="text-2xl font-bold text-yellow-400">{stat.value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right panel: Auth form ───────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* Mobile logo - only visible on small screens */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div
              className="w-9 h-9 rounded-xl bg-linear-to-br from-yellow-500 
                            to-orange-500 flex items-center justify-center"
            >
              <Zap className="w-5 h-5 text-black" fill="black" />
            </div>
            <p className="font-bold text-white">EnergyOptimizer</p>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}