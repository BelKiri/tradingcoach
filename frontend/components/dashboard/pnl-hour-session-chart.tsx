"use client";

import { useState, useMemo } from "react";
import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getAdaptiveFontSize } from "@/lib/adaptive-font";
import { fmtPnl } from "@/lib/format";

/* ---- shared types ---- */

interface HourSessionData {
  pnl: number;
  win_rate: number;
  trades: number;
}

interface PnlHourSessionChartProps {
  hourData: Record<string, HourSessionData>;
  sessionData: Record<string, HourSessionData>;
}

/* ---- helpers ---- */

const ALL_SESSIONS = ["Asian", "London", "New York"];

/* ---- toggle ---- */

type View = "hour" | "session";

function ViewToggle({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  return (
    <div className="flex rounded overflow-hidden border border-[#262626]">
      <button
        onClick={() => onChange("hour")}
        className={`px-2 py-0.5 text-[10px] transition-colors ${
          view === "hour"
            ? "bg-[#262626] text-white"
            : "bg-transparent text-neutral-400 hover:text-gray-300"
        }`}
      >
        By Hour
      </button>
      <button
        onClick={() => onChange("session")}
        className={`px-2 py-0.5 text-[10px] transition-colors ${
          view === "session"
            ? "bg-[#262626] text-white"
            : "bg-transparent text-neutral-400 hover:text-gray-300"
        }`}
      >
        By Session
      </button>
    </div>
  );
}

/* ---- hour heatmap ---- */

function HourHeatmap({ data }: { data: Record<string, HourSessionData> }) {
  const [hoveredHour, setHoveredHour] = useState<number | null>(null);

  const hourData = useMemo(() => {
    // Debug: log raw hour data from API
    if (process.env.NODE_ENV === "development") {
      console.log("[HourHeatmap] raw data keys:", Object.keys(data), "sample:", Object.entries(data).slice(0, 3));
    }
    return Array.from({ length: 24 }, (_, hour) => {
      const d = data[String(hour)];
      return {
        hour,
        pnl: d?.pnl ?? 0,
        trades: d?.trades ?? 0,
        wr: d?.win_rate ?? 0,
      };
    });
  }, [data]);

  const nonZeroData = hourData.filter((d) => d.trades > 0);
  const maxAbsValue = nonZeroData.length > 0 ? Math.max(...nonZeroData.map((d) => Math.abs(d.pnl))) : 1;

  const getColor = (pnl: number, trades: number) => {
    if (trades === 0) return "bg-[#2a2a2a]";
    if (pnl === 0) return "bg-[#262626]";
    const ratio = Math.abs(pnl) / maxAbsValue;
    if (pnl > 0) {
      if (ratio > 0.66) return "bg-emerald-800";
      if (ratio > 0.33) return "bg-emerald-600";
      return "bg-emerald-300";
    } else {
      if (ratio > 0.66) return "bg-red-800";
      if (ratio > 0.33) return "bg-red-600";
      return "bg-red-300";
    }
  };

  const rows = [
    hourData.slice(0, 6),
    hourData.slice(6, 12),
    hourData.slice(12, 18),
    hourData.slice(18, 24),
  ];

  return (
    <>
      <div className="flex-1 flex flex-col justify-center gap-1.5">
        {rows.map((row, rowIndex) => (
          <div key={rowIndex} className="flex justify-center gap-1.5">
            {row.map((d) => (
              <div
                key={d.hour}
                className="relative"
                onMouseEnter={() => setHoveredHour(d.hour)}
                onMouseLeave={() => setHoveredHour(null)}
              >
                <div
                  className={`w-10 h-10 rounded flex items-center justify-center text-[10px] text-white font-bold cursor-pointer transition-transform hover:scale-105 ${getColor(
                    d.pnl,
                    d.trades
                  )}`}
                  style={{ textShadow: "0 0 3px rgba(0,0,0,0.8), 0 0 6px rgba(0,0,0,0.5)" }}
                >
                  {d.hour.toString().padStart(2, "0")}
                </div>

                {hoveredHour === d.hour && d.trades > 0 && (
                  <div className="absolute z-10 bg-[#2a2a2a] border border-[#262626] rounded px-2 py-1.5 shadow-lg whitespace-nowrap bottom-full left-1/2 -translate-x-1/2 mb-1">
                    <div className="text-white text-[11px] font-medium">
                      {d.hour.toString().padStart(2, "0")}:00–{((d.hour + 1) % 24).toString().padStart(2, "0")}:00 UTC
                    </div>
                    <div className={`text-[11px] ${d.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                      P&L: {d.pnl >= 0 ? "+$" : "-$"}{Math.abs(d.pnl).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </div>
                    <div className="text-neutral-400 text-[10px]">Trades: {d.trades}</div>
                    <div className="text-neutral-400 text-[10px]">WR: {d.wr.toFixed(0)}%</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="flex items-center justify-center gap-3 mt-2">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-red-500" />
          <span className="text-[9px] text-neutral-400">Loss</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-[#2a2a2a]" />
          <span className="text-[9px] text-neutral-400">No trades</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-emerald-500" />
          <span className="text-[9px] text-neutral-400">Profit</span>
        </div>
      </div>
    </>
  );
}

/* ---- session table ---- */

function SessionTable({ data }: { data: Record<string, HourSessionData> }) {
  const maxAbs = Math.max(
    ...ALL_SESSIONS.map((s) => Math.abs(data[s]?.pnl ?? 0)),
    1,
  );

  return (
    <>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#262626] text-left">
            <th className="pb-2 pr-3 text-[11px] uppercase tracking-wide font-medium text-neutral-400">Session</th>
            <th className="pb-2 pr-3 text-[11px] uppercase tracking-wide font-medium text-neutral-400 text-right">P&L</th>
            <th className="pb-2 pr-3 text-[11px] uppercase tracking-wide font-medium text-neutral-400 text-right">Trades</th>
            <th className="pb-2 text-[11px] uppercase tracking-wide font-medium text-neutral-400 text-right">WR</th>
          </tr>
        </thead>
        <tbody>
          {ALL_SESSIONS.map((session) => {
            const d = data[session];
            const has = d && d.trades > 0;
            const intensity = has
              ? Math.min(Math.abs(d.pnl) / maxAbs, 1) * 0.12
              : 0;
            const bg = !has
              ? undefined
              : d.pnl >= 0
              ? `rgba(34,197,94,${intensity})`
              : `rgba(239,68,68,${intensity})`;
            return (
              <tr
                key={session}
                className="border-b border-[#262626] last:border-0"
                style={bg ? { backgroundColor: bg } : undefined}
              >
                <td className="py-1.5 pr-3 font-medium text-white text-[13px]">{session}</td>
                <td
                  className={`py-1.5 pr-3 text-right font-mono font-semibold tabular-nums ${has ? (d.pnl >= 0 ? "text-emerald-500" : "text-red-500") : "text-neutral-400"}`}
                  style={{ fontSize: has ? getAdaptiveFontSize(fmtPnl(d.pnl)) : "13px" }}
                >
                  {has ? fmtPnl(d.pnl) : "\u2014"}
                </td>
                <td className={`py-1.5 pr-3 text-right text-[13px] tabular-nums ${has ? "text-white" : "text-neutral-400"}`}>
                  {has ? d.trades : "\u2014"}
                </td>
                <td className={`py-1.5 text-right text-[13px] tabular-nums ${has ? "text-white" : "text-neutral-400"}`}>
                  {has ? `${d.win_rate.toFixed(0)}%` : "\u2014"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="mt-auto pt-3 space-y-0.5">
        <p className="text-[11px] text-neutral-400">Asian: 00:00 — 08:00 UTC</p>
        <p className="text-[11px] text-neutral-400">London: 08:00 — 16:00 UTC</p>
        <p className="text-[11px] text-neutral-400">New York: 16:00 — 24:00 UTC</p>
      </div>
    </>
  );
}

/* ---- main component ---- */

export function PnlHourSessionChart({ hourData, sessionData }: PnlHourSessionChartProps) {
  const [view, setView] = useState<View>("hour");

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-lg p-2.5 min-h-[280px] flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
            {view === "hour" ? "P&L by Hour" : "P&L by Session"}
          </h3>
          {view === "hour" && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 text-neutral-400 cursor-help" />
                </TooltipTrigger>
                <TooltipContent
                  side="top"
                  className="bg-[#2a2a2a] border-[#262626] text-white text-[11px] max-w-[220px] rounded"
                >
                  Profit and loss grouped by the hour (UTC) when trades were opened. Color intensity shows magnitude
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        <ViewToggle view={view} onChange={setView} />
      </div>

      {view === "hour" ? (
        <HourHeatmap data={hourData} />
      ) : (
        <SessionTable data={sessionData} />
      )}
    </div>
  );
}
