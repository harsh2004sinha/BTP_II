"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Mail,
  Lock,
  Zap,
  ArrowRight,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

// ─── Validation ───────────────────────────────────────────────────────────────
const validateLoginForm = (fields) => {
  const errors = {};

  // Email
  if (!fields.email.trim()) {
    errors.email = "Email is required";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email)) {
    errors.email = "Please enter a valid email address";
  }

  // Password
  if (!fields.password) {
    errors.password = "Password is required";
  } else if (fields.password.length < 6) {
    errors.password = "Password must be at least 6 characters";
  }

  return errors;
};

export default function LoginPage() {
  const { login } = useAuth();

  // ── Form State ───────────────────────────────────────────────────────────
  const [fields, setFields] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [globalError, setGlobalError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // ── Handle field change ──────────────────────────────────────────────────
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFields((prev) => ({ ...prev, [name]: value }));

    // Clear field error on change
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
    // Clear global error on any change
    if (globalError) setGlobalError("");
  };

  // ── Handle Submit ────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate
    const validationErrors = validateLoginForm(fields);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setLoading(true);
    setGlobalError("");

    const result = await login(fields.email, fields.password);

    if (!result.success) {
      setGlobalError(result.message || "Invalid email or password");
    }

    setLoading(false);
  };

  // ── Field valid state ────────────────────────────────────────────────────
  const isEmailValid =
    fields.email && !errors.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email);
  const isPasswordValid = fields.password && !errors.password && fields.password.length >= 6;

  return (
    <div className="animate-fade-in">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">Welcome back</h1>
        <p className="text-slate-400 text-sm">
          Log in to your EnergyOptimizer account
        </p>
      </div>

      {/* ── Global Error Banner ──────────────────────────────────────────── */}
      {globalError && (
        <div
          className="flex items-center gap-3 p-4 rounded-xl mb-6
                      bg-red-500/10 border border-red-500/30 animate-fade-in"
        >
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">Login failed</p>
            <p className="text-xs text-red-400 mt-0.5">{globalError}</p>
          </div>
        </div>
      )}

      {/* ── Form ────────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        {/* Email Field */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300 flex items-center gap-1">
            Email address
            <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            {/* Left icon */}
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none z-10" />

            <input
              type="email"
              name="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={fields.email}
              onChange={handleChange}
              disabled={loading}
              className={`
                w-full bg-white/5 border rounded-xl
                text-slate-100 placeholder:text-slate-500
                pl-10 pr-10 py-3 text-sm
                transition-all duration-200
                focus:outline-none focus:ring-2 focus:bg-white/8
                disabled:opacity-50 disabled:cursor-not-allowed
                ${
                  errors.email
                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/20"
                    : isEmailValid
                    ? "border-green-500/70 focus:border-green-500 focus:ring-green-500/20"
                    : "border-white/10 focus:border-yellow-500/70 focus:ring-yellow-500/20"
                }
              `}
            />

            {/* Right status icon */}
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
              {errors.email && (
                <AlertCircle className="w-4 h-4 text-red-400" />
              )}
              {isEmailValid && (
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              )}
            </div>
          </div>

          {/* Error message */}
          {errors.email && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 shrink-0" />
              {errors.email}
            </p>
          )}
        </div>

        {/* Password Field */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-1">
              Password
              <span className="text-red-400">*</span>
            </label>
            <Link
              href="/forgot-password"
              className="text-xs text-yellow-400 hover:text-yellow-300 
                         transition-colors font-medium"
            >
              Forgot password?
            </Link>
          </div>

          <div className="relative">
            {/* Left icon */}
            <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none z-10" />

            <input
              type={showPassword ? "text" : "password"}
              name="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              value={fields.password}
              onChange={handleChange}
              disabled={loading}
              className={`
                w-full bg-white/5 border rounded-xl
                text-slate-100 placeholder:text-slate-500
                pl-10 pr-10 py-3 text-sm
                transition-all duration-200
                focus:outline-none focus:ring-2 focus:bg-white/8
                disabled:opacity-50 disabled:cursor-not-allowed
                ${
                  errors.password
                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/20"
                    : isPasswordValid
                    ? "border-green-500/70 focus:border-green-500 focus:ring-green-500/20"
                    : "border-white/10 focus:border-yellow-500/70 focus:ring-yellow-500/20"
                }
              `}
            />

            {/* Toggle password visibility */}
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              disabled={loading}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 
                         text-slate-400 hover:text-slate-200 transition-colors z-10"
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Error message */}
          {errors.password && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 shrink-0" />
              {errors.password}
            </p>
          )}
        </div>

        {/* Remember me */}
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setRememberMe(!rememberMe)}
            disabled={loading}
            className={`
              w-5 h-5 rounded flex items-center justify-center
              border transition-all shrink-0
              ${
                rememberMe
                  ? "bg-yellow-500 border-yellow-500"
                  : "bg-white/5 border-white/20 hover:border-white/40"
              }
            `}
          >
            {rememberMe && (
              <CheckCircle2 className="w-3 h-3 text-black" strokeWidth={3} />
            )}
          </button>
          <span className="text-sm text-slate-400 select-none cursor-pointer"
            onClick={() => setRememberMe(!rememberMe)}
          >
            Remember me for 7 days
          </span>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className={`
            w-full flex items-center justify-center gap-2
            bg-linear-to-r from-yellow-500 to-orange-500
            hover:from-yellow-400 hover:to-orange-400
            text-black font-semibold py-3.5 rounded-xl
            transition-all duration-200 shadow-lg shadow-yellow-500/25
            hover:shadow-yellow-500/40 active:scale-[0.98]
            focus:outline-none focus:ring-2 focus:ring-yellow-500/50
            disabled:opacity-50 disabled:cursor-not-allowed
            disabled:hover:from-yellow-500 disabled:hover:to-orange-500
            text-sm
          `}
        >
          {loading ? (
            <>
              {/* Spinner */}
              <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
              Logging in...
            </>
          ) : (
            <>
              Log in to Dashboard
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>

        {/* Divider */}
        <div className="relative flex items-center gap-3 my-2">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-xs text-slate-500 shrink-0">
            or continue with
          </span>
          <div className="flex-1 h-px bg-white/10" />
        </div>

        {/* Demo login button */}
        <button
          type="button"
          disabled={loading}
          onClick={() => {
            setFields({
              email: "demo@energyoptimizer.com",
              password: "demo1234",
            });
            setErrors({});
            setGlobalError("");
          }}
          className="w-full flex items-center justify-center gap-2
                     bg-white/5 hover:bg-white/10 border border-white/10 
                     hover:border-white/20 text-slate-300 text-sm font-medium
                     py-3 rounded-xl transition-all disabled:opacity-50"
        >
          <Zap className="w-4 h-4 text-yellow-400" />
          Fill Demo Credentials
        </button>
      </form>

      {/* ── Register link ────────────────────────────────────────────────── */}
      <p className="text-center text-sm text-slate-400 mt-8">
        Don't have an account?{" "}
        <Link
          href="/register"
          className="text-yellow-400 hover:text-yellow-300 font-medium 
                     transition-colors underline-offset-4 hover:underline"
        >
          Create one free
        </Link>
      </p>

      {/* ── Terms note ───────────────────────────────────────────────────── */}
      <p className="text-center text-[11px] text-slate-600 mt-4 leading-relaxed">
        By logging in, you agree to our{" "}
        <a href="#" className="text-slate-500 hover:text-slate-400 underline">
          Terms of Service
        </a>{" "}
        and{" "}
        <a href="#" className="text-slate-500 hover:text-slate-400 underline">
          Privacy Policy
        </a>
      </p>
    </div>
  );
}