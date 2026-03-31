"use client";

import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { format } from "date-fns";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 shadow-xl min-w-40">
      <p className="text-xs text-slate-400 mb-2">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex justify-between gap-4 text-xs">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="font-semibold text-slate-200">
            {Number(p.value).toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
};

export function PredictionChart({ data }) {
  if (!data?.length) {
    return (
      <div className="h-72 flex items-center justify-center text-slate-500 text-sm">
        No prediction data available
      </div>
    );
  }

  const chartData = data.map((d) => ({
    hour:       d.time ? new Date(d.time).getHours() + ":00" : "",
    solar:      d.solar_kW,
    battery:    d.batterySOC,
    gridCost:   d.gridCost,
    gridImport: d.gridImport,
    consumption: d.consumption,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="hour"
          tick={{ fill: "#64748b", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          yAxisId="left"
          tick={{ fill: "#64748b", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tick={{ fill: "#64748b", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }} />
        <Bar
          yAxisId="left"
          dataKey="solar"
          name="Solar (kW)"
          fill="#f59e0b"
          opacity={0.8}
          radius={[2, 2, 0, 0]}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="battery"
          name="Battery SOC (%)"
          stroke="#8b5cf6"
          strokeWidth={2}
          dot={false}
        />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="consumption"
          name="Load (kW)"
          stroke="#ef4444"
          strokeWidth={2}
          dot={false}
          strokeDasharray="4 2"
        />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="gridImport"
          name="Grid Import (kW)"
          stroke="#60a5fa"
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}