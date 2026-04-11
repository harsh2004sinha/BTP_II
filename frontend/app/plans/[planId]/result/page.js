"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { resultsApi } from "@/lib/resultsApi";
import { plansApi } from "@/lib/plansApi";
import { uploadApi } from "@/lib/uploadApi";
import { CostChart } from "@/components/charts/CostChart";
import { ConsumptionChart } from "@/components/charts/ConsumptionChart";
import { getErrorMessage, formatCurrency, formatNumber } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/Badge";
import toast from "react-hot-toast";
import {
  Sun, Battery, TrendingDown, Clock, Leaf,
  Zap, BarChart3, Activity, RefreshCw,
  ChevronLeft, Play, AlertCircle, Info,
  CheckCircle, DollarSign, ArrowRight,
  MapPin, Calendar,
} from "lucide-react";

/* ─────────────────────────────────────────────────────────────────────────
   Sub-components
───────────────────────────────────────────────────────────────────────── */

function ResultStat({ icon: Icon, label, value, unit, color, sub }) {
  const colorMap = {
    emerald: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
    amber:   "bg-amber-500/10  border-amber-500/20  text-amber-400",
    blue:    "bg-blue-500/10   border-blue-500/20   text-blue-400",
    purple:  "bg-purple-500/10 border-purple-500/20 text-purple-400",
    rose:    "bg-rose-500/10   border-rose-500/20   text-rose-400",
    cyan:    "bg-cyan-500/10   border-cyan-500/20   text-cyan-400",
  };

  return (
    <div className={`rounded-2xl border p-5 ${colorMap[color]}`}>
      <div className="w-10 h-10 rounded-xl bg-slate-900/40 flex items-center
                      justify-center mb-3">
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-xs text-slate-400 uppercase tracking-wider mb-1.5">
        {label}
      </p>
      <div className="flex items-baseline gap-1 flex-wrap">
        <span className="text-2xl font-black text-slate-100">{value ?? "—"}</span>
        {unit && <span className="text-sm text-slate-400">{unit}</span>}
      </div>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

function ProcessingBanner() {
  return (
    <div className="rounded-3xl bg-linear-to-br from-purple-500/15
                    to-blue-500/10 border border-purple-500/20 p-10 text-center mb-6">
      <div className="w-16 h-16 rounded-2xl bg-purple-500/15 flex items-center
                      justify-center mx-auto mb-5">
        <RefreshCw className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
      <h2 className="text-xl font-bold text-slate-100 mb-2">
        Running Optimization…
      </h2>
      <p className="text-slate-400 text-sm max-w-sm mx-auto leading-relaxed">
        Our algorithm is calculating the optimal solar + battery configuration
        using your consumption data and local weather data. This takes
        10–30 seconds.
      </p>
      <div className="flex justify-center gap-2 mt-6">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full bg-purple-400 animate-bounce"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </div>
    </div>
  );
}

function SkeletonLoader() {
  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto">
        <div className="h-7 w-44 bg-slate-800 rounded-xl mb-6 animate-pulse" />
        <div className="h-10 w-64 bg-slate-800 rounded-xl mb-2 animate-pulse" />
        <div className="h-4 w-48 bg-slate-800 rounded-xl mb-8 animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-32 bg-slate-800 rounded-2xl animate-pulse" />
          ))}
        </div>
        <div className="h-72 bg-slate-800 rounded-2xl animate-pulse mb-4" />
        <div className="h-40 bg-slate-800 rounded-2xl animate-pulse" />
      </div>
    </DashboardLayout>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   Main Page
