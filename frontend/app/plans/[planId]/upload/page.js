"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { uploadApi } from "@/lib/uploadApi";
import { getErrorMessage, formatNumber } from "@/lib/utils";
import { ConsumptionChart } from "@/components/charts/ConsumptionChart";
import toast from "react-hot-toast";
import {
  Upload, FileText, CheckCircle, AlertCircle,
  ChevronLeft, ArrowRight, X, Eye,
  BarChart3, Keyboard, Info,
} from "lucide-react";

const ALLOWED = [".pdf", ".csv", ".png", ".jpg", ".jpeg"];
const MAX_MB  = 10;

/* ── drag-and-drop zone ──────────────────────────────────────────────────── */
function DropZone({ onFile, uploading }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) onFile(file);
    },
    [onFile]
  );

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      className={`relative rounded-2xl border-2 border-dashed p-10
                  flex flex-col items-center justify-center gap-4 cursor-pointer
                  transition-all duration-200 select-none
                  ${dragging
                    ? "border-emerald-500/60 bg-emerald-500/8 scale-[1.01]"
                    : "border-slate-700 hover:border-slate-600 bg-slate-800/30 hover:bg-slate-800/50"
                  }
                  ${uploading ? "pointer-events-none opacity-60" : ""}`}
    >
      <div className={`w-16 h-16 rounded-2xl flex items-center justify-center
                       transition-all duration-200
                       ${dragging
                         ? "bg-emerald-500/20 text-emerald-400"
                         : "bg-slate-800 text-slate-500"
                       }`}>
        <Upload className="w-8 h-8" />
      </div>

      <div className="text-center">
        <p className="text-slate-200 font-semibold mb-1">
          {dragging ? "Drop your file here" : "Drag & drop your bill"}
        </p>
        <p className="text-slate-500 text-sm">
          or{" "}
          <span className="text-emerald-400 font-medium underline
                           underline-offset-2">
            browse files
          </span>
        </p>
      </div>

      <div className="flex items-center gap-2 flex-wrap justify-center">
        {ALLOWED.map((ext) => (
          <span
            key={ext}
            className="px-2.5 py-1 rounded-full bg-slate-800 border
                       border-slate-700 text-xs text-slate-400 font-mono"
          >
            {ext}
          </span>
        ))}
        <span className="text-xs text-slate-600">· Max {MAX_MB} MB</span>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED.join(",")}
        onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        className="hidden"
      />
    </div>
  );
}

