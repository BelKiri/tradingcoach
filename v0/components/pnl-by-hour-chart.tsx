"use client"

import { useState } from "react"
import { Info } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

// Sample data for 24 hours
const hourData = [
  { hour: 0, pnl: 0, trades: 0 },
  { hour: 1, pnl: 0, trades: 0 },
  { hour: 2, pnl: 0, trades: 0 },
  { hour: 3, pnl: 0, trades: 0 },
  { hour: 4, pnl: 120.50, trades: 3 },
  { hour: 5, pnl: -85.20, trades: 2 },
  { hour: 6, pnl: 245.30, trades: 5 },
  { hour: 7, pnl: -320.40, trades: 4 },
  { hour: 8, pnl: 580.60, trades: 8 },
  { hour: 9, pnl: -450.80, trades: 6 },
  { hour: 10, pnl: 890.20, trades: 12 },
  { hour: 11, pnl: -180.30, trades: 4 },
  { hour: 12, pnl: 320.50, trades: 5 },
  { hour: 13, pnl: -620.40, trades: 7 },
  { hour: 14, pnl: 480.30, trades: 6 },
  { hour: 15, pnl: -290.60, trades: 4 },
  { hour: 16, pnl: 720.80, trades: 9 },
  { hour: 17, pnl: -150.20, trades: 3 },
  { hour: 18, pnl: 0, trades: 0 },
  { hour: 19, pnl: 0, trades: 0 },
  { hour: 20, pnl: 0, trades: 0 },
  { hour: 21, pnl: 0, trades: 0 },
  { hour: 22, pnl: 0, trades: 0 },
  { hour: 23, pnl: 0, trades: 0 },
]

export function PnlByHourChart() {
  const [hoveredHour, setHoveredHour] = useState<number | null>(null)

  const nonZeroData = hourData.filter((d) => d.trades > 0)
  const maxAbsValue = nonZeroData.length > 0 ? Math.max(...nonZeroData.map((d) => Math.abs(d.pnl))) : 1

  const getColor = (pnl: number, trades: number) => {
    if (trades === 0) return "bg-[#1a1a1a]"
    const intensity = Math.abs(pnl) / maxAbsValue
    if (pnl >= 0) {
      if (intensity > 0.66) return "bg-emerald-500"
      if (intensity > 0.33) return "bg-emerald-600"
      return "bg-emerald-700"
    } else {
      if (intensity > 0.66) return "bg-red-500"
      if (intensity > 0.33) return "bg-red-600"
      return "bg-red-700"
    }
  }

  // Split into 4 rows of 6
  const rows = [
    hourData.slice(0, 6),
    hourData.slice(6, 12),
    hourData.slice(12, 18),
    hourData.slice(18, 24),
  ]

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-lg p-2.5 h-[280px] flex flex-col">
      <div className="flex items-center gap-1.5 mb-3">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
          P&L by Hour
        </h3>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="w-3 h-3 text-neutral-500 cursor-help" />
            </TooltipTrigger>
            <TooltipContent
              side="top"
              className="bg-[#1a1a1a] border-[#262626] text-white text-[11px] max-w-[220px] rounded"
            >
              Profit and loss grouped by the hour (UTC) when trades were opened. Color intensity shows magnitude
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div className="flex-1 flex flex-col justify-center gap-1.5">
        {rows.map((row, rowIndex) => (
          <div key={rowIndex} className="flex justify-center gap-1.5">
            {row.map((data) => (
              <div
                key={data.hour}
                className="relative"
                onMouseEnter={() => setHoveredHour(data.hour)}
                onMouseLeave={() => setHoveredHour(null)}
              >
                <div
                  className={`w-10 h-10 rounded flex items-center justify-center text-[10px] text-neutral-400 cursor-pointer transition-transform hover:scale-105 ${getColor(
                    data.pnl,
                    data.trades
                  )}`}
                >
                  {data.hour.toString().padStart(2, "0")}
                </div>

                {/* Tooltip on hover */}
                {hoveredHour === data.hour && data.trades > 0 && (
                  <div className="absolute z-10 bg-[#1a1a1a] border border-[#262626] rounded px-2 py-1.5 shadow-lg whitespace-nowrap bottom-full left-1/2 -translate-x-1/2 mb-1">
                    <div className="text-white text-[11px] font-medium">{data.hour}:00 UTC</div>
                    <div className={`text-[11px] ${data.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                      P&L: {data.pnl >= 0 ? "+" : ""}${Math.abs(data.pnl).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </div>
                    <div className="text-neutral-400 text-[10px]">Trades: {data.trades}</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-3 mt-2">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-red-500" />
          <span className="text-[9px] text-neutral-500">Loss</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-[#1a1a1a]" />
          <span className="text-[9px] text-neutral-500">No trades</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-emerald-500" />
          <span className="text-[9px] text-neutral-500">Profit</span>
        </div>
      </div>
    </div>
  )
}
