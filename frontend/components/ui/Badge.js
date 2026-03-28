"use client";

// ─── Color Variants ───────────────────────────────────────────────────────────
const variants = {
  yellow: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30",
  green: "bg-green-500/15 text-green-400 border border-green-500/30",
  blue: "bg-blue-500/15 text-blue-400 border border-blue-500/30",
  red: "bg-red-500/15 text-red-400 border border-red-500/30",
  purple: "bg-purple-500/15 text-purple-400 border border-purple-500/30",
  orange: "bg-orange-500/15 text-orange-400 border border-orange-500/30",
  slate: "bg-slate-500/15 text-slate-400 border border-slate-500/30",
  cyan: "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30",
};

// ─── Size Variants ────────────────────────────────────────────────────────────
const sizes = {
  sm: "text-[10px] px-2 py-0.5 rounded-md",
  md: "text-xs px-2.5 py-1 rounded-lg",
  lg: "text-sm px-3 py-1.5 rounded-xl",
};

export default function Badge({
  children,
  variant = "yellow",
  size = "md",
  dot = false,
  pulse = false,
  className = "",
}) {
  return (
    <span
      className={`
        inline-flex items-center gap-1.5 font-medium
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
    >
      {/* Dot indicator */}
      {dot && (
        <span
          className={`
            w-1.5 h-1.5 rounded-full
            ${pulse ? "animate-pulse" : ""}
            ${
              variant === "green"
                ? "bg-green-400"
                : variant === "red"
                ? "bg-red-400"
                : variant === "yellow"
                ? "bg-yellow-400"
                : variant === "blue"
                ? "bg-blue-400"
                : "bg-current"
            }
          `}
        />
      )}
      {children}
    </span>
  );
}

// ─── Status Badge Preset ──────────────────────────────────────────────────────
export function StatusBadge({ status }) {
  const config = {
    active: { variant: "green", label: "Active", dot: true, pulse: true },
    pending: { variant: "yellow", label: "Pending", dot: true },
    completed: { variant: "blue", label: "Completed", dot: true },
    error: { variant: "red", label: "Error", dot: true },
    inactive: { variant: "slate", label: "Inactive", dot: true },
    optimizing: {
      variant: "purple",
      label: "Optimizing",
      dot: true,
      pulse: true,
    },
  };

  const { variant, label, dot, pulse } = config[status] || config.inactive;

  return (
    <Badge variant={variant} dot={dot} pulse={pulse}>
      {label}
    </Badge>
  );
}