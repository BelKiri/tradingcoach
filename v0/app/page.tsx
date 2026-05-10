import { TradingMetricsCard } from "@/components/trading-metrics-card"
import { Navbar } from "@/components/navbar"
import { DashboardHeader } from "@/components/dashboard-header"
import { ChartsRow } from "@/components/charts-row"
import { AnalyticsRow } from "@/components/analytics-row"

export default function Page() {
  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Navbar />
      <main className="max-w-5xl mx-auto">
        <DashboardHeader />
        <div className="px-6 pb-8 space-y-4">
          <TradingMetricsCard />
          <ChartsRow />
          <AnalyticsRow />
        </div>
      </main>
    </div>
  )
}
