"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

const allData = [
  { name: "USDJPY", pnl: 755 },
  { name: "US500", pnl: 584 },
  { name: "BTCUSD", pnl: 572 },
  { name: "GBPUSD", pnl: 320 },
  { name: "NZDUSD", pnl: 180 },
  { name: "AUDUSD", pnl: -95 },
  { name: "XAUUSD", pnl: -263 },
  { name: "XAGUSD", pnl: -924 },
  { name: "EURUSD", pnl: -1049 },
]

const gainers = allData.filter(d => d.pnl > 0).sort((a, b) => b.pnl - a.pnl)
const losers = allData.filter(d => d.pnl < 0).sort((a, b) => a.pnl - b.pnl)

const top3Gainers = gainers.slice(0, 3)
const top3Losers = losers.slice(0, 3)

export function PnlByInstrumentChart() {
  const [isModalOpen, setIsModalOpen] = useState(false)

  return (
    <>
      <div className="rounded-lg border border-[#262626] bg-[#141414] p-2.5 h-[280px] flex flex-col">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[#d4a843]">
          P&L by Instrument
        </h3>
        
        {/* Top Gainers */}
        <div className="mt-1.5">
          <h4 className="text-[9px] uppercase tracking-wide text-[#d4a843] mb-0.5">Top Gainers</h4>
          {top3Gainers.map((item) => (
            <div 
              key={item.name} 
              className="flex items-center justify-between h-6"
            >
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
          {top3Losers.map((item) => (
            <div 
              key={item.name} 
              className="flex items-center justify-between h-6"
            >
              <span className="text-[11px] text-white">{item.name}</span>
              <span className="text-[11px] text-red-500 tabular-nums font-medium">
                -${Math.abs(item.pnl).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
        
        <div className="mt-auto pt-1.5">
          <button
            onClick={() => setIsModalOpen(true)}
            className="text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
          >
            Show all instruments
          </button>
        </div>
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="bg-[#0a0a0a] border-[#262626] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">P&L by Instrument (all)</DialogTitle>
          </DialogHeader>
          <div className="mt-4 space-y-4">
            {/* All Gainers */}
            <div>
              <h4 className="text-[9px] uppercase tracking-wide text-[#d4a843] mb-1">Top Gainers</h4>
              {gainers.map((item) => (
                <div 
                  key={item.name} 
                  className="flex items-center justify-between h-6"
                >
                  <span className="text-[11px] text-white">{item.name}</span>
                  <span className="text-[11px] text-emerald-500 tabular-nums font-medium">
                    +${item.pnl.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
            {/* All Losers */}
            <div>
              <h4 className="text-[9px] uppercase tracking-wide text-[#d4a843] mb-1">Top Losers</h4>
              {losers.map((item) => (
                <div 
                  key={item.name} 
                  className="flex items-center justify-between h-6"
                >
                  <span className="text-[11px] text-white">{item.name}</span>
                  <span className="text-[11px] text-red-500 tabular-nums font-medium">
                    -${Math.abs(item.pnl).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
