"use client"

import { Area, AreaChart, XAxis, YAxis, ReferenceLine } from "recharts"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"

const data = [
  { date: "7 Jan", balance: 25000 },
  { date: "14 Jan", balance: 24547 },
  { date: "21 Jan", balance: 24620 },
  { date: "28 Jan", balance: 26762 },
  { date: "3 Feb", balance: 25800 },
  { date: "10 Feb", balance: 26300 },
  { date: "17 Feb", balance: 25200 },
  { date: "24 Feb", balance: 24500 },
  { date: "2 Mar", balance: 24036 },
]

const chartConfig = {
  balance: {
    label: "Balance",
    color: "#d4a843",
  },
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null
  
  return (
    <div className="rounded-md border border-[#262626] bg-[#1a1a1a] px-3 py-2 shadow-lg">
      <p className="text-xs text-gray-400">{label} 2026</p>
      <p className="text-sm font-medium text-white tabular-nums">
        ${payload[0].value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </p>
    </div>
  )
}

interface EquityCurveChartProps {
  periodLabel?: string
}

export function EquityCurveChart({ periodLabel = "All time" }: EquityCurveChartProps) {
  return (
    <div className="rounded-lg border border-[#262626] bg-[#141414] p-3.5 h-[280px] flex flex-col">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
          Equity Curve
        </h3>
        <span className="text-[11px] text-gray-500">{periodLabel}</span>
      </div>
      <div className="flex-1 min-h-[200px]">
        <ChartContainer config={chartConfig} className="h-full w-full aspect-auto">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
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
              interval={0}
              tickMargin={8}
            />
            <YAxis
              domain={[23000, 28000]}
              ticks={[23000, 24000, 25000, 26000, 27000, 28000]}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#ffffff", fontSize: 10 }}
              tickFormatter={(value) => `$${value.toLocaleString()}`}
              width={55}
            />
            <ReferenceLine
              y={25000}
              stroke="#404040"
              strokeDasharray="4 4"
            />
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
  )
}
