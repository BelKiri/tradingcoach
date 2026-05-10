import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const exchanges = [
  { name: "Binance", status: "Available", desc: "Futures & Spot trading" },
  { name: "Bybit", status: "Available", desc: "Derivatives & Spot" },
  { name: "OKX", status: "Coming soon", desc: "Futures & Spot" },
];

const propFirms = [
  {
    name: "cTrader",
    status: "Coming soon",
    desc: "FTMO, The Funded Trader, etc.",
  },
];

export default function ConnectPage() {
  return (
    <div className="mx-auto max-w-3xl py-8">
      <h1 className="text-2xl font-bold">Connect your platform</h1>
      <p className="mt-2 text-muted-foreground">
        Auto-sync trades from your exchange or trading platform.
      </p>

      {/* Crypto */}
      <h2 className="mb-4 mt-10 text-lg font-semibold">
        Crypto exchanges
      </h2>
      <div className="grid gap-4 sm:grid-cols-3">
        {exchanges.map((ex) => (
          <Card key={ex.name}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{ex.name}</CardTitle>
                <Badge
                  variant={
                    ex.status === "Available" ? "success" : "secondary"
                  }
                  className="text-[10px]"
                >
                  {ex.status}
                </Badge>
              </div>
              <CardDescription className="text-xs">{ex.desc}</CardDescription>
            </CardHeader>
            <CardContent>
              {ex.status === "Available" ? (
                <div className="space-y-2">
                  <Input placeholder="API Key" className="text-xs" />
                  <Input
                    placeholder="API Secret"
                    type="password"
                    className="text-xs"
                  />
                  <Button size="sm" className="w-full">
                    Connect
                  </Button>
                </div>
              ) : (
                <p className="text-center text-xs text-muted-foreground py-4">
                  Coming soon
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Prop firms */}
      <h2 className="mb-4 mt-10 text-lg font-semibold">Prop firms</h2>
      <div className="grid gap-4 sm:grid-cols-3">
        {propFirms.map((pf) => (
          <Card key={pf.name}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{pf.name}</CardTitle>
                <Badge variant="secondary" className="text-[10px]">
                  {pf.status}
                </Badge>
              </div>
              <CardDescription className="text-xs">{pf.desc}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-center text-xs text-muted-foreground py-4">
                Coming soon
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Forex */}
      <h2 className="mb-4 mt-10 text-lg font-semibold">Forex brokers</h2>
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">
            Forex brokers don&apos;t offer public APIs for trade history.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Export your trades as CSV or Excel and upload them manually. We
            support MT4, MT5, cTrader, and any broker format.
          </p>
          <Button variant="outline" className="mt-4">
            Go to Upload
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
