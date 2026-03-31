"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { usePlans } from "@/hooks/usePlans";
import { useAuth } from "@/context/authContext";
import { StatusBadge } from "@/components/ui/Badge";
import { formatCurrency } from "@/lib/utils";
import {
  PlusCircle, FolderOpen, Zap, Sun, Battery,
  TrendingUp, ArrowRight, Clock, MapPin,
  BarChart3, Activity, Trash2, MoreVertical,
} from "lucide-react";

function WelcomeBanner({ name }) {
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="relative rounded-3xl overflow-hidden bg-linear-to-br
                    from-emerald-500/20 via-emerald-600/10 to-slate-900
                    border border-emerald-500/20 p-8 mb-6">
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5
                      rounded-full blur-3xl pointer-events-none" />
      <div className="relative">
        <p className="text-slate-400 text-sm mb-1">{greeting} 👋</p>
        <h1 className="text-2xl md:text-3xl font-bold text-slate-100 mb-2">
          {name || "Welcome back"}!
        </h1>
        <p className="text-slate-400 text-sm max-w-md">
          Manage your energy plans, track optimization results, and monitor
          real-time predictions from your dashboard.
        </p>
      </div>
    </div>
  );
}

function QuickActionCard({ icon: Icon, title, description, href, color, badge }) {
  return (
    <Link
      href={href}
      className="group relative rounded-2xl border border-slate-700/50
                 bg-slate-800/50 hover:bg-slate-800 p-6 transition-all
                 duration-200 hover:border-slate-600 hover:scale-[1.02]
                 hover:shadow-xl hover:shadow-slate-900/50 flex flex-col gap-3"
    >
      {badge && (
        <span className="absolute top-4 right-4 text-xs px-2 py-0.5
                         rounded-full bg-emerald-500/20 text-emerald-400
                         border border-emerald-500/20 font-medium">
          {badge}
        </span>
      )}
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center
                       transition-transform group-hover:scale-110 ${color}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <h3 className="font-semibold text-slate-100 mb-1">{title}</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
      </div>
      <div className="flex items-center gap-1 text-xs font-medium text-slate-500
                      group-hover:text-emerald-400 transition-colors mt-auto">
        Get started <ArrowRight className="w-3 h-3 transition-transform
                                           group-hover:translate-x-1" />
      </div>
    </Link>
  );
}

