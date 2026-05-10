"use client"

import { useState } from "react"
import { Info } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const dayData = [
  { abbr: "Mon", name: "Monday", pnl: -1096.64, trades: 21, wr: 33, wins: 7, losses: 14 },
  { abbr: "Tue", name: "Tuesday", pnl: 1732.28, trades: 31, wr: 35, wins: 11, losses: 20 },
  { abbr: "Wed", name: "Wednesday", pnl: -1144.44, trades: 19, wr: 37, wins: 7, losses: 12 },
  { abbr: "Thu", name: "Thursday", pnl: -1254.50, trades: 7, wr: 29, wins: 2, losses: 5 },
  { abbr: "Fri", name: "Friday", pnl: 799.50, trades: 3, wr: 67, wins: 2, losses: 1 },
  { abbr: "Sat", name: "Saturday", pnl: 0, trades: 0, wr: 0, wins: 0, losses: 0 },
  { abbr: "Sun", name: "Sunday", pnl: 0, trades: 0, wr: 0, wins: 0, losses: 0 },
]

export function PnlByDayChart() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const nonZeroData = dayData.filter((d) => d.trades > 0)
  const maxAbsValue = nonZeroData.length > 0 ? Math.max(...nonZeroData.map((d) => Math.abs(d.pnl))) : 1
  const chartHeight = 140

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-lg p-2.5 h-[280px] flex flex-col">
      <div className="flex items-center gap-1.5 mb-3">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
          P&L by Day
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
              Profit and loss grouped by the day of the week when trades were opened
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div className="flex-1 flex items-center justify-center">
        <div className="relative w-full" style={{ height: chartHeight }}>
          {/* Zero line */}
          <div
            className="absolute left-0 right-0 h-px bg-[#404040]"
            style={{ top: "50%" }}
          />

          {/* Bars */}
          <div className="flex justify-center items-center h-full gap-2">
            {dayData.map((day, index) => {
              const hasData = day.trades > 0
              const barHeight = hasData
                ? (Math.abs(day.pnl) / maxAbsValue) * (chartHeight / 2 - 10)
                : 0
              const isPositive = day.pnl >= 0

              return (
                <div
                  key={day.abbr}
                  className="flex flex-col items-center relative"
                  onMouseEnter={() => hasData && setHoveredIndex(index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  {/* Bar container */}
                  <div
                    className="relative flex flex-col items-center justify-center"
                    style={{ height: chartHeight }}
                  >
                    {hasData ? (
                      /* Bar */
                      <div
                        className={`w-8 rounded-sm transition-opacity ${
                          isPositive ? "bg-emerald-500" : "bg-red-500"
                        } ${hoveredIndex === index ? "opacity-100" : "opacity-80"}`}
                        style={{
                          height: Math.max(barHeight, 4),
                          position: "absolute",
                          [isPositive ? "bottom" : "top"]: "50%",
                        }}
                      />
                    ) : (
                      /* Gray dot for zero trades */
                      <div
                        className="w-2 h-2 rounded-full bg-neutral-600 absolute"
                        style={{ top: "calc(50% - 4px)" }}
                      />
                    )}

                    {/* Tooltip on hover */}
                    {hoveredIndex === index && hasData && (
                      <div
                        className="absolute z-10 bg-[#1a1a1a] border border-[#262626] rounded px-2 py-1.5 shadow-lg whitespace-nowrap"
                        style={{
                          [isPositive ? "bottom" : "top"]: `calc(50% + ${barHeight + 8}px)`,
                        }}
                      >
                        <div className="text-white text-[11px] font-medium">{day.name}</div>
                        <div className={`text-[11px] ${isPositive ? "text-emerald-500" : "text-red-500"}`}>
                          P&L: {isPositive ? "+" : "-"}${Math.abs(day.pnl).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </div>
                        <div className="text-neutral-400 text-[10px]">Trades: {day.trades}</div>
                        <div className="text-neutral-400 text-[10px]">WR: {day.wr}%</div>
                        <div className="text-neutral-400 text-[10px]">W/L: {day.wins}W / {day.losses}L</div>
                      </div>
                    )}
                  </div>

                  {/* Label */}
                  <span className="text-[11px] text-white mt-1">{day.abbr}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
