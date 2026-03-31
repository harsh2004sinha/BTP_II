"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { useAuth } from "@/context/authContext";
import { useRouter } from "next/navigation";
import {
  Sun, Battery, Zap, TrendingDown, BarChart3,
  ArrowRight, CheckCircle, Globe,
} from "lucide-react";

const features = [
  {
    icon: Sun,
    title: "Solar Optimization",
    desc:  "AI-calculated solar panel sizing based on your rooftop area, location & consumption patterns.",
    color: "text-amber-400",
    bg:    "bg-amber-500/10 border-amber-500/20",
  },
  {
    icon: Battery,
    title: "Smart Battery Management",
    desc:  "Optimal battery sizing with real-time charge/discharge scheduling using Time-of-Use tariffs.",
    color: "text-purple-400",
    bg:    "bg-purple-500/10 border-purple-500/20",
  },
  {
    icon: Zap,
    title: "Grid Intelligence",
    desc:  "Minimize grid import costs and maximize solar self-consumption with predictive algorithms.",
    color: "text-blue-400",
    bg:    "bg-blue-500/10 border-blue-500/20",
  },
  {
    icon: TrendingDown,
    title: "Cost Savings",
    desc:  "See projected ROI, payback period, and annual savings before you invest a single ringgit.",
    color: "text-emerald-400",
    bg:    "bg-emerald-500/10 border-emerald-500/20",
  },
  {
    icon: BarChart3,
    title: "Real-Time Predictions",
    desc:  "24-hour rolling predictions for solar output, battery state, and grid costs.",
    color: "text-cyan-400",
    bg:    "bg-cyan-500/10 border-cyan-500/20",
  },
  {
    icon: Globe,
    title: "Weather Integration",
    desc:  "Live solar irradiance data from your exact GPS coordinates for accurate forecasting.",
    color: "text-rose-400",
    bg:    "bg-rose-500/10 border-rose-500/20",
  },
];

const stats = [
  { value: "35%",    label: "Average Bill Reduction" },
  { value: "4 yrs",  label: "Typical ROI Period"      },
  { value: "10 kW+", label: "Solar Capacity Modelled"  },
  { value: "24/7",   label: "Live Optimization"        },
];

export default function LandingPage() {
  const { user } = useAuth();
  const router   = useRouter();

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  return (
    <div className="min-h-screen bg-slate-950 overflow-x-hidden">
      {/* ── Background decorations ────────────────────────────────────────── */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/3 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl" />
      </div>

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-emerald-500 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <Sun className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="font-bold text-slate-100 leading-none">SolarOptima</p>
              <p className="text-xs text-slate-500">Energy Intelligence</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-slate-300
                         hover:text-slate-100 transition-colors"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="px-5 py-2 bg-emerald-500 hover:bg-emerald-600 text-white
                         text-sm font-medium rounded-xl transition-all
                         shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-6 pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full
                        bg-emerald-500/10 border border-emerald-500/20 mb-8">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span className="text-xs font-medium text-emerald-400">
            AI-Powered Energy Optimization
          </span>
        </div>

        <h1 className="text-5xl md:text-7xl font-black text-slate-100 mb-6 leading-[1.1]">
          Cut Your Energy Bills
          <br />
          <span className="gradient-text">Intelligently</span>
        </h1>

        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Upload your electricity bill, tell us your roof size and budget — we&apos;ll
          design the optimal solar + battery system and show you exactly how much you save.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-8 py-4 bg-emerald-500
                       hover:bg-emerald-600 text-white font-semibold rounded-2xl
                       transition-all shadow-xl shadow-emerald-500/30 text-lg
                       hover:scale-105 active:scale-100"
          >
            Create Free Plan
            <ArrowRight className="w-5 h-5" />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 px-8 py-4 border
                       border-slate-700 hover:border-slate-600 text-slate-300
                       hover:text-slate-100 font-semibold rounded-2xl transition-all
                       text-lg hover:bg-slate-800"
          >
            Sign In
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
          {stats.map((s) => (
            <div
              key={s.label}
              className="rounded-2xl bg-slate-800/50 border border-slate-700/50 p-4"
            >
              <div className="text-2xl font-black text-emerald-400 mb-1">
                {s.value}
              </div>
              <div className="text-xs text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-slate-100 mb-3">
            Everything You Need
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            From bill upload to optimization results — our end-to-end platform handles it all.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map(({ icon: Icon, title, desc, color, bg }) => (
            <div
              key={title}
              className={`rounded-2xl border p-6 hover:scale-[1.02]
                          transition-all duration-200 ${bg}`}
            >
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center
                               bg-slate-900/60 mb-4 ${color}`}>
                <Icon className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-slate-100 mb-2">{title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-slate-100 mb-3">
            How It Works
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            { step: "1", title: "Register",      desc: "Create your free account in 30 seconds" },
            { step: "2", title: "Upload Bill",   desc: "Upload your electricity bill PDF or CSV" },
            { step: "3", title: "Set Parameters", desc: "Enter budget, roof area and location"   },
            { step: "4", title: "Get Results",   desc: "Receive your optimized energy plan"      },
          ].map(({ step, title, desc }) => (
            <div key={step} className="text-center">
              <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/30
                              flex items-center justify-center mx-auto mb-3">
                <span className="text-lg font-black text-emerald-400">{step}</span>
              </div>
              <h3 className="font-semibold text-slate-200 mb-1">{title}</h3>
              <p className="text-sm text-slate-500">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 py-16 text-center">
        <div className="rounded-3xl bg-linear-to-br from-emerald-500/20 to-blue-500/10
                        border border-emerald-500/20 p-12">
          <h2 className="text-3xl font-bold text-slate-100 mb-3">
            Ready to Save?
          </h2>
          <p className="text-slate-400 mb-8">
            Join thousands optimizing their energy systems with SolarOptima.
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-8 py-4 bg-emerald-500
                       hover:bg-emerald-600 text-white font-semibold rounded-2xl
                       transition-all shadow-xl shadow-emerald-500/30 text-lg"
          >
            Start Free Today <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-800/50 py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row
                        items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-emerald-500 rounded-lg flex items-center justify-center">
              <Sun className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-sm font-semibold text-slate-300">SolarOptima</span>
          </div>
          <p className="text-xs text-slate-600">
            © {new Date().getFullYear()} SolarOptima. Intelligent Cost-Optimized Energy Management.
          </p>
        </div>
      </footer>
    </div>
  );
}