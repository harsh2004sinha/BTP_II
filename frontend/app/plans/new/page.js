"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { plansApi } from "@/lib/plansApi";
import { getErrorMessage } from "@/lib/utils";
import toast from "react-hot-toast";
import {
  MapPin, ChevronLeft, Info, PlusCircle,
  DollarSign, Home, Zap, CheckCircle,
} from "lucide-react";

const LOCATIONS = [
  "Kuala Lumpur, Malaysia",
  "Petaling Jaya, Selangor",
  "Shah Alam, Selangor",
  "Johor Bahru, Johor",
  "Georgetown, Penang",
  "Kota Kinabalu, Sabah",
  "Kuching, Sarawak",
  "Ipoh, Perak",
  "Alor Setar, Kedah",
  "Kota Bharu, Kelantan",
  "Seremban, Negeri Sembilan",
  "Melaka, Malaysia",
  "Putrajaya, Malaysia",
  "Cyberjaya, Selangor",
  "Subang Jaya, Selangor",
];

const BUDGET_PRESETS  = [15000, 25000, 40000, 60000];
const ROOFAREA_PRESETS = [20, 40, 60, 100];

const STEP_LIST = [
  { n: 1, label: "Plan Setup"  },
  { n: 2, label: "Upload Bill" },
  { n: 3, label: "Optimize"   },
  { n: 4, label: "Results"    },
];

/* ── tiny field wrapper ──────────────────────────────────────────────────── */
function Field({ label, required, hint, error, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-2">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
      {error ? (
        <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
          <span>⚠</span> {error}
        </p>
      ) : hint ? (
        <p className="mt-1.5 text-xs text-slate-600 flex items-center gap-1">
          <Info className="w-3 h-3 shrink-0" /> {hint}
        </p>
      ) : null}
    </div>
  );
}

