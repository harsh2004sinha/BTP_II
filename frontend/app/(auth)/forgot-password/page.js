"use client";

import { useState } from "react";
import Link from "next/link";
import { Mail, ArrowLeft, CheckCircle2, AlertCircle } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const validateEmail = (val) => {
    if (!val.trim()) return "Email is required";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val))
      return "Enter a valid email address";
    return "";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const error = validateEmail(email);
    if (error) {
      setEmailError(error);
      return;
    }

    setLoading(true);
    // Simulate API call
    await new Promise((r) => setTimeout(r, 1500));
    setLoading(false);
    setSent(true);
  };

  // ── Success state ────────────────────────────────────────────────────────
  if (sent) {
    return (
      <div className="animate-fade-in text-center">
        <div
          className="w-16 h-16 rounded-2xl bg-green-500/15 border border-green-500/30
                      flex items-center justify-center mx-auto mb-6"
        >
          <CheckCircle2 className="w-8 h-8 text-green-400" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">Check your email</h1>
        <p className="text-slate-400 text-sm mb-2">
          We sent a password reset link to
        </p>
        <p className="text-yellow-400 font-medium text-sm mb-8">{email}</p>
        <p className="text-xs text-slate-500 mb-8 leading-relaxed">
          Didn't receive the email? Check your spam folder or{" "}
          <button
            onClick={() => setSent(false)}
            className="text-yellow-400 hover:text-yellow-300 underline"
          >
            try again
          </button>
        </p>
        <Link
          href="/login"
          className="inline-flex items-center gap-2 text-sm text-slate-400
                     hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to login
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/login"
          className="inline-flex items-center gap-1.5 text-sm text-slate-400
                     hover:text-white transition-colors mb-6 group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Back to login
        </Link>
        <h1 className="text-2xl font-bold text-white mb-2">Forgot password?</h1>
        <p className="text-slate-400 text-sm">
          Enter your email and we'll send you a reset link
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        {/* Email field */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">
            Email address
          </label>
          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            <input
              type="email"
              name="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError("");
              }}
              disabled={loading}
              className={`
                w-full bg-white/5 border rounded-xl text-slate-100
                placeholder:text-slate-500 pl-10 pr-4 py-3 text-sm
                transition-all duration-200 focus:outline-none focus:ring-2
                focus:bg-white/8 disabled:opacity-50 disabled:cursor-not-allowed
                ${
                  emailError
                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/20"
                    : "border-white/10 focus:border-yellow-500/70 focus:ring-yellow-500/20"
                }
              `}
            />
          </div>
          {emailError && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 shrink-0" />
              {emailError}
            </p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2
                     bg-linear-to-r from-yellow-500 to-orange-500
                     hover:from-yellow-400 hover:to-orange-400
                     text-black font-semibold py-3.5 rounded-xl
                     transition-all shadow-lg shadow-yellow-500/25
                     active:scale-[0.98] focus:outline-none focus:ring-2
                     focus:ring-yellow-500/50 disabled:opacity-50
                     disabled:cursor-not-allowed text-sm"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
              Sending reset link...
            </>
          ) : (
            "Send Reset Link"
          )}
        </button>
      </form>
    </div>
  );
}