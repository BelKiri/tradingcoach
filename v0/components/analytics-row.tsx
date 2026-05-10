import { PnlBySessionChart } from "@/components/pnl-by-session-chart"
import { PnlByDayChart } from "@/components/pnl-by-day-chart"
import { PnlByHourChart } from "@/components/pnl-by-hour-chart"

export function AnalyticsRow() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <PnlBySessionChart />
      <PnlByDayChart />
      <PnlByHourChart />
    </div>
  )
}
