"use client";

import { useCallback, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR, { mutate } from "swr";
import { ChevronDown, Upload, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUser } from "@/lib/hooks/useUser";
import {
  requestCoaching,
  uploadTrades,
  type AccountSummary,
  type DashboardData,
} from "@/lib/api";
import { fetcher } from "@/lib/swr";
import { fmtPnl } from "@/lib/format";

/* Dashboard components (v0 design + real data) */
import { TradingMetricsCard } from "@/components/dashboard/trading-metrics-card";
import { EquityCurveChart } from "@/components/dashboard/equity-curve-chart";
import { TradesByInstrumentChart } from "@/components/dashboard/trades-by-instrument-chart";
import { PnlByInstrumentChart } from "@/components/dashboard/pnl-by-instrument-chart";
import { PnlByDayChart } from "@/components/dashboard/pnl-by-day-chart";
import { PnlHourSessionChart } from "@/components/dashboard/pnl-hour-session-chart";

/* ================================================================
   HELPERS
   ================================================================ */

function pnlColor(val: number): string {
  if (val > 0) return "text-emerald-400";
  if (val < 0) return "text-red-400";
  return "text-muted-foreground";
}

function hasSL(sl: unknown): boolean {
  if (sl === null || sl === undefined) return false;
  const n = Number(sl);
  return !isNaN(n) && n !== 0;
}

const CACHE_TTL = 5 * 60 * 1000;

/* ================================================================
   PERIOD FILTER
   ================================================================ */

type PeriodKey = "all" | "7d" | "30d" | "month" | "custom";

const periodLabels: Record<PeriodKey, string> = {
  all: "All time",
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  month: "This month",
  custom: "Custom range",
};

function getDateRange(key: PeriodKey): { from?: string; to?: string } {
  const now = new Date();
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  switch (key) {
    case "7d": {
      const from = new Date(now);
      from.setDate(from.getDate() - 7);
      return { from: fmt(from), to: fmt(now) };
    }
    case "30d": {
      const from = new Date(now);
      from.setDate(from.getDate() - 30);
      return { from: fmt(from), to: fmt(now) };
    }
    case "month":
      return {
        from: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`,
        to: fmt(now),
      };
    default:
      return {};
  }
}

/* ================================================================
   DASHBOARD HEADER (v0 style)
   ================================================================ */

function DashboardHeader({
  totalTrades,
  period,
  onPeriodChange,
  customFrom,
  customTo,
  onCustomChange,
  onUpload,
  uploading,
  uploadResult,
  onCoaching,
  coachingLoading,
}: {
  totalTrades: number;
  period: PeriodKey;
  onPeriodChange: (v: PeriodKey) => void;
  customFrom: string;
  customTo: string;
  onCustomChange: (from: string, to: string) => void;
  onUpload: (f: File) => void;
  uploading: boolean;
  uploadResult: string | null;
  onCoaching: () => void;
  coachingLoading: boolean;
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  return (
    <div className="w-full px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      {/* Left side */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-baseline gap-3">
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <span className="text-sm text-gray-500">{totalTrades} trades</span>
        </div>

        {/* Period Dropdown */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 bg-[#1a1a1a] border border-[#262626] rounded hover:border-[#3a3a3a] transition-colors"
          >
            {periodLabels[period]}
            <ChevronDown className="w-4 h-4" />
          </button>

          {dropdownOpen && (
            <div className="absolute top-full left-0 mt-1 w-40 bg-[#1a1a1a] border border-[#262626] rounded shadow-lg z-10">
              {(Object.entries(periodLabels) as [PeriodKey, string][]).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => {
                    onPeriodChange(key);
                    setDropdownOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                    period === key
                      ? "text-white bg-[#262626]"
                      : "text-gray-400 hover:text-white hover:bg-[#262626]"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Custom date inputs */}
        {period === "custom" && (
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={customFrom}
              onChange={(e) => onCustomChange(e.target.value, customTo)}
              className="rounded border border-[#262626] bg-[#1a1a1a] px-2 py-1.5 text-sm text-gray-300"
            />
            <span className="text-gray-500 text-sm">to</span>
            <input
              type="date"
              value={customTo}
              onChange={(e) => onCustomChange(customFrom, e.target.value)}
              className="rounded border border-[#262626] bg-[#1a1a1a] px-2 py-1.5 text-sm text-gray-300"
            />
          </div>
        )}

        {uploadResult && (
          <span className="text-xs text-gray-400">{uploadResult}</span>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        <label className="cursor-pointer">
          <input
            type="file"
            accept=".csv,.txt,.xlsx,.xls"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
            }}
          />
          <span className="flex items-center gap-2 px-4 py-2 text-sm text-gray-300 border border-[#262626] rounded hover:border-[#3a3a3a] hover:text-white transition-colors cursor-pointer">
            <Upload className="w-4 h-4" />
            {uploading ? "Uploading..." : "Upload file"}
          </span>
        </label>
        <button
          onClick={onCoaching}
          disabled={coachingLoading}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-bold rounded transition-colors ${
            coachingLoading ? "opacity-80 cursor-not-allowed" : ""
          }`}
          style={{
            backgroundColor: "var(--brand-gold, #d4a843)",
            color: "#000",
          }}
          onMouseEnter={(e) => { if (!coachingLoading) e.currentTarget.style.backgroundColor = "#e0b84e"; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "var(--brand-gold, #d4a843)"; }}
        >
          {coachingLoading ? (
            <span className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
          ) : (
            <Brain className="w-4 h-4" />
          )}
          {coachingLoading ? "Analyzing..." : "AI Coach"}
        </button>
      </div>
    </div>
  );
}

/* ================================================================
   TRADES TABLE (existing — collapsible with filters)
   ================================================================ */

function TradesTable({
  trades,
  totalTrades,
}: {
  trades: Array<Record<string, unknown>>;
  totalTrades: number;
}) {
  const [open, setOpen] = useState(false);
  const [filterSym, setFilterSym] = useState("");
  const [filterDir, setFilterDir] = useState("");

  const symbols = useMemo(() => {
    const s = new Set(trades.map((t) => t.symbol as string));
    return Array.from(s).sort();
  }, [trades]);

  const filtered = useMemo(() => {
    let result = trades;
    if (filterSym) result = result.filter((t) => t.symbol === filterSym);
    if (filterDir) result = result.filter((t) => t.direction === filterDir);
    return result;
  }, [trades, filterSym, filterDir]);

  return (
    <div className="rounded-lg border border-[#262626] bg-[#141414]">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-5 py-3 text-left font-semibold transition-colors hover:bg-[#1a1a1a]"
      >
        <span className="text-white">
          Trades{" "}
          <span className="text-sm font-normal text-gray-500">
            ({totalTrades} total)
          </span>
        </span>
        <span className={`text-gray-500 text-sm transition-transform ${open ? "rotate-180" : ""}`}>
          {"\u25BC"}
        </span>
      </button>
      {open && (
        <div className="border-t border-[#262626] px-5 py-4">
          <div className="mb-3 flex flex-wrap gap-2">
            <select
              value={filterSym}
              onChange={(e) => setFilterSym(e.target.value)}
              className="rounded border border-[#262626] bg-[#1a1a1a] px-2 py-1 text-xs text-gray-300"
            >
              <option value="">All pairs</option>
              {symbols.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select
              value={filterDir}
              onChange={(e) => setFilterDir(e.target.value)}
              className="rounded border border-[#262626] bg-[#1a1a1a] px-2 py-1 text-xs text-gray-300"
            >
              <option value="">All directions</option>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#262626] text-left">
                  <th className="pb-2 pr-4 text-[11px] uppercase tracking-wide font-medium text-neutral-500">Date</th>
                  <th className="pb-2 pr-4 text-[11px] uppercase tracking-wide font-medium text-neutral-500">Symbol</th>
                  <th className="pb-2 pr-4 text-[11px] uppercase tracking-wide font-medium text-neutral-500">Dir</th>
                  <th className="pb-2 pr-4 text-[11px] uppercase tracking-wide font-medium text-neutral-500">Lot</th>
                  <th className="pb-2 pr-4 text-[11px] uppercase tracking-wide font-medium text-neutral-500 text-right">P&L</th>
                  <th className="pb-2 text-[11px] uppercase tracking-wide font-medium text-neutral-500 text-center">SL</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 100).map((t, i) => {
                  const pnl =
                    ((t.profit_money as number) || 0) +
                    ((t.commission as number) || 0) +
                    ((t.swap as number) || 0);
                  const closed = t.closed_at as string | null;
                  const dateStr = closed
                    ? new Date(closed).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "\u2014";
                  return (
                    <tr key={i} className="border-b border-[#262626] last:border-0">
                      <td className="py-1.5 pr-4 font-mono text-xs text-gray-500">{dateStr}</td>
                      <td className="py-1.5 pr-4 font-medium text-xs text-white">{t.symbol as string}</td>
                      <td className="py-1.5 pr-4">
                        <span className={`text-xs ${t.direction === "buy" ? "text-emerald-400" : "text-red-400"}`}>
                          {(t.direction as string).toUpperCase()}
                        </span>
                      </td>
                      <td className="py-1.5 pr-4 font-mono text-xs text-gray-400">{t.lot as number}</td>
                      <td className={`py-1.5 pr-4 text-right font-mono text-xs ${pnlColor(pnl)}`}>
                        {fmtPnl(pnl)}
                      </td>
                      <td className="py-1.5 text-center">
                        {hasSL(t.stop_loss) ? (
                          <span className="text-emerald-400">{"\u2713"}</span>
                        ) : (
                          <span className="text-red-400">{"\u2717"}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {filtered.length > 100 && (
            <p className="mt-2 text-center text-xs text-gray-500">
              Showing 100 of {filtered.length} trades
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   LOADING SKELETON (v0 style)
   ================================================================ */

function DashboardSkeleton() {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-7 w-32 animate-pulse rounded bg-[#262626]" />
          <div className="h-5 w-20 animate-pulse rounded bg-[#262626]" />
        </div>
        <div className="flex items-center gap-3">
          <div className="h-9 w-28 animate-pulse rounded bg-[#262626]" />
          <div className="h-9 w-24 animate-pulse rounded bg-[#262626]" />
        </div>
      </div>
      <div className="px-6 pb-8 space-y-4">
        <div className="bg-[#141414] border border-[#262626] rounded-lg h-[200px] animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="md:col-span-2 bg-[#141414] border border-[#262626] rounded-lg h-[280px] animate-pulse" />
          <div className="bg-[#141414] border border-[#262626] rounded-lg h-[280px] animate-pulse" />
          <div className="bg-[#141414] border border-[#262626] rounded-lg h-[280px] animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[#141414] border border-[#262626] rounded-lg h-[280px] animate-pulse" />
          <div className="bg-[#141414] border border-[#262626] rounded-lg h-[280px] animate-pulse" />
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   MAIN PAGE
   ================================================================ */

export default function DashboardPage() {
  const params = useParams();
  const accountId = params.accountId as string;
  const { user } = useUser();

  const router = useRouter();
  const [coachingLoading, setCoachingLoading] = useState(false);
  const [coachingError, setCoachingError] = useState("");

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);

  // Period filter state
  const [period, setPeriod] = useState<PeriodKey>("all");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  // SWR keys — include period so changing filter auto-refetches
  const range = useMemo(
    () =>
      period === "custom"
        ? { from: customFrom || undefined, to: customTo || undefined }
        : getDateRange(period),
    [period, customFrom, customTo],
  );

  const dashParams = useMemo(() => {
    const p = new URLSearchParams({ account_id: accountId });
    if (range.from) p.set("since", range.from);
    if (range.to) p.set("until", range.to);
    return p.toString();
  }, [accountId, range]);

  const dashKey = user ? `/api/dashboard/${user.id}?${dashParams}` : null;
  const acctKey = `/api/accounts/detail/${accountId}`;

  const { data, error: dashError, isLoading: dashLoading } = useSWR<DashboardData>(
    dashKey,
    fetcher,
    { dedupingInterval: CACHE_TTL },
  );
  const { data: account } = useSWR<AccountSummary>(acctKey, fetcher);

  const loading = dashLoading && !data;
  const error = dashError?.message ?? "";

  const forceReload = useCallback(() => {
    if (dashKey) mutate(dashKey);
    mutate(acctKey);
  }, [dashKey, acctKey]);

  const handleUpload = useCallback(
    async (f: File) => {
      if (!user) return;
      setUploading(true);
      setUploadResult(null);
      try {
        const res = await uploadTrades(user.id, accountId, f);
        setUploadResult(
          `${res.trades_saved} new trades saved (${res.trades_duplicate} duplicates skipped)`
        );
        if (res.trades_saved > 0) setTimeout(forceReload, 1500);
      } catch {
        setUploadResult("Upload failed. Check file format.");
      }
      setUploading(false);
    },
    [user, accountId, forceReload],
  );

  const handleCoaching = useCallback(async () => {
    if (!user) return;
    setCoachingLoading(true);
    setCoachingError("");
    try {
      const res = await requestCoaching(user.id, accountId);
      mutate((key: string) => typeof key === "string" && key.includes("/api/coaching/sessions/"));
      router.push(`/app/coaching/${res.session_id}`);
    } catch (e: unknown) {
      setCoachingError(
        e instanceof Error ? e.message : "Coaching request failed",
      );
      setCoachingLoading(false);
    }
  }, [user, accountId, router]);

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <p className="text-red-400">Error: {error}</p>
      </div>
    );
  }

  if (!data || data.total_trades === 0) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 px-6">
          <p className="text-gray-400">
            No trades yet. Upload your trade history to get started.
          </p>
          {user && (
            <label className="cursor-pointer">
              <input
                type="file"
                accept=".csv,.txt,.xlsx,.xls"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleUpload(f);
                }}
              />
              <Button variant="outline" size="sm" asChild>
                <span>{uploading ? "Uploading..." : "Upload trades"}</span>
              </Button>
            </label>
          )}
          {uploadResult && (
            <span className="text-xs text-gray-400">{uploadResult}</span>
          )}
        </div>
      </div>
    );
  }

  const startingBalance = account?.starting_balance ?? 0;

  return (
    <div className="max-w-5xl mx-auto">
      <DashboardHeader
        totalTrades={data.total_trades}
        period={period}
        onPeriodChange={setPeriod}
        customFrom={customFrom}
        customTo={customTo}
        onCustomChange={(f, t) => {
          setCustomFrom(f);
          setCustomTo(t);
        }}
        onUpload={handleUpload}
        uploading={uploading}
        uploadResult={uploadResult}
        onCoaching={handleCoaching}
        coachingLoading={coachingLoading}
      />

      {coachingError && (
        <div className="mx-6 mb-4 rounded-md bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          {coachingError}
        </div>
      )}

      <div className="px-6 pb-8 space-y-4">
        {/* ROW 1: Performance + Behavioral metrics card */}
        <TradingMetricsCard
          data={data}
          behavioral={data.behavioral}
        />

        {/* ROW 2: Equity Curve (50%) + Trades by Instrument (25%) + P&L by Instrument (25%) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">
          <div className="md:col-span-2 flex">
            <EquityCurveChart data={data} startingBalance={startingBalance} />
          </div>
          <div className="md:col-span-1 flex">
            <TradesByInstrumentChart pnlBySymbol={data.pnl_by_symbol} />
          </div>
          <div className="md:col-span-1 flex">
            <PnlByInstrumentChart pnlBySymbol={data.pnl_by_symbol} />
          </div>
        </div>

        {/* ROW 3: P&L by Day (50%) + P&L by Hour/Session toggle (50%) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
          <PnlByDayChart data={data.pnl_by_day_of_week} />
          <PnlHourSessionChart hourData={data.pnl_by_hour} sessionData={data.pnl_by_session} />
        </div>

        {/* ROW 4: Trades Table (collapsible) */}
        <TradesTable trades={data.trades} totalTrades={data.total_trades} />
      </div>
    </div>
  );
}
