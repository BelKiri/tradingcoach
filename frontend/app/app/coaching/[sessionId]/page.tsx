"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { CoachingSession, AccountSummary } from "@/lib/api";
import { CoachMarkdown } from "@/lib/coach-markdown";
import { fetcher } from "@/lib/swr";
import { Skeleton } from "@/components/ui/skeleton";

const verdictConfig: Record<
  string,
  { icon: string; label: string; variant: "success" | "warning" | "destructive" }
> = {
  progress: { icon: "\uD83D\uDC4D", label: "Improving", variant: "success" },
  setback: { icon: "\uD83D\uDC4E", label: "Needs work", variant: "destructive" },
  no_change: { icon: "\u27A1\uFE0F", label: "No change", variant: "warning" },
};

export default function CoachingSessionPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  const { data: session, error: swrError, isLoading } = useSWR<CoachingSession>(
    `/api/coaching/session/${sessionId}`,
    fetcher,
  );

  const { data: account } = useSWR<AccountSummary>(
    session?.account_id ? `/api/accounts/detail/${session.account_id}` : null,
    fetcher,
  );

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-8">
        <div>
          <div className="mb-2 h-8 w-24 animate-pulse rounded bg-muted/50" />
          <div className="h-7 w-48 animate-pulse rounded bg-muted/50" />
          <div className="mt-2 h-4 w-64 animate-pulse rounded bg-muted/50" />
        </div>
        <div className="rounded-lg border bg-card p-6">
          <Skeleton className="mb-4 h-5 w-20" />
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i}>
                <Skeleton className="mb-1 h-3 w-16" />
                <Skeleton className="h-7 w-20" />
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <Skeleton className="mb-4 h-5 w-24" />
          <Skeleton className="mb-2 h-4 w-full" />
          <Skeleton className="mb-2 h-4 w-full" />
          <Skeleton className="mb-2 h-4 w-3/4" />
          <Skeleton className="mb-4 h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
    );
  }

  const error = swrError?.message ?? "";

  if (error || !session) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Button asChild variant="ghost" size="sm">
          <Link href="/app/coaching">&larr; All sessions</Link>
        </Button>
        <div className="rounded-md bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          {error || "Session not found"}
        </div>
      </div>
    );
  }

  const v = session.verdict
    ? verdictConfig[session.verdict]
    : null;

  const date = new Date(session.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const metrics = session.metrics_snapshot as Record<string, unknown> | null;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <Button asChild variant="ghost" size="sm" className="mb-2">
            <Link href="/app/coaching">&larr; All sessions</Link>
          </Button>
          <h1 className="text-2xl font-bold">Coaching Session</h1>
          {account && (
            <p className="text-[16px] text-white flex items-center gap-1.5 mt-0.5">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">A</span>
              Analysis for: {account.name}
            </p>
          )}
          <p className="text-sm text-muted-foreground">
            {date}
            {session.new_trades_count
              ? ` \u2022 ${session.new_trades_count} trades analyzed`
              : ""}
          </p>
        </div>
        {v && <Badge variant={v.variant}>{v.icon} {v.label}</Badge>}
      </div>

      {/* Metrics snapshot */}
      {metrics && Object.keys(metrics).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Snapshot</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {metrics.trades_count != null && (
                <div>
                  <p className="text-xs text-muted-foreground">Trades</p>
                  <p className="text-lg font-bold">{String(metrics.trades_count)}</p>
                </div>
              )}
              {metrics.win_rate != null && (
                <div>
                  <p className="text-xs text-muted-foreground">Win Rate</p>
                  <p className="text-lg font-bold">
                    {Number(metrics.win_rate).toFixed(1)}%
                  </p>
                </div>
              )}
              {metrics.total_pnl != null && (
                <div>
                  <p className="text-xs text-muted-foreground">P&amp;L</p>
                  <p
                    className={`text-lg font-bold ${
                      Number(metrics.total_pnl) >= 0
                        ? "text-emerald-400"
                        : "text-red-400"
                    }`}
                  >
                    ${Number(metrics.total_pnl).toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </p>
                </div>
              )}
              {metrics.revenge_count != null && (
                <div>
                  <p className="text-xs text-muted-foreground">Revenge Trades</p>
                  <p
                    className={`text-lg font-bold ${
                      Number(metrics.revenge_count) > 0
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {String(metrics.revenge_count)}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* AI Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">AI Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <CoachMarkdown text={session.ai_response} />
        </CardContent>
      </Card>

      {/* Action plan (structured rules) */}
      {session.rules && session.rules.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">План действий</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {session.rules.map((rule, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 rounded-md bg-muted/30 px-4 py-3"
                >
                  <span
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-muted-foreground/40 bg-background"
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-sm font-medium">{rule.action}</p>
                      {rule.savings_estimate_usd > 0 && (
                        <Badge variant="secondary" className="shrink-0 text-xs">
                          ~${rule.savings_estimate_usd.toLocaleString("en-US")}/мес
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">{rule.rationale}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-center text-xs text-muted-foreground">
        {session.model_used
          ? `Powered by ${session.model_used}`
          : "Powered by Claude Sonnet"}
      </p>
    </div>
  );
}
