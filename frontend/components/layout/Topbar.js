"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Link from "next/link";
import {
  Bell,
  Search,
  Sun,
  Battery,
  Zap,
  ChevronRight,
  Home,
  RefreshCw,
  X,
} from "lucide-react";
import Badge from "@/components/ui/Badge";

// ─── Page titles and breadcrumbs config ──────────────────────────────────────
const pageConfig = {
  "/dashboard": {
    title: "Dashboard",
    breadcrumbs: [{ label: "Home", href: "/dashboard" }],
  },
  "/plans": {
    title: "My Plans",
    breadcrumbs: [
      { label: "Home", href: "/dashboard" },
      { label: "Plans", href: "/plans" },
    ],
  },
  "/new-plan": {
    title: "Create New Plan",
    breadcrumbs: [
      { label: "Home", href: "/dashboard" },
      { label: "New Plan", href: "/new-plan" },
    ],
  },
  "/upload": {
    title: "Upload Bill",
    breadcrumbs: [
      { label: "Home", href: "/dashboard" },
      { label: "Upload Bill", href: "/upload" },
    ],
  },
  "/results": {
    title: "Optimization Results",
    breadcrumbs: [
      { label: "Home", href: "/dashboard" },
      { label: "Results", href: "/results" },
    ],
  },
  "/prediction": {
    title: "Live Prediction",
    breadcrumbs: [
      { label: "Home", href: "/dashboard" },
      { label: "Prediction", href: "/prediction" },
    ],
  },
  "/profile": {
    title: "My Profile",
    breadcrumbs: [
      { label: "Home", href: "/dashboard" },
      { label: "Profile", href: "/profile" },
    ],
  },
};

// ─── Mock notifications ───────────────────────────────────────────────────────
const mockNotifications = [
  {
    id: 1,
    type: "success",
    title: "Optimization complete",
    message: "Your energy plan has been optimized.",
    time: "2 min ago",
    unread: true,
  },
  {
    id: 2,
    type: "info",
    title: "Battery charged",
    message: "Battery reached 100% capacity.",
    time: "1 hr ago",
    unread: true,
  },
  {
    id: 3,
    type: "warning",
    title: "High consumption",
    message: "Consumption spike detected at 3PM.",
    time: "3 hr ago",
    unread: false,
  },
];

