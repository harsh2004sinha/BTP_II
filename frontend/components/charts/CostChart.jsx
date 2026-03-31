"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";

export function CostChart({ graphData }) {
  // graphData comes from backend result.graphData
  if (!graphData) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
        No cost data available
      </div>
    );
  }

  const data =
    graphData.monthly_savings ||
    Array.from({ length: 12 }, (_, i) => ({
      month: ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"][i],
      withSolar:    (graphData.monthly_bill_solar?.[i] ?? 0),
      withoutSolar: (graphData.monthly_bill_grid?.[i] ?? 0),
    }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="month"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "12px",
            color: "#f1f5f9",
            fontSize: "12px",
          }}
        />
        <Legend wrapperStyle={{ fontSize: "12px", color: "#94a3b8" }} />
        <Line
          type="monotone"
          dataKey="withoutSolar"
          name="Grid Only (RM)"
          stroke="#ef4444"
          strokeWidth={2}
          dot={{ fill: "#ef4444", r: 3 }}
        />
        <Line
          type="monotone"
          dataKey="withSolar"
          name="With Solar (RM)"
          stroke="#10b981"
          strokeWidth={2}
          dot={{ fill: "#10b981", r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}