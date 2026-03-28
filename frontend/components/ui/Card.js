"use client";

// ─── Card Variants ────────────────────────────────────────────────────────────
const variants = {
  default: "bg-slate-800/60 border border-slate-700/50",
  glass: "bg-white/5 backdrop-blur-sm border border-white/10",
  elevated: "bg-slate-800 border border-slate-700/50 shadow-xl shadow-black/30",
  highlighted:
    "bg-gradient-to-br from-yellow-500/10 to-orange-500/10 \
     border border-yellow-500/30",
  success:
    "bg-gradient-to-br from-green-500/10 to-emerald-500/10 \
     border border-green-500/30",
  danger:
    "bg-gradient-to-br from-red-500/10 to-rose-500/10 \
     border border-red-500/30",
};

// ─── Padding Sizes ────────────────────────────────────────────────────────────
const paddings = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
  xl: "p-8",
};

export default function Card({
  children,
  variant = "default",
  padding = "lg",
  hover = false,
  onClick,
  className = "",
  animate = false,
}) {
  return (
    <div
      onClick={onClick}
      className={`
        rounded-2xl transition-all duration-300
        ${variants[variant]}
        ${paddings[padding]}
        ${hover ? "hover:border-yellow-500/40 hover:shadow-lg hover:shadow-yellow-500/10 hover:-translate-y-0.5" : ""}
        ${onClick ? "cursor-pointer" : ""}
        ${animate ? "animate-fade-in" : ""}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

// ─── Card Sub-Components ──────────────────────────────────────────────────────

// Card Header
export function CardHeader({ children, className = "" }) {
  return (
    <div className={`flex items-center justify-between mb-5 ${className}`}>
      {children}
    </div>
  );
}

// Card Title
export function CardTitle({ children, icon = null, className = "" }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {icon && (
        <div className="p-2 rounded-lg bg-yellow-500/15 text-yellow-400">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-slate-100">{children}</h3>
    </div>
  );
}

// Card Body
export function CardBody({ children, className = "" }) {
  return <div className={className}>{children}</div>;
}

// Card Footer
export function CardFooter({ children, className = "" }) {
  return (
    <div
      className={`mt-5 pt-4 border-t border-white/5 flex items-center justify-between ${className}`}
    >
      {children}
    </div>
  );
}

// Card Divider
export function CardDivider() {
  return <hr className="border-white/5 my-4" />;
}