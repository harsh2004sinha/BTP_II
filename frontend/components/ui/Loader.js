"use client";

import { Zap } from "lucide-react";

// ─── Spinner Loader ───────────────────────────────────────────────────────────
export function Spinner({ size = "md", className = "" }) {
  const sizes = {
    sm: "w-4 h-4 border-2",
    md: "w-8 h-8 border-2",
    lg: "w-12 h-12 border-3",
    xl: "w-16 h-16 border-4",
  };

  return (
    <div
      className={`
        ${sizes[size]}
        border-white/10 border-t-yellow-500
        rounded-full animate-spin
        ${className}
      `}
    />
  );
}

// ─── Full Page Loader ─────────────────────────────────────────────────────────
export function PageLoader({ message = "Loading..." }) {
  return (
    <div className="fixed inset-0 bg-slate-950 flex flex-col items-center justify-center z-50">
      {/* Animated logo */}
      <div className="relative mb-8">
        <div className="w-20 h-20 rounded-2xl bg-linear-to-br from-yellow-500 to-orange-500 
                        flex items-center justify-center animate-pulse-slow">
          <Zap className="w-10 h-10 text-black" fill="black" />
        </div>
        {/* Glow ring */}
        <div className="absolute inset-0 rounded-2xl bg-linear-to-br from-yellow-500 to-orange-500 
                        blur-xl opacity-40 animate-pulse-slow" />
      </div>

      {/* Spinner */}
      <Spinner size="lg" className="mb-4" />

      {/* Message */}
      <p className="text-slate-400 text-sm animate-pulse">{message}</p>
    </div>
  );
}

// ─── Skeleton Loader ──────────────────────────────────────────────────────────
export function Skeleton({ className = "", rounded = "rounded-lg" }) {
  return (
    <div
      className={`
        bg-white/5 animate-pulse
        ${rounded}
        ${className}
      `}
    />
  );
}

// ─── Card Skeleton ────────────────────────────────────────────────────────────
export function CardSkeleton() {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10" rounded="rounded-xl" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>
      <Skeleton className="h-24 w-full" />
      <div className="flex gap-2">
        <Skeleton className="h-8 w-24" rounded="rounded-lg" />
        <Skeleton className="h-8 w-24" rounded="rounded-lg" />
      </div>
    </div>
  );
}

// ─── Stat Card Skeleton ───────────────────────────────────────────────────────
export function StatCardSkeleton() {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5 space-y-3">
      <div className="flex justify-between items-start">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="w-9 h-9" rounded="rounded-xl" />
      </div>
      <Skeleton className="h-8 w-20" />
      <Skeleton className="h-2 w-full" rounded="rounded-full" />
    </div>
  );
}

// ─── Inline Loading Dots ──────────────────────────────────────────────────────
export function LoadingDots({ className = "" }) {
  return (
    <span className={`inline-flex items-center gap-1 ${className}`}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}