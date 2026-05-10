import { EquityCurveChart } from "@/components/equity-curve-chart"
import { TradesByInstrumentChart } from "@/components/trades-by-instrument-chart"
import { PnlByInstrumentChart } from "@/components/pnl-by-instrument-chart"

export function ChartsRow() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Equity Curve - 50% on desktop (2 cols of 4) */}
      <div className="md:col-span-2">
        <EquityCurveChart />
      </div>
      {/* Trades by Instrument - 25% on desktop */}
      <div className="md:col-span-1">
        <TradesByInstrumentChart />
      </div>
      {/* P&L by Instrument - 25% on desktop */}
      <div className="md:col-span-1">
        <PnlByInstrumentChart />
      </div>
    </div>
  )
}
