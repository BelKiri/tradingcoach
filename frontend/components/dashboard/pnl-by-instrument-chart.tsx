"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface PnlByInstrumentChartProps {
  pnlBySymbol: Record<string, { pnl: number; win_rate: number; trades: number }>;
}

export function PnlByInstrumentChart({ pnlBySymbol }: PnlByInstrumentChartProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { gainers, losers } = useMemo(() => {
    const all = Object.entries(pnlBySymbol)
      .map(([name, d]) => ({ name, pnl: Math.round(d.pnl * 100) / 100 }));
    return {
      gainers: all.filter((d) => d.pnl > 0).sort((a, b) => b.pnl - a.pnl),
      losers: all.filter((d) => d.pnl < 0).sort((a, b) => a.pnl - b.pnl),
    };
  }, [pnlBySymbol]);

  const top3Gainers = gainers.slice(0, 3);
  const top3Losers = losers.slice(0, 3);
  const hasMore = gainers.length > 3 || losers.length > 3;

  return (
    <>
      <div className="rounded-lg border border-[#262626] bg-[#141414] p-2.5 w-full h-full">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
          P&L by Instrument
        </h3>

        {/* Top Gainers */}
        <div className="mt-1.5">
          <h4 className="text-[9px] uppercase tracking-wide text-[#d4a843] mb-0.5">Top Gainers</h4>
          {top3Gainers.length === 0 && (
            <p className="text-[11px] text-neutral-400 h-6 flex items-center">No gainers</p>
          )}
          {top3Gainers.map((item) => (
            <div key={item.name} className="flex items-center justify-between h-6">
              <span className="text-[11px] text-white">{item.name}</span>
              <span className="text-[11px] text-emerald-500 tabular-nums font-medium">
                +${item.pnl.toLocaleString()}
              </span>
            </div>
          ))}
        </div>

        {/* Top Losers */}
        <div className="mt-2">
          <h4 className="text-[9px] uppercase tracking-wide text-[#d4a843] mb-0.5">Top Losers</h4>
          {top3Losers.length === 0 && (
            <p className="text-[11px] text-neutral-400 h-6 flex items-center">No losers</p>
          )}
          {top3Losers.map((item) => (
            <div key={item.name} className="flex items-center justify-between h-6">
              <span className="text-[11px] text-white">{item.name}</span>
              <span className="text-[11px] text-red-500 tabular-nums font-medium">
                -${Math.abs(item.pnl).toLocaleString()}
              </span>
            </div>
          ))}
        </div>

        {hasMore && (
          <div className="text-center pt-3 pb-2">
            <button
              onClick={() => setIsModalOpen(true)}
              className="text-xs text-neutral-400 hover:text-gray-300 transition-colors"
            >
              Show all
            </button>
          </div>
        )}
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="bg-[#0a0a0a] border-[#262626] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">P&L by Instrument (all)</DialogTitle>
          </DialogHeader>
          <div className="mt-4 space-y-4">
            {gainers.length > 0 && (
              <div>
                <h4 className="text-[9px] uppercase tracking-wide text-[#d4a843] mb-1">Top Gainers</h4>
                {gainers.map((item) => (
                  <div key={item.name} className="flex items-center justify-between h-6">
                    <span className="text-[11px] text-white">{item.name}</span>
                    <span className="text-[11px] text-emerald-500 tabular-nums font-medium">
                      +${item.pnl.toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {losers.length > 0 && (
              <div>
                <h4 className="text-[9px] uppercase tracking-wide text-[#d4a843] mb-1">Top Losers</h4>
                {losers.map((item) => (
                  <div key={item.name} className="flex items-center justify-between h-6">
                    <span className="text-[11px] text-white">{item.name}</span>
                    <span className="text-[11px] text-red-500 tabular-nums font-medium">
                      -${Math.abs(item.pnl).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
