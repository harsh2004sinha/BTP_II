import axios from "axios";
import Cookies from "js-cookie";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

/* ── Request interceptor ────────────────────────────────────────────────── */
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/* ── Response interceptor ───────────────────────────────────────────────── */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status   = error?.response?.status;
    const url      = error?.config?.url || "";

    /*
      Only redirect to login on 401 if:
      1. Status is 401
      2. Request is NOT the login or register endpoint
         (avoid infinite redirect loop)
    */
    const isAuthEndpoint =
      url.includes("/auth/login") ||
      url.includes("/auth/register");

    if (status === 401 && !isAuthEndpoint) {
      Cookies.remove("token");
      Cookies.remove("user");
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

export default api;