"use client";

import { useState } from "react";
import {
  CheckCircle2,
  AlertCircle,
  Info,
  AlertTriangle,
  X,
} from "lucide-react";

// ─── Alert Config ─────────────────────────────────────────────────────────────
const alertConfig = {
  success: {
    icon: CheckCircle2,
    container: "bg-green-500/10 border-green-500/30 text-green-300",
    iconColor: "text-green-400",
    title: "text-green-300",
  },
  error: {
    icon: AlertCircle,
    container: "bg-red-500/10 border-red-500/30 text-red-300",
    iconColor: "text-red-400",
    title: "text-red-300",
  },
  warning: {
    icon: AlertTriangle,
    container: "bg-yellow-500/10 border-yellow-500/30 text-yellow-300",
    iconColor: "text-yellow-400",
    title: "text-yellow-300",
  },
  info: {
    icon: Info,
    container: "bg-blue-500/10 border-blue-500/30 text-blue-300",
    iconColor: "text-blue-400",
    title: "text-blue-300",
  },
};

export default function Alert({
  type = "info",
  title = "",
  message = "",
  dismissible = false,
  className = "",
  onDismiss,
  actions = null,
}) {
  const [visible, setVisible] = useState(true);
  const config = alertConfig[type] || alertConfig.info;
  const Icon = config.icon;

  // Handle dismiss
  const handleDismiss = () => {
    setVisible(false);
    onDismiss?.();
  };

  if (!visible) return null;

  return (
    <div
      className={`
        flex gap-3 p-4 rounded-xl border
        animate-fade-in
        ${config.container}
        ${className}
      `}
    >
      {/* Icon */}
      <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${config.iconColor}`} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        {title && (
          <p className={`font-semibold text-sm mb-0.5 ${config.title}`}>
            {title}
          </p>
        )}
        {message && (
          <p className="text-sm opacity-90 leading-relaxed">{message}</p>
        )}
        {/* Action buttons */}
        {actions && <div className="mt-3 flex gap-2">{actions}</div>}
      </div>

      {/* Dismiss button */}
      {dismissible && (
        <button
          onClick={handleDismiss}
          className="shrink-0 opacity-60 hover:opacity-100 
                     transition-opacity p-0.5"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

// ─── Inline Error ─────────────────────────────────────────────────────────────
export function InlineError({ message, className = "" }) {
  if (!message) return null;
  return (
    <div
      className={`flex items-center gap-2 text-red-400 text-sm ${className}`}
    >
      <AlertCircle className="w-4 h-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}