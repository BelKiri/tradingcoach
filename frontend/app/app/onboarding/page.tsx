"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useUser } from "@/lib/hooks/useUser";
import { createAccount, uploadTrades } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const { user } = useUser();

  const [name, setName] = useState("");
  const [balance, setBalance] = useState("");
  const [brokerTz, setBrokerTz] = useState("UTC+2");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) setFile(f);
    },
    []
  );

  async function handleSubmit() {
    if (!user) return;
    if (!name.trim()) {
      setError("Account name is required");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Create account
      const acct = await createAccount(
        user.id,
        name.trim(),
        balance ? parseFloat(balance) : null,
        undefined,
        brokerTz,
      );

      // Upload file if provided
      if (file) {
        const result = await uploadTrades(user.id, acct.id, file);
        if (result.errors.length > 0 && result.trades_saved === 0) {
          setError(`Upload failed: ${result.errors[0]}`);
          setLoading(false);
          return;
        }
      }

      router.push(`/app/dashboard/${acct.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl py-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold">Add trading account</h1>
        <p className="mt-2 text-muted-foreground">
          Set up your account, then upload trades or connect an exchange.
        </p>
      </div>

      {/* Account info */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle className="text-lg">Account details</CardTitle>
          <CardDescription>
            Give your account a name so you can identify it.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium">
              Account name
            </label>
            <Input
              placeholder='e.g. "Exness Main" or "Binance Futures"'
              value={name}
              onChange={(e) => { setName(e.target.value); setError(""); }}
            />
            {error && (
              <p className="mt-1.5 text-sm text-red-500">{error}</p>
            )}
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium">
              Starting balance ($)
            </label>
            <Input
              type="number"
              placeholder="10000"
              value={balance}
              onChange={(e) => setBalance(e.target.value)}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Used for drawdown % and risk % calculations.
            </p>
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium">
              Broker timezone
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={brokerTz}
              onChange={(e) => setBrokerTz(e.target.value)}
            >
              <option value="UTC-5">UTC-5 (New York)</option>
              <option value="UTC-4">UTC-4 (Eastern DST)</option>
              <option value="UTC+0">UTC+0 (London / Exchange API)</option>
              <option value="UTC+1">UTC+1 (Central Europe)</option>
              <option value="UTC+2">UTC+2 (Most MT4/MT5 brokers)</option>
              <option value="UTC+3">UTC+3 (MT4/MT5 DST / Moscow)</option>
              <option value="UTC+8">UTC+8 (Singapore / Hong Kong)</option>
              <option value="UTC+9">UTC+9 (Tokyo)</option>
            </select>
            <p className="mt-1 text-xs text-muted-foreground">
              Check your broker&apos;s server time. Most MT4/MT5 brokers use UTC+2 (or UTC+3 in summer).
            </p>
          </div>
        </CardContent>
      </Card>

      {/* File upload */}
      <h2 className="mb-4 mt-10 text-lg font-semibold">
        Upload trade history (optional)
      </h2>

      <div className="grid gap-4 sm:grid-cols-2">
        <div
          className={`cursor-pointer rounded-lg border-2 border-dashed p-6 transition-colors ${
            dragOver
              ? "border-primary bg-primary/5"
              : file
              ? "border-emerald-500/50 bg-emerald-500/5"
              : "hover:border-muted-foreground/50"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept=".csv,.txt,.xlsx,.xls"
            className="hidden"
            onChange={handleFileSelect}
          />
          <div className="flex h-32 flex-col items-center justify-center text-center">
            {file ? (
              <>
                <p className="text-2xl text-emerald-400">{"\u2713"}</p>
                <p className="mt-2 text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </>
            ) : (
              <>
                <p className="text-2xl text-muted-foreground">+</p>
                <p className="mt-1 text-sm font-medium">Drop file here</p>
                <p className="text-xs text-muted-foreground">
                  CSV or Excel from any broker
                </p>
              </>
            )}
          </div>
        </div>

        <Link href="/app/connect" onClick={() => setBrokerTz("UTC+0")}>
          <Card className="h-full cursor-pointer transition-colors hover:border-primary/50">
            <CardHeader>
              <CardTitle className="text-base">Connect API</CardTitle>
              <CardDescription>
                Auto-sync trades from your exchange
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-32 flex-col items-center justify-center text-muted-foreground">
                <p className="text-2xl">{"\u26a1"}</p>
                <p className="mt-1 text-sm">Connect exchange</p>
              </div>
              <p className="text-xs text-muted-foreground">
                Binance, Bybit, OKX &mdash; coming soon
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>

      <div className="mt-8 flex justify-end">
        <Button size="lg" onClick={handleSubmit} disabled={loading}>
          {loading ? "Creating..." : "Create Account"}
        </Button>
      </div>
    </div>
  );
}
