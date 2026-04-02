import { cn } from "@/lib/utils";

export function Input({
  label,
  error,
  hint,
  icon,
  className,
  containerClass,
  ...props
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", containerClass)}>
      {label && (
        <label className="text-sm font-medium text-slate-300">{label}</label>
      )}
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5">
            {icon}
          </div>
        )}
        <input
          className={cn(
            "w-full rounded-xl bg-slate-800/80 border border-slate-700",
            "text-slate-100 placeholder-slate-500",
            "focus:outline-none focus:ring-2 focus:ring-emerald-500/50",
            "focus:border-emerald-500/50 transition-all duration-200",
            "py-3 pr-4 text-sm",
            icon ? "pl-10" : "pl-4",
            error && "border-red-500/50 focus:ring-red-500/50",
            className
          )}
          {...props}
        />
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}