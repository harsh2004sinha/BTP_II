import { cn } from "@/lib/utils";

const statusConfig = {
  pending:       { label: "Pending",     cls: "bg-amber-500/20 text-amber-400 border-amber-500/30"   },
  processing:    { label: "Processing",  cls: "bg-blue-500/20 text-blue-400 border-blue-500/30 animate-pulse" },
  bill_uploaded: { label: "Bill Ready",  cls: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  completed:     { label: "Completed",   cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  failed:        { label: "Failed",      cls: "bg-red-500/20 text-red-400 border-red-500/30"          },
};

export function StatusBadge({ status }) {
  const cfg = statusConfig[status] ?? {
    label: status,
    cls: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2.5 py-1 rounded-full",
        "text-xs font-medium border",
        cfg.cls
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {cfg.label}
    </span>
  );
}