"use client";

import { useState, useMemo } from "react";
import { getAdaptiveFontSize } from "@/lib/adaptive-font";
import { fmtPnl } from "@/lib/format";

const ALL_DAYS = [
  { abbr: "Mon", name: "Monday" },
  { abbr: "Tue", name: "Tuesday" },
  { abbr: "Wed", name: "Wednesday" },
  { abbr: "Thu", name: "Thursday" },
  { abbr: "Fri", name: "Friday" },
  { abbr: "Sat", name: "Saturday" },
  { abbr: "Sun", name: "Sunday" },
];

type SortDir = "asc" | "desc";

function SortHeader({
  label,
  sortKey,
  current,
  dir,
  onSort,
  className,
}: {
  label: string;
  sortKey: string;
  current: string;
  dir: SortDir;
  onSort: (k: string) => void;
  className?: string;
}) {
  return (
    <th
      className={`pb-1.5 pr-2 text-[10px] uppercase tracking-wide font-medium text-neutral-400 cursor-pointer select-none hover:text-neutral-300 ${className || ""}`}
      style={{ borderRight: "1px solid #333333" }}
      onClick={() => onSort(sortKey)}
    >
      {label}
      {current === sortKey && (
        <span className="ml-0.5 text-[9px]">
          {dir === "asc" ? "\u25B2" : "\u25BC"}
        </span>
      )}
    </th>
  );
}

interface PnlByDayChartProps {
  data: Record<string, { pnl: number; win_rate: number; trades: number }>;
}

export function PnlByDayChart({ data }: PnlByDayChartProps) {
  const [sortKey, setSortKey] = useState("order");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else {
      setSortKey(key);
      setSortDir(key === "order" ? "asc" : "desc");
    }
  };

  const rows = useMemo(() => {
    return ALL_DAYS.map((day, i) => {
      const d = data[day.name];
      const trades = d?.trades ?? 0;
      const pnl = d?.pnl ?? 0;
      const wr = d?.win_rate ?? 0;
      const wins = trades > 0 ? Math.round((trades * wr) / 100) : 0;
      return {
        abbr: day.abbr,
        name: day.name,
        order: i,
        pnl,
        trades,
        win_rate: wr,
        wins,
        losses: trades - wins,
        hasData: trades > 0,
      };
    });
  }, [data]);

  const maxAbs = Math.max(...rows.map((r) => Math.abs(r.pnl)), 1);

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => {
      const av = a[sortKey as keyof typeof a] as number;
      const bv = b[sortKey as keyof typeof b] as number;
      return sortDir === "asc" ? av - bv : bv - av;
    });
  }, [rows, sortKey, sortDir]);

  return (
    <div className="bg-[#141414] border border-[#262626] rounded-lg p-2.5 min-h-[280px] flex flex-col">
      <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843] mb-2">
        P&L by Day
      </h3>

      <div className="overflow-hidden">
        <table className="w-full" style={{ tableLayout: "fixed" }}>
          <colgroup>
            <col style={{ width: "10%" }} />
            <col style={{ width: "30%" }} />
            <col style={{ width: "18%" }} />
            <col style={{ width: "17%" }} />
            <col style={{ width: "25%" }} />
          </colgroup>
          <thead>
            <tr className="border-b border-[#262626] text-left">
              <SortHeader label="Day" sortKey="order" current={sortKey} dir={sortDir} onSort={handleSort} />
              <SortHeader label="P&L" sortKey="pnl" current={sortKey} dir={sortDir} onSort={handleSort} className="text-right" />
              <SortHeader label="Trades" sortKey="trades" current={sortKey} dir={sortDir} onSort={handleSort} className="text-right" />
              <SortHeader label="WR" sortKey="win_rate" current={sortKey} dir={sortDir} onSort={handleSort} className="text-right" />
              <th className="pb-1.5 pr-2 text-[10px] uppercase tracking-wide font-medium text-neutral-400 text-right">
                W/L
              </th>
              {/* W/L column has no right border (last column) */}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const intensity = Math.min(Math.abs(r.pnl) / maxAbs, 1) * 0.12;
              const bg = !r.hasData
                ? undefined
                : r.pnl >= 0
                ? `rgba(34,197,94,${intensity})`
                : `rgba(239,68,68,${intensity})`;
              const pnlStr = fmtPnl(r.pnl);
              return (
                <tr
                  key={r.name}
                  className="border-b border-[#262626] last:border-0"
                  style={{ height: 32, ...(bg ? { backgroundColor: bg } : {}) }}
                >
                  <td className="pr-2 font-medium text-white text-[12px]" style={{ borderRight: "1px solid #333333" }}>{r.abbr}</td>
                  <td
                    className={`pr-2 text-right font-mono font-semibold tabular-nums ${r.hasData ? (r.pnl >= 0 ? "text-emerald-500" : "text-red-500") : "text-neutral-400"}`}
                    style={{ fontSize: r.hasData ? getAdaptiveFontSize(pnlStr) : "11px", borderRight: "1px solid #333333" }}
                  >
                    {r.hasData ? pnlStr : "\u2014"}
                  </td>
                  <td className={`pr-2 text-right text-[11px] tabular-nums ${r.hasData ? "text-white" : "text-neutral-400"}`} style={{ borderRight: "1px solid #333333" }}>
                    {r.hasData ? r.trades : "\u2014"}
                  </td>
                  <td className={`pr-2 text-right text-[11px] tabular-nums ${r.hasData ? "text-white" : "text-neutral-400"}`} style={{ borderRight: "1px solid #333333" }}>
                    {r.hasData ? `${r.win_rate.toFixed(0)}%` : "\u2014"}
                  </td>
                  <td className={`pr-2 text-right text-[11px] tabular-nums ${r.hasData ? "text-white" : "text-neutral-400"}`}>
                    {r.hasData ? (
                      <>
                        <span className="text-emerald-500">{r.wins}W</span>
                        {"/"}
                        <span className="text-red-500">{r.losses}L</span>
                      </>
                    ) : (
                      "\u2014"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
