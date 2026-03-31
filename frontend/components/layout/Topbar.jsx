"use client";

import { usePathname } from "next/navigation";
import { Menu, Bell, ChevronRight } from "lucide-react";
import { useAuth } from "@/context/authContext";

const titles = {
  "/dashboard":  "Dashboard",
  "/plans":      "My Plans",
  "/plans/new":  "New Plan",
  "/profile":    "Profile",
};

function getBreadcrumb(pathname) {
  const parts = pathname.split("/").filter(Boolean);
  return parts;
}

export function Topbar({ onMenuClick, sidebarWidth }) {
  const pathname = usePathname();
  const { user }  = useAuth();
  const crumbs    = getBreadcrumb(pathname);

  return (
    <header
      className="fixed top-0 right-0 z-20 h-16 flex items-center px-6
                 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800
                 transition-all duration-300"
      style={{ left: sidebarWidth }}
    >
      {/* Left */}
      <div className="flex items-center gap-3 flex-1">
        <button
          onClick={onMenuClick}
          className="p-2 rounded-lg text-slate-400 hover:text-slate-100
                     hover:bg-slate-800 transition-all lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Breadcrumb */}
        <nav className="flex items-center gap-1 text-sm text-slate-400">
          {crumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="w-3 h-3" />}
              <span
                className={
                  i === crumbs.length - 1 ? "text-slate-100 font-medium" : ""
                }
              >
                {crumb.charAt(0).toUpperCase() + crumb.slice(1)}
              </span>
            </span>
          ))}
        </nav>
      </div>

      {/* Right */}
      <div className="flex items-center gap-3">

        {user && (
          <div className="flex items-center gap-2 pl-3 border-l border-slate-800">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border
                            border-emerald-500/30 flex items-center justify-center">
              <span className="text-xs font-bold text-emerald-400">
                {user.name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <span className="text-sm text-slate-300 hidden sm:block">
              {user.name}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}