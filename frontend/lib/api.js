import axios from "axios";
import Cookies from "js-cookie";

// Base API instance
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
});

// ─── Request Interceptor ────────────────────────────────────────────────────
// Automatically attach token to every request
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ─── Response Interceptor ───────────────────────────────────────────────────
// Handle global errors (401, 500, etc.)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Token expired or invalid → logout user
      if (error.response.status === 401) {
        Cookies.remove("token");
        Cookies.remove("user");
        window.location.href = "/login";
      }

      // Server error
      if (error.response.status >= 500) {
        console.error("Server error:", error.response.data);
      }
    }

    return Promise.reject(error);
  }
);

// ─── Auth Endpoints ─────────────────────────────────────────────────────────
export const authAPI = {
  login: (data) => api.post("/auth/login", data),
  register: (data) => api.post("/auth/register", data),
  getProfile: () => api.get("/auth/me"),
  logout: () => api.post("/auth/logout"),
};

// ─── Plans Endpoints ─────────────────────────────────────────────────────────
export const plansAPI = {
  getAll: () => api.get("/plans"),
  getById: (id) => api.get(`/plans/${id}`),
  create: (data) => api.post("/plans", data),
  update: (id, data) => api.put(`/plans/${id}`, data),
  delete: (id) => api.delete(`/plans/${id}`),
};

// ─── Upload Endpoints ────────────────────────────────────────────────────────
export const uploadAPI = {
  uploadBill: (planId, formData) =>
    api.post(`/upload/bill/${planId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  getConsumption: (planId) => api.get(`/upload/consumption/${planId}`),
};

// ─── Weather Endpoints ────────────────────────────────────────────────────────
export const weatherAPI = {
  getWeather: (location) => api.get(`/weather?location=${location}`),
  getSolarData: (location) => api.get(`/weather/solar?location=${location}`),
};

// ─── Results Endpoints ────────────────────────────────────────────────────────
export const resultsAPI = {
  getResult: (planId) => api.get(`/results/${planId}`),
  runOptimizer: (planId) => api.post(`/results/optimize/${planId}`),
};

// ─── Prediction Endpoints ─────────────────────────────────────────────────────
export const predictionAPI = {
  getCurrent: (planId) => api.get(`/prediction/${planId}`),
  getHistory: (planId) => api.get(`/prediction/history/${planId}`),
};

export default api;