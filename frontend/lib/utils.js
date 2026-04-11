import { clsx } from "clsx";

export function cn(...inputs) {
  return inputs.flat().filter(Boolean).join(" ");
}

/* ── Currency formatter — Indian Rupees ─────────────────────────────────── */
export function formatCurrency(value) {
  if (value == null || value === "") return "—";

  const num = Number(value);
  if (isNaN(num)) return "—";

  /* Indian number system: 1,00,000 / 10,00,000 etc. */
  return new Intl.NumberFormat("en-IN", {
    style:                 "currency",
    currency:              "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

/* ── Short format: ₹1.2L, ₹45K etc. ───────────────────────────────────── */
export function formatCurrencyShort(value) {
  if (value == null) return "—";
  const num = Number(value);
  if (isNaN(num)) return "—";

  if (num >= 10_000_000) return `₹${(num / 10_000_000).toFixed(1)}Cr`;
  if (num >= 100_000)    return `₹${(num / 100_000).toFixed(1)}L`;
  if (num >= 1_000)      return `₹${(num / 1_000).toFixed(0)}K`;
  return `₹${num}`;
}

export function formatNumber(value, decimals = 1) {
  if (value == null) return "—";
  return Number(value).toFixed(decimals);
}

/**
 * Human-readable API/axios error for toasts and UI.
 * FastAPI validation errors use `detail` as string | {msg} | Array<{msg}>.
 */
export function getErrorMessage(error) {
  const data = error?.response?.data;
  const detail = data?.detail;

  if (detail != null) {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (item == null) return null;
          if (typeof item === "string") return item;
          if (typeof item.msg === "string") return item.msg;
          try {
            return JSON.stringify(item);
          } catch {
            return String(item);
          }
        })
        .filter(Boolean);
      if (parts.length) return parts.join("; ");
    }
    if (typeof detail === "object" && typeof detail.msg === "string") {
      return detail.msg;
    }
  }

  if (data?.message != null && typeof data.message === "string") {
    return data.message;
  }

  if (error?.message && typeof error.message === "string") {
    return error.message;
  }

  return "Something went wrong";
}