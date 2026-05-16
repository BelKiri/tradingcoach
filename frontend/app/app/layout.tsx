"use client";

import { SWRConfig } from "swr";
import { AppNav } from "@/components/layout/app-nav";
import { BetaQuotaBanner } from "@/components/layout/beta-quota-banner";
import { swrConfig } from "@/lib/swr";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SWRConfig value={swrConfig}>
      <AppNav />
      <div className="mx-auto max-w-7xl px-4">
        <BetaQuotaBanner />
        <main className="py-6">{children}</main>
      </div>
    </SWRConfig>
  );
}
