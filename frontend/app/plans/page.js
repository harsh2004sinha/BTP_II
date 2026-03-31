"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { usePlans } from "@/hooks/usePlans";
import { StatusBadge } from "@/components/ui/Badge";
import { formatCurrency } from "@/lib/utils";
import {
  PlusCircle, Search, FolderOpen, MapPin, Clock,
  BarChart3, Upload, Activity, Trash2, Zap,
  RefreshCw, Filter,
} from "lucide-react";

const STATUS_FILTERS = [
  { value: "all",          label: "All Plans"   },
  { value: "pending",      label: "Pending"     },
  { value: "bill_uploaded", label: "Bill Ready" },
  { value: "processing",   label: "Processing"  },
  { value: "completed",    label: "Completed"   },
  { value: "failed",       label: "Failed"      },
];

function PlanRow({ plan, onDelete }) {
  const router = useRouter();

  const nextAction = (() => {
    switch (plan.status) {
      case "pending":
        return {
          label: "Upload Bill",
          icon: Upload,
          href: `/plans/${plan.planId}/upload`,
          color: "text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border-amber-500/20",
        };
      case "bill_uploaded":
        return {
          label: "View / Optimize",
          icon: BarChart3,
          href: `/plans/${plan.planId}/result`,
          color: "text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border-blue-500/20",
        };
      case "processing":
        return {
          label: "Checking...",
          icon: RefreshCw,
          href: `/plans/${plan.planId}/result`,
          color: "text-purple-400 bg-purple-500/10 hover:bg-purple-500/20 border-purple-500/20",
        };
      case "completed":
        return {
          label: "View Results",
          icon: BarChart3,
          href: `/plans/${plan.planId}/result`,
          color: "text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/20",
        };
      default:
        return {
          label: "Open Plan",
          icon: FolderOpen,
          href: `/plans/${plan.planId}/result`,
          color: "text-slate-400 bg-slate-700/50 hover:bg-slate-700 border-slate-600/50",
        };
    }
  })();

  const ActionIcon = nextAction.icon;

  return (
    <div className="rounded-2xl border border-slate-700/50 bg-slate-800/50
                    hover:bg-slate-800/80 transition-all duration-200 p-5
                    hover:border-slate-600 group">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        {/* Icon & Info */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-11 h-11 rounded-xl bg-emerald-500/15 border
                          border-emerald-500/20 flex items-center justify-center
                          shrink-0">
            <Zap className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-semibold text-slate-100 text-sm">
                Energy Plan
              </p>
              <span className="text-xs text-slate-600 font-mono">
                #{plan.planId?.slice(0, 8)}
              </span>
              <StatusBadge status={plan.status} />
            </div>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              <span className="flex items-center gap-1 text-xs text-slate-500">
                <MapPin className="w-3 h-3" />
                {plan.location || "No location"}
              </span>
              <span className="flex items-center gap-1 text-xs text-slate-500">
                <Clock className="w-3 h-3" />
                {plan.createdAt
                  ? new Date(plan.createdAt).toLocaleDateString("en-MY", {
                      day: "2-digit", month: "short", year: "numeric",
                    })
                  : "—"
                }
              </span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden sm:block text-right">
            <p className="text-xs text-slate-500">Budget</p>
            <p className="text-sm font-semibold text-slate-200">
              {formatCurrency(plan.budget)}
            </p>
          </div>
          <div className="hidden md:block text-right">
            <p className="text-xs text-slate-500">Roof</p>
            <p className="text-sm font-semibold text-slate-200">
              {plan.roofArea ? `${plan.roofArea} m²` : "—"}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {plan.status === "completed" && (
              <button
                onClick={() =>
                  router.push(`/plans/${plan.planId}/prediction`)
                }
                className="p-2 rounded-xl text-purple-400 bg-purple-500/10
                           hover:bg-purple-500/20 border border-purple-500/20
                           transition-all"
                title="Live Prediction"
              >
                <Activity className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => router.push(nextAction.href)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl
                          border text-xs font-medium transition-all ${nextAction.color}`}
            >
              <ActionIcon className="w-3.5 h-3.5" />
              {nextAction.label}
            </button>
            <button
              onClick={() => onDelete(plan.planId)}
              className="p-2 rounded-xl text-slate-500 hover:text-red-400
                         hover:bg-red-500/10 transition-all"
              title="Delete plan"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PlansPage() {
  const { plans, loading, refetch, deletePlan } = usePlans();
  const [search, setSearch]   = useState("");
  const [filter, setFilter]   = useState("all");

  const filtered = plans.filter((p) => {
    const matchSearch =
      !search ||
      p.location?.toLowerCase().includes(search.toLowerCase()) ||
      p.planId?.toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === "all" || p.status === filter;
    return matchSearch && matchFilter;
  });

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto page-enter">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center
                        justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">My Plans</h1>
            <p className="text-slate-500 text-sm mt-0.5">
              {plans.length} plan{plans.length !== 1 ? "s" : ""} total
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refetch}
              className="p-2.5 rounded-xl border border-slate-700 text-slate-400
                         hover:text-slate-100 hover:bg-slate-800 transition-all"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <Link
              href="/plans/new"
              className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500
                         hover:bg-emerald-600 text-white font-medium text-sm
                         rounded-xl transition-all shadow-lg shadow-emerald-500/25"
            >
              <PlusCircle className="w-4 h-4" /> New Plan
            </Link>
          </div>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2
                               w-4 h-4 text-slate-500 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by location or plan ID..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-800/80
                         border border-slate-700 text-sm text-slate-100
                         placeholder-slate-500 focus:outline-none focus:ring-2
                         focus:ring-emerald-500/30 focus:border-emerald-500/50
                         transition-all"
            />
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <Filter className="w-4 h-4 text-slate-500 shrink-0" />
            {STATUS_FILTERS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setFilter(value)}
                className={`px-3 py-2 rounded-xl text-xs font-medium
                            whitespace-nowrap transition-all
                            ${filter === value
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                              : "text-slate-400 hover:text-slate-200 border border-slate-700 hover:border-slate-600"
                            }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Plans list */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="rounded-2xl bg-slate-800/50 border border-slate-700/50
                           h-24 animate-pulse"
              />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-700
                          bg-slate-900/30 p-16 text-center">
            <FolderOpen className="w-12 h-12 text-slate-700 mx-auto mb-4" />
            <p className="text-slate-400 font-medium mb-1">
              {plans.length === 0 ? "No plans yet" : "No plans match your filter"}
            </p>
            <p className="text-slate-600 text-sm mb-6">
              {plans.length === 0
                ? "Create your first plan to get started."
                : "Try changing your search or filter."}
            </p>
            {plans.length === 0 && (
              <Link
                href="/plans/new"
                className="inline-flex items-center gap-2 px-5 py-2.5
                           bg-emerald-500 hover:bg-emerald-600 text-white
                           font-medium text-sm rounded-xl transition-all"
              >
                <PlusCircle className="w-4 h-4" /> Create Plan
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((plan) => (
              <PlanRow key={plan.planId} plan={plan} onDelete={deletePlan} />
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}