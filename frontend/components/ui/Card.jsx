import { cn } from "@/lib/utils";

export function Card({ children, className, glass, ...props }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-700/50 p-6",
        glass
          ? "bg-slate-800/40 backdrop-blur-xl"
          : "bg-slate-800/60",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }) {
  return (
    <div className={cn("mb-4 flex items-center justify-between", className)}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className }) {
  return (
    <h3 className={cn("text-lg font-semibold text-slate-100", className)}>
      {children}
    </h3>
  );
}