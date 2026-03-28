"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  Zap,
  LayoutDashboard,
  FolderOpen,
  PlusCircle,
  Upload,
  BarChart3,
  Brain,
  User,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Settings,
  HelpCircle,
  Sun,
  Battery,
} from "lucide-react";
import { ConfirmModal } from "@/components/ui/Modal";

// ─── Navigation Items ─────────────────────────────────────────────────────────
const navItems = [
  {
    section: "Main",
    items: [
      {
        label: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
        description: "Overview & stats",
      },
      {
        label: "My Plans",
        href: "/plans",
        icon: FolderOpen,
        description: "View all plans",
      },
      {
        label: "New Plan",
        href: "/new-plan",
        icon: PlusCircle,
        description: "Create energy plan",
      },
    ],
  },
  {
    section: "Energy",
    items: [
      {
        label: "Upload Bill",
        href: "/upload",
        icon: Upload,
        description: "Upload electricity bill",
      },
      {
        label: "Results",
        href: "/results",
        icon: BarChart3,
        description: "Optimization results",
      },
      {
        label: "Prediction",
        href: "/prediction",
        icon: Brain,
        description: "Real-time optimization",
        badge: "Live",
      },
    ],
  },
  {
    section: "Account",
    items: [
      {
        label: "Profile",
        href: "/profile",
        icon: User,
        description: "Your account",
      },
    ],
  },
];

