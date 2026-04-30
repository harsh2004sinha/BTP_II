"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { plansApi } from "@/lib/plansApi";
import { getErrorMessage, formatCurrencyShort } from "@/lib/utils";
import toast from "react-hot-toast";
import {
  MapPin, ChevronLeft, Info, PlusCircle,
  Zap, Home, Navigation, Loader,
} from "lucide-react";

const BUDGET_PRESETS   = [50000, 100000, 200000, 500000];
const ROOFAREA_PRESETS = [20, 40, 60, 100, 150];

const STEP_LIST = [
  { n: 1, label: "Plan Setup"   },
  { n: 2, label: "Upload Bill"  },
  { n: 3, label: "Optimize"     },
  { n: 4, label: "Results"      },
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

  const [form, setForm]         = useState({ budget: "", roofArea: "", location: "" });
  const [errors, setErrors]     = useState({});
  const [submitting, setSubmitting] = useState(false);

  /* ── location autocomplete via Nominatim ─────────────────────────────── */
  const [suggestions, setSuggestions]   = useState([]);
  const [showSug, setShowSug]           = useState(false);
  const [locSearching, setLocSearching] = useState(false);
  const [gpsLoading, setGpsLoading]     = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    const q = form.location.trim();
    if (q.length < 2) { setSuggestions([]); setShowSug(false); return; }

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLocSearching(true);
      try {
        const url =
          `https://nominatim.openstreetmap.org/search` +
          `?q=${encodeURIComponent(q)}&format=json&limit=6&addressdetails=1`;
        const res  = await fetch(url, { headers: { "Accept-Language": "en" } });
        const data = await res.json();
        const hits = data.map((d) => ({
          label: d.display_name.split(",").slice(0, 3).join(", "),
          full : d.display_name,
        }));
        setSuggestions(hits);
        setShowSug(hits.length > 0);
      } catch {
        setSuggestions([]);
      } finally {
        setLocSearching(false);
      }
    }, 350);
  }, [form.location]);

  /* ── GPS: "Use my location" ─────────────────────────────────────────── */
  async function handleGPS() {
    if (!navigator.geolocation) {
      toast.error("Geolocation not supported by your browser");
      return;
    }
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { latitude: lat, longitude: lon } = pos.coords;
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`,
            { headers: { "Accept-Language": "en" } }
          );
          const data = await res.json();
          const addr = data.address || {};
          // Build a short, human-readable location string
          const parts = [
            addr.city || addr.town || addr.village || addr.county,
            addr.state,
            addr.country,
          ].filter(Boolean);
          const loc = parts.join(", ");
          setForm((p) => ({ ...p, location: loc }));
          setShowSug(false);
          if (errors.location) setErrors((p) => ({ ...p, location: "" }));
          toast.success(`📍 Location set: ${loc}`);
        } catch {
          toast.error("Could not reverse-geocode your location");
        } finally {
          setGpsLoading(false);
        }
      },
      (err) => {
        setGpsLoading(false);
        toast.error(
          err.code === 1
            ? "Location access denied. Please allow location access."
            : "Could not get your location. Try again."
        );
      },
      { timeout: 10000 }
    );
  }

  /* ── pick from dropdown ─────────────────────────────────────────────── */
  function pickLocation(label) {
    setForm((p) => ({ ...p, location: label }));
    setShowSug(false);
    if (errors.location) setErrors((p) => ({ ...p, location: "" }));
  }

  /* ── validation ─────────────────────────────────────────────────────── */
  function validate() {
    const e = {};
    if (!form.budget) e.budget = "Budget is required";
    else if (isNaN(form.budget) || Number(form.budget) < 1000)
      e.budget = "Minimum budget is ₹1,000";

    if (!form.roofArea) e.roofArea = "Roof area is required";
    else if (isNaN(form.roofArea) || Number(form.roofArea) < 5)
      e.roofArea = "Minimum roof area is 5 m²";

    if (!form.location.trim()) e.location = "Location is required";
    else if (form.location.trim().length < 3)
      e.location = "Enter a more specific location";

    return e;
  }

  /* ── submit ──────────────────────────────────────────────────────────── */
  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setSubmitting(true);
    try {
      const res = await plansApi.createPlan({
        budget  : Number(form.budget),
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

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: value }));
    if (errors[name]) setErrors((p) => ({ ...p, [name]: "" }));
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
                <span
                  className={`text-xs whitespace-nowrap hidden sm:block
                  ${n === 1 ? "text-emerald-400 font-medium" : "text-slate-600"}`}
                >
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
                <h1 className="text-xl font-bold text-slate-100">New Energy Plan</h1>
                <p className="text-xs text-slate-500">Step 1 of 4 — Plan Setup</p>
              </div>
            </div>
            <p className="text-slate-500 text-sm leading-relaxed">
              Fill in your requirements. We&apos;ll calculate the optimal solar
              + battery configuration for your property.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">

            {/* ── Budget ─────────────────────────────────────────────────── */}
            <Field
              label="Total Budget"
              required
              error={errors.budget}
              hint="Typical residential systems cost ₹50,000 – ₹5,00,000"
            >
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2
                  text-slate-400 text-sm font-semibold pointer-events-none">
                  ₹
                </span>
                <input
                  type="number"
                  name="budget"
                  value={form.budget}
                  onChange={handleChange}
                  placeholder="e.g. 500000"
                  min="10000"
                  step="1000"
                  className={`w-full pl-8 pr-4 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${errors.budget
                      ? "border-red-500/60 focus:ring-red-500/30"
                      : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />
              </div>
              <div className="flex gap-2 mt-2.5 flex-wrap">
                {BUDGET_PRESETS.map((v) => (
                  <Chip
                    key={v}
                    label={formatCurrencyShort(v)}
                    active={form.budget === v.toString()}
                    onClick={() => setPreset("budget", v)}
                  />
                ))}
              </div>
            </Field>

            {/* ── Roof Area ──────────────────────────────────────────────── */}
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
                  placeholder="e.g. 150"
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
                                text-slate-500 text-xs font-medium pointer-events-none">
                  m²
                </span>
              </div>
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

            {/* ── Location ───────────────────────────────────────────────── */}
            <Field
              label="Property Location"
              required
              error={errors.location}
              hint="Used to calculate solar irradiance and weather data"
            >
              <div className="relative">
                <MapPin className="absolute left-3.5 top-1/2 -translate-y-1/2
                                  w-4 h-4 text-slate-500 pointer-events-none z-10" />
                <input
                  type="text"
                  name="location"
                  value={form.location}
                  onChange={handleChange}
                  onBlur={() => setTimeout(() => setShowSug(false), 180)}
                  onFocus={() => suggestions.length > 0 && setShowSug(true)}
                  placeholder="e.g. Kharagpur, West Bengal"
                  autoComplete="off"
                  className={`w-full pl-10 pr-28 py-3 rounded-xl bg-slate-800/80
                    border text-sm text-slate-100 placeholder-slate-600
                    focus:outline-none focus:ring-2 transition-all duration-200
                    ${errors.location
                      ? "border-red-500/60 focus:ring-red-500/30"
                      : "border-slate-700 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    }`}
                />

                {/* Inline spinner */}
                {locSearching && (
                  <Loader className="absolute right-26 top-1/2 -translate-y-1/2
                                    w-3.5 h-3.5 text-slate-500 animate-spin" />
                )}

                {/* GPS button */}
                <button
                  type="button"
                  onClick={handleGPS}
                  disabled={gpsLoading}
                  title="Use my current location"
                  className="absolute right-2 top-1/2 -translate-y-1/2
                             flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                             bg-slate-700 hover:bg-slate-600 border border-slate-600
                             text-xs text-slate-300 font-medium transition-all
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {gpsLoading
                    ? <Loader className="w-3 h-3 animate-spin" />
                    : <Navigation className="w-3 h-3" />
                  }
                  {gpsLoading ? "..." : "Locate"}
                </button>

                {/* Dropdown suggestions */}
                {showSug && suggestions.length > 0 && (
                  <ul className="absolute z-20 top-full left-0 right-0 mt-1
                                 bg-slate-800 border border-slate-700 rounded-xl
                                 overflow-hidden shadow-2xl">
                    {suggestions.map((s, i) => (
                      <li key={i}>
                        <button
                          type="button"
                          onMouseDown={() => pickLocation(s.label)}
                          className="w-full px-4 py-2.5 text-left text-sm
                                     text-slate-300 hover:bg-slate-700
                                     hover:text-slate-100 flex items-center gap-2
                                     transition-colors"
                        >
                          <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          {s.label}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Field>

            {/* ── Info box ───────────────────────────────────────────────── */}
            <div className="rounded-2xl bg-blue-500/5 border border-blue-500/15 p-4">
              <div className="flex gap-3">
                <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold text-blue-400 mb-1">What happens next?</p>
                  <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside leading-relaxed">
                    <li>Enter your monthly electricity consumption (12 months)</li>
                    <li>Our AI calculates optimal solar + battery system</li>
                    <li>View ROI, savings, and 24-hour energy predictions</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* ── Submit ─────────────────────────────────────────────────── */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-600
                         active:bg-emerald-700 text-white font-semibold text-sm
                         transition-all duration-200 shadow-lg shadow-emerald-500/25
                         hover:shadow-emerald-500/40 disabled:opacity-60
                         disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <Loader className="animate-spin w-4 h-4" />
                  Creating plan...
                </>
              ) : (
                <>
                  <PlusCircle className="w-4 h-4" />
                  Create Plan &amp; Continue
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </DashboardLayout>
  );
}
