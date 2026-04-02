"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";

export function SolarOutputChart({ data }) {
  if (!data?.length) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
        No solar data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="hour"
          tick={{ fill: "#64748b", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#64748b", fontSize: 10 }}
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
        <Bar dataKey="solar_kW" name="Solar Output (kW)" radius={[4, 4, 0, 0]}>
          {data.map((_, index) => (
            <Cell
              key={index}
              fill={`hsl(${40 + index * 3}, 85%, ${50 + index}%)`}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}