export default function Topbar({ sidebarCollapsed }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [notifications, setNotifications] = useState(mockNotifications);

  // ── Get current page config ──────────────────────────────────────────────
  const currentPage = Object.entries(pageConfig).find(([key]) =>
    pathname.startsWith(key)
  );
  const pageInfo = currentPage?.[1] || {
    title: "EnergyOptimizer",
    breadcrumbs: [],
  };

  // ── Unread count ─────────────────────────────────────────────────────────
  const unreadCount = notifications.filter((n) => n.unread).length;

  // ── Mark all as read ─────────────────────────────────────────────────────
  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
  };

  // ── Get notification icon color ──────────────────────────────────────────
  const getNotifColor = (type) => {
    const map = {
      success: "text-green-400 bg-green-400/10",
      warning: "text-yellow-400 bg-yellow-400/10",
      error: "text-red-400 bg-red-400/10",
      info: "text-blue-400 bg-blue-400/10",
    };
    return map[type] || map.info;
  };

  return (
    <header
      className={`
        fixed top-0 right-0 z-20 h-16
        bg-slate-900/80 backdrop-blur-md
        border-b border-slate-800
        flex items-center justify-between
        px-5 transition-all duration-300
        ${sidebarCollapsed ? "left-17.5" : "left-60"}
      `}
    >
      {/* ── Left: Title & Breadcrumbs ────────────────────────────────────── */}
      <div className="flex flex-col justify-center">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-1 text-[11px] text-slate-500 mb-0.5">
          <Home className="w-3 h-3" />
          {pageInfo.breadcrumbs.map((crumb, i) => (
            <span key={crumb.href} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="w-2.5 h-2.5" />}
              {i === pageInfo.breadcrumbs.length - 1 ? (
                <span className="text-slate-400">{crumb.label}</span>
              ) : (
                <Link
                  href={crumb.href}
                  className="hover:text-slate-300 transition-colors"
                >
                  {crumb.label}
                </Link>
              )}
            </span>
          ))}
        </div>

        {/* Page title */}
        <h1 className="text-base font-semibold text-slate-100">
          {pageInfo.title}
        </h1>
      </div>

      {/* ── Right: Actions ───────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* ── Live Energy Status Strip ────────────────────────────────────── */}
        <div
          className="hidden md:flex items-center gap-3 px-3 py-1.5
                       bg-white/5 border border-white/10 rounded-xl mr-1"
        >
          {/* Solar */}
          <div className="flex items-center gap-1.5">
            <Sun className="w-3.5 h-3.5 text-yellow-400" />
            <span className="text-xs text-slate-300 font-medium">4.2 kW</span>
          </div>

          <div className="w-px h-3 bg-slate-700" />

          {/* Battery */}
          <div className="flex items-center gap-1.5">
            <Battery className="w-3.5 h-3.5 text-green-400" />
            <span className="text-xs text-slate-300 font-medium">82%</span>
          </div>

          <div className="w-px h-3 bg-slate-700" />

          {/* Grid */}
          <div className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-xs text-slate-300 font-medium">1.1 kW</span>
          </div>
        </div>

        {/* ── Search Button ────────────────────────────────────────────────── */}
        <button
          onClick={() => setShowSearch(!showSearch)}
          className="relative p-2.5 rounded-xl text-slate-400 
                     hover:text-slate-200 hover:bg-white/10
                     transition-all"
        >
          {showSearch ? (
            <X className="w-4.5 h-4.5" />
          ) : (
            <Search className="w-4.5 h-4.5" />
          )}
        </button>

        {/* ── Search Input (expands when active) ──────────────────────────── */}
        {showSearch && (
          <div className="absolute right-32 top-3">
            <input
              autoFocus
              type="text"
              placeholder="Search plans, results..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 bg-slate-800 border border-slate-700 rounded-xl
                         px-4 py-2 text-sm text-slate-200 placeholder:text-slate-500
                         focus:outline-none focus:border-yellow-500/50 focus:ring-2
                         focus:ring-yellow-500/20 transition-all"
            />
          </div>
        )}

        {/* ── Notifications Button ─────────────────────────────────────────── */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2.5 rounded-xl text-slate-400 
                       hover:text-slate-200 hover:bg-white/10
                       transition-all"
          >
            <Bell className="w-4.5 h-4.5" />
            {/* Unread badge */}
            {unreadCount > 0 && (
              <span
                className="absolute top-1.5 right-1.5 w-2 h-2 
                             bg-yellow-500 rounded-full animate-pulse"
              />
            )}
          </button>

          {/* ── Notification Dropdown ────────────────────────────────────── */}
          {showNotifications && (
            <>
              {/* Backdrop */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowNotifications(false)}
              />
              <div
                className="absolute right-0 top-12 w-80 z-20
                             bg-slate-800 border border-slate-700
                             rounded-2xl shadow-2xl shadow-black/40
                             overflow-hidden animate-slide-up"
              >
                {/* Dropdown header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-slate-200">
                      Notifications
                    </h3>
                    {unreadCount > 0 && (
                      <Badge variant="yellow" size="sm">
                        {unreadCount} new
                      </Badge>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="text-xs text-yellow-400 hover:text-yellow-300 
                                 flex items-center gap-1 transition-colors"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Mark all read
                    </button>
                  )}
                </div>

                {/* Notification list */}
                <div className="max-h-72 overflow-y-auto">
                  {notifications.map((notif) => (
                    <div
                      key={notif.id}
                      className={`
                        flex gap-3 px-4 py-3 border-b border-slate-700/50
                        hover:bg-white/5 transition-colors cursor-pointer
                        ${notif.unread ? "bg-white/2" : ""}
                      `}
                    >
                      {/* Type dot */}
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center 
                                    shrink-0 mt-0.5 text-xs font-bold
                                    ${getNotifColor(notif.type)}`}
                      >
                        {notif.type === "success"
                          ? "✓"
                          : notif.type === "warning"
                          ? "!"
                          : "i"}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p
                            className={`text-sm font-medium ${
                              notif.unread ? "text-slate-200" : "text-slate-400"
                            }`}
                          >
                            {notif.title}
                          </p>
                          {notif.unread && (
                            <div className="w-1.5 h-1.5 rounded-full bg-yellow-400 shrink-0 mt-1.5" />
                          )}
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5 truncate">
                          {notif.message}
                        </p>
                        <p className="text-[10px] text-slate-600 mt-1">
                          {notif.time}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Footer */}
                <div className="px-4 py-3 text-center">
                  <button
                    className="text-xs text-yellow-400 hover:text-yellow-300 
                               transition-colors font-medium"
                  >
                    View all notifications
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ── User Avatar ──────────────────────────────────────────────────── */}
        <Link href="/profile">
          <div
            className="w-9 h-9 rounded-xl bg-linear-to-br from-yellow-500 
                         to-orange-500 flex items-center justify-center
                         cursor-pointer hover:scale-105 transition-transform
                         shadow-md shadow-yellow-500/20"
          >
            <span className="text-black font-bold text-sm">
              {user?.name?.charAt(0)?.toUpperCase() || "U"}
            </span>
          </div>
        </Link>
      </div>
    </header>
  );
}