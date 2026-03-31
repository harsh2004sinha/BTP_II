import { cn } from "@/lib/utils";

export function StatCard({
  title,
  value,
  unit,
  icon,
  trend,
  trendLabel,
  color = "emerald",
  className,
}) {
  const colorMap = {
    emerald: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/20 text-emerald-400",
    blue:    "from-blue-500/20 to-blue-600/5 border-blue-500/20 text-blue-400",
    amber:   "from-amber-500/20 to-amber-600/5 border-amber-500/20 text-amber-400",
    purple:  "from-purple-500/20 to-purple-600/5 border-purple-500/20 text-purple-400",
    rose:    "from-rose-500/20 to-rose-600/5 border-rose-500/20 text-rose-400",
  };

  return (
    <div
      className={cn(
        "relative rounded-2xl border p-5 overflow-hidden",
        "bg-linear-to-br",
        colorMap[color],
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
            {title}
          </p>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-slate-100">{value ?? "—"}</span>
            {unit && (
              <span className="text-sm font-medium text-slate-400">{unit}</span>
            )}
          </div>
          {trendLabel && (
            <p
              className={cn(
                "text-xs mt-1.5",
                trend > 0 ? "text-emerald-400" : "text-rose-400"
              )}
            >
              {trend > 0 ? "↑" : "↓"} {trendLabel}
            </p>
          )}
        </div>
        {icon && (
          <div
            className={cn(
              "p-3 rounded-xl bg-slate-900/40",
              colorMap[color].split(" ")[3]
            )}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}