/* ── quick-select chip ───────────────────────────────────────────────────── */
function Chip({ label, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
        ${active
          ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
          : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300"
        }`}
    >
      {label}
    </button>
  );
}

export default function NewPlanPage() {
  const router = useRouter();

  const [form, setForm] = useState({ budget: "", roofArea: "", location: "" });
  const [errors, setErrors]         = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showSug, setShowSug]         = useState(false);

  /* ── validation ────────────────────────────────────────────────────────── */
  function validate() {
    const e = {};
    if (!form.budget)
      e.budget = "Budget is required";
    else if (isNaN(form.budget) || Number(form.budget) < 1000)
      e.budget = "Minimum budget is RM 1,000";

    if (!form.roofArea)
      e.roofArea = "Roof area is required";
    else if (isNaN(form.roofArea) || Number(form.roofArea) < 5)
      e.roofArea = "Minimum roof area is 5 m²";

    if (!form.location.trim())
      e.location = "Location is required";
    else if (form.location.trim().length < 3)
      e.location = "Enter a more specific location";

    return e;
  }

  /* ── submit ─────────────────────────────────────────────────────────────── */
  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setSubmitting(true);
    try {
      const res = await plansApi.createPlan({
        budget:   Number(form.budget),
        roofArea: Number(form.roofArea),
        location: form.location.trim(),
      });

      if (res.success) {
        toast.success("Plan created! Upload your bill next.");
        router.push(`/plans/${res.data.planId}/upload`);
      } else {
        toast.error(res.message || "Failed to create plan");
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  /* ── helpers ─────────────────────────────────────────────────────────────── */
  function handleChange(e) {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: value }));
    if (errors[name]) setErrors((p) => ({ ...p, [name]: "" }));

    if (name === "location") {
      const hits = LOCATIONS.filter((l) =>
        l.toLowerCase().includes(value.toLowerCase())
      );
      setSuggestions(hits);
      setShowSug(value.length > 0 && hits.length > 0);
    }
  }

  function pickLocation(loc) {
    setForm((p) => ({ ...p, location: loc }));
    setShowSug(false);
    if (errors.location) setErrors((p) => ({ ...p, location: "" }));
  }

  function setPreset(name, value) {
    setForm((p) => ({ ...p, [name]: value.toString() }));
    if (errors[name]) setErrors((p) => ({ ...p, [name]: "" }));
  }

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto page-enter">
        {/* Back */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300
                     text-sm mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Plans
        </button>

        {/* Progress steps */}
        <div className="flex items-center mb-8">
          {STEP_LIST.map(({ n, label }, idx) => (
            <div key={n} className="flex items-center flex-1">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center
                               text-xs font-bold border-2 transition-all
                               ${n === 1
                                 ? "bg-emerald-500 border-emerald-500 text-white"
                                 : "bg-slate-800 border-slate-700 text-slate-500"
                               }`}
                >
                  {n}
                </div>
                <span className={`text-xs whitespace-nowrap hidden sm:block
                  ${n === 1 ? "text-emerald-400 font-medium" : "text-slate-600"}`}>
                  {label}
                </span>
              </div>
              {idx < STEP_LIST.length - 1 && (
                <div className="flex-1 h-px bg-slate-800 mx-2 mb-4" />
              )}
            </div>
          ))}
        </div>

        {/* Main card */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800
                        rounded-3xl p-8 shadow-2xl">
          {/* Heading */}
          <div className="mb-7">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border
                              border-emerald-500/20 flex items-center justify-center">
                <Zap className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-100">
                  New Energy Plan
                </h1>
                <p className="text-xs text-slate-500">Step 1 of 4 — Plan Setup</p>
              </div>
            </div>
            <p className="text-slate-500 text-sm leading-relaxed">
              Fill in your requirements. We&apos;ll calculate the optimal
              solar + battery configuration for your property.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">

            {/* ── Budget ──────────────────────────────────────────────────── */}
            <Field
              label="Total Budget"
              required
              error={errors.budget}
              hint="Typical residential systems cost RM 15,000 – RM 60,000"
            >
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2
                                  text-slate-400 text-sm font-semibold
                                  pointer-events-none">
                  RM
                </span>
                <input
                  type="number"
                  name="budget"
                  value={form.budget}
                  onChange={handleChange}
                  placeholder="e.g. 25000"
                  min="1000"
                  step="500"
                  className={`w-full pl-10 pr-4 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${errors.budget
                      ? "border-red-500/60 focus:ring-red-500/30"
                      : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />
              </div>
              {/* quick-select */}
              <div className="flex gap-2 mt-2.5 flex-wrap">
                {BUDGET_PRESETS.map((v) => (
                  <Chip
                    key={v}
                    label={`RM ${v.toLocaleString()}`}
                    active={form.budget === v.toString()}
                    onClick={() => setPreset("budget", v)}
                  />
                ))}
              </div>
            </Field>

            {/* ── Roof Area ───────────────────────────────────────────────── */}
            <Field
              label="Available Roof Area"
              required
              error={errors.roofArea}
              hint="Each solar panel needs roughly 2 m². More area = more solar capacity."
            >
              <div className="relative">
                <Home className="absolute left-3.5 top-1/2 -translate-y-1/2
                                  w-4 h-4 text-slate-500 pointer-events-none" />
                <input
                  type="number"
                  name="roofArea"
                  value={form.roofArea}
                  onChange={handleChange}
                  placeholder="e.g. 40"
                  min="5"
                  step="1"
                  className={`w-full pl-10 pr-16 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${errors.roofArea
                      ? "border-red-500/60 focus:ring-red-500/30"
                      : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />
                <span className="absolute right-3.5 top-1/2 -translate-y-1/2
                                  text-slate-500 text-xs font-medium
                                  pointer-events-none">
                  m²
                </span>
              </div>
              {/* quick-select */}
              <div className="flex gap-2 mt-2.5 flex-wrap">
                {ROOFAREA_PRESETS.map((v) => (
                  <Chip
                    key={v}
                    label={`${v} m²`}
                    active={form.roofArea === v.toString()}
                    onClick={() => setPreset("roofArea", v)}
                  />
                ))}
              </div>
            </Field>

            {/* ── Location ────────────────────────────────────────────────── */}
            <Field
              label="Property Location"
              required
              error={errors.location}
              hint="Used to calculate solar irradiance and weather data"
            >
              <div className="relative">
                <MapPin className="absolute left-3.5 top-1/2 -translate-y-1/2
                                    w-4 h-4 text-slate-500 pointer-events-none" />
                <input
                  type="text"
                  name="location"
                  value={form.location}
                  onChange={handleChange}
                  onFocus={() =>
                    form.location && setSuggestions(LOCATIONS.filter((l) =>
                      l.toLowerCase().includes(form.location.toLowerCase())
                    )) && setShowSug(true)
                  }
                  onBlur={() => setTimeout(() => setShowSug(false), 150)}
                  placeholder="e.g. Kuala Lumpur, Malaysia"
                  autoComplete="off"
                  className={`w-full pl-10 pr-4 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${errors.location
                      ? "border-red-500/60 focus:ring-red-500/30"
                      : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />

                {/* Dropdown suggestions */}
                {showSug && suggestions.length > 0 && (
                  <ul className="absolute z-20 top-full left-0 right-0 mt-1
                                  bg-slate-800 border border-slate-700 rounded-xl
                                  overflow-hidden shadow-2xl">
                    {suggestions.slice(0, 6).map((loc) => (
                      <li key={loc}>
                        <button
                          type="button"
                          onMouseDown={() => pickLocation(loc)}
                          className="w-full px-4 py-2.5 text-left text-sm
                                     text-slate-300 hover:bg-slate-700
                                     hover:text-slate-100 flex items-center gap-2
                                     transition-colors"
                        >
                          <MapPin className="w-3.5 h-3.5 text-slate-500
                                             shrink-0" />
                          {loc}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Field>

            {/* ── Info box ────────────────────────────────────────────────── */}
            <div className="rounded-2xl bg-blue-500/5 border border-blue-500/15 p-4">
              <div className="flex gap-3">
                <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold text-blue-400 mb-1">
                    What happens next?
                  </p>
                  <ul className="text-xs text-slate-400 space-y-1 list-disc
                                  list-inside leading-relaxed">
                    <li>Upload your electricity bill (PDF or CSV)</li>
                    <li>Our AI parses monthly consumption data</li>
                    <li>Algorithm designs optimal solar + battery system</li>
                    <li>View ROI, savings, and 24-hour predictions</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* ── Submit ──────────────────────────────────────────────────── */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-600
                         active:bg-emerald-700 text-white font-semibold text-sm
                         transition-all duration-200 shadow-lg shadow-emerald-500/25
                         hover:shadow-emerald-500/40 disabled:opacity-60
                         disabled:cursor-not-allowed flex items-center
                         justify-center gap-2"
            >
              {submitting ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creating plan...
                </>
              ) : (
                <>
                  <PlusCircle className="w-4 h-4" />
                  Create Plan & Continue
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </DashboardLayout>
  );
}