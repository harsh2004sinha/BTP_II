import { cn } from "@/lib/utils";

const variants = {
  primary:   "bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/25",
  secondary: "bg-slate-700 hover:bg-slate-600 text-white",
  danger:    "bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/25",
  ghost:     "bg-transparent hover:bg-slate-800 text-slate-300",
  outline:   "border border-slate-600 hover:bg-slate-800 text-slate-300",
};

const sizes = {
  sm:   "px-3 py-1.5 text-sm",
  md:   "px-4 py-2 text-sm",
  lg:   "px-6 py-3 text-base",
  xl:   "px-8 py-4 text-lg",
};

export function Button({
  children,
  variant = "primary",
  size = "md",
  className,
  loading,
  disabled,
  icon,
  ...props
}) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium",
        "transition-all duration-200 cursor-pointer disabled:opacity-50",
        "disabled:cursor-not-allowed focus:outline-none focus:ring-2",
        "focus:ring-emerald-500/50 active:scale-[0.98]",
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <svg
          className="animate-spin h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12" cy="12" r="10"
            stroke="currentColor" strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      ) : icon ? (
        <span className="w-5 h-5">{icon}</span>
      ) : null}
      {children}
    </button>
  );
}