"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Mail,
  Lock,
  User,
  ArrowRight,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
  Shield,
} from "lucide-react";

// ─── Password strength calculator ────────────────────────────────────────────
const getPasswordStrength = (password) => {
  if (!password) return { score: 0, label: "", color: "" };

  let score = 0;
  const checks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };

  score = Object.values(checks).filter(Boolean).length;

  const levels = [
    { score: 0, label: "", color: "" },
    { score: 1, label: "Very weak", color: "bg-red-500" },
    { score: 2, label: "Weak", color: "bg-orange-500" },
    { score: 3, label: "Fair", color: "bg-yellow-500" },
    { score: 4, label: "Strong", color: "bg-green-400" },
    { score: 5, label: "Very strong", color: "bg-green-500" },
  ];

  return { ...levels[score], score, checks };
};

// ─── Validation ───────────────────────────────────────────────────────────────
const validateRegisterForm = (fields) => {
  const errors = {};

  // Name
  if (!fields.name.trim()) {
    errors.name = "Full name is required";
  } else if (fields.name.trim().length < 2) {
    errors.name = "Name must be at least 2 characters";
  } else if (fields.name.trim().length > 50) {
    errors.name = "Name must be less than 50 characters";
  }

  // Email
  if (!fields.email.trim()) {
    errors.email = "Email is required";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email)) {
    errors.email = "Please enter a valid email address";
  }

  // Password
  if (!fields.password) {
    errors.password = "Password is required";
  } else if (fields.password.length < 8) {
    errors.password = "Password must be at least 8 characters";
  }

  // Confirm password
  if (!fields.confirmPassword) {
    errors.confirmPassword = "Please confirm your password";
  } else if (fields.password !== fields.confirmPassword) {
    errors.confirmPassword = "Passwords do not match";
  }

  // Terms
  if (!fields.agreeToTerms) {
    errors.agreeToTerms = "You must agree to the terms";
  }

  return errors;
};

// ─── Password requirement item ────────────────────────────────────────────────
function PasswordRequirement({ met, label }) {
  return (
    <div className={`flex items-center gap-1.5 text-xs transition-colors
                     ${met ? "text-green-400" : "text-slate-500"}`}>
      <CheckCircle2
        className={`w-3 h-3 shrink-0 transition-all ${met ? "scale-110" : ""}`}
      />
      {label}
    </div>
  );
}

