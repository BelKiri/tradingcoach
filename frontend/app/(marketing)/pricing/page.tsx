import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const features = [
  { name: "Trade uploads (CSV/Excel)", free: "Unlimited", pro: "Unlimited" },
  { name: "Performance dashboard", free: "Full", pro: "Full" },
  { name: "Behavioral analysis", free: "\u2713", pro: "\u2713" },
  { name: "AI coaching sessions", free: "1", pro: "Unlimited" },
  { name: "Progress tracking", free: "\u2014", pro: "\u2713" },
  { name: "Multiple trading accounts", free: "\u2014", pro: "\u2713" },
  { name: "Weekly AI action plan", free: "\u2014", pro: "Monday briefing" },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-20">
      <div className="text-center">
        <h1 className="text-4xl font-bold">Pricing</h1>
        <p className="mt-3 text-lg text-muted-foreground">
          Start free with full analytics. Upgrade for unlimited AI coaching and
          progress tracking.
        </p>
      </div>

      {/* Cards */}
      <div className="mt-12 grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Free</CardTitle>
            <p className="text-4xl font-bold mt-2">
              $0
              <span className="text-base font-normal text-muted-foreground">
                /forever
              </span>
            </p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {[
                "Unlimited trade uploads (CSV/Excel)",
                "Full performance dashboard",
                "Behavioral analysis",
                "1 AI coaching session",
              ].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <span className="text-primary">{"\u2713"}</span>
                  {f}
                </li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            <Button asChild variant="outline" className="w-full">
              <Link href="/signup">Start Free</Link>
            </Button>
          </CardFooter>
        </Card>

        <Card className="relative border-primary/50">
          <CardHeader>
            <CardTitle>Pro</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              For serious traders who want to improve
            </p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2 text-muted-foreground">
                <span className="text-primary">{"\u2713"}</span>
                Everything in Free, plus:
              </li>
              {[
                "Unlimited AI coaching sessions",
                "Progress tracking",
                "Multiple trading accounts",
                "Weekly AI action plan (Monday briefing)",
              ].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <span className="text-primary">{"\u2713"}</span>
                  {f}
                </li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            <Button asChild className="w-full">
              <Link href="/signup">Start Free, Upgrade Later</Link>
            </Button>
          </CardFooter>
        </Card>
      </div>

      {/* Comparison table */}
      <div className="mt-16">
        <h2 className="mb-8 text-center text-2xl font-bold">
          Full comparison
        </h2>
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="p-4 text-left font-medium">Feature</th>
                <th className="p-4 text-center font-medium">Free</th>
                <th className="p-4 text-center font-medium text-primary">
                  Pro
                </th>
              </tr>
            </thead>
            <tbody>
              {features.map((f, i) => (
                <tr
                  key={f.name}
                  className={i < features.length - 1 ? "border-b" : ""}
                >
                  <td className="p-4">{f.name}</td>
                  <td className="p-4 text-center text-muted-foreground">
                    {f.free}
                  </td>
                  <td className="p-4 text-center">{f.pro}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
