"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import Cookies from "js-cookie";
import { authApi } from "@/lib/authApi";
import { getErrorMessage } from "@/lib/utils";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [token, setToken]     = useState(null);
  const [loading, setLoading] = useState(true);

  /* ── Bootstrap on mount ─────────────────────────────────────────────── */
  useEffect(() => {
    const savedToken = Cookies.get("token");
    const savedUser  = Cookies.get("user");

    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      } catch {
        Cookies.remove("token");
        Cookies.remove("user");
      }
    }
    setLoading(false);
  }, []);

  /* ── Login ──────────────────────────────────────────────────────────── */
  const login = useCallback(async (email, password) => {
    try {
      const res = await authApi.login({ email, password });

      console.log("Login API response:", res); // ← debug, remove later

      if (!res.success) {
        return { success: false, message: res.message || "Login failed" };
      }

      const data = res.data || {};

      /*
        Backend may return any of these field names for the token:
        token | access_token | accessToken
      */
      const newToken =
        data.token ||
        data.access_token ||
        data.accessToken ||
        null;

      if (!newToken) {
        console.error("No token found in login response:", data);
        return { success: false, message: "No token received from server" };
      }

      const userId = data.userId || data.user_id || data.id || null;
      const name   = data.name   || data.username || email;

      const userData = { id: userId, name, email };

      /* ── Cookie settings ─────────────────────────────────────────────
         secure:true breaks on HTTP (localhost).
         Use secure only in production.
      ─────────────────────────────────────────────────────────────────── */
      const isProduction = process.env.NODE_ENV === "production";

      const cookieOptions = {
        expires:  7,
        sameSite: "strict",
        secure:   isProduction,
      };

      Cookies.set("token", newToken,               cookieOptions);
      Cookies.set("user",  JSON.stringify(userData), cookieOptions);

      /* Update state */
      setToken(newToken);
      setUser(userData);

      return { success: true };

    } catch (err) {
      console.error("Login error:", err);

      return { success: false, message: getErrorMessage(err) };
    }
  }, []);

  /* ── Register ───────────────────────────────────────────────────────── */
  const register = useCallback(async (name, email, password) => {
    try {
      const res = await authApi.register({ name, email, password });
      return res;
    } catch (err) {
      return { success: false, message: getErrorMessage(err) };
    }
  }, []);

  /* ── Logout ─────────────────────────────────────────────────────────── */
  const logout = useCallback(() => {
    Cookies.remove("token");
    Cookies.remove("user");
    setToken(null);
    setUser(null);
    window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, token, loading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
};