export default function Sidebar({ collapsed, onToggle }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  // ── Check if nav item is active ──────────────────────────────────────────
  const isActive = (href) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  // ── Handle logout confirm ────────────────────────────────────────────────
  const handleLogout = () => {
    setShowLogoutModal(false);
    logout();
  };

  return (
    <>
      {/* ── Sidebar Container ──────────────────────────────────────────────── */}
      <aside
        className={`
          fixed left-0 top-0 h-screen z-30
          bg-slate-900 border-r border-slate-800
          flex flex-col
          transition-all duration-300 ease-in-out
          ${collapsed ? "w-17.5" : "w-60"}
        `}
      >
        {/* ── Logo ────────────────────────────────────────────────────────── */}
        <div
          className={`
            flex items-center h-16 border-b border-slate-800
            ${collapsed ? "justify-center px-0" : "px-5 gap-3"}
          `}
        >
          {/* Logo icon */}
          <div
            className="w-9 h-9 rounded-xl bg-linear-to-br from-yellow-500 
                          to-orange-500 flex items-center justify-center shrink-0
                          shadow-lg shadow-yellow-500/25"
          >
            <Zap className="w-5 h-5 text-black" fill="black" />
          </div>

          {/* Logo text - hidden when collapsed */}
          {!collapsed && (
            <div className="overflow-hidden">
              <p className="font-bold text-sm text-white leading-tight whitespace-nowrap">
                EnergyOptimizer
              </p>
              <p className="text-[10px] text-slate-500 whitespace-nowrap">
                Smart Energy Management
              </p>
            </div>
          )}
        </div>

        {/* ── Navigation ──────────────────────────────────────────────────── */}
        <nav className="flex-1 overflow-y-auto py-4 space-y-6 px-3">
          {navItems.map((section) => (
            <div key={section.section}>
              {/* Section label - hidden when collapsed */}
              {!collapsed && (
                <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest mb-2 px-2">
                  {section.section}
                </p>
              )}

              {/* Nav links */}
              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      title={collapsed ? item.label : ""}
                      className={`
                        flex items-center gap-3 rounded-xl
                        transition-all duration-200 group relative
                        ${collapsed ? "justify-center p-2.5" : "px-3 py-2.5"}
                        ${
                          active
                            ? "bg-yellow-500/15 text-yellow-400 border border-yellow-500/25"
                            : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                        }
                      `}
                    >
                      {/* Active indicator bar */}
                      {active && (
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-yellow-400 rounded-r-full" />
                      )}

                      {/* Icon */}
                      <Icon
                        className={`w-4.5 h-4.5 shrink-0 transition-transform
                          ${active ? "text-yellow-400" : ""}
                          ${!active ? "group-hover:scale-110" : ""}
                        `}
                      />

                      {/* Label + badge */}
                      {!collapsed && (
                        <div className="flex items-center justify-between flex-1 min-w-0">
                          <span className="text-sm font-medium truncate">
                            {item.label}
                          </span>
                          {item.badge && (
                            <span
                              className="text-[10px] font-bold px-1.5 py-0.5 
                                         rounded-full bg-green-500/20 text-green-400
                                         border border-green-500/30 animate-pulse"
                            >
                              {item.badge}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Tooltip on collapsed */}
                      {collapsed && (
                        <div
                          className="absolute left-full ml-3 px-2.5 py-1.5
                                     bg-slate-800 border border-slate-700
                                     rounded-lg text-xs text-slate-200 
                                     whitespace-nowrap pointer-events-none
                                     opacity-0 group-hover:opacity-100
                                     transition-opacity z-50 shadow-xl"
                        >
                          {item.label}
                          {item.badge && (
                            <span className="ml-1.5 text-green-400">
                              • {item.badge}
                            </span>
                          )}
                        </div>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* ── Energy Info Strip ────────────────────────────────────────────── */}
        {!collapsed && (
          <div className="mx-3 mb-3 p-3 rounded-xl bg-linear-to-br from-yellow-500/10 to-orange-500/10 border border-yellow-500/20">
            <div className="flex items-center gap-2 mb-2">
              <Sun className="w-3.5 h-3.5 text-yellow-400" />
              <span className="text-[11px] font-medium text-yellow-400">
                Solar Active
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <div className="flex items-center gap-1">
                <Battery className="w-3 h-3 text-green-400" />
                <span>Battery 82%</span>
              </div>
              <span className="text-green-400 font-medium">4.2 kW</span>
            </div>
          </div>
        )}

        {/* ── User Section ─────────────────────────────────────────────────── */}
        <div className="border-t border-slate-800 p-3">
          {!collapsed ? (
            // Expanded user card
            <div className="flex items-center gap-2.5 p-2 rounded-xl hover:bg-white/5 transition-colors">
              {/* Avatar */}
              <div
                className="w-8 h-8 rounded-lg bg-linear-to-br from-yellow-500 
                              to-orange-500 flex items-center justify-center shrink-0"
              >
                <span className="text-black font-bold text-sm">
                  {user?.name?.charAt(0)?.toUpperCase() || "U"}
                </span>
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">
                  {user?.name || "User"}
                </p>
                <p className="text-[11px] text-slate-500 truncate">
                  {user?.email || ""}
                </p>
              </div>

              {/* Logout button */}
              <button
                onClick={() => setShowLogoutModal(true)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 
                           hover:bg-red-400/10 transition-all"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            // Collapsed: just logout icon
            <button
              onClick={() => setShowLogoutModal(true)}
              className="w-full flex justify-center p-2.5 rounded-xl
                         text-slate-500 hover:text-red-400 hover:bg-red-400/10
                         transition-all"
              title="Logout"
            >
              <LogOut className="w-4.5 h-4.5" />
            </button>
          )}
        </div>

        {/* ── Collapse Toggle Button ────────────────────────────────────────── */}
        <button
          onClick={onToggle}
          className="absolute -right-3 top-20 w-6 h-6
                     bg-slate-800 border border-slate-700
                     rounded-full flex items-center justify-center
                     text-slate-400 hover:text-slate-200
                     hover:border-yellow-500/50 transition-all
                     shadow-lg z-10"
        >
          {collapsed ? (
            <ChevronRight className="w-3.5 h-3.5" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5" />
          )}
        </button>
      </aside>

      {/* ── Logout Confirm Modal ──────────────────────────────────────────────── */}
      <ConfirmModal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        onConfirm={handleLogout}
        title="Log out?"
        message="Are you sure you want to log out of EnergyOptimizer?"
        confirmText="Log out"
        cancelText="Stay"
        variant="danger"
      />
    </>
  );
}