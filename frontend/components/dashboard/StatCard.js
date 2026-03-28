"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Skeleton } from "@/components/ui/Loader";

export default function StatCard({
  title = "",
  value = "",
  unit = "",
  icon: Icon,
  iconColor = "text-yellow-400",
  iconBg = "bg-yellow-500/15",
  trend = null,       // positive number = up, negative = down, 0 = flat
  trendLabel = "",
  loading = false,
  className = "",
  onClick,
}) {
  // ── Trend indicator ──────────────────────────────────────────────────────
  const getTrend = () => {
    if (trend === null || trend === undefined) return null;
    if (trend > 0)
      return {
        Icon: TrendingUp,
        color: "text-green-400",
        bg: "bg-green-400/10",
        label: `+${trend}%`,
      };
    if (trend < 0)
      return {
        Icon: TrendingDown,
        color: "text-red-400",
        bg: "bg-red-400/10",
        label: `${trend}%`,
      };
    return {
      Icon: Minus,
      color: "text-slate-400",
      bg: "bg-slate-400/10",
      label: "0%",
    };
  };

  const trendInfo = getTrend();

  if (loading) {
    return (
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5 space-y-3">
        <div className="flex justify-between items-start">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="w-10 h-10" rounded="rounded-xl" />
        </div>
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-3 w-32" />
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={`
        bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5
        transition-all duration-300 group
        ${onClick ? "cursor-pointer hover:border-yellow-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-yellow-500/5" : ""}
        ${className}
      `}
    >
      {/* Top row */}
      <div className="flex items-start justify-between mb-3">
        <p className="text-sm text-slate-400 font-medium">{title}</p>
        {Icon && (
          <div className={`p-2.5 rounded-xl ${iconBg} ${iconColor} 
                          transition-transform group-hover:scale-110`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-end gap-1.5 mb-3">
        <span className="text-3xl font-bold text-slate-100 leading-none">
          {value}
        </span>
        {unit && (
          <span className="text-base text-slate-400 mb-0.5 font-medium">
            {unit}
          </span>
        )}
      </div>

      {/* Trend */}
      {trendInfo && (
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 text-xs font-medium 
                         px-2 py-0.5 rounded-full ${trendInfo.color} ${trendInfo.bg}`}
          >
            <trendInfo.Icon className="w-3 h-3" />
            {trendInfo.label}
          </span>
          {trendLabel && (
            <span className="text-xs text-slate-500">{trendLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}