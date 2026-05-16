"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { X } from "lucide-react";
import { useUser } from "@/lib/hooks/useUser";
import { fetcher } from "@/lib/swr";
import type { UserQuota } from "@/lib/api";

function dismissKey(userId: string): string {
  return `beta-quota-banner-dismissed:${userId}`;
}

export function BetaQuotaBanner() {
  const { user } = useUser();
  const { data: quota } = useSWR<UserQuota>(
    user ? `/api/users/${user.id}/quota` : null,
    fetcher,
  );
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!user) return;
    setDismissed(localStorage.getItem(dismissKey(user.id)) === "1");
  }, [user]);

  if (!quota || quota.is_beta_exempt) {
    return null;
  }

  const forceShow = quota.coaching_sessions_used >= 3;
  if (dismissed && !forceShow) {
    return null;
  }

  const message =
    quota.coaching_sessions_used >= 3
      ? "All sessions used. Reach out for more access at TG: @BMNCap"
      : `AI Coach sessions used: ${quota.coaching_sessions_used}/3`;

  function handleDismiss() {
    if (!user || forceShow) return;
    localStorage.setItem(dismissKey(user.id), "1");
    setDismissed(true);
  }

  return (
    <div className="mb-4 flex items-center justify-between gap-3 rounded-md border border-[#d4a843]/30 bg-[#d4a843]/10 px-4 py-3 text-sm text-foreground">
      <p>{message}</p>
      {!forceShow && (
        <button
          type="button"
          onClick={handleDismiss}
          className="shrink-0 rounded p-1 text-muted-foreground hover:text-foreground"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
