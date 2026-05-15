"use client";

import { useMemo } from "react";
import { Area, AreaChart, XAxis, YAxis, ReferenceLine } from "recharts";
import { ChartContainer, ChartTooltip } from "@/components/ui/chart";
import type { DashboardData } from "@/lib/api";

const chartConfig = {
  balance: {
    label: "Balance",
    color: "#d4a843",
  },
};

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-md border border-[#262626] bg-[#1a1a1a] px-3 py-2 shadow-lg">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-medium text-white tabular-nums">
        ${payload[0].value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </p>
    </div>
  );
}

interface EquityCurveChartProps {
  data: DashboardData;
  startingBalance: number;
}

export function EquityCurveChart({ data, startingBalance }: EquityCurveChartProps) {
  const chartData = useMemo(() => {
    const pts = data.equity_curve
      .map((pt) => pt as { day?: string; label?: string; equity?: number })
      .filter((row) => row.day && row.equity !== undefined);
    return pts
      .sort((a, b) => (a.day as string).localeCompare(b.day as string))
      .map((row) => ({
        date: (row.label || row.day) as string,
        balance: Math.round((startingBalance + (row.equity as number)) * 100) / 100,
      }));
  }, [data, startingBalance]);

  const xTicks = useMemo(() => {
    if (chartData.length <= 7) return chartData.map((d) => d.date);
    const ticks: string[] = [];
    for (let i = 0; i < 7; i++) {
      const idx = Math.round((i * (chartData.length - 1)) / 6);
      ticks.push(chartData[idx].date);
    }
    return ticks;
  }, [chartData]);

  if (!chartData.length) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-neutral-500">
        Not enough data
      </div>
    );
  }

  const minVal = Math.min(...chartData.map((d) => d.balance));
  const maxVal = Math.max(...chartData.map((d) => d.balance));
  const upDeviation = maxVal - startingBalance;
  const downDeviation = startingBalance - minVal;
  const maxDeviation = Math.max(upDeviation, downDeviation);
  const rawStep = maxDeviation / 2;
  const NICE_STEPS = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000];
  const step = NICE_STEPS.find((s) => s >= rawStep) ?? Math.ceil(rawStep / 1000) * 1000;
  const yTicks = [
    startingBalance - 2 * step,
    startingBalance - step,
    startingBalance,
    startingBalance + step,
    startingBalance + 2 * step,
  ];
  const domainMin = startingBalance - 2.2 * step;
  const domainMax = startingBalance + 2.2 * step;

  return (
    <div className="rounded-lg border border-[#262626] bg-[#141414] p-3.5 flex flex-col w-full h-full">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
          Equity Curve
        </h3>
      </div>
      <div className="flex-1 min-h-[200px]">
        <ChartContainer config={chartConfig} className="h-full w-full aspect-auto">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 45, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="goldGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#d4a843" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#d4a843" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#ffffff", fontSize: 10 }}
              ticks={xTicks}
              tickMargin={8}
            />
            <YAxis
              domain={[domainMin, domainMax]}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#ffffff", fontSize: 10 }}
              ticks={yTicks}
              tickFormatter={(value: number) => `$${(value / 1000).toFixed(1)}k`}
              width={55}
            />
            {startingBalance > 0 && (
              <ReferenceLine
                y={startingBalance}
                stroke="#d4a843"
                strokeDasharray="8 4"
                strokeOpacity={0.4}
                label={{
                  value: `$${(startingBalance / 1000).toFixed(1)}k`,
                  position: "right",
                  fill: "#d4a843",
                  fontSize: 11,
                }}
              />
            )}
            <ChartTooltip
              content={<CustomTooltip />}
              cursor={{ stroke: "#d4a843", strokeWidth: 1, strokeDasharray: "4 4" }}
            />
            <Area
              type="monotone"
              dataKey="balance"
              stroke="#d4a843"
              strokeWidth={2}
              fill="url(#goldGradient)"
              dot={false}
              activeDot={{ r: 5, fill: "#d4a843", stroke: "#0a0a0a", strokeWidth: 2 }}
            />
          </AreaChart>
        </ChartContainer>
      </div>
    </div>
  );
}
