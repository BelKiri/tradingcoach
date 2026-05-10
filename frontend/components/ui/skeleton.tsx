import { cn } from "@/lib/utils";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-muted/50",
        className,
      )}
      {...props}
    />
  );
}

/** Skeleton card matching the account card layout. */
export function AccountCardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between pb-3">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="mb-4 h-4 w-20" />
      <div className="space-y-3">
        <div className="flex justify-between">
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="flex justify-between">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-12" />
        </div>
      </div>
    </div>
  );
}

/** Skeleton for dashboard metric cards row. */
export function MetricCardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <Skeleton className="mb-2 h-3 w-16" />
      <Skeleton className="h-7 w-20" />
    </div>
  );
}

/** Skeleton for a chart area. */
export function ChartSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-lg border bg-card p-6 shadow-sm", className)}>
      <Skeleton className="mb-4 h-5 w-32" />
      <Skeleton className="h-48 w-full rounded" />
    </div>
  );
}

/** Skeleton for coaching session card. */
export function CoachingCardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <div className="flex items-center gap-3 pb-3">
        <Skeleton className="h-8 w-8 rounded-full" />
        <div>
          <Skeleton className="mb-1 h-4 w-40" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="mt-1 h-4 w-3/4" />
    </div>
  );
}
