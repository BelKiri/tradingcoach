"use client";

import Link from "next/link";
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AccountCardSkeleton } from "@/components/ui/skeleton";
import { useUser } from "@/lib/hooks/useUser";
import { fetcher } from "@/lib/swr";
import type { AccountSummary } from "@/lib/api";

export default function AppHomePage() {
  const { user, loading: userLoading } = useUser();

  const { data: accountsData, isLoading } = useSWR<{ accounts: AccountSummary[] }>(
    user ? `/api/accounts/${user.id}` : null,
    fetcher,
  );

  const accounts = accountsData?.accounts ?? [];

  if ((userLoading || isLoading) && accounts.length === 0) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-7 w-40 animate-pulse rounded bg-muted/50" />
            <div className="mt-2 h-4 w-64 animate-pulse rounded bg-muted/50" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <AccountCardSkeleton />
          <AccountCardSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Welcome back</h1>
          <p className="text-sm text-muted-foreground">
            {accounts.length > 0
              ? `You have ${accounts.length} trading account${accounts.length > 1 ? "s" : ""}.`
              : "Get started by adding your first trading account."}
          </p>
        </div>
        <Button asChild>
          <Link href="/app/onboarding">+ Add Account</Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {accounts.map((acct) => (
          <Link key={acct.id} href={`/app/dashboard/${acct.id}`}>
            <Card className="transition-colors hover:border-primary/30">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{acct.name}</CardTitle>
                  {acct.broker && (
                    <Badge variant="outline" className="text-xs">
                      {acct.broker}
                    </Badge>
                  )}
                </div>
                <CardDescription>{acct.trades} trades</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">P&L</span>
                  <span
                    className={
                      acct.pnl >= 0 ? "text-emerald-400" : "text-red-400"
                    }
                  >
                    {acct.pnl >= 0 ? "+" : ""}$
                    {Math.abs(acct.pnl).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Win Rate</span>
                  <span>
                    {acct.win_rate !== null
                      ? `${acct.win_rate.toFixed(1)}%`
                      : "\u2014"}
                  </span>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}

        <Link href="/app/onboarding">
          <Card className="flex min-h-[180px] items-center justify-center border-dashed transition-colors hover:border-primary/30">
            <div className="text-center text-muted-foreground">
              <p className="text-3xl">+</p>
              <p className="mt-2 text-sm font-medium">Add Account</p>
            </div>
          </Card>
        </Link>
      </div>
    </div>
  );
}
