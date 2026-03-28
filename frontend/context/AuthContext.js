"use client";

import { createContext, useContext, useState, useEffect } from "react";
import Cookies from "js-cookie";
import { authAPI } from "@/lib/api";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

// Create the context
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true); // loading on first mount
  const router = useRouter();

  // ── On App Load: restore session ──────────────────────────────────────────
  useEffect(() => {
    const savedToken = Cookies.get("token");
    const savedUser = Cookies.get("user");

    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      } catch {
        // Cookie corrupted → clear
        Cookies.remove("token");
        Cookies.remove("user");
      }
    }

    setLoading(false);
  }, []);

  // ── Login ─────────────────────────────────────────────────────────────────
  const login = async (email, password) => {
    try {
      const response = await authAPI.login({ email, password });
      const { access_token, user: userData } = response.data;

      // Save to cookies (7 day expiry)
      Cookies.set("token", access_token, { expires: 7 });
      Cookies.set("user", JSON.stringify(userData), { expires: 7 });

      setToken(access_token);
      setUser(userData);

      toast.success(`Welcome back, ${userData.name}! 👋`);
      router.push("/dashboard");

      return { success: true };
    } catch (error) {
      const message =
        error.response?.data?.detail || "Login failed. Please try again.";
      toast.error(message);
      return { success: false, message };
    }
  };

  // ── Register ──────────────────────────────────────────────────────────────
  const register = async (name, email, password) => {
    try {
      await authAPI.register({ name, email, password });

      toast.success("Account created! Please log in. ✅");
      router.push("/login");

      return { success: true };
    } catch (error) {
      const message =
        error.response?.data?.detail || "Registration failed. Try again.";
      toast.error(message);
      return { success: false, message };
    }
  };

  // ── Logout ─────────────────────────────────────────────────────────────────
  const logout = () => {
    Cookies.remove("token");
    Cookies.remove("user");
    setUser(null);
    setToken(null);
    toast.success("Logged out successfully");
    router.push("/login");
  };

  // ── Check if logged in ────────────────────────────────────────────────────
  const isAuthenticated = !!token && !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
        isAuthenticated,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}