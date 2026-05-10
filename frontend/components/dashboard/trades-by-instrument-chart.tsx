"use client";

import { useState, useMemo } from "react";
import { PieChart, Pie, Cell } from "recharts";
import { ChartContainer } from "@/components/ui/chart";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const PIE_COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#f97316", "#14b8a6",
];

const chartConfig = {
  trades: { label: "Trades" },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomLabel(props: any) {
  const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props;
  const percentage = Math.round((percent || 0) * 100);
  if (percentage < 5) return null;

  const RADIAN = Math.PI / 180;
  const radiusRatio = percentage < 15 ? 0.7 : 0.5;
  const radius = (outerRadius - innerRadius) * radiusRatio + innerRadius;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      className="text-[10px] font-bold"
    >
      {percentage}%
    </text>
  );
}

interface TradesByInstrumentChartProps {
  pnlBySymbol: Record<string, { pnl: number; win_rate: number; trades: number }>;
}

export function TradesByInstrumentChart({ pnlBySymbol }: TradesByInstrumentChartProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { allData, displayData, totalTrades } = useMemo(() => {
    const entries = Object.entries(pnlBySymbol)
      .map(([name, d], i) => ({
        name,
        trades: d.trades,
        percentage: 0,
        color: PIE_COLORS[i % PIE_COLORS.length],
      }))
      .sort((a, b) => b.trades - a.trades);

    const total = entries.reduce((sum, e) => sum + e.trades, 0) || 1;
    entries.forEach((e) => (e.percentage = Math.round((e.trades / total) * 100)));

    const top5 = entries.slice(0, 5);
    const others = entries.slice(5);
    const othersTotal = others.reduce((sum, e) => sum + e.trades, 0);
    const othersPct = others.reduce((sum, e) => sum + e.percentage, 0);

    const display = othersTotal > 0
      ? [...top5, { name: "Others", trades: othersTotal, percentage: othersPct, color: "#6b7280" }]
      : top5;

    return { allData: entries, displayData: display, totalTrades: total };
  }, [pnlBySymbol]);

  return (
    <>
      <div className="rounded-lg border border-[#262626] bg-[#141414] p-3.5 w-full">
        <div className="flex items-start justify-between mb-2">
          <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
            Trades by Instrument
          </h3>
          <span className="text-xs text-neutral-400 tabular-nums">{totalTrades} trades</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center min-h-0">
          <ChartContainer config={chartConfig} className="h-[140px] w-[140px] aspect-square">
            <PieChart>
              <Pie
                data={displayData}
                cx="50%"
                cy="50%"
                innerRadius={0}
                outerRadius={70}
                paddingAngle={1}
                dataKey="trades"
                labelLine={false}
                label={CustomLabel}
              >
                {displayData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="#141414" strokeWidth={1} />
                ))}
              </Pie>
            </PieChart>
          </ChartContainer>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-3 w-full">
            {displayData.map((item) => (
              <div key={item.name} className="flex items-center gap-2 text-xs">
                <div
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-neutral-400 truncate">{item.name}</span>
              </div>
            ))}
          </div>
        </div>
        {allData.length > 5 && (
          <div className="text-center pt-3 pb-2">
            <button
              onClick={() => setIsModalOpen(true)}
              className="text-xs text-neutral-400 hover:text-gray-300 transition-colors"
            >
              Show all
            </button>
          </div>
        )}
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="bg-[#0a0a0a] border-[#262626] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Trades by Instrument (all)</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 mt-4">
            {allData.map((item) => (
              <div key={item.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="h-3 w-3 rounded-full shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm text-gray-300">{item.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-white tabular-nums">{item.percentage}%</span>
                  <span className="text-sm text-gray-400 tabular-nums w-16 text-right">{item.trades} trades</span>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