───────────────────────────────────────────────────────────────────────── */
export default function ResultPage() {
  const { planId } = useParams();
  const router     = useRouter();

  const [plan, setPlan]               = useState(null);
  const [result, setResult]           = useState(null);
  const [consumption, setConsumption] = useState([]);
  const [loading, setLoading]         = useState(true);
  const [optimizing, setOptimizing]   = useState(false);
  const [polling, setPolling]         = useState(false);
  const [error, setError]             = useState(null);

  /* ── initial fetch ──────────────────────────────────────────────────── */
  const fetchData = useCallback(async () => {
    setError(null);
    try {
      const [planRes, consumptionRes] = await Promise.allSettled([
        plansApi.getPlan(planId),
        uploadApi.getConsumption(planId),
      ]);

      if (planRes.status === "fulfilled" && planRes.value.success) {
        setPlan(planRes.value.data);
      }

      if (consumptionRes.status === "fulfilled" && consumptionRes.value.success) {
        const records = consumptionRes.value.data?.records || [];
        setConsumption(
          records.map((r) => ({
            month: r.month || r.date?.slice(0, 7) || "—",
            units: Number(r.units || 0),
          }))
        );
      }

      /* try result — 404 means not run yet */
      try {
        const resResult = await resultsApi.getResult(planId);
        if (resResult.success) {
          if (resResult.data?.status === "processing") {
            setPolling(true);
          } else if (resResult.data?.status === "completed") {
            setResult(resResult.data);
            setPolling(false);
          } else {
            setResult(null);
            setPolling(false);
          }
        }
      } catch (err) {
        if (err?.response?.status !== 404) {
          console.warn("Result fetch error:", err);
        }
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [planId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  /* ── poll while processing ──────────────────────────────────────────── */
  useEffect(() => {
    if (!polling) return;

    const id = setInterval(async () => {
      try {
        const res = await resultsApi.getResult(planId);
        if (res.success && res.data?.status === "completed") {
          setResult(res.data);
          setPlan((prev) => prev ? { ...prev, status: res.data.status } : prev);
          setPolling(false);
          clearInterval(id);
          toast.success("Optimization complete! 🎉");
        } else if (res.success && res.data?.status === "failed") {
          setPolling(false);
          setPlan((prev) => prev ? { ...prev, status: "failed" } : prev);
          clearInterval(id);
          toast.error("Optimization failed. Try again or check server logs.");
        }
      } catch { /* still running */ }
    }, 4000);

    return () => clearInterval(id);
  }, [polling, planId]);

  /* ── trigger optimization ───────────────────────────────────────────── */
  async function handleOptimize() {
    setOptimizing(true);
    try {
      const res = await resultsApi.runOptimization(planId);
      if (res.success) {
        setPolling(true);
        setResult(null);
        setPlan((prev) => prev ? { ...prev, status: "processing" } : prev);
        toast.success("Optimization started!");
      } else {
        toast.error(res.message || "Could not start optimization");
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setOptimizing(false);
    }
  }

  /* ── states ─────────────────────────────────────────────────────────── */
  if (loading) return <SkeletonLoader />;

  if (error) {
    return (
      <DashboardLayout>
        <div className="max-w-5xl mx-auto page-enter">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300
                       text-sm mb-6 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </button>
          <div className="rounded-2xl bg-red-500/10 border border-red-500/20
                          p-8 flex items-center gap-4">
            <AlertCircle className="w-8 h-8 text-red-" />
            <div>
              <p className="font-semibold text-red-400 mb-1">Error Loading Page</p>
              <p className="text-sm text-slate-400">{error}</p>
              <button
                onClick={fetchData}
                className="mt-3 text-sm text-emerald-400 hover:text-emerald-300
                           underline underline-offset-2 transition-colors"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const noBill       = plan?.status === "pending";
  const hasBill      = ["bill_uploaded", "completed", "failed"].includes(plan?.status);
  const isProcessing = polling || plan?.status === "processing";
  const isDone       = !!result && plan?.status === "completed";

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto page-enter">

        {/* Back */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300
                     text-sm mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Plans
        </button>

        {/* ── Page header ─────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-start
                        justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h1 className="text-2xl font-bold text-slate-100">
                Optimization Results
              </h1>
              {plan && <StatusBadge status={plan.status} />}
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm text-slate-500">
              <span className="flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5" />
                {plan?.location || "—"}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                {plan?.createdAt
                  ? new Date(plan.createdAt).toLocaleDateString("en-MY", {
                      day: "2-digit", month: "short", year: "numeric",
                    })
                  : "—"
                }
              </span>
              <span className="font-mono text-xs text-slate-600">
                #{planId?.slice(0, 8)}
              </span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center ga">
            <button
              onClick={fetchData}
              title="Refresh"
              className="p-2.5 rounded-xl border border-slate-700 text-slate-400
                         hover:text-slate-200 hover:bg-slate-800 transition-all"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {isDone && (
              <button
                onClick={() => router.push(`/plans/${planId}/prediction`)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                           bg-purple-500/15 border border-purple-500/30
                           text-purple-400 hover:bg-purple-500/25
                           font-medium text-sm transition-all"
              >
                <Activity className="w-4 h-4" />
                Live Prediction
              </button>
            )}

            {hasBill && !isProcessing && (
              <button
                onClick={handleOptimize}
                disabled={optimizing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                           bg-emerald-500 hover:bg-emerald-600 text-white
                           font-medium text-sm transition-all shadow-lg
                           shadow-emerald-500/25 disabled:opacity-60
                           disabled:cursor-not-allowed"
              >
                {optimizing ? (
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {isDone ? "Re-Optimize" : "Run Optimization"}
              </button>
            )}
          </div>
        </div>

        {/* ── No bill yet ─────────────────────────────────────────────── */}
        {noBill && (
          <div className="rounded-3xl border border-amber-500/20
                          bg-amber-500/5 p-10 text-center mb-6">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/10
                            flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-7 h-7 text-amber-400" />
            </div>
            <h2 className="text-lg font-bold text-slate-100 mb-2">
              Upload Your Electricity Bill First
            </h2>
            <p className="text-slate-400 text-sm mb-6 max-w-sm mx-auto
                          leading-relaxed">
              We need your monthly consumption data before running the
              optimization algorithm.
            </p>
            <button
              onClick={() => router.push(`/plans/${planId}/upload`)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-amber-500
                         hover:bg-amber-600 text-white font-semibold text-sm
                         rounded-xl transition-all shadow-lg shadow-amber-500/25"
            >
              Upload Bill <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ── Processing ──────────────────────────────────────────────── */}
        {isProcessing && <ProcessingBanner />}

        {/* ── Consumption chart ───────────────────────────────────────── */}
        {consumption.length > 0 && (
          <div className="rounded-2xl border border-slate-700/50
                          bg-slate-800/50 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-slate-200
                               flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-slate-400" />
                  Monthly Consumption
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Extracted from your uploaded electricity bill
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500">Total records</p>
                <p className="text-lg font-bold text-slate-200">
                  {consumption.length}
                </p>
              </div>
            </div>
            <ConsumptionChart data={consumption} />
          </div>
        )}

        {/* ── Bill uploaded but no result yet ─────────────────────────── */}
        {hasBill && !isDone && !isProcessing && (
          <div className="rounded-3xl border border-blue-500/20 bg-blue-500/5
                          p-8 text-center mb-6">
            <div className="w-14 h-14 rounded-2xl bg-blue-500/10
                            flex items-center justify-center mx-auto mb-4">
              <Zap className="w-7 h-7 text-blue-400" />
            </div>
            <h2 className="text-lg font-bold text-slate-100 mb-2">
              Ready to Optimize
            </h2>
            <p className="text-slate-400 text-sm mb-6 max-w-sm mx-auto
                          leading-relaxed">
              Your bill has been processed. Click below to run the optimization
              algorithm and get your solar + battery recommendation.
            </p>
            <button
              onClick={handleOptimize}
              disabled={optimizing}
              className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-500
                         hover:bg-emerald-600 text-white font-semibold text-sm
                         rounded-xl transition-all shadow-lg shadow-emerald-500/25
                         disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {optimizing ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Starting...
                </>
              ) : (
                <><Play className="w-4 h-4" /> Run Optimization</>
              )}
            </button>
          </div>
        )}

        {/* ── Results section ─────────────────────────────────────────── */}
        {isDone && (
          <>
            {/* KPI cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              <ResultStat
                icon={Sun}
                label="Solar Capacity"
                value={formatNumber(result.solarSize_kW)}
                unit="kW"
                color="amber"
                sub="Recommended panel size"
              />
              <ResultStat
                icon={Battery}
                label="Battery Storage"
                value={formatNumber(result.batterySize_kWh)}
                unit="kWh"
                color="purple"
                sub="Energy storage capacity"
              />
              <ResultStat
                icon={Clock}
                label="Payback Period"
                value={formatNumber(result.roi_years)}
                unit="yrs"
                color="blue"
                sub="Return on investment"
              />
              <ResultStat
                icon={TrendingDown}
                label="Annual Savings"
                value={formatCurrency(result.annualSaving)}
                color="emerald"
                sub="Estimated savings / year"
              />
              <ResultStat
                icon={DollarSign}
                label="System Cost"
                value={formatCurrency(result.totalCost)}
                color="rose"
                sub="Total installation cost"
              />
              <ResultStat
                icon={Leaf}
                label="CO₂ Reduction"
                value={formatNumber(result.co2Reduction_kg, 0)}
                unit="kg/yr"
                color="cyan"
                sub="Annual carbon offset"
              />
            </div>

            {/* Hero summary banner */}
            <div className="rounded-2xl bg-linear-to-br from-emerald-500/15
                            to-blue-500/10 border border-emerald-500/20 p-6 mb-6">
              <div className="flex items-center gap-3 mb-5">
                <CheckCircle className="w-6 h-6 text-emerald-" />
                <h3 className="font-bold text-slate-100 text-lg">
                  Your Optimized Energy Plan
                </h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div className="text-center">
                  <p className="text-4xl font-black text-emerald-400">
                    {formatNumber(result.solarSize_kW)}<span className="text-xl"> kW</span>
                  </p>
                  <p className="text-sm text-slate-400 mt-1.5">Solar PV System</p>
                </div>
                <div className="text-center sm:border-l sm:border-r
                                border-slate-700/50">
                  <p className="text-4xl font-black text-amber-400">
                    {formatNumber(result.roi_years)}<span className="text-xl"> yrs</span>
                  </p>
                  <p className="text-sm text-slate-400 mt-1.5">Payback Period</p>
                </div>
                <div className="text-center">
                  <p className="text-4xl font-black text-blue-400">
                    {formatCurrency(result.annualSaving)}
                  </p>
                  <p className="text-sm text-slate-400 mt-1.5">Saved Per Year</p>
                </div>
              </div>
            </div>

            {/* Cost comparison chart */}
            {result.graphData && (
              <div className="rounded-2xl border border-slate-700/50
                              bg-slate-800/50 p-6 mb-6">
                <h2 className="text-base font-semibold text-slate-200
                               flex items-center gap-2 mb-1">
                  <TrendingDown className="w-4 h-4 text-slate-400" />
                  Monthly Cost Comparison
                </h2>
                <p className="text-xs text-slate-500 mb-5">
                  Grid-only electricity bill vs. Solar + Battery system
                </p>
                <CostChart graphData={result.graphData} />
              </div>
            )}

            {/* Annual generation */}
            {result.annualGeneration != null && (
              <div className="rounded-2xl border border-slate-700/50
                              bg-slate-800/50 p-5 mb-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-amber-500/10
                                  border border-amber-500/20 flex items-center
                                  justify-cen">
                    <Zap className="w-6 h-6 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">
                      Annual Solar Generation
                    </p>
                    <p className="text-2xl font-bold text-slate-100">
                      {formatNumber(result.annualGeneration, 0)}{" "}
                      <span className="text-base font-normal text-slate-400">
                        kWh / year
                      </span>
                    </p>
                  </div>
                  <div className="ml-auto text-right">
                    <p className="text-xs text-slate-500 mb-0.5">
                      Last updated
                    </p>
                    <p className="text-xs text-slate-400">
                      {result.createdAt
                        ? new Date(result.createdAt).toLocaleDateString("en-MY", {
                            day: "2-digit", month: "short", year: "numeric",
                          })
                        : "—"
                      }
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Info + CTA row */}
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 rounded-2xl bg-blue-500/5 border
                              border-blue-500/15 p-4 flex gap-3">
                <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-400 leading-relaxed">
                  Results are calculated using your consumption history,
                  solar irradiance data for your location, and TNB
                  Time-of-Use tariffs. Re-run optimization anytime to
                  get updated figures.
                </p>
              </div>

              <button
                onClick={() => router.push(`/plans/${planId}/prediction`)}
                className="sm:w-56 flex items-center justify-center gap-2
                           px-5 py-4 rounded-2xl bg-purple-500/15 border
                           border-purple-500/30 text-purple-400
                           hover:bg-purple-500/25 font-medium text-sm
                           transition-all"
              >
                <Activity className="w-4 h-4" />
                View Live Predictions
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}