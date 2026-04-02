"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/authContext";
import { getErrorMessage } from "@/lib/utils";
import toast from "react-hot-toast";
import { Sun, Mail, Lock, Eye, EyeOff, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const router = useRouter();

  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // If already logged in, redirect
  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

  // ── Validation ──────────────────────────────────────────────────────────
  function validate() {
    const e = {};
    if (!form.email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(form.email))
      e.email = "Invalid email address";
    if (!form.password) e.password = "Password is required";
    else if (form.password.length < 6) e.password = "Minimum 6 characters";
    return e;
  }

  // ── Submit ───────────────────────────────────────────────────────────────
  async function handleSubmit(e) {
    e.preventDefault();

    const errs = validate();
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }

    setSubmitting(true);
    setErrors({});

    try {
      const result = await login(form.email, form.password);

      if (result.success) {
        toast.success("Welcome back!");
        router.replace("/dashboard");
      } else {
        /* Show the exact error from backend */
        toast.error(result.message || "Login failed");

        /* If wrong credentials, highlight the fields */
        if (
          result.message?.toLowerCase().includes("password") ||
          result.message?.toLowerCase().includes("credential") ||
          result.message?.toLowerCase().includes("incorrect") ||
          result.message?.toLowerCase().includes("invalid")
        ) {
          setErrors({
            email: "Check your email or password",
            password: "Check your email or password",
          });
        }
      }
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Something went wrong";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }));
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      {/* Background blobs */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-80 h-80 bg-emerald-500/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-500/8 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md page-enter">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center
                          justify-center shadow-2xl shadow-emerald-500/30 mb-4"
          >
            <Sun className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Welcome back</h1>
          <p className="text-slate-500 text-sm mt-1">
            Sign in to your SolarOptima account
          </p>
        </div>

        {/* Card */}
        <div
          className="bg-slate-900/80 backdrop-blur-xl border border-slate-800
                        rounded-3xl p-8 shadow-2xl"
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail
                  className="absolute left-3.5 top-1/2 -translate-y-1/2
                                 w-4 h-4 text-slate-500 pointer-events-none"
                />
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  autoComplete="email"
                  className={`w-full pl-10 pr-4 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${
                      errors.email
                        ? "border-red-500/60 focus:ring-red-500/30"
                        : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />
              </div>
              {errors.email && (
                <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
                  <span>⚠</span> {errors.email}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock
                  className="absolute left-3.5 top-1/2 -translate-y-1/2
                                 w-4 h-4 text-slate-500 pointer-events-none"
                />
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className={`w-full pl-10 pr-11 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${
                      errors.password
                        ? "border-red-500/60 focus:ring-red-500/30"
                        : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2
                             text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
                  <span>⚠</span> {errors.password}
                </p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600
                         active:bg-emerald-700 text-white font-semibold text-sm
                         transition-all duration-200 shadow-lg shadow-emerald-500/25
                         hover:shadow-emerald-500/40 disabled:opacity-60
                         disabled:cursor-not-allowed flex items-center justify-center gap-2
                         mt-2"
            >
              {submitting ? (
                <>
                  <svg
                    className="animate-spin w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Signing in...
                </>
              ) : (
                <>
                  Sign In <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-slate-800" />
            <span className="text-xs text-slate-600">New here?</span>
            <div className="flex-1 h-px bg-slate-800" />
          </div>

          {/* Register link */}
          <Link
            href="/register"
            className="block w-full py-3 rounded-xl border border-slate-700
                       hover:border-slate-600 text-slate-300 hover:text-slate-100
                       font-medium text-sm text-center transition-all duration-200
                       hover:bg-slate-800"
          >
            Create an Account
          </Link>
        </div>

        {/* Back to home */}
        <p className="text-center mt-6 text-xs text-slate-600">
          <Link href="/" className="hover:text-slate-400 transition-colors">
            ← Back to Home
          </Link>
        </p>
      </div>
    </div>
  );
}
