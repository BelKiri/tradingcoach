"use client"

import { HelpCircle } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface MetricCellProps {
  label: string
  value: string
  subtitle?: string
  valueColor?: "green" | "red" | "neutral"
}

function MetricCell({ label, value, subtitle, valueColor = "neutral" }: MetricCellProps) {
  const colorClass = {
    green: "text-emerald-500",
    red: "text-red-500",
    neutral: "text-white",
  }[valueColor]

  return (
    <div className="min-w-[100px]">
      <p className="text-[11px] uppercase tracking-wide text-neutral-500 mb-1">{label}</p>
      <p className={`text-[22px] font-bold tabular-nums ${colorClass}`}>{value}</p>
      {subtitle && <p className="text-xs text-neutral-500 tabular-nums">{subtitle}</p>}
    </div>
  )
}

interface PatternRowProps {
  pattern: string
  pnl: string
  trades: string
  tooltip: string
  isPositive: boolean
}

function PatternRow({ pattern, pnl, trades, tooltip, isPositive }: PatternRowProps) {
  return (
    <tr className="border-b border-[#262626] last:border-b-0">
      <td className="py-1.5 pr-3">
        <span className="flex items-center gap-1.5">
          <span className="text-sm text-white">{pattern}</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="text-neutral-500 opacity-50 hover:opacity-100 transition-opacity">
                <HelpCircle className="size-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent 
              side="top" 
              className="bg-[#1a1a1a] text-white text-xs rounded px-3 py-2 max-w-[250px] shadow-lg border border-[#262626]"
            >
              {tooltip}
            </TooltipContent>
          </Tooltip>
        </span>
      </td>
      <td className={`py-1.5 px-3 text-right tabular-nums text-sm min-w-[90px] ${isPositive ? "text-emerald-500" : "text-red-500"}`}>
        {pnl}
      </td>
      <td className="py-1.5 pl-3 text-right text-neutral-500 text-sm tabular-nums min-w-[50px]">
        {trades}
      </td>
    </tr>
  )
}

export function TradingMetricsCard() {
  const patterns = [
    { pattern: "Revenge Trading", pnl: "-$3,259.73", trades: "21", tooltip: "Trade opened within 5 minutes after a loss", isPositive: false },
    { pattern: "Martingale", pnl: "+$571.06", trades: "5", tooltip: "Lot size increased 40%+ after a loss on same symbol", isPositive: true },
    { pattern: "Overtrading", pnl: "-$177.70", trades: "5 days", tooltip: "Days with 5 or more trades opened", isPositive: false },
    { pattern: "Averaging Down", pnl: "-$311.00", trades: "14", tooltip: "Same symbol, same direction, overlapping positions", isPositive: false },
    { pattern: "Quick Exits", pnl: "-$122.00", trades: "9", tooltip: "Trade closed within 2 minutes of opening", isPositive: false },
    { pattern: "No Stop Loss", pnl: "-$2,643.00", trades: "35", tooltip: "Trades opened without a stop loss level", isPositive: false },
  ]

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-lg overflow-hidden">
      <div className="flex flex-col lg:flex-row">
        {/* Performance Section */}
        <div className="lg:w-[55%] p-3.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843] mb-4">Performance</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-4">
            <MetricCell label="Win Rate" value="33.3%" valueColor="neutral" />
            <MetricCell
              label="Net P&L"
              value="-$963.80"
              subtitle="+$7,374 / -$8,337"
              valueColor="red"
            />
            <MetricCell
              label="Max Drawdown"
              value="$2,827.18"
              subtitle="10.6% from peak"
              valueColor="red"
            />
            <MetricCell label="Profit Factor" value="0.88" valueColor="red" />
            <MetricCell label="Expectancy" value="-$11.90" valueColor="red" />
            <MetricCell label="SL Usage" value="57%" subtitle="46 with / 35 without" valueColor="neutral" />
            <MetricCell label="Avg Win" value="+$273.10" valueColor="green" />
            <MetricCell label="Avg Loss" value="-$154.40" valueColor="red" />
            <MetricCell label="Best / Worst Streak" value="3W / 7L" valueColor="neutral" />
          </div>
        </div>

        {/* Divider */}
        <div className="h-px bg-[#262626] lg:hidden" />
        <div className="hidden lg:block w-px bg-[#262626]" />

        {/* Behavioral Analysis Section */}
        <div className="lg:w-[45%] p-3.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843] mb-4">Behavioral Analysis</h3>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#262626]">
                <th className="text-[11px] uppercase tracking-wide text-neutral-500 text-left font-normal pb-2">Pattern</th>
                <th className="text-[11px] uppercase tracking-wide text-neutral-500 text-right font-normal pb-2 px-3">P&L</th>
                <th className="text-[11px] uppercase tracking-wide text-neutral-500 text-right font-normal pb-2 pl-3">Trades</th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((item) => (
                <PatternRow key={item.pattern} {...item} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
