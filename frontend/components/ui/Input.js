"use client";

import { useState } from "react";
import { Eye, EyeOff, AlertCircle, CheckCircle2 } from "lucide-react";

export default function Input({
  label = "",
  type = "text",
  placeholder = "",
  value,
  onChange,
  error = "",
  success = false,
  hint = "",
  leftIcon = null,
  rightIcon = null,
  disabled = false,
  required = false,
  fullWidth = true,
  className = "",
  name = "",
  accept = "",
  min,
  max,
  step,
  ...props
}) {
  // Track password visibility toggle
  const [showPassword, setShowPassword] = useState(false);

  // Determine actual input type (handle password toggle)
  const inputType =
    type === "password" ? (showPassword ? "text" : "password") : type;

  // ── Border color based on state ──────────────────────────────────────────
  const borderClass = error
    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/20"
    : success
    ? "border-green-500/70 focus:border-green-500 focus:ring-green-500/20"
    : "border-white/10 focus:border-yellow-500/70 focus:ring-yellow-500/20";

  return (
    <div className={`flex flex-col gap-1.5 ${fullWidth ? "w-full" : ""} ${className}`}>
      {/* Label */}
      {label && (
        <label className="text-sm font-medium text-slate-300 flex items-center gap-1">
          {label}
          {required && <span className="text-red-400">*</span>}
        </label>
      )}

      {/* Input wrapper */}
      <div className="relative flex items-center">
        {/* Left icon */}
        {leftIcon && (
          <div className="absolute left-3.5 text-slate-400 pointer-events-none z-10">
            {leftIcon}
          </div>
        )}

        {/* The actual input */}
        <input
          type={inputType}
          name={name}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          disabled={disabled}
          required={required}
          accept={accept}
          min={min}
          max={max}
          step={step}
          className={`
            w-full bg-white/5 border rounded-xl
            text-slate-100 placeholder:text-slate-500
            transition-all duration-200
            focus:outline-none focus:ring-2 focus:bg-white/8
            ${borderClass}
            ${leftIcon ? "pl-10" : "pl-4"}
            ${rightIcon || type === "password" ? "pr-10" : "pr-4"}
            py-3 text-sm
            ${disabled ? "opacity-50 cursor-not-allowed" : ""}
            ${type === "file" ? "file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:bg-yellow-500 file:text-black file:text-sm file:font-medium file:cursor-pointer cursor-pointer" : ""}
          `}
          {...props}
        />

        {/* Password toggle button */}
        {type === "password" && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3.5 text-slate-400 hover:text-slate-200 
                       transition-colors z-10"
          >
            {showPassword ? (
              <EyeOff className="w-4 h-4" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
          </button>
        )}

        {/* Custom right icon (not for password) */}
        {rightIcon && type !== "password" && (
          <div className="absolute right-3.5 text-slate-400 pointer-events-none z-10">
            {rightIcon}
          </div>
        )}

        {/* Status icon */}
        {error && !rightIcon && type !== "password" && (
          <div className="absolute right-3.5 text-red-400 pointer-events-none z-10">
            <AlertCircle className="w-4 h-4" />
          </div>
        )}
        {success && !error && !rightIcon && type !== "password" && (
          <div className="absolute right-3.5 text-green-400 pointer-events-none z-10">
            <CheckCircle2 className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <p className="text-xs text-red-400 flex items-center gap-1 mt-0.5">
          <AlertCircle className="w-3 h-3 shrink-0" />
          {error}
        </p>
      )}

      {/* Hint text (shown when no error) */}
      {hint && !error && (
        <p className="text-xs text-slate-500 mt-0.5">{hint}</p>
      )}
    </div>
  );
}