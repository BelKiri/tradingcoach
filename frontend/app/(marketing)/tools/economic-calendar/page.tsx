import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";

const events = [
  {
    time: "08:30",
    currency: "USD",
    event: "Non-Farm Payrolls",
    impact: "high",
    forecast: "180K",
    previous: "175K",
  },
  {
    time: "08:30",
    currency: "USD",
    event: "Unemployment Rate",
    impact: "high",
    forecast: "3.8%",
    previous: "3.7%",
  },
  {
    time: "10:00",
    currency: "USD",
    event: "ISM Manufacturing PMI",
    impact: "high",
    forecast: "49.5",
    previous: "49.1",
  },
  {
    time: "12:00",
    currency: "EUR",
    event: "ECB President Lagarde Speaks",
    impact: "medium",
    forecast: "\u2014",
    previous: "\u2014",
  },
  {
    time: "14:00",
    currency: "GBP",
    event: "BoE Interest Rate Decision",
    impact: "high",
    forecast: "5.25%",
    previous: "5.25%",
  },
  {
    time: "19:00",
    currency: "USD",
    event: "FOMC Meeting Minutes",
    impact: "high",
    forecast: "\u2014",
    previous: "\u2014",
  },
  {
    time: "21:30",
    currency: "AUD",
    event: "Employment Change",
    impact: "medium",
    forecast: "25.0K",
    previous: "14.6K",
  },
];

function ImpactDot({ level }: { level: string }) {
  const color =
    level === "high"
      ? "bg-red-400"
      : level === "medium"
      ? "bg-amber-400"
      : "bg-emerald-400";
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />;
}

export default function EconomicCalendar() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Economic Calendar</h1>
        <p className="mt-2 text-muted-foreground">
          Key economic events that move the markets. All times in UTC.
        </p>
      </div>

      <div className="mt-6 flex items-center justify-center gap-4">
        <Badge variant="secondary">Today</Badge>
        <span className="text-sm text-muted-foreground">
          Friday, March 14, 2026
        </span>
      </div>

      <div className="mt-8 overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-3 text-left font-medium">Time</th>
              <th className="p-3 text-left font-medium">Currency</th>
              <th className="p-3 text-left font-medium">Event</th>
              <th className="p-3 text-center font-medium">Impact</th>
              <th className="p-3 text-right font-medium">Forecast</th>
              <th className="p-3 text-right font-medium">Previous</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr
                key={`${e.time}-${e.event}`}
                className={i < events.length - 1 ? "border-b" : ""}
              >
                <td className="p-3 font-mono text-muted-foreground">
                  {e.time}
                </td>
                <td className="p-3">
                  <Badge variant="outline" className="font-mono text-xs">
                    {e.currency}
                  </Badge>
                </td>
                <td className="p-3 font-medium">{e.event}</td>
                <td className="p-3 text-center">
                  <ImpactDot level={e.impact} />
                </td>
                <td className="p-3 text-right font-mono">{e.forecast}</td>
                <td className="p-3 text-right font-mono text-muted-foreground">
                  {e.previous}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8 text-center">
        <p className="text-sm text-muted-foreground">
          TradeCoach checks news impact before every trade in the Trade Checker.
        </p>
        <Button asChild variant="link" className="mt-1">
          <Link href="/signup">Try TradeCoach free &rarr;</Link>
        </Button>
      </div>
    </div>
  );
}
