"use client";

import Button from "./Button";

export default function EmptyState({
  icon: Icon = null,
  title = "Nothing here yet",
  description = "",
  action = null,
  className = "",
}) {
  return (
    <div
      className={`
        flex flex-col items-center justify-center 
        py-16 px-6 text-center
        ${className}
      `}
    >
      {/* Icon */}
      {Icon && (
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 
                        flex items-center justify-center mb-5 text-slate-500">
          <Icon className="w-8 h-8" />
        </div>
      )}

      {/* Text */}
      <h3 className="text-base font-semibold text-slate-200 mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-slate-500 max-w-sm leading-relaxed mb-6">
          {description}
        </p>
      )}

      {/* Action button */}
      {action && (
        <Button
          variant={action.variant || "primary"}
          onClick={action.onClick}
          leftIcon={action.icon}
          size="md"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}