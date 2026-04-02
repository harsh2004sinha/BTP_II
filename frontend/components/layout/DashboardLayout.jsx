"use client";

import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export function DashboardLayout({ children }) {
  const [collapsed, setCollapsed] = useState(false);

  const sidebarWidth = collapsed ? "4rem" : "16rem";

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-950">
        <Sidebar
          collapsed={collapsed}
          onToggle={() => setCollapsed(!collapsed)}
        />

        <Topbar
          onMenuClick={() => setCollapsed(!collapsed)}
          sidebarWidth={sidebarWidth}
        />

        <main
          className="min-h-screen transition-all duration-300 pt-16"
          style={{ paddingLeft: sidebarWidth }}
        >
          <div className="p-6">{children}</div>
        </main>
      </div>
    </ProtectedRoute>
  );
}