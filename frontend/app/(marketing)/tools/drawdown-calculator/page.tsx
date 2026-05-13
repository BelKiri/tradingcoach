import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function DrawdownCalculator() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Drawdown Calculator</h1>
        <p className="mt-2 text-muted-foreground">
          See how consecutive losses impact your account and how much you need
          to recover.
        </p>
      </div>

      <Card className="mt-10">
        <CardHeader>
          <CardTitle className="text-lg">Calculate drawdown impact</CardTitle>
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
                Consecutive Losses
              </label>
              <Input type="number" placeholder="5" />
            </div>
          </div>

          <Button className="w-full" size="lg">
            Calculate
          </Button>

          <div className="space-y-3 rounded-lg bg-muted p-6">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">
                After 5 consecutive losses
              </p>
              <p className="mt-1 text-4xl font-bold text-red-400">-9.6%</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Balance: $9,039 &bull; Lost: $961 &bull; Need +10.6% to recover
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="mt-8 text-center">
        <p className="text-sm text-muted-foreground">
          TradingCoach tracks your real drawdown from peak equity automatically.
        </p>
        <Button asChild variant="link" className="mt-1">
          <Link href="/signup">Try TradingCoach free &rarr;</Link>
        </Button>
      </div>
    </div>
  );
}
