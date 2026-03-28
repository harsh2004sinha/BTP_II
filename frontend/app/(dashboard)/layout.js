"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { PageLoader } from "@/components/ui/Loader";

export default function DashboardLayout({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // ── Detect mobile screen ─────────────────────────────────────────────────
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      // Auto-collapse on mobile
      if (mobile) setSidebarCollapsed(true);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // ── Route protection ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, loading, router]);

  // ── Show loader while checking auth ─────────────────────────────────────
  if (loading) {
    return <PageLoader message="Loading your dashboard..." />;
  }

  // ── Don't render if not authenticated (before redirect) ─────────────────
  if (!isAuthenticated) {
    return <PageLoader message="Redirecting to login..." />;
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((prev) => !prev)}
      />

      {/* ── Mobile overlay backdrop ──────────────────────────────────────── */}
      {isMobile && !sidebarCollapsed && (
        <div
          className="fixed inset-0 bg-black/60 z-20 md:hidden"
          onClick={() => setSidebarCollapsed(true)}
        />
      )}

      {/* ── Main area ────────────────────────────────────────────────────── */}
      <div
        className={`
          flex flex-col min-h-screen
          transition-all duration-300
          ${sidebarCollapsed ? "ml-17.5" : "ml-60"}
        `}
      >
        {/* Topbar */}
        <Topbar sidebarCollapsed={sidebarCollapsed} />

        {/* Page content */}
        <main className="flex-1 mt-16 p-5 md:p-6 lg:p-7">
          {/* Page wrapper with max width */}
          <div className="max-w-7xl mx-auto animate-fade-in">{children}</div>
        </main>

        {/* ── Footer ──────────────────────────────────────────────────────── */}
        <footer className="border-t border-slate-800/50 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <p className="text-xs text-slate-600">
              © 2025 EnergyOptimizer. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              <a
                href="#"
                className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
              >
                Privacy
              </a>
              <a
                href="#"
                className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
              >
                Terms
              </a>
              <a
                href="#"
                className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
              >
                Support
              </a>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}