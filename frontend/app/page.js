import Link from "next/link";
import {
  Zap,
  Sun,
  Battery,
  BarChart3,
  Brain,
  ArrowRight,
  CheckCircle2,
  Star,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* ── Background effects ───────────────────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-yellow-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-orange-500/5 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-0 w-64 h-64 bg-blue-500/3 rounded-full blur-3xl" />
      </div>

      {/* ── Navbar ───────────────────────────────────────────────────────── */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-xl bg-linear-to-br from-yellow-500 
                          to-orange-500 flex items-center justify-center
                          shadow-lg shadow-yellow-500/25"
          >
            <Zap className="w-5 h-5 text-black" fill="black" />
          </div>
          <span className="font-bold text-white">EnergyOptimizer</span>
        </div>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-6 text-sm text-slate-400">
          <a href="#features" className="hover:text-white transition-colors">
            Features
          </a>
          <a href="#how-it-works" className="hover:text-white transition-colors">
            How it works
          </a>
          <a href="#pricing" className="hover:text-white transition-colors">
            Pricing
          </a>
        </div>

        {/* CTA buttons */}
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm text-slate-300 hover:text-white 
                       transition-colors px-4 py-2 rounded-xl hover:bg-white/5"
          >
            Log in
          </Link>
          <Link
            href="/register"
            className="text-sm font-semibold bg-linear-to-r from-yellow-500 
                       to-orange-500 text-black px-5 py-2.5 rounded-xl
                       hover:from-yellow-400 hover:to-orange-400 
                       transition-all shadow-lg shadow-yellow-500/25
                       active:scale-95"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* ── Hero Section ─────────────────────────────────────────────────── */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-16 pb-20 text-center">
        {/* Badge */}
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
                      bg-yellow-500/10 border border-yellow-500/25 text-yellow-400 
                      text-sm font-medium mb-8"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
          AI-Powered Energy Optimization
        </div>

        {/* Heading */}
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight">
          Cut your energy bills
          <br />
          <span className="bg-linear-to-r from-yellow-400 via-orange-400 to-orange-500 bg-clip-text text-transparent">
            by up to 35%
          </span>
        </h1>

        {/* Subheading */}
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Smart energy management with solar generation, battery storage, and
          real-time optimization. Upload your electricity bill and let AI do the
          rest.
        </p>

        {/* CTA buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <Link
            href="/register"
            className="flex items-center gap-2 bg-linear-to-r from-yellow-500 
                       to-orange-500 text-black font-semibold px-8 py-4 rounded-2xl
                       hover:from-yellow-400 hover:to-orange-400 transition-all 
                       shadow-xl shadow-yellow-500/30 text-base active:scale-95"
          >
            Start Optimizing Free
            <ArrowRight className="w-5 h-5" />
          </Link>
          <Link
            href="/login"
            className="flex items-center gap-2 bg-white/10 text-white 
                       border border-white/20 font-medium px-8 py-4 rounded-2xl
                       hover:bg-white/20 transition-all text-base"
          >
            View Demo
          </Link>
        </div>

        {/* Hero stats */}
        <div
          className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto
                      p-6 bg-white/5 border border-white/10 rounded-2xl"
        >
          {[
            { value: "35%", label: "Average bill reduction" },
            { value: "4yr", label: "Average ROI period" },
            { value: "2,400+", label: "Active users" },
            { value: "98%", label: "Uptime guarantee" },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="text-2xl font-bold text-yellow-400">{stat.value}</p>
              <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features Section ──────────────────────────────────────────────── */}
      <section
        id="features"
        className="relative z-10 max-w-7xl mx-auto px-6 py-20"
      >
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Everything you need to{" "}
            <span className="gradient-text">save energy</span>
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            Our platform handles everything from bill analysis to real-time
            optimization.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[
            {
              icon: Sun,
              color: "text-yellow-400",
              bg: "bg-yellow-500/10",
              border: "border-yellow-500/20",
              title: "Solar Optimization",
              desc: "AI calculates the optimal solar panel size for your rooftop and location using real weather data.",
            },
            {
              icon: Battery,
              color: "text-green-400",
              bg: "bg-green-500/10",
              border: "border-green-500/20",
              title: "Battery Storage",
              desc: "Smart battery management to store excess solar energy and reduce grid dependency.",
            },
            {
              icon: BarChart3,
              color: "text-blue-400",
              bg: "bg-blue-500/10",
              border: "border-blue-500/20",
              title: "Bill Analytics",
              desc: "Upload your electricity bill and get instant consumption analysis and cost breakdown.",
            },
            {
              icon: Brain,
              color: "text-purple-400",
              bg: "bg-purple-500/10",
              border: "border-purple-500/20",
              title: "AI Predictions",
              desc: "Continuous AI optimization for charge, discharge, and grid usage based on forecasts.",
            },
            {
              icon: Zap,
              color: "text-orange-400",
              bg: "bg-orange-500/10",
              border: "border-orange-500/20",
              title: "Grid Management",
              desc: "Smart grid import/export decisions to minimize costs during peak and off-peak hours.",
            },
            {
              icon: CheckCircle2,
              color: "text-cyan-400",
              bg: "bg-cyan-500/10",
              border: "border-cyan-500/20",
              title: "ROI Calculator",
              desc: "Get detailed ROI projections, payback periods, and long-term savings forecasts.",
            },
          ].map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className={`p-6 rounded-2xl bg-white/3 border ${feature.border}
                            hover:bg-white/5 transition-all hover:-translate-y-1
                            hover:shadow-lg group`}
              >
                <div
                  className={`w-12 h-12 rounded-xl ${feature.bg} ${feature.color}
                                flex items-center justify-center mb-4
                                group-hover:scale-110 transition-transform`}
                >
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-base font-semibold text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  {feature.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <section
        id="how-it-works"
        className="relative z-10 max-w-7xl mx-auto px-6 py-20"
      >
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Get started in{" "}
            <span className="gradient-text">4 simple steps</span>
          </h2>
        </div>

        <div className="grid md:grid-cols-4 gap-6">
          {[
            {
              step: "01",
              title: "Register",
              desc: "Create your free account in 30 seconds.",
            },
            {
              step: "02",
              title: "Upload Bill",
              desc: "Upload your electricity bill PDF or image.",
            },
            {
              step: "03",
              title: "Set Preferences",
              desc: "Enter your budget, roof area, and location.",
            },
            {
              step: "04",
              title: "Get Results",
              desc: "Receive your optimized energy plan instantly.",
            },
          ].map((step, i) => (
            <div key={step.step} className="relative text-center">
              {/* Connector line */}
              {i < 3 && (
                <div
                  className="hidden md:block absolute top-8 left-[60%] 
                               w-[80%] h-px bg-linear-to-r from-yellow-500/50 
                               to-transparent"
                />
              )}
              <div
                className="w-16 h-16 rounded-2xl bg-linear-to-br from-yellow-500 
                              to-orange-500 flex items-center justify-center mx-auto mb-4
                              shadow-lg shadow-yellow-500/25"
              >
                <span className="text-black font-bold text-lg">{step.step}</span>
              </div>
              <h3 className="text-base font-semibold text-white mb-2">
                {step.title}
              </h3>
              <p className="text-sm text-slate-400">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA Section ──────────────────────────────────────────────────── */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 py-20 text-center">
        <div
          className="p-10 rounded-3xl bg-linear-to-br from-yellow-500/15 
                      to-orange-500/10 border border-yellow-500/25"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to start saving?
          </h2>
          <p className="text-slate-400 mb-8 max-w-md mx-auto">
            Join thousands of users already optimizing their energy costs with
            AI.
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 bg-linear-to-r 
                       from-yellow-500 to-orange-500 text-black font-bold 
                       px-10 py-4 rounded-2xl hover:from-yellow-400 
                       hover:to-orange-400 transition-all shadow-xl 
                       shadow-yellow-500/30 text-base active:scale-95"
          >
            Get Started Free
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-slate-800 px-6 py-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div
              className="w-7 h-7 rounded-lg bg-linear-to-br from-yellow-500 
                            to-orange-500 flex items-center justify-center"
            >
              <Zap className="w-4 h-4 text-black" fill="black" />
            </div>
            <span className="font-bold text-white text-sm">EnergyOptimizer</span>
          </div>
          <p className="text-xs text-slate-600">
            © 2025 EnergyOptimizer. All rights reserved.
          </p>
          <div className="flex gap-4 text-xs text-slate-600">
            <a href="#" className="hover:text-slate-400 transition-colors">
              Privacy
            </a>
            <a href="#" className="hover:text-slate-400 transition-colors">
              Terms
            </a>
            <a href="#" className="hover:text-slate-400 transition-colors">
              Contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}