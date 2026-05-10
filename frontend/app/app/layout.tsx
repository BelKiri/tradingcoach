"use client";

import { SWRConfig } from "swr";
import { AppNav } from "@/components/layout/app-nav";
import { swrConfig } from "@/lib/swr";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SWRConfig value={swrConfig}>
      <AppNav />
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </SWRConfig>
  );
}
