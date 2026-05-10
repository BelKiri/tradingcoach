"use client";

import { HelpCircle } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { DashboardData, BehavioralData } from "@/lib/api";
import { getMetricFontSize } from "@/lib/adaptive-font";
import { fmtPnl } from "@/lib/format";

/* ---------- helpers ---------- */

function fmtDollar(val: number): string {
  return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/* ---------- sub-components ---------- */

interface MetricCellProps {
  label: string;
  value: string;
  subtitle?: string;
  valueColor?: "green" | "red" | "neutral";
}

function MetricCell({ label, value, subtitle, valueColor = "neutral" }: MetricCellProps) {
  const colorClass = {
    green: "text-emerald-500",
    red: "text-red-500",
    neutral: "text-white",
  }[valueColor];

  const isDollarValue = value.includes("$");
  const fontSize = isDollarValue ? getMetricFontSize(value) : undefined;

  return (
    <div className="min-w-[100px]">
      <p className="text-[11px] uppercase tracking-wide text-neutral-400 mb-1">{label}</p>
      <p
        className={`font-bold tabular-nums ${colorClass} ${!isDollarValue ? "text-[22px]" : ""}`}
        style={fontSize ? { fontSize } : undefined}
      >
        {value}
      </p>
      {subtitle && <p className="text-xs text-neutral-400 tabular-nums">{subtitle}</p>}
    </div>
  );
}

interface PatternRowProps {
  pattern: string;
  pnl: string;
  trades: string;
  tooltip: string;
  isPositive: boolean;
}

function PatternRow({ pattern, pnl, trades, tooltip, isPositive }: PatternRowProps) {
  return (
    <tr className="border-b border-[#262626] last:border-b-0">
      <td className="py-1.5 pr-3">
        <span className="flex items-center gap-1.5">
          <span className="text-sm text-white">{pattern}</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="text-neutral-400 opacity-50 hover:opacity-100 transition-opacity">
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
      <td className="py-1.5 pl-3 text-right text-neutral-400 text-sm tabular-nums min-w-[50px]">
        {trades}
      </td>
    </tr>
  );
}

/* ---------- main component ---------- */

interface TradingMetricsCardProps {
  data: DashboardData;
  behavioral: BehavioralData;
}

export function TradingMetricsCard({ data, behavioral: b }: TradingMetricsCardProps) {
  const dd = data.max_drawdown as Record<string, number>;
  const streaks = data.streaks as Record<string, number>;
  const slTotal = b.sl_with + b.sl_without;
  const slPct = slTotal > 0 ? Math.round((b.sl_with / slTotal) * 100) : 0;

  const patterns = [
    {
      pattern: "Revenge Trading",
      pnl: fmtPnl(b.revenge_cost),
      trades: String(b.revenge_count),
      tooltip: "Trade opened within 5 minutes after a loss",
      isPositive: b.revenge_cost >= 0,
    },
    {
      pattern: "Martingale",
      pnl: fmtPnl(b.martingale_pnl),
      trades: String(b.martingale_count),
      tooltip: "Lot size increased 40%+ after a loss on same symbol",
      isPositive: b.martingale_pnl >= 0,
    },
    {
      pattern: "Overtrading",
      pnl: fmtPnl(b.overtrading_pnl),
      trades: `${b.overtrading_days} days`,
      tooltip: "Days with 5 or more trades opened",
      isPositive: b.overtrading_pnl >= 0,
    },
    {
      pattern: "Averaging Down",
      pnl: fmtPnl(b.averaging_pnl),
      trades: String(b.averaging_count),
      tooltip: "Same symbol, same direction, overlapping positions",
      isPositive: b.averaging_pnl >= 0,
    },
    {
      pattern: "Quick Exits",
      pnl: fmtPnl(b.quick_exits_pnl),
      trades: String(b.quick_exits_count),
      tooltip: "Trade closed within 2 minutes of opening",
      isPositive: b.quick_exits_pnl >= 0,
    },
    {
      pattern: "No Stop Loss",
      pnl: fmtPnl(b.no_sl_pnl),
      trades: String(b.sl_without),
      tooltip: "Trades opened without a stop loss level",
      isPositive: b.no_sl_pnl >= 0,
    },
  ];

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-lg overflow-hidden">
      <div className="flex flex-col lg:flex-row">
        {/* Performance Section */}
        <div className="lg:w-[55%] p-3.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843] mb-4">Performance</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-4">
            <MetricCell
              label="Win Rate"
              value={data.win_rate !== null ? `${data.win_rate.toFixed(1)}%` : "\u2014"}
            />
            <MetricCell
              label="Net P&L"
              value={fmtPnl(data.total_pnl)}
              subtitle={`+$${data.gross_profit.toFixed(0)} / -$${Math.abs(data.gross_loss).toFixed(0)}`}
              valueColor={data.total_pnl >= 0 ? "green" : "red"}
            />
            <MetricCell
              label="Max Drawdown"
              value={dd.amount > 0 ? fmtDollar(dd.amount) : "\u2014"}
              subtitle={dd.amount > 0 ? `${dd.percent.toFixed(1)}% from peak` : undefined}
              valueColor="red"
            />
            <MetricCell
              label="Profit Factor"
              value={data.profit_factor !== null ? data.profit_factor.toFixed(2) : "\u2014"}
              valueColor={data.profit_factor !== null ? (data.profit_factor >= 1 ? "green" : "red") : "neutral"}
            />
            <MetricCell
              label="Expectancy"
              value={data.expectancy !== null ? `$${data.expectancy.toFixed(2)}` : "\u2014"}
              valueColor={data.expectancy !== null ? (data.expectancy >= 0 ? "green" : "red") : "neutral"}
            />
            <MetricCell
              label="SL Usage"
              value={slTotal > 0 ? `${slPct}%` : "\u2014"}
              subtitle={slTotal > 0 ? `${b.sl_with} with / ${b.sl_without} without` : undefined}
            />
            <MetricCell
              label="Avg Win"
              value={data.avg_win !== null ? `+$${data.avg_win.toFixed(2)}` : "\u2014"}
              valueColor="green"
            />
            <MetricCell
              label="Avg Loss"
              value={data.avg_loss !== null ? `-$${Math.abs(data.avg_loss).toFixed(2)}` : "\u2014"}
              valueColor="red"
            />
            <MetricCell
              label="Best / Worst Streak"
              value={`${streaks.max_win_streak ?? 0}W / ${streaks.max_loss_streak ?? 0}L`}
            />
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
                <th className="text-[11px] uppercase tracking-wide text-neutral-400 text-left font-normal pb-2">Pattern</th>
                <th className="text-[11px] uppercase tracking-wide text-neutral-400 text-right font-normal pb-2 px-3">P&L</th>
                <th className="text-[11px] uppercase tracking-wide text-neutral-400 text-right font-normal pb-2 pl-3">Trades</th>
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
  );
}
