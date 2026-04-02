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

export function getErrorMessage(error) {
  if (error?.response?.data?.detail)  return error.response.data.detail;
  if (error?.response?.data?.message) return error.response.data.message;
  if (error?.message)                 return error.message;
  return "Something went wrong";
}