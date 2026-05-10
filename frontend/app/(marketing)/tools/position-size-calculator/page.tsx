import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function PositionSizeCalculator() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Position Size Calculator</h1>
        <p className="mt-2 text-muted-foreground">
          Calculate the correct lot size for any trade based on your risk
          tolerance.
        </p>
      </div>

      <Card className="mt-10">
        <CardHeader>
          <CardTitle className="text-lg">Calculate your position</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                Account Balance ($)
              </label>
              <Input type="number" placeholder="10000" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                Risk per Trade (%)
              </label>
              <Input type="number" placeholder="2" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                Stop Loss (pips)
              </label>
              <Input type="number" placeholder="30" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                Currency Pair
              </label>
              <Input placeholder="EURUSD" />
            </div>
          </div>

          <Button className="w-full" size="lg">
            Calculate
          </Button>

          <div className="rounded-lg bg-muted p-6 text-center">
            <p className="text-sm text-muted-foreground">Recommended lot size</p>
            <p className="mt-1 text-4xl font-bold text-primary">0.67</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Risk: $200 (2.0% of $10,000) &bull; Pip value: $6.67
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="mt-8 text-center">
        <p className="text-sm text-muted-foreground">
          Want to track if you actually follow your position sizing?
        </p>
        <Button asChild variant="link" className="mt-1">
          <Link href="/signup">Try TradeCoach free &rarr;</Link>
        </Button>
      </div>
    </div>
  );
}