function PlanCard({ plan, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();

  function handleOpen() {
    router.push(`/plans/${plan.planId}/result`);
  }

  return (
    <div className="rounded-2xl border border-slate-700/50 bg-slate-800/50
                    hover:bg-slate-800/80 transition-all duration-200 p-5
                    hover:border-slate-600">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5 flex-1 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border
                          border-emerald-500/20 flex items-center justify-center
                          shrink-0">
            <Zap className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-slate-100 text-sm truncate">
              Plan — {plan.planId?.slice(0, 8)}
            </p>
            <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
              <MapPin className="w-3 h-3" />
              <span className="truncate">{plan.location || "Unknown location"}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 ml-2">
          <StatusBadge status={plan.status} />
          <div className="relative">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300
                         hover:bg-slate-700 transition-all"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
            {menuOpen && (
              <div className="absolute right-0 top-8 z-10 w-36 bg-slate-800
                              border border-slate-700 rounded-xl shadow-xl
                              overflow-hidden">
                <button
                  onClick={() => { handleOpen(); setMenuOpen(false); }}
                  className="w-full px-3 py-2.5 text-xs text-left text-slate-300
                             hover:bg-slate-700 flex items-center gap-2"
                >
                  <BarChart3 className="w-3.5 h-3.5" /> View Results
                </button>
                <button
                  onClick={() => {
                    onDelete(plan.planId);
                    setMenuOpen(false);
                  }}
                  className="w-full px-3 py-2.5 text-xs text-left text-red-400
                             hover:bg-red-500/10 flex items-center gap-2"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mt-3">
        <div className="bg-slate-900/50 rounded-xl p-3">
          <p className="text-xs text-slate-500 mb-1">Budget</p>
          <p className="text-sm font-semibold text-slate-200">
            {formatCurrency(plan.budget)}
          </p>
        </div>
        <div className="bg-slate-900/50 rounded-xl p-3">
          <p className="text-xs text-slate-500 mb-1">Roof Area</p>
          <p className="text-sm font-semibold text-slate-200">
            {plan.roofArea ? `${plan.roofArea} m²` : "—"}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <Clock className="w-3 h-3" />
          {plan.createdAt
            ? new Date(plan.createdAt).toLocaleDateString("en-MY", {
                day: "2-digit", month: "short", year: "numeric",
              })
            : "—"
          }
        </div>
        <button
          onClick={handleOpen}
          className="text-xs font-medium text-emerald-400 hover:text-emerald-300
                     flex items-center gap-1 transition-colors"
        >
          Open <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { plans, loading, deletePlan } = usePlans();

  const completedPlans  = plans.filter((p) => p.status === "completed");
  const pendingPlans    = plans.filter(
    (p) => p.status === "pending" || p.status === "bill_uploaded"
  );
  const processingPlans = plans.filter((p) => p.status === "processing");

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto page-enter">
        {/* Welcome banner */}
        <WelcomeBanner name={user?.name} />

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            {
              label: "Total Plans",
              value: plans.length,
              icon: FolderOpen,
              color: "text-blue-400 bg-blue-500/10",
            },
            {
              label: "Completed",
              value: completedPlans.length,
              icon: BarChart3,
              color: "text-emerald-400 bg-emerald-500/10",
            },
            {
              label: "Pending",
              value: pendingPlans.length,
              icon: Clock,
              color: "text-amber-400 bg-amber-500/10",
            },
            {
              label: "Processing",
              value: processingPlans.length,
              icon: Activity,
              color: "text-purple-400 bg-purple-500/10",
            },
          ].map(({ label, value, icon: Icon, color }) => (
            <div
              key={label}
              className="rounded-2xl bg-slate-800/50 border border-slate-700/50
                         p-5 flex items-center gap-4"
            >
              <div className={`w-10 h-10 rounded-xl flex items-center
                               justify-center shrink-0 ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{value}</p>
                <p className="text-xs text-slate-500">{label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Actions */}
        <h2 className="text-lg font-semibold text-slate-200 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          <QuickActionCard
            icon={PlusCircle}
            title="Create New Plan"
            description="Design a new solar + battery system with your requirements."
            href="/plans/new"
            color="bg-emerald-500/15 text-emerald-400"
            badge="Start here"
          />
          <QuickActionCard
            icon={FolderOpen}
            title="Continue Plan"
            description="Resume uploading bills or view results for existing plans."
            href="/plans"
            color="bg-blue-500/15 text-blue-400"
          />
          <QuickActionCard
            icon={Activity}
            title="Live Predictions"
            description="Monitor real-time solar, battery, and grid optimization."
            href={completedPlans[0]
              ? `/plans/${completedPlans[0].planId}/prediction`
              : "/plans"
            }
            color="bg-purple-500/15 text-purple-400"
          />
        </div>

        {/* Recent Plans */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-200">Recent Plans</h2>
          {plans.length > 0 && (
            <Link
              href="/plans"
              className="text-sm text-emerald-400 hover:text-emerald-300
                         flex items-center gap-1 transition-colors"
            >
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-2xl bg-slate-800/50 border border-slate-700/50
                           h-40 animate-pulse"
              />
            ))}
          </div>
        ) : plans.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-700
                          bg-slate-900/30 p-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center
                            justify-center mx-auto mb-4">
              <Sun className="w-8 h-8 text-slate-600" />
            </div>
            <p className="text-slate-400 font-medium mb-2">No plans yet</p>
            <p className="text-slate-600 text-sm mb-6">
              Create your first energy optimization plan to get started.
            </p>
            <Link
              href="/plans/new"
              className="inline-flex items-center gap-2 px-5 py-2.5
                         bg-emerald-500 hover:bg-emerald-600 text-white
                         font-medium text-sm rounded-xl transition-all
                         shadow-lg shadow-emerald-500/25"
            >
              <PlusCircle className="w-4 h-4" /> Create First Plan
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plans.slice(0, 6).map((plan) => (
              <PlanCard key={plan.planId} plan={plan} onDelete={deletePlan} />
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}