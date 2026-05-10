"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import useSWR from "swr";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CoachingCardSkeleton } from "@/components/ui/skeleton";
import { useUser } from "@/lib/hooks/useUser";
import { fetcher } from "@/lib/swr";
import type { CoachingSession, AccountSummary } from "@/lib/api";

const verdictConfig: Record<
  string,
  { icon: string; label: string; variant: "success" | "warning" | "destructive" }
> = {
  progress: { icon: "\uD83D\uDC4D", label: "Improving", variant: "success" },
  setback: { icon: "\uD83D\uDC4E", label: "Needs work", variant: "destructive" },
  no_change: { icon: "\u27A1\uFE0F", label: "No change", variant: "warning" },
};

const defaultVerdict = { icon: "\uD83E\uDDE0", label: "First analysis", variant: "secondary" as const };

export default function CoachingListPage() {
  const { user, loading: userLoading } = useUser();
  const [selectedAccount, setSelectedAccount] = useState<string>("all");
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const { data: sessions, error, isLoading } = useSWR<CoachingSession[]>(
    user ? `/api/coaching/sessions/${user.id}` : null,
    fetcher,
  );

  const { data: accountsData } = useSWR<{ accounts: AccountSummary[] }>(
    user ? `/api/accounts/${user.id}` : null,
    fetcher,
  );

  const accounts = accountsData?.accounts ?? [];
  const accountMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const a of accounts) m[a.id] = a.name;
    return m;
  }, [accounts]);

  const filteredSessions = useMemo(() => {
    if (!sessions) return [];
    if (selectedAccount === "all") return sessions;
    return sessions.filter((s) => s.account_id === selectedAccount);
  }, [sessions, selectedAccount]);

  const loading = (userLoading || isLoading) && !sessions;

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-7 w-32 animate-pulse rounded bg-muted/50" />
            <div className="mt-2 h-4 w-56 animate-pulse rounded bg-muted/50" />
          </div>
        </div>
        <div className="space-y-4">
          <CoachingCardSkeleton />
          <CoachingCardSkeleton />
          <CoachingCardSkeleton />
        </div>
      </div>
    );
  }

  const list = filteredSessions;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Coaching</h1>
          <p className="text-sm text-muted-foreground">
            Personalized insights powered by Claude Sonnet.
          </p>
        </div>
      </div>

      {/* Account filter */}
      {accounts.length > 0 && (
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 bg-[#1a1a1a] border border-[#262626] rounded hover:border-[#3a3a3a] transition-colors"
          >
            Account: {selectedAccount === "all" ? "All accounts" : accountMap[selectedAccount] || selectedAccount}
            <ChevronDown className="w-4 h-4" />
          </button>
          {dropdownOpen && (
            <div className="absolute top-full left-0 mt-1 w-52 bg-[#1a1a1a] border border-[#262626] rounded shadow-lg z-10">
              <button
                onClick={() => { setSelectedAccount("all"); setDropdownOpen(false); }}
                className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                  selectedAccount === "all"
                    ? "text-white bg-[#262626]"
                    : "text-gray-400 hover:text-white hover:bg-[#262626]"
                }`}
              >
                All accounts
              </button>
              {accounts.map((a) => (
                <button
                  key={a.id}
                  onClick={() => { setSelectedAccount(a.id); setDropdownOpen(false); }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                    selectedAccount === a.id
                      ? "text-white bg-[#262626]"
                      : "text-gray-400 hover:text-white hover:bg-[#262626]"
                  }`}
                >
                  {a.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="rounded-md bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          {error.message}
        </div>
      )}

      {list.length === 0 && !error ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-lg font-medium">No coaching sessions yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Go to your dashboard and click &quot;AI Coaching&quot; to get your
              first analysis.
            </p>
            <Button asChild className="mt-4">
              <Link href="/app">Go to Dashboard</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {list.map((s) => {
            const v = s.verdict
              ? verdictConfig[s.verdict] || defaultVerdict
              : defaultVerdict;
            const firstLine =
              s.main_problem || s.ai_response.split("\n")[0].slice(0, 120);
            const date = new Date(s.created_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            });
            return (
              <Link key={s.id} href={`/app/coaching/${s.id}`}>
                <Card className="transition-colors hover:border-primary/30">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{v.icon}</span>
                        <div>
                          <CardTitle className="text-base">
                            {s.new_trades_count
                              ? `${s.new_trades_count} trades analyzed`
                              : "Coaching Session"}
                          </CardTitle>
                          <p className="text-xs text-muted-foreground">
                            {date}
                            {accountMap[s.account_id] && (
                              <span className="text-gray-500"> &middot; {accountMap[s.account_id]}</span>
                            )}
                          </p>
                        </div>
                      </div>
                      <Badge variant={v.variant}>{v.label}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {firstLine}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}

      <div className="text-center">
        <p className="text-sm text-muted-foreground">
          Free plan: 1 coaching session included.{" "}
          <Link href="/pricing" className="text-primary hover:underline">
            Upgrade to Pro
          </Link>{" "}
          for unlimited sessions.
        </p>
      </div>
    </div>
  );
}
