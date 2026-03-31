"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/authContext";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Zap,
  PlusCircle,
  FolderOpen,
  BarChart3,
  Activity,
  User,
  LogOut,
  Sun,
} from "lucide-react";

const navItems = [
  { href: "/dashboard",  label: "Dashboard",   icon: LayoutDashboard },
  { href: "/plans/new",  label: "New Plan",    icon: PlusCircle      },
  { href: "/plans",      label: "My Plans",    icon: FolderOpen      },
  { href: "/profile",    label: "Profile",     icon: User            },
];

export function Sidebar({ collapsed, onToggle }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 h-full z-30",
        "bg-slate-900/95 backdrop-blur-xl border-r border-slate-800",
        "flex flex-col transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-800">
        <div className="shrink-0 w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
          <Sun className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <div>
            <p className="text-sm font-bold text-slate-100 leading-tight">
              SolarOptima
            </p>
            <p className="text-xs text-slate-500">Energy Manager</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl",
                "text-sm font-medium transition-all duration-150",
                active
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800"
              )}
            >
              <Icon className="w-5 h-5 shrink-0" />
              {!collapsed && label}
            </Link>
          );
        })}
      </nav>

      {/* User / Logout */}
      <div className="px-2 pb-4 border-t border-slate-800 pt-3 space-y-1">
        {!collapsed && user && (
          <div className="px-3 py-2 rounded-xl bg-slate-800/60 mb-2">
            <p className="text-xs font-semibold text-slate-200 truncate">
              {user.name}
            </p>
            <p className="text-xs text-slate-500 truncate">{user.email}</p>
          </div>
        )}
        <button
          onClick={logout}
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-xl w-full",
            "text-sm font-medium text-slate-400",
            "hover:text-red-400 hover:bg-red-500/10 transition-all"
          )}
        >
          <LogOut className="w-5 h-5 shrink-0" />
          {!collapsed && "Logout"}
        </button>
      </div>
    </aside>
  );
}