"use client";

import { Loader2 } from "lucide-react";

// ─── Variant Styles ───────────────────────────────────────────────────────────
const variants = {
  primary:
    "bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 \
     hover:to-orange-400 text-black font-semibold shadow-lg \
     shadow-yellow-500/25 hover:shadow-yellow-500/40",

  secondary:
    "bg-white/10 hover:bg-white/20 text-white border \
     border-white/20 hover:border-white/40",

  danger:
    "bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 \
     hover:to-red-400 text-white shadow-lg shadow-red-500/25",

  ghost:
    "bg-transparent hover:bg-white/10 text-slate-300 \
     hover:text-white",

  success:
    "bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 \
     hover:to-emerald-400 text-white shadow-lg shadow-green-500/25",

  outline:
    "bg-transparent border-2 border-yellow-500 text-yellow-500 \
     hover:bg-yellow-500 hover:text-black",
};

// ─── Size Styles ──────────────────────────────────────────────────────────────
const sizes = {
  sm: "px-3 py-1.5 text-sm rounded-lg",
  md: "px-5 py-2.5 text-sm rounded-xl",
  lg: "px-7 py-3.5 text-base rounded-xl",
  xl: "px-10 py-4 text-lg rounded-2xl",
  icon: "p-2.5 rounded-xl",
};

export default function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  fullWidth = false,
  leftIcon = null,
  rightIcon = null,
  onClick,
  type = "button",
  className = "",
}) {
  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={`
        inline-flex items-center justify-center gap-2
        font-medium transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-yellow-500/50
        active:scale-95
        ${variants[variant]}
        ${sizes[size]}
        ${fullWidth ? "w-full" : ""}
        ${isDisabled ? "opacity-50 cursor-not-allowed pointer-events-none" : "cursor-pointer"}
        ${className}
      `}
    >
      {/* Loading spinner */}
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}

      {/* Left icon (only show if not loading) */}
      {!loading && leftIcon && <span className="shrink-0">{leftIcon}</span>}

      {/* Button text */}
      {children}

      {/* Right icon */}
      {!loading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
    </button>
  );
}