// ─── Format Currency ──────────────────────────────────────────────────────────
export const formatCurrency = (amount, currency = "USD") => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

// ─── Format Number ────────────────────────────────────────────────────────────
export const formatNumber = (num, decimals = 1) => {
  if (num >= 1000000) return `${(num / 1000000).toFixed(decimals)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(decimals)}K`;
  return num?.toFixed(decimals) ?? "0";
};

// ─── Format Date ──────────────────────────────────────────────────────────────
export const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

// ─── Format Time ──────────────────────────────────────────────────────────────
export const formatTime = (dateString) => {
  return new Date(dateString).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

// ─── Calculate ROI ────────────────────────────────────────────────────────────
export const calculateROI = (savings, investment) => {
  if (!investment || investment === 0) return 0;
  return ((savings / investment) * 100).toFixed(1);
};

// ─── Calculate Payback Period ─────────────────────────────────────────────────
export const calculatePayback = (investment, annualSavings) => {
  if (!annualSavings || annualSavings === 0) return "N/A";
  const years = investment / annualSavings;
  return `${years.toFixed(1)} years`;
};

// ─── Get Status Color ─────────────────────────────────────────────────────────
export const getStatusColor = (status) => {
  const colors = {
    active: "text-green-400 bg-green-400/10",
    pending: "text-yellow-400 bg-yellow-400/10",
    completed: "text-blue-400 bg-blue-400/10",
    error: "text-red-400 bg-red-400/10",
  };
  return colors[status] || colors.pending;
};

// ─── Validate File ────────────────────────────────────────────────────────────
export const validateFile = (file, allowedTypes, maxSizeMB = 10) => {
  const maxBytes = maxSizeMB * 1024 * 1024;

  if (!allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: `Invalid file type. Allowed: ${allowedTypes.join(", ")}`,
    };
  }

  if (file.size > maxBytes) {
    return {
      valid: false,
      error: `File too large. Maximum size: ${maxSizeMB}MB`,
    };
  }

  return { valid: true };
};

// ─── Generate Chart Colors ────────────────────────────────────────────────────
export const chartColors = {
  yellow: "#EAB308",
  orange: "#F97316",
  green: "#22C55E",
  blue: "#3B82F6",
  purple: "#A855F7",
  red: "#EF4444",
  cyan: "#06B6D4",
  grid: "rgba(255,255,255,0.1)",
};

// ─── Truncate Text ────────────────────────────────────────────────────────────
export const truncate = (text, maxLength = 50) => {
  if (!text) return "";
  return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
};