"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/authContext";
import { getErrorMessage } from "@/lib/utils";
import toast from "react-hot-toast";
import {
  Sun, Mail, Lock, Eye, EyeOff, User,
  ArrowRight, CheckCircle,
} from "lucide-react";

const strengthLevels = [
  { label: "Weak",   color: "bg-red-500",    min: 1 },
  { label: "Fair",   color: "bg-amber-500",  min: 2 },
  { label: "Good",   color: "bg-blue-500",   min: 3 },
  { label: "Strong", color: "bg-emerald-500", min: 4 },
];

function getStrength(password) {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  return score;
}

export default function RegisterPage() {
  const { register, user, loading } = useAuth();
  const router = useRouter();

  const [form, setForm] = useState({
    name: "", email: "", password: "", confirmPassword: "",
  });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [strength, setStrength] = useState(0);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

  useEffect(() => {
    setStrength(getStrength(form.password));
  }, [form.password]);

  function validate() {
    const e = {};
    if (!form.name.trim()) e.name = "Full name is required";
    else if (form.name.trim().length < 2) e.name = "Name too short";

    if (!form.email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = "Invalid email address";

    if (!form.password) e.password = "Password is required";
    else if (form.password.length < 6) e.password = "Minimum 6 characters";

    if (!form.confirmPassword) e.confirmPassword = "Please confirm your password";
    else if (form.password !== form.confirmPassword)
      e.confirmPassword = "Passwords do not match";

    return e;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setSubmitting(true);
    setErrors({});
    try {
      const result = await register(form.name.trim(), form.email, form.password);
      if (result.success) {
        toast.success("Account created! Please sign in.");
        router.replace("/login");
      } else {
        toast.error(result.message || "Registration failed");
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }));
  }

  const strengthInfo = strengthLevels[Math.max(0, strength - 1)] || strengthLevels[0];

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      {/* Background */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-emerald-500/8
                        rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 left-1/4 w-80 h-80 bg-purple-500/8
                        rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md page-enter">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center
                          justify-center shadow-2xl shadow-emerald-500/30 mb-4">
            <Sun className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Create Account</h1>
          <p className="text-slate-500 text-sm mt-1">
            Start optimizing your energy today
          </p>
        </div>

        {/* Benefits row */}
        <div className="flex gap-4 mb-6 justify-center">
          {["Free Forever", "No Credit Card", "Instant Access"].map((t) => (
            <div key={t} className="flex items-center gap-1.5 text-xs text-slate-500">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
              {t}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800
                        rounded-3xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2
                                  w-4 h-4 text-slate-500 pointer-events-none" />
                <input
                  type="text"
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Ahmad Rizal"
                  autoComplete="name"
                  className={`w-full pl-10 pr-4 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${errors.name
                      ? "border-red-500/60 focus:ring-red-500/30"
                      : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />
              </div>
              {errors.name && (
                <p className="mt-1.5 text-xs text-red-400">⚠ {errors.name}</p>
              )}
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2
                                 w-4 h-4 text-slate-500 pointer-events-none" />
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
                    ${errors.email
                      ? "border-red-500/60 focus:ring-red-500/30"
                      : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />
              </div>
              {errors.email && (
                <p className="mt-1.5 text-xs text-red-400">⚠ {errors.email}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2
                                 w-4 h-4 text-slate-500 pointer-events-none" />
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="Create a strong password"
                  autoComplete="new-password"
                  className={`w-full pl-10 pr-11 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${errors.password
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
                  {showPassword
                    ? <EyeOff className="w-4 h-4" />
                    : <Eye className="w-4 h-4" />
                  }
                </button>
              </div>

              {/* Strength meter */}
              {form.password && (
                <div className="mt-2 space-y-1.5">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((lvl) => (
                      <div
                        key={lvl}
                        className={`flex-1 h-1 rounded-full transition-all duration-300
                          ${strength >= lvl
                            ? strengthInfo.color
                            : "bg-slate-800"
                          }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-slate-500">
                    Strength:{" "}
                    <span className={`font-medium
                      ${strength >= 4 ? "text-emerald-400"
                        : strength >= 3 ? "text-blue-400"
                        : strength >= 2 ? "text-amber-400"
                        : "text-red-400"}`
                    }>
                      {strengthInfo.label}
                    </span>
                  </p>
                </div>
              )}

              {errors.password && (
                <p className="mt-1.5 text-xs text-red-400">⚠ {errors.password}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2
                                 w-4 h-4 text-slate-500 pointer-events-none" />
                <input
                  type={showConfirm ? "text" : "password"}
                  name="confirmPassword"
                  value={form.confirmPassword}
                  onChange={handleChange}
                  placeholder="Repeat your password"
                  autoComplete="new-password"
                  className={`w-full pl-10 pr-11 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${errors.confirmPassword
                      ? "border-red-500/60 focus:ring-red-500/30"
                      : form.confirmPassword && form.password === form.confirmPassword
                        ? "border-emerald-500/50 focus:ring-emerald-500/20"
                        : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2
                             text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showConfirm
                    ? <EyeOff className="w-4 h-4" />
                    : <Eye className="w-4 h-4" />
                  }
                </button>
                {form.confirmPassword && form.password === form.confirmPassword && (
                  <CheckCircle className="absolute right-10 top-1/2 -translate-y-1/2
                                         w-4 h-4 text-emerald-400 pointer-events-none" />
                )}
              </div>
              {errors.confirmPassword && (
                <p className="mt-1.5 text-xs text-red-400">
                  ⚠ {errors.confirmPassword}
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
                         disabled:cursor-not-allowed flex items-center
                         justify-center gap-2 mt-2"
            >
              {submitting ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creating account...
                </>
              ) : (
                <>
                  Create Account <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-slate-800" />
            <span className="text-xs text-slate-600">Already have an account?</span>
            <div className="flex-1 h-px bg-slate-800" />
          </div>

          <Link
            href="/login"
            className="block w-full py-3 rounded-xl border border-slate-700
                       hover:border-slate-600 text-slate-300 hover:text-slate-100
                       font-medium text-sm text-center transition-all hover:bg-slate-800"
          >
            Sign In Instead
          </Link>
        </div>

        <p className="text-center mt-6 text-xs text-slate-600">
          <Link href="/" className="hover:text-slate-400 transition-colors">
            ← Back to Home
          </Link>
        </p>
      </div>
    </div>
  );
}