"use client"

import { useState } from "react"
import { PieChart, Pie, Cell } from "recharts"
import { ChartContainer } from "@/components/ui/chart"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

const allData = [
  { name: "XAUUSD", trades: 35, percentage: 43, color: "#10b981" },
  { name: "EURUSD", trades: 23, percentage: 28, color: "#3b82f6" },
  { name: "BTCUSD", trades: 8, percentage: 10, color: "#f59e0b" },
  { name: "USDJPY", trades: 5, percentage: 6, color: "#ef4444" },
  { name: "GBPUSD", trades: 4, percentage: 5, color: "#8b5cf6" },
  { name: "US500", trades: 2, percentage: 2, color: "#ec4899" },
  { name: "NZDUSD", trades: 2, percentage: 2, color: "#06b6d4" },
  { name: "AUDUSD", trades: 1, percentage: 1, color: "#f97316" },
  { name: "XAGUSD", trades: 1, percentage: 1, color: "#14b8a6" },
]

// Top 5 + Others for display
const top5 = allData.slice(0, 5)
const othersData = allData.slice(5)
const othersTotal = othersData.reduce((sum, item) => sum + item.trades, 0)
const othersPercentage = othersData.reduce((sum, item) => sum + item.percentage, 0)

const displayData = [
  ...top5,
  { name: "Others", trades: othersTotal, percentage: othersPercentage, color: "#6b7280" },
]

const totalTrades = allData.reduce((sum, item) => sum + item.trades, 0)

const chartConfig = {
  trades: {
    label: "Trades",
  },
}

function CustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percentage }: {
  cx: number
  cy: number
  midAngle: number
  innerRadius: number
  outerRadius: number
  percentage: number
}) {
  // No label for segments < 5%
  if (percentage < 5) return null
  
  const RADIAN = Math.PI / 180
  
  // Calculate radius based on percentage
  // >= 15%: centered at 50% of radius
  // 5-15%: positioned at 75% of radius but ensure inside boundary
  let radiusRatio = 0.5
  if (percentage < 15) {
    radiusRatio = 0.7 // slightly outward but still safely inside
  }
  
  const radius = (outerRadius - innerRadius) * radiusRatio + innerRadius
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)

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
  )
}

export function TradesByInstrumentChart() {
  const [isModalOpen, setIsModalOpen] = useState(false)

  return (
    <>
      <div className="rounded-lg border border-[#262626] bg-[#141414] p-3.5 h-[280px] flex flex-col">
        <div className="flex items-start justify-between mb-2">
          <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
            Trades by Instrument
          </h3>
          <span className="text-xs text-gray-400 tabular-nums">{totalTrades} trades</span>
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
                <span className="text-gray-400 truncate">{item.name}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-auto pt-2">
          <button
            onClick={() => setIsModalOpen(true)}
            className="text-[11px] text-gray-500 hover:text-gray-300 transition-colors"
          >
            Show all instruments
          </button>
        </div>
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
  )
}