export default function RegisterPage() {
  const { register } = useAuth();

  // ── Form State ───────────────────────────────────────────────────────────
  const [fields, setFields] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    agreeToTerms: false,
  });
  const [errors, setErrors] = useState({});
  const [globalError, setGlobalError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [showPasswordHints, setShowPasswordHints] = useState(false);

  // ── Password strength ────────────────────────────────────────────────────
  const strength = getPasswordStrength(fields.password);

  // ── Handle field change ──────────────────────────────────────────────────
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === "checkbox" ? checked : value;

    setFields((prev) => ({ ...prev, [name]: newValue }));

    // Clear field error on change
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
    if (globalError) setGlobalError("");
  };

  // ── Handle submit ────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();

    const validationErrors = validateRegisterForm(fields);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setLoading(true);
    setGlobalError("");

    const result = await register(fields.name, fields.email, fields.password);

    if (!result.success) {
      setGlobalError(result.message || "Registration failed. Please try again.");
    }

    setLoading(false);
  };

  // ── Field helpers ────────────────────────────────────────────────────────
  const isNameValid = fields.name.trim().length >= 2 && !errors.name;
  const isEmailValid =
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email) && !errors.email;
  const passwordsMatch =
    fields.confirmPassword &&
    fields.password === fields.confirmPassword;

  // ── Strength bar segments ─────────────────────────────────────────────────
  const strengthSegments = [1, 2, 3, 4, 5];

  return (
    <div className="animate-fade-in">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="mb-7">
        <h1 className="text-2xl font-bold text-white mb-2">Create account</h1>
        <p className="text-slate-400 text-sm">
          Start optimizing your energy costs today — it's free
        </p>
      </div>

      {/* ── Global Error Banner ──────────────────────────────────────────── */}
      {globalError && (
        <div
          className="flex items-center gap-3 p-4 rounded-xl mb-5
                      bg-red-500/10 border border-red-500/30 animate-fade-in"
        >
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">
              Registration failed
            </p>
            <p className="text-xs text-red-400 mt-0.5">{globalError}</p>
          </div>
        </div>
      )}

      {/* ── Form ────────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {/* Full Name */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300 flex items-center gap-1">
            Full name <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            <input
              type="text"
              name="name"
              autoComplete="name"
              placeholder="John Smith"
              value={fields.name}
              onChange={handleChange}
              disabled={loading}
              className={`
                w-full bg-white/5 border rounded-xl text-slate-100
                placeholder:text-slate-500 pl-10 pr-10 py-3 text-sm
                transition-all duration-200 focus:outline-none focus:ring-2
                focus:bg-white/8 disabled:opacity-50 disabled:cursor-not-allowed
                ${
                  errors.name
                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/20"
                    : isNameValid
                    ? "border-green-500/70 focus:border-green-500 focus:ring-green-500/20"
                    : "border-white/10 focus:border-yellow-500/70 focus:ring-yellow-500/20"
                }
              `}
            />
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
              {errors.name && <AlertCircle className="w-4 h-4 text-red-400" />}
              {isNameValid && <CheckCircle2 className="w-4 h-4 text-green-400" />}
            </div>
          </div>
          {errors.name && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 shrink-0" />
              {errors.name}
            </p>
          )}
        </div>

        {/* Email */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300 flex items-center gap-1">
            Email address <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            <input
              type="email"
              name="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={fields.email}
              onChange={handleChange}
              disabled={loading}
              className={`
                w-full bg-white/5 border rounded-xl text-slate-100
                placeholder:text-slate-500 pl-10 pr-10 py-3 text-sm
                transition-all duration-200 focus:outline-none focus:ring-2
                focus:bg-white/8 disabled:opacity-50 disabled:cursor-not-allowed
                ${
                  errors.email
                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/20"
                    : isEmailValid
                    ? "border-green-500/70 focus:border-green-500 focus:ring-green-500/20"
                    : "border-white/10 focus:border-yellow-500/70 focus:ring-yellow-500/20"
                }
              `}
            />
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
              {errors.email && <AlertCircle className="w-4 h-4 text-red-400" />}
              {isEmailValid && <CheckCircle2 className="w-4 h-4 text-green-400" />}
            </div>
          </div>
          {errors.email && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 shrink-0" />
              {errors.email}
            </p>
          )}
        </div>

        {/* Password */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300 flex items-center gap-1">
            Password <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            <input
              type={showPassword ? "text" : "password"}
              name="password"
              autoComplete="new-password"
              placeholder="Min. 8 characters"
              value={fields.password}
              onChange={handleChange}
              onFocus={() => setShowPasswordHints(true)}
              disabled={loading}
              className={`
                w-full bg-white/5 border rounded-xl text-slate-100
                placeholder:text-slate-500 pl-10 pr-10 py-3 text-sm
                transition-all duration-200 focus:outline-none focus:ring-2
                focus:bg-white/8 disabled:opacity-50 disabled:cursor-not-allowed
                ${
                  errors.password
                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/20"
                    : strength.score >= 3 && !errors.password
                    ? "border-green-500/70 focus:border-green-500 focus:ring-green-500/20"
                    : "border-white/10 focus:border-yellow-500/70 focus:ring-yellow-500/20"
                }
              `}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              disabled={loading}
              className="absolute right-3.5 top-1/2 -translate-y-1/2
                         text-slate-400 hover:text-slate-200 transition-colors"
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Password strength bar */}
          {fields.password && (
            <div className="space-y-2 animate-fade-in">
              {/* Strength segments */}
              <div className="flex items-center gap-1.5">
                {strengthSegments.map((seg) => (
                  <div
                    key={seg}
                    className={`
                      flex-1 h-1.5 rounded-full transition-all duration-300
                      ${
                        seg <= strength.score
                          ? strength.color
                          : "bg-white/10"
                      }
                    `}
                  />
                ))}
                {strength.label && (
                  <span
                    className={`text-xs font-medium ml-1 whitespace-nowrap
                      ${strength.score <= 2 ? "text-red-400" : ""}
                      ${strength.score === 3 ? "text-yellow-400" : ""}
                      ${strength.score >= 4 ? "text-green-400" : ""}
                    `}
                  >
                    {strength.label}
                  </span>
                )}
              </div>

              {/* Password requirements */}
              {showPasswordHints && (
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 p-3 rounded-xl bg-white/5 border border-white/5">
                  <PasswordRequirement
                    met={strength.checks?.length}
                    label="8+ characters"
                  />
                  <PasswordRequirement
                    met={strength.checks?.uppercase}
                    label="Uppercase letter"
                  />
                  <PasswordRequirement
                    met={strength.checks?.number}
                    label="Number"
                  />
                  <PasswordRequirement
                    met={strength.checks?.special}
                    label="Special character"
                  />
                </div>
              )}
            </div>
          )}

          {errors.password && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 shrink-0" />
              {errors.password}
            </p>
          )}
        </div>

        {/* Confirm Password */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300 flex items-center gap-1">
            Confirm password <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            <Shield className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            <input
              type={showConfirmPassword ? "text" : "password"}
              name="confirmPassword"
              autoComplete="new-password"
              placeholder="Repeat your password"
              value={fields.confirmPassword}
              onChange={handleChange}
              disabled={loading}
              className={`
                w-full bg-white/5 border rounded-xl text-slate-100
                placeholder:text-slate-500 pl-10 pr-10 py-3 text-sm
                transition-all duration-200 focus:outline-none focus:ring-2
                focus:bg-white/8 disabled:opacity-50 disabled:cursor-not-allowed
                ${
                  errors.confirmPassword
                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/20"
                    : passwordsMatch
                    ? "border-green-500/70 focus:border-green-500 focus:ring-green-500/20"
                    : "border-white/10 focus:border-yellow-500/70 focus:ring-yellow-500/20"
                }
              `}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              disabled={loading}
              className="absolute right-3.5 top-1/2 -translate-y-1/2
                         text-slate-400 hover:text-slate-200 transition-colors"
            >
              {showConfirmPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Match indicator */}
          {fields.confirmPassword && !errors.confirmPassword && (
            <p
              className={`text-xs flex items-center gap-1 animate-fade-in
                ${passwordsMatch ? "text-green-400" : "text-red-400"}`}
            >
              {passwordsMatch ? (
                <>
                  <CheckCircle2 className="w-3 h-3" />
                  Passwords match
                </>
              ) : (
                <>
                  <AlertCircle className="w-3 h-3" />
                  Passwords do not match
                </>
              )}
            </p>
          )}

          {errors.confirmPassword && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 shrink-0" />
              {errors.confirmPassword}
            </p>
          )}
        </div>

        {/* Terms & Conditions */}
        <div className="space-y-1">
          <div className="flex items-start gap-2.5">
            <button
              type="button"
              onClick={() =>
                handleChange({
                  target: {
                    name: "agreeToTerms",
                    type: "checkbox",
                    checked: !fields.agreeToTerms,
                  },
                })
              }
              disabled={loading}
              className={`
                w-5 h-5 rounded flex items-center justify-center
                border transition-all shrink-0 mt-0.5
                ${
                  fields.agreeToTerms
                    ? "bg-yellow-500 border-yellow-500"
                    : errors.agreeToTerms
                    ? "bg-white/5 border-red-500/70"
                    : "bg-white/5 border-white/20 hover:border-white/40"
                }
              `}
            >
              {fields.agreeToTerms && (
                <CheckCircle2
                  className="w-3 h-3 text-black"
                  strokeWidth={3}
                />
              )}
            </button>
            <p className="text-sm text-slate-400 leading-relaxed">
              I agree to the{" "}
              <a
                href="#"
                className="text-yellow-400 hover:text-yellow-300 underline-offset-2 hover:underline"
              >
                Terms of Service
              </a>{" "}
              and{" "}
              <a
                href="#"
                className="text-yellow-400 hover:text-yellow-300 underline-offset-2 hover:underline"
              >
                Privacy Policy
              </a>
            </p>
          </div>
          {errors.agreeToTerms && (
            <p className="text-xs text-red-400 flex items-center gap-1 pl-7">
              <AlertCircle className="w-3 h-3 shrink-0" />
              {errors.agreeToTerms}
            </p>
          )}
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
            disabled:opacity-50 disabled:cursor-not-allowed mt-2
            text-sm
          `}
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
              Creating account...
            </>
          ) : (
            <>
              Create Free Account
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>

      {/* ── Login link ───────────────────────────────────────────────────── */}
      <p className="text-center text-sm text-slate-400 mt-7">
        Already have an account?{" "}
        <Link
          href="/login"
          className="text-yellow-400 hover:text-yellow-300 font-medium 
                     transition-colors underline-offset-4 hover:underline"
        >
          Log in instead
        </Link>
      </p>
    </div>
  );
}