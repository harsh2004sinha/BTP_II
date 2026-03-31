"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { predictionApi } from "@/lib/predictionApi";
import { plansApi } from "@/lib/plansApi";
import { PredictionChart } from "@/components/charts/PredictionChart";
import { SolarOutputChart } from "@/components/charts/SolarOutputChart";
import { getErrorMessage, formatNumber } from "@/lib/utils";
import toast from "react-hot-toast";
import {
  Activity, RefreshCw, ChevronLeft, Sun,
  Battery, Zap, DollarSign, TrendingUp,
  TrendingDown, Wifi, WifiOff, Clock,
  BarChart3, Info, AlertCircle, Play, Pause,
} from "lucide-react";

/* ─────────────────────────────────────────────────────────────────────────
   Action pill
───────────────────────────────────────────────────────────────────────── */
const ACTION_CONFIG = {
  use_solar: {
    label: "Use Solar",
    color: "bg-amber-500/20 border-amber-500/30 text-amber-300",
    dot:   "bg-amber-400",
    icon:  Sun,
  },
  charge_battery: {
    label: "Charging Battery",
    color: "bg-purple-500/20 border-purple-500/30 text-purple-300",
    dot:   "bg-purple-400",
    icon:  Battery,
  },
  use_grid: {
    label: "Using Grid",
    color: "bg-blue-500/20 border-blue-500/30 text-blue-300",
    dot:   "bg-blue-400",
    icon:  Zap,
  },
  sell_power: {
    label: "Selling Power",
    color: "bg-emerald-500/20 border-emerald-500/30 text-emerald-300",
    dot:   "bg-emerald-400",
    icon:  TrendingUp,
  },
  idle: {
    label: "Idle",
    color: "bg-slate-700/60 border-slate-600/40 text-slate-400",
    dot:   "bg-slate-500",
    icon:  Activity,
  },
};

function ActionBadge({ action }) {
  const cfg = ACTION_CONFIG[action] ?? ACTION_CONFIG.idle;
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full
                  text-sm font-semibold border ${cfg.color}`}
    >
      <span className={`w-2 h-2 rounded-full animate-pulse ${cfg.dot}`} />
      <Icon className="w-3.5 h-3.5" />
      {cfg.label}
    </span>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Live metric card
───────────────────────────────────────────────────────────────────────── */
function LiveMetric({ icon: Icon, label, value, unit, color, subLabel }) {
  const colorMap = {
    amber:   "bg-amber-500/10   border-amber-500/20   text-amber-400",
    purple:  "bg-purple-500/10  border-purple-500/20  text-purple-400",
    blue:    "bg-blue-500/10    border-blue-500/20    text-blue-400",
    emerald: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
    rose:    "bg-rose-500/10    border-rose-500/20    text-rose-400",
  };

  return (
    <div className={`rounded-2xl border p-5 ${colorMap[color]}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="w-9 h-9 rounded-xl bg-slate-900/40 flex items-center
                        justify-center">
          <Icon className="w-4 h-4" />
        </div>
        <span className="text-xs text-slate-600 font-medium">LIVE</span>
      </div>
      <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
        {label}
      </p>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-black text-slate-100">
          {value ?? "—"}
        </span>
        {unit && <span className="text-sm text-slate-400">{unit}</span>}
      </div>
      {subLabel && (
        <p className="text-xs text-slate-500 mt-1">{subLabel}</p>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Hourly table row
───────────────────────────────────────────────────────────────────────── */
function HourRow({ pred, isNow }) {
  const cfg = ACTION_CONFIG[pred.action] ?? ACTION_CONFIG.idle;
  const hour = pred.time
    ? new Date(pred.time).getHours().toString().padStart(2, "0") + ":00"
    : "—";

  return (
    <tr
      className={`border-b border-slate-800/50 transition-colors
        ${isNow
          ? "bg-emerald-500/8 border-emerald-500/20"
          : "hover:bg-slate-800/30"
        }`}
    >
      <td className="px-4 py-3 text-sm font-mono text-slate-300">
        {hour}
        {isNow && (
          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full
                           bg-emerald-500/20 text-emerald-400 font-sans
                           font-semibold">
            NOW
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-amber-300 font-medium">
        {formatNumber(pred.solar_kW)} kW
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden
                          max-w-15">
            <div
              className="h-full rounded-full bg-purple-500 transition-all"
              style={{ width: `${Math.min(100, pred.batterySOC || 0)}%` }}
            />
          </div>
          <span className="text-sm text-slate-300 font-medium tabular-nums">
            {formatNumber(pred.batterySOC, 0)}%
          </span>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-rose-300 font-medium">
        RM {formatNumber(pred.gridCost, 3)}
      </td>
      <td className="px-4 py-3 text-sm text-slate-300">
        {formatNumber(pred.consumption)} kW
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                      text-xs font-medium border ${cfg.color}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
          {cfg.label}
        </span>
      </td>
    </tr>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Main page
───────────────────────────────────────────────────────────────────────── */
export default function PredictionPage() {
  const { planId } = useParams();
  const router     = useRouter();

  const [plan, setPlan]               = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading]         = useState(true);
  const [refreshing, setRefreshing]   = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [isOnline, setIsOnline]       = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError]             = useState(null);
  const [activeTab, setActiveTab]     = useState("overview");
  const intervalRef                   = useRef(null);

  /* ── fetch predictions ──────────────────────────────────────────────── */
  const fetchPredictions = useCallback(
    async (silent = false) => {
      if (!silent) setRefreshing(true);
      setIsOnline(true);
      try {
        const [planRes, predRes] = await Promise.allSettled([
          plansApi.getPlan(planId),
          predictionApi.getPrediction(planId, 24),
        ]);

        if (planRes.status === "fulfilled" && planRes.value.success) {
          setPlan(planRes.value.data);
        }

        if (predRes.status === "fulfilled" && predRes.value.success) {
          setPredictions(predRes.value.data?.predictions || []);
          setLastUpdated(new Date());
          setError(null);
        } else if (predRes.status === "rejected") {
          throw predRes.reason;
        }
      } catch (err) {
        setIsOnline(false);
        if (!silent) {
          setError(getErrorMessage(err));
          toast.error("Could not fetch predictions");
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [planId]
  );

  /* ── manual refresh ─────────────────────────────────────────────────── */
  async function handleRefresh() {
    setRefreshing(true);
    try {
      await predictionApi.refreshPrediction(planId);
      await fetchPredictions();
      toast.success("Predictions refreshed with latest weather data");
    } catch (err) {
      toast.error(getErrorMessage(err));
      setRefreshing(false);
    }
  }

  /* ── initial load ───────────────────────────────────────────────────── */
  useEffect(() => {
    fetchPredictions();
  }, [fetchPredictions]);

  /* ── auto-refresh every 30 s ────────────────────────────────────────── */
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(
        () => fetchPredictions(true),
        30_000
      );
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [autoRefresh, fetchPredictions]);

  /* ── current hour data ──────────────────────────────────────────────── */
  const currentHour = new Date().getHours();
  const currentPred = predictions.find((p) => {
    if (!p.time) return false;
    return new Date(p.time).getHours() === currentHour;
  }) ?? predictions[0];

  /* ── chart-ready solar data ─────────────────────────────────────────── */
  const solarChartData = predictions.map((p) => ({
    hour:     p.time ? new Date(p.time).getHours() + ":00" : "—",
    solar_kW: Number(p.solar_kW || 0),
  }));

  /* ── derive today's totals ──────────────────────────────────────────── */
  const totalSolar  = predictions.reduce((s, p) => s + (p.solar_kW || 0), 0);
  const totalCost   = predictions.reduce((s, p) => s + (p.gridCost || 0), 0);
  const peakSolar   = Math.max(...predictions.map((p) => p.solar_kW || 0));
  const avgBattery  = predictions.length
    ? predictions.reduce((s, p) => s + (p.batterySOC || 0), 0) / predictions.length
    : 0;

  /* ── loading ────────────────────────────────────────────────────────── */
  if (loading) {
    return (
      <DashboardLayout>
        <div className="max-w-6xl mx-auto">
          <div className="h-7 w-44 bg-slate-800 rounded-xl mb-6 animate-pulse" />
          <div className="h-10 w-60 bg-slate-800 rounded-xl mb-8 animate-pulse" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-28 bg-slate-800 rounded-2xl animate-pulse" />
            ))}
          </div>
          <div className="h-80 bg-slate-800 rounded-2xl animate-pulse mb-4" />
          <div className="h-60 bg-slate-800 rounded-2xl animate-pulse" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto page-enter">

        {/* Back */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300
                     text-sm mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Results
        </button>

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center
                        justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h1 className="text-2xl font-bold text-slate-100">
                Live Predictions
              </h1>
              {/* Online / offline dot */}
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1
                            rounded-full text-xs font-medium border
                            ${isOnline
                              ? "bg-emerald-500/15 border-emerald-500/25 text-emerald-400"
                              : "bg-red-500/15 border-red-500/25 text-red-400"
                            }`}
              >
                {isOnline
                  ? <><Wifi className="w-3 h-3" /> Live</>
                  : <><WifiOff className="w-3 h-3" /> Offline</>
                }
              </span>
            </div>
            <div className="flex items-center gap-3 text-sm text-slate-500
                            flex-wrap">
              <span>{plan?.location || "—"}</span>
              {lastUpdated && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Updated {lastUpdated.toLocaleTimeString("en-MY", {
                    hour: "2-digit", minute: "2-digit",
                  })}
                </span>
              )}
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            {/* Auto-refresh toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl
                          border text-sm font-medium transition-all
                          ${autoRefresh
                            ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                            : "bg-slate-800 border-slate-700 text-slate-400"
                          }`}
            >
              {autoRefresh
                ? <><Play className="w-3.5 h-3.5" /> Auto</>
                : <><Pause className="w-3.5 h-3.5" /> Paused</>
              }
            </button>

            {/* Manual refresh */}
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl
                         border border-slate-700 text-slate-400
                         hover:text-slate-200 hover:bg-slate-800
                         text-sm font-medium transition-all
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </button>
          </div>
        </div>

        {/* ── Error ───────────────────────────────────────────────────── */}
        {error && (
          <div className="rounded-2xl bg-red-500/10 border border-red-500/20
                          p-4 flex items-center gap-3 mb-6">
            <AlertCircle className="w-5 h-5 text-red-" />
            <p className="text-sm text-red-300">{error}</p>
            <button
              onClick={() => fetchPredictions()}
              className="ml-auto text-xs text-red-400 hover:text-red-300
                         underline underline-offset-2 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* ── Current hour action ─────────────────────────────────────── */}
        {currentPred && (
          <div className="rounded-2xl bg-linear-to-br from-slate-800/80
                          to-slate-900/50 border border-slate-700/50 p-5 mb-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
                  Current Recommendation
                </p>
                <ActionBadge action={currentPred.action} />
              </div>
              <div className="flex items-center gap-6 flex-wrap">
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Solar Now</p>
                  <p className="text-xl font-bold text-amber-400">
                    {formatNumber(currentPred.solar_kW)} kW
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Battery SOC</p>
                  <p className="text-xl font-bold text-purple-400">
                    {formatNumber(currentPred.batterySOC, 0)}%
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Grid Cost</p>
                  <p className="text-xl font-bold text-rose-400">
                    RM {formatNumber(currentPred.gridCost, 3)}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Load</p>
                  <p className="text-xl font-bold text-slate-200">
                    {formatNumber(currentPred.consumption)} kW
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── 24-hour summary stats ────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <LiveMetric
            icon={Sun}
            label="Total Solar Today"
            value={formatNumber(totalSolar)}
            unit="kWh"
            color="amber"
            subLabel="Forecasted generation"
          />
          <LiveMetric
            icon={TrendingDown}
            label="Total Grid Cost"
            value={`RM ${formatNumber(totalCost, 2)}`}
            color="rose"
            subLabel="Estimated for today"
          />
          <LiveMetric
            icon={Zap}
            label="Peak Solar Output"
            value={formatNumber(peakSolar)}
            unit="kW"
            color="emerald"
            subLabel="Maximum generation"
          />
          <LiveMetric
            icon={Battery}
            label="Avg Battery SOC"
            value={formatNumber(avgBattery, 0)}
            unit="%"
            color="purple"
            subLabel="Daily average"
          />
        </div>

        {/* ── Tab bar ─────────────────────────────────────────────────── */}
        <div className="flex gap-1 p-1 rounded-xl bg-slate-800/60 border
                        border-slate-700/50 mb-6 w-fit">
          {[
            { key: "overview", label: "Overview", icon: BarChart3 },
            { key: "solar",    label: "Solar Output", icon: Sun   },
            { key: "table",    label: "Hourly Data",  icon: Clock },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg
                          text-sm font-medium transition-all
                          ${activeTab === key
                            ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/25"
                            : "text-slate-400 hover:text-slate-200"
                          }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* ── Overview tab ────────────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div className="rounded-2xl border border-slate-700/50
                          bg-slate-800/50 p-6">
            <h2 className="text-base font-semibold text-slate-200
                           flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-slate-400" />
              24-Hour Energy Overview
            </h2>
            <p className="text-xs text-slate-500 mb-5">
              Solar generation, battery state-of-charge, load, and grid import
            </p>
            {predictions.length > 0 ? (
              <PredictionChart data={predictions} />
            ) : (
              <div className="h-72 flex flex-col items-center justify-center gap-3">
                <Activity className="w-10 h-10 text-slate-700" />
                <p className="text-slate-500 text-sm">No prediction data available</p>
                <button
                  onClick={handleRefresh}
                  className="text-xs text-emerald-400 hover:text-emerald-300
                             underline underline-offset-2 transition-colors"
                >
                  Generate predictions
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Solar output tab ────────────────────────────────────────── */}
        {activeTab === "solar" && (
          <div className="rounded-2xl border border-slate-700/50
                          bg-slate-800/50 p-6">
            <h2 className="text-base font-semibold text-slate-200
                           flex items-center gap-2 mb-1">
              <Sun className="w-4 h-4 text-amber-400" />
              Hourly Solar Output
            </h2>
            <p className="text-xs text-slate-500 mb-5">
              Expected PV generation for each hour of the day
            </p>
            {solarChartData.length > 0 ? (
              <SolarOutputChart data={solarChartData} />
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-slate-500 text-sm">No solar data available</p>
              </div>
            )}

            {/* Peak info */}
            {peakSolar > 0 && (
              <div className="mt-5 flex flex-wrap gap-4">
                <div className="flex items-center gap-3 bg-amber-500/8
                                border border-amber-500/15 rounded-xl p-3 flex-1">
                  <Sun className="w-5 h-5 text-amber-" />
                  <div>
                    <p className="text-xs text-slate-500">Peak Generation</p>
                    <p className="font-bold text-amber-400">
                      {formatNumber(peakSolar)} kW
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 bg-emerald-500/8
                                border border-emerald-500/15 rounded-xl p-3 flex-1">
                  <Zap className="w-5 h-5 text-emerald-" />
                  <div>
                    <p className="text-xs text-slate-500">Total Generation</p>
                    <p className="font-bold text-emerald-400">
                      {formatNumber(totalSolar)} kWh
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Hourly table tab ────────────────────────────────────────── */}
        {activeTab === "table" && (
          <div className="rounded-2xl border border-slate-700/50
                          bg-slate-800/50 overflow-hidden">
            <div className="p-5 border-b border-slate-700/50">
              <h2 className="text-base font-semibold text-slate-200
                             flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-400" />
                Hourly Prediction Data
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {predictions.length} hours · Next 24 hours forecast
              </p>
            </div>

            {predictions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-slate-700/50 bg-slate-900/40">
                      {[
                        "Hour", "Solar (kW)", "Battery SOC",
                        "Grid Cost", "Load (kW)", "Action",
                      ].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-xs font-semibold text-slate-500
                                     uppercase tracking-wider whitespace-nowrap"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.map((pred, i) => {
                      const isNow =
                        pred.time &&
                        new Date(pred.time).getHours() === currentHour;
                      return (
                        <HourRow key={i} pred={pred} isNow={isNow} />
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-16 text-center">
                <Clock className="w-10 h-10 text-slate-700 mx-auto mb-3" />
                <p className="text-slate-500 text-sm">No hourly data available</p>
              </div>
            )}
          </div>
        )}

        {/* ── Info footer ─────────────────────────────────────────────── */}
        <div className="rounded-2xl bg-blue-500/5 border border-blue-500/15
                        p-4 flex gap-3 mt-6">
          <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-400 leading-relaxed">
            Predictions are generated using real-time solar irradiance data,
            TNB Time-of-Use tariff schedule, and your consumption profile.
            Auto-refresh is every 30 seconds.
            {autoRefresh
              ? " Auto-refresh is ON."
              : " Auto-refresh is currently paused."
            }
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}