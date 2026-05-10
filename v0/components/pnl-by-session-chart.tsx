"use client"

import { useState } from "react"
import { Info } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const sessionData = [
  { name: "Asian", pnl: 300.30, trades: 23, wr: 52 },
  { name: "London", pnl: -1942.63, trades: 42, wr: 38 },
  { name: "New York", pnl: 678.53, trades: 16, wr: 44 },
]

export function PnlBySessionChart() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const maxAbsValue = Math.max(...sessionData.map((d) => Math.abs(d.pnl)))
  const chartHeight = 140

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-lg p-2.5 h-[280px] flex flex-col">
      <div className="flex items-center gap-1.5 mb-3">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
          P&L by Session
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
              Profit and loss grouped by trading session. Asian: 00:00-08:00 UTC, London: 08:00-16:00 UTC, New York: 16:00-24:00 UTC
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
          <div className="flex justify-center items-center h-full gap-6">
            {sessionData.map((session, index) => {
              const barHeight = (Math.abs(session.pnl) / maxAbsValue) * (chartHeight / 2 - 10)
              const isPositive = session.pnl >= 0

              return (
                <div
                  key={session.name}
                  className="flex flex-col items-center relative"
                  onMouseEnter={() => setHoveredIndex(index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  {/* Bar container */}
                  <div
                    className="relative flex flex-col items-center justify-center"
                    style={{ height: chartHeight }}
                  >
                    {/* Bar */}
                    <div
                      className={`w-12 rounded-sm transition-opacity ${
                        isPositive ? "bg-emerald-500" : "bg-red-500"
                      } ${hoveredIndex === index ? "opacity-100" : "opacity-80"}`}
                      style={{
                        height: barHeight,
                        position: "absolute",
                        [isPositive ? "bottom" : "top"]: "50%",
                      }}
                    />

                    {/* Tooltip on hover */}
                    {hoveredIndex === index && (
                      <div
                        className="absolute z-10 bg-[#1a1a1a] border border-[#262626] rounded px-2 py-1.5 shadow-lg whitespace-nowrap"
                        style={{
                          [isPositive ? "bottom" : "top"]: `calc(50% + ${barHeight + 8}px)`,
                        }}
                      >
                        <div className="text-white text-[11px] font-medium">{session.name}</div>
                        <div className={`text-[11px] ${isPositive ? "text-emerald-500" : "text-red-500"}`}>
                          P&L: {isPositive ? "+" : ""}${Math.abs(session.pnl).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </div>
                        <div className="text-neutral-400 text-[10px]">Trades: {session.trades}</div>
                        <div className="text-neutral-400 text-[10px]">WR: {session.wr}%</div>
                      </div>
                    )}
                  </div>

                  {/* Label */}
                  <span className="text-[11px] text-white mt-1">{session.name}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