/* ── selected file preview ───────────────────────────────────────────────── */
function FilePreview({ file, progress, onRemove }) {
  const ext  = file.name.split(".").pop().toUpperCase();
  const size = (file.size / 1024 / 1024).toFixed(2);
  const isImg = ["PNG", "JPG", "JPEG"].includes(ext);
  const imgUrl = isImg ? URL.createObjectURL(file) : null;

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
      <div className="flex items-center gap-3">
        {/* thumbnail / icon */}
        {imgUrl ? (
          <img
            src={imgUrl}
            alt="preview"
            className="w-12 h-12 rounded-xl object-cover border border-slate-700"
          />
        ) : (
          <div className="w-12 h-12 rounded-xl bg-slate-700 flex items-center
                          justify-center shrink-0">
            <FileText className="w-6 h-6 text-slate-400" />
          </div>
        )}

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate">{file.name}</p>
          <p className="text-xs text-slate-500 mt-0.5">
            {ext} · {size} MB
          </p>
          {progress !== null && (
            <div className="mt-2">
              <div className="w-full h-1.5 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {progress < 100 ? `Uploading ${progress}%…` : "Processing…"}
              </p>
            </div>
          )}
        </div>

        {progress === null && (
          <button
            onClick={onRemove}
            className="p-1.5 rounded-lg text-slate-500 hover:text-red-400
                       hover:bg-red-500/10 transition-all shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

/* ── manual entry form ───────────────────────────────────────────────────── */
function ManualEntry({ planId, onSuccess }) {
  const [units, setUnits]       = useState("");
  const [pattern, setPattern]   = useState("flat");
  const [saving, setSaving]     = useState(false);

  async function handleSave() {
    const n = Number(units);
    if (!n || n < 1) { toast.error("Enter a valid monthly kWh"); return; }
    setSaving(true);
    try {
      const res = await uploadApi.addManualConsumption(planId, n, pattern);
      if (res.success) {
        toast.success("Manual data saved!");
        onSuccess(res.data);
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800/40 p-5 space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <Keyboard className="w-4 h-4 text-slate-400" />
        <p className="text-sm font-semibold text-slate-200">
          Enter Manually Instead
        </p>
      </div>
      <p className="text-xs text-slate-500">
        Don&apos;t have a bill file? Enter your average monthly usage and we&apos;ll
        estimate annual consumption.
      </p>

      <div>
        <label className="text-xs font-medium text-slate-400 mb-1.5 block">
          Average Monthly Usage (kWh)
        </label>
        <input
          type="number"
          value={units}
          onChange={(e) => setUnits(e.target.value)}
          placeholder="e.g. 400"
          min="1"
          className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border
                     border-slate-700 text-sm text-slate-100 placeholder-slate-600
                     focus:outline-none focus:ring-2 focus:ring-emerald-500/30
                     focus:border-emerald-500/50 transition-all"
        />
      </div>

      <div>
        <label className="text-xs font-medium text-slate-400 mb-1.5 block">
          Distribution Pattern
        </label>
        <div className="flex gap-2">
          {["flat", "seasonal"].map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPattern(p)}
              className={`flex-1 py-2 rounded-xl text-xs font-medium border
                          transition-all capitalize
                          ${pattern === p
                            ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
                            : "bg-slate-800 border-slate-700 text-slate-400"
                          }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={handleSave}
        disabled={saving || !units}
        className="w-full py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600
                   text-slate-200 text-sm font-medium transition-all
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? "Saving…" : "Save Manual Data"}
      </button>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════ */
export default function UploadBillPage() {
  const router          = useRouter();
  const { planId }      = useParams();

  const [file, setFile]           = useState(null);
  const [progress, setProgress]   = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult]       = useState(null);   // upload response
  const [tab, setTab]             = useState("upload"); // "upload" | "manual"

  /* chart data derived from parsed records */
  const chartData = result?.parsedData?.map((r) => ({
    month: r.month || r.date?.slice(0, 7) || "—",
    units: Number(r.units || 0),
  })) ?? [];

  /* ── pick file ────────────────────────────────────────────────────────── */
  function handleFile(f) {
    const ext = "." + f.name.split(".").pop().toLowerCase();
    if (!ALLOWED.includes(ext)) {
      toast.error(`File type not allowed. Use: ${ALLOWED.join(", ")}`);
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      toast.error(`File too large. Maximum is ${MAX_MB} MB`);
      return;
    }
    setFile(f);
    setResult(null);
  }

  /* ── upload ───────────────────────────────────────────────────────────── */
  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setProgress(0);

    try {
      const res = await uploadApi.uploadBill(planId, file, (p) =>
        setProgress(p)
      );
      if (res.success) {
        setResult(res.data);
        toast.success(
          `✅ Extracted ${res.data.recordsSaved} consumption record(s)`
        );
      } else {
        toast.error(res.message || "Upload failed");
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setUploading(false);
      setProgress(null);
    }
  }

  /* ── navigate forward ─────────────────────────────────────────────────── */
  function handleContinue() {
    router.push(`/plans/${planId}/result`);
  }

  const uploadDone = result && result.recordsSaved > 0;

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto page-enter">
        {/* Back */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300
                     text-sm mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Back
        </button>

        {/* Steps */}
        <div className="flex items-center mb-8">
          {[
            { n: 1, label: "Plan Setup",  done: true  },
            { n: 2, label: "Upload Bill", done: false, active: true },
            { n: 3, label: "Optimize",    done: false },
            { n: 4, label: "Results",     done: false },
          ].map(({ n, label, done, active }, idx, arr) => (
            <div key={n} className="flex items-center flex-1">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center
                               text-xs font-bold border-2 transition-all
                               ${done
                                 ? "bg-emerald-500 border-emerald-500 text-white"
                                 : active
                                   ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                                   : "bg-slate-800 border-slate-700 text-slate-500"
                               }`}
                >
                  {done ? <CheckCircle className="w-4 h-4" /> : n}
                </div>
                <span className={`text-xs whitespace-nowrap hidden sm:block
                  ${active ? "text-emerald-400 font-medium" : done ? "text-emerald-600" : "text-slate-600"}`}>
                  {label}
                </span>
              </div>
              {idx < arr.length - 1 && (
                <div className={`flex-1 h-px mx-2 mb-4
                  ${done ? "bg-emerald-500/40" : "bg-slate-800"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Heading */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-100 mb-1">
            Upload Electricity Bill
          </h1>
          <p className="text-slate-500 text-sm">
            Upload your TNB / utility bill so we can extract monthly
            consumption data automatically.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-1 p-1 rounded-xl bg-slate-800/80 border
                        border-slate-700/50 mb-6 w-fit">
          {[
            { key: "upload", label: "Upload File", icon: Upload        },
            { key: "manual", label: "Enter Manually", icon: Keyboard   },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm
                          font-medium transition-all
                          ${tab === key
                            ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/25"
                            : "text-slate-400 hover:text-slate-200"
                          }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {tab === "upload" ? (
          <div className="space-y-5">
            {/* Drop zone */}
            {!file && !uploadDone && (
              <DropZone onFile={handleFile} uploading={uploading} />
            )}

            {/* File preview */}
            {file && (
              <FilePreview
                file={file}
                progress={uploading ? progress : null}
                onRemove={() => { setFile(null); setResult(null); }}
              />
            )}

            {/* Warnings / errors */}
            {result?.parseErrors?.length > 0 && (
              <div className="rounded-2xl bg-amber-500/8 border border-amber-500/20
                              p-4 flex gap-3">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold text-amber-400 mb-1">
                    Parse Warnings
                  </p>
                  {result.parseErrors.map((e, i) => (
                    <p key={i} className="text-xs text-slate-400">{e}</p>
                  ))}
                </div>
              </div>
            )}

            {/* Success result */}
            {uploadDone && (
              <div className="rounded-2xl bg-emerald-500/8 border border-emerald-500/20 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <p className="font-semibold text-emerald-400">
                    Bill processed successfully!
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-5">
                  {[
                    { label: "Records Saved",  value: result.recordsSaved },
                    {
                      label: "File Size",
                      value: `${(result.fileSize / 1024).toFixed(0)} KB`,
                    },
                    { label: "Status", value: result.status?.replace("_", " ") },
                  ].map(({ label, value }) => (
                    <div
                      key={label}
                      className="bg-slate-900/60 rounded-xl p-3 text-center"
                    >
                      <p className="text-xs text-slate-500 mb-1">{label}</p>
                      <p className="text-sm font-bold text-slate-100 capitalize">
                        {value}
                      </p>
                    </div>
                  ))}
                </div>

                {/* Preview chart */}
                {chartData.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-400 mb-3 flex
                                  items-center gap-1.5">
                      <BarChart3 className="w-3.5 h-3.5" />
                      Extracted Consumption Preview
                    </p>
                    <ConsumptionChart data={chartData} />
                  </div>
                )}
              </div>
            )}

            {/* Info tip */}
            {!file && !uploadDone && (
              <div className="rounded-2xl bg-blue-500/5 border border-blue-500/15
                              p-4 flex gap-3">
                <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-400 leading-relaxed">
                  Upload a PDF or CSV export of your TNB / utility bill.
                  We&apos;ll automatically extract monthly kWh usage.
                  Images (PNG / JPG) are accepted but text extraction
                  may be limited.
                </p>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-3">
              {file && !uploadDone && (
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="flex-1 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600
                             text-white font-semibold text-sm transition-all
                             shadow-lg shadow-emerald-500/25 disabled:opacity-60
                             disabled:cursor-not-allowed flex items-center
                             justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10"
                          stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Uploading {progress}%...
                    </>
                  ) : (
                    <><Upload className="w-4 h-4" /> Upload & Parse Bill</>
                  )}
                </button>
              )}

              {uploadDone && (
                <button
                  onClick={handleContinue}
                  className="flex-1 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600
                             text-white font-semibold text-sm transition-all
                             shadow-lg shadow-emerald-500/25 flex items-center
                             justify-center gap-2"
                >
                  Continue to Optimization
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ) : (
          /* Manual tab */
          <div className="space-y-5">
            <ManualEntry
              planId={planId}
              onSuccess={() => handleContinue()}
            />
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}