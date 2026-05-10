"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function CheckerPage() {
  return (
    <div className="relative mx-auto max-w-3xl space-y-8">
      {/* Under development overlay */}
      <div className="absolute inset-0 z-20 flex items-center justify-center rounded-lg" style={{ backgroundColor: "rgba(10, 10, 10, 0.85)" }}>
        <div className="text-center px-8 py-12">
          <p className="text-4xl mb-4">&#128679;</p>
          <h2 className="text-2xl font-bold text-white">
            Trade Checker is under development
          </h2>
          <p className="mt-3 text-base text-gray-400 max-w-md mx-auto">
            This feature will allow you to check any trade before you open it.
          </p>
          <p
            className="mt-4 text-sm font-semibold"
            style={{ color: "var(--brand-gold, #d4a843)" }}
          >
            Coming soon.
          </p>
        </div>
      </div>

      {/* Dimmed/blurred form underneath */}
      <div className="pointer-events-none select-none blur-[2px] opacity-40">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Trade Checker</h1>
            <p className="text-sm text-muted-foreground">
              Validate your trade before you place it. AI checks risk, news, and
              your history.
            </p>
          </div>
          <Badge variant="secondary" className="text-sm">
            1/1 checks remaining today
          </Badge>
        </div>

        {/* Input form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">New trade check</CardTitle>
            <CardDescription>
              Enter your planned trade details.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  Pair / Symbol
                </label>
                <Input placeholder="XAUUSD" readOnly />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  Direction
                </label>
                <div className="flex gap-2">
                  <Button variant="outline" className="flex-1 border-emerald-500/30 text-emerald-400">
                    BUY
                  </Button>
                  <Button variant="outline" className="flex-1 border-red-500/30 text-red-400">
                    SELL
                  </Button>
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  Lot Size
                </label>
                <Input type="number" placeholder="0.50" readOnly />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  Stop Loss (price)
                </label>
                <Input type="number" placeholder="2280.00" readOnly />
              </div>
            </div>

            <Button className="w-full" size="lg" disabled>
              Check Trade
            </Button>
          </CardContent>
        </Card>

        {/* Result area */}
        <Card className="border-amber-500/30">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Check Result</CardTitle>
              <Badge variant="warning">Proceed with caution</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">Risk</p>
                <p className="mt-1 font-semibold text-amber-400">
                  2.8% ($280)
                </p>
                <p className="text-xs text-muted-foreground">
                  Above your 2% target
                </p>
              </div>
              <div className="rounded-md bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">Today&apos;s trades</p>
                <p className="mt-1 font-semibold">3 trades</p>
                <p className="text-xs text-muted-foreground">
                  Below 5-trade limit
                </p>
              </div>
              <div className="rounded-md bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">Loss streak</p>
                <p className="mt-1 font-semibold text-red-400">
                  2 consecutive losses
                </p>
                <p className="text-xs text-muted-foreground">
                  Consider reducing size
                </p>
              </div>
              <div className="rounded-md bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">
                  Your XAUUSD history
                </p>
                <p className="mt-1 font-semibold">62% WR, +$2,450</p>
                <p className="text-xs text-muted-foreground">
                  Best pair — good choice
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
