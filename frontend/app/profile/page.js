"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/authContext";
import { authApi } from "@/lib/authApi";
import { usePlans } from "@/hooks/usePlans";
import { StatusBadge } from "@/components/ui/Badge";
import { getErrorMessage, formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";
import {
  User, Mail, Calendar, Shield, LogOut,
  BarChart3, Zap, CheckCircle, Clock,
  TrendingDown, Sun, ArrowRight, Battery,
  RefreshCw, AlertCircle, Edit3, MapPin,
  Activity, Leaf,
} from "lucide-react";

/* ─────────────────────────────────────────────────────────────────────────
   Avatar component
───────────────────────────────────────────────────────────────────────── */
function Avatar({ name, size = "lg" }) {
  const sizeMap = {
    sm: "w-10 h-10 text-sm",
    md: "w-14 h-14 text-xl",
    lg: "w-20 h-20 text-3xl",
  };

  const initials = name
    ? name
        .split(" ")
        .map((w) => w[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "?";

  return (
    <div
      className={`rounded-2xl bg-linear-to-br from-emerald-500/30
                  to-blue-500/20 border border-emerald-500/30 flex items-center
                  justify-center font-black text-emerald-400 shrink-0
                  ${sizeMap[size]}`}
    >
      {initials}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Info row
───────────────────────────────────────────────────────────────────────── */
function InfoRow({ icon: Icon, label, value, mono = false }) {
  return (
    <div
      className="flex items-center gap-4 py-4 border-b border-slate-800/60
                 last:border-b-0"
    >
      <div
        className="w-9 h-9 rounded-xl bg-slate-800/80 flex items-center
                    justify-center shrink-0"
      >
        <Icon className="w-4 h-4 text-slate-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-500 mb-0.5 uppercase tracking-wider">
          {label}
        </p>
        <p
          className={`text-sm text-slate-200 font-medium truncate
                      ${mono ? "font-mono text-emerald-400" : ""}`}
        >
          {value || "—"}
        </p>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Stat card
───────────────────────────────────────────────────────────────────────── */
function StatCard({ icon: Icon, label, value, color }) {
  const colorMap = {
    emerald: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
    blue:    "bg-blue-500/10    border-blue-500/20    text-blue-400",
    amber:   "bg-amber-500/10   border-amber-500/20   text-amber-400",
    purple:  "bg-purple-500/10  border-purple-500/20  text-purple-400",
  };

  return (
    <div className={`rounded-2xl border p-5 text-center ${colorMap[color]}`}>
      <div
        className="w-10 h-10 rounded-xl bg-slate-900/50 flex items-center
                    justify-center mx-auto mb-3"
      >
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-xs text-slate-400 mb-1.5 uppercase tracking-wider">
        {label}
      </p>
      <p className="text-2xl font-black text-slate-100">{value ?? "—"}</p>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Plan row
───────────────────────────────────────────────────────────────────────── */
function PlanRow({ plan }) {
  const router = useRouter();

  return (
    <div
      onClick={() => router.push(`/plans/${plan.planId}/result`)}
      className="flex items-center gap-3 p-3.5 rounded-xl hover:bg-slate-800/60
                 transition-all cursor-pointer group border border-transparent
                 hover:border-slate-700/50"
    >
      {/* icon */}
      <div
        className="w-10 h-10 rounded-xl bg-emerald-500/10 border
                    border-emerald-500/20 flex items-center justify-center
                    shrink-0 group-hover:bg-emerald-500/20 transition-all"
      >
        <Zap className="w-4 h-4 text-emerald-400" />
      </div>

      {/* info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-0.5">
          <p className="text-sm font-semibold text-slate-200 truncate">
            {plan.location || "Unknown location"}
          </p>
          <StatusBadge status={plan.status} />
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs text-slate-500 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {plan.createdAt
              ? new Date(plan.createdAt).toLocaleDateString("en-MY", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })
              : "—"}
          </span>
          {plan.budget && (
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <TrendingDown className="w-3 h-3" />
              {formatCurrency(plan.budget)}
            </span>
          )}
        </div>
      </div>

      {/* arrow */}
      <ArrowRight
        className="w-4 h-4 text-slate-600 group-hover:text-emerald-400
                   transition-all group-hover:translate-x-0.5 shrink-0"
      />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Logout confirm modal
───────────────────────────────────────────────────────────────────────── */
function LogoutModal({ onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-sm bg-slate-900 border border-slate-800
                    rounded-3xl p-6 shadow-2xl"
      >
        <div
          className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20
                      flex items-center justify-center mx-auto mb-4"
        >
          <LogOut className="w-7 h-7 text-red-400" />
        </div>

        <h3 className="text-lg font-bold text-slate-100 text-center mb-2">
          Sign Out?
        </h3>
        <p className="text-sm text-slate-400 text-center mb-6 leading-relaxed">
          You will be redirected to the login page. Your plans and data
          will be saved.
        </p>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-xl border border-slate-700
                       text-slate-300 hover:text-slate-100 hover:bg-slate-800
                       font-medium text-sm transition-all"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-2.5 rounded-xl bg-red-500 hover:bg-red-600
                       text-white font-semibold text-sm transition-all
                       shadow-lg shadow-red-500/25"
          >
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Main page
───────────────────────────────────────────────────────────────────────── */
export default function ProfilePage() {
  const { user, logout }        = useAuth();
  const { plans, loading: plansLoading, refetch } = usePlans();
  const router                  = useRouter();

  const [meData, setMeData]         = useState(null);
  const [meLoading, setMeLoading]   = useState(true);
  const [meError, setMeError]       = useState(null);
  const [showLogout, setShowLogout] = useState(false);

  /* ── fetch /auth/me ─────────────────────────────────────────────────── */
  useEffect(() => {
    async function fetchMe() {
      setMeLoading(true);
      setMeError(null);
      try {
        const res = await authApi.getMe();
        if (res.success) setMeData(res.data);
      } catch (err) {
        setMeError(getErrorMessage(err));
      } finally {
        setMeLoading(false);
      }
    }
    fetchMe();
  }, []);

  /* ── derived plan stats ─────────────────────────────────────────────── */
  const totalPlans     = plans.length;
  const completedPlans = plans.filter((p) => p.status === "completed").length;
  const pendingPlans   = plans.filter(
    (p) => p.status === "pending" || p.status === "bill_uploaded"
  ).length;
  const recentPlans    = [...plans]
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    .slice(0, 5);

  /* ── display data: prefer /me, fallback to cookie ───────────────────── */
  const displayName  = meData?.name  || user?.name  || "—";
  const displayEmail = meData?.email || user?.email || "—";
  const createdAt    = meData?.createdAt
    ? new Date(meData.createdAt).toLocaleDateString("en-MY", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    : "—";

  const isActive = meData?.is_active ?? true;

  /* ── skeleton ───────────────────────────────────────────────────────── */
  if (meLoading) {
    return (
      <DashboardLayout>
        <div className="max-w-5xl mx-auto page-enter">
          <div className="h-8 w-32 bg-slate-800 rounded-xl mb-8 animate-pulse" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="h-80 bg-slate-800 rounded-2xl animate-pulse" />
            <div className="lg:col-span-2 space-y-4">
              <div className="h-40 bg-slate-800 rounded-2xl animate-pulse" />
              <div className="h-56 bg-slate-800 rounded-2xl animate-pulse" />
            </div>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      {/* Logout confirm modal */}
      {showLogout && (
        <LogoutModal
          onConfirm={logout}
          onCancel={() => setShowLogout(false)}
        />
      )}

      <div className="max-w-5xl mx-auto page-enter">
        {/* ── Page heading ────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Profile</h1>
            <p className="text-slate-500 text-sm mt-0.5">
              Manage your account and view your energy plans
            </p>
          </div>
          <button
            onClick={refetch}
            title="Refresh plans"
            className="p-2.5 rounded-xl border border-slate-700 text-slate-400
                       hover:text-slate-200 hover:bg-slate-800 transition-all"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* ── API error banner ────────────────────────────────────────── */}
        {meError && (
          <div
            className="rounded-2xl bg-red-500/10 border border-red-500/20
                        p-4 flex items-center gap-3 mb-6"
          >
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            <p className="text-sm text-red-300">{meError}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ────────────────────────────────────────────────────────────
              LEFT COLUMN — Profile card
          ──────────────────────────────────────────────────────────── */}
          <div className="space-y-5">
            {/* Profile hero card */}
            <div
              className="rounded-2xl border border-slate-700/50 bg-slate-800/50
                          p-6 text-center"
            >
              {/* Avatar */}
              <div className="flex justify-center mb-4">
                <Avatar name={displayName} size="lg" />
              </div>

              {/* Name & email */}
              <h2 className="text-xl font-bold text-slate-100 mb-1">
                {displayName}
              </h2>
              <p className="text-sm text-slate-400 mb-4 truncate px-2">
                {displayEmail}
              </p>

              {/* Active badge */}
              <div className="flex justify-center mb-5">
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5
                              rounded-full text-xs font-semibold border
                              ${isActive
                                ? "bg-emerald-500/15 border-emerald-500/25 text-emerald-400"
                                : "bg-slate-700/60 border-slate-600 text-slate-400"
                              }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full
                      ${isActive ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`}
                  />
                  {isActive ? "Active Account" : "Inactive"}
                </span>
              </div>

              {/* Divider */}
              <div className="h-px bg-slate-700/50 mb-5" />

              {/* Quick actions */}
              <div className="space-y-2">
                <button
                  onClick={() => router.push("/plans/new")}
                  className="w-full flex items-center gap-3 px-4 py-2.5
                             rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20
                             border border-emerald-500/20 text-emerald-400
                             text-sm font-medium transition-all"
                >
                  <Sun className="w-4 h-4" />
                  New Energy Plan
                  <ArrowRight className="w-3.5 h-3.5 ml-auto" />
                </button>

                <button
                  onClick={() => router.push("/plans")}
                  className="w-full flex items-center gap-3 px-4 py-2.5
                             rounded-xl bg-slate-700/40 hover:bg-slate-700/70
                             border border-slate-700/50 text-slate-300
                             text-sm font-medium transition-all"
                >
                  <BarChart3 className="w-4 h-4" />
                  View All Plans
                  <ArrowRight className="w-3.5 h-3.5 ml-auto" />
                </button>

                <button
                  onClick={() => setShowLogout(true)}
                  className="w-full flex items-center gap-3 px-4 py-2.5
                             rounded-xl bg-red-500/5 hover:bg-red-500/15
                             border border-red-500/15 hover:border-red-500/30
                             text-red-400 text-sm font-medium transition-all"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                  <ArrowRight className="w-3.5 h-3.5 ml-auto" />
                </button>
              </div>
            </div>

            {/* Account details card */}
            <div
              className="rounded-2xl border border-slate-700/50 bg-slate-800/50
                          p-5"
            >
              <h3 className="text-sm font-semibold text-slate-300 mb-2
                             flex items-center gap-2">
                <Shield className="w-4 h-4 text-slate-400" />
                Account Details
              </h3>

              <InfoRow
                icon={User}
                label="Full Name"
                value={displayName}
              />
              <InfoRow
                icon={Mail}
                label="Email Address"
                value={displayEmail}
              />
              <InfoRow
                icon={Calendar}
                label="Member Since"
                value={createdAt}
              />
              <InfoRow
                icon={Shield}
                label="User ID"
                value={meData?.userId || user?.id}
                mono
              />
            </div>
          </div>

          {/* ────────────────────────────────────────────────────────────
              RIGHT COLUMN — Stats + Plans
          ──────────────────────────────────────────────────────────── */}
          <div className="lg:col-span-2 space-y-6">
            {/* ── Plan statistics ─────────────────────────────────────── */}
            <div>
              <h2 className="text-base font-semibold text-slate-200 mb-4
                             flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-slate-400" />
                Plan Statistics
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <StatCard
                  icon={Zap}
                  label="Total Plans"
                  value={totalPlans}
                  color="blue"
                />
                <StatCard
                  icon={CheckCircle}
                  label="Completed"
                  value={completedPlans}
                  color="emerald"
                />
                <StatCard
                  icon={Clock}
                  label="Pending"
                  value={pendingPlans}
                  color="amber"
                />
                <StatCard
                  icon={Activity}
                  label="In Progress"
                  value={plans.filter((p) => p.status === "processing").length}
                  color="purple"
                />
              </div>
            </div>

            {/* ── Summary banner ──────────────────────────────────────── */}
            {completedPlans > 0 && (
              <div
                className="rounded-2xl bg-linear-to-br from-emerald-500/15
                            to-blue-500/10 border border-emerald-500/20 p-6"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-10 h-10 rounded-xl bg-emerald-500/15
                                flex items-center justify-center"
                  >
                    <Sun className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-100">
                      You&apos;re on the right track!
                    </h3>
                    <p className="text-xs text-slate-400">
                      {completedPlans} plan{completedPlans > 1 ? "s" : ""}{" "}
                      optimized successfully
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    {
                      icon: Battery,
                      label: "Systems Designed",
                      value: completedPlans,
                      color: "text-purple-400",
                    },
                    {
                      icon: TrendingDown,
                      label: "Plans Saved",
                      value: totalPlans,
                      color: "text-emerald-400",
                    },
                    {
                      icon: Leaf,
                      label: "CO₂ Offset Plans",
                      value: completedPlans,
                      color: "text-cyan-400",
                    },
                  ].map(({ icon: Icon, label, value, color }) => (
                    <div
                      key={label}
                      className="bg-slate-900/40 rounded-xl p-3 text-center"
                    >
                      <Icon className={`w-5 h-5 mx-auto mb-1.5 ${color}`} />
                      <p className="text-lg font-black text-slate-100">
                        {value}
                      </p>
                      <p className="text-xs text-slate-500">{label}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Recent plans ────────────────────────────────────────── */}
            <div
              className="rounded-2xl border border-slate-700/50 bg-slate-800/50
                          overflow-hidden"
            >
              {/* Header */}
              <div
                className="flex items-center justify-between px-5 py-4
                            border-b border-slate-700/50"
              >
                <h3 className="text-sm font-semibold text-slate-200
                               flex items-center gap-2">
                  <Clock className="w-4 h-4 text-slate-400" />
                  Recent Plans
                </h3>
                {plans.length > 5 && (
                  <button
                    onClick={() => router.push("/plans")}
                    className="text-xs text-emerald-400 hover:text-emerald-300
                               flex items-center gap-1 transition-colors"
                  >
                    View all{" "}
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Body */}
              <div className="p-3">
                {plansLoading ? (
                  /* skeleton rows */
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="h-14 rounded-xl bg-slate-800/80 animate-pulse"
                      />
                    ))}
                  </div>
                ) : recentPlans.length === 0 ? (
                  /* empty state */
                  <div className="py-10 text-center">
                    <div
                      className="w-12 h-12 rounded-2xl bg-slate-800 flex
                                  items-center justify-center mx-auto mb-3"
                    >
                      <Zap className="w-6 h-6 text-slate-600" />
                    </div>
                    <p className="text-slate-400 text-sm font-medium mb-1">
                      No plans yet
                    </p>
                    <p className="text-slate-600 text-xs mb-4">
                      Create your first energy optimization plan
                    </p>
                    <button
                      onClick={() => router.push("/plans/new")}
                      className="inline-flex items-center gap-2 px-4 py-2
                                 bg-emerald-500 hover:bg-emerald-600 text-white
                                 font-medium text-xs rounded-xl transition-all
                                 shadow-lg shadow-emerald-500/25"
                    >
                      <Sun className="w-3.5 h-3.5" />
                      Create First Plan
                    </button>
                  </div>
                ) : (
                  /* plan rows */
                  <div className="space-y-1">
                    {recentPlans.map((plan) => (
                      <PlanRow key={plan.planId} plan={plan} />
                    ))}
                  </div>
                )}
              </div>

              {/* Footer CTA */}
              {recentPlans.length > 0 && (
                <div className="px-5 py-3 border-t border-slate-700/50
                                bg-slate-900/30">
                  <button
                    onClick={() => router.push("/plans/new")}
                    className="w-full flex items-center justify-center gap-2
                               py-2.5 rounded-xl bg-emerald-500/10
                               hover:bg-emerald-500/20 border border-emerald-500/20
                               text-emerald-400 text-sm font-medium transition-all"
                  >
                    <Sun className="w-4 h-4" />
                    Create New Plan
                  </button>
                </div>
              )}
            </div>

            {/* ── Tips card ───────────────────────────────────────────── */}
            <div
              className="rounded-2xl bg-blue-500/5 border border-blue-500/15
                          p-5"
            >
              <h3 className="text-sm font-semibold text-blue-400 mb-3
                             flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Tips to Get the Best Results
              </h3>
              <ul className="space-y-2">
                {[
                  "Upload at least 12 months of electricity bills for accurate optimization",
                  "Make sure your roof area is measured accurately — it directly affects solar capacity",
                  "Check live predictions regularly to see real-time solar and battery recommendations",
                  "Re-run optimization after uploading newer bills to keep results up to date",
                ].map((tip, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-xs
                                         text-slate-400 leading-relaxed">
                    <CheckCircle
                      className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5"
                    />
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}