import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function PipCalculator() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Pip Value Calculator</h1>
        <p className="mt-2 text-muted-foreground">
          Calculate the monetary value of a pip for any currency pair and lot
          size.
        </p>
      </div>

      <Card className="mt-10">
        <CardHeader>
          <CardTitle className="text-lg">Calculate pip value</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                Currency Pair
              </label>
              <Input placeholder="EURUSD" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                Lot Size
              </label>
              <Input type="number" placeholder="1.00" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                Account Currency
              </label>
              <Input placeholder="USD" />
            </div>
          </div>

          <Button className="w-full" size="lg">
            Calculate
          </Button>

          <div className="rounded-lg bg-muted p-6 text-center">
            <p className="text-sm text-muted-foreground">Pip value</p>
            <p className="mt-1 text-4xl font-bold text-primary">$10.00</p>
            <p className="mt-2 text-sm text-muted-foreground">
              1 standard lot EURUSD &bull; 10 pip move = $100.00
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="mt-8 text-center">
        <p className="text-sm text-muted-foreground">
          TradingCoach calculates pip values automatically from your trade
          history.
        </p>
        <Button asChild variant="link" className="mt-1">
          <Link href="/signup">Try TradingCoach free &rarr;</Link>
        </Button>
      </div>
    </div>
  );
}
