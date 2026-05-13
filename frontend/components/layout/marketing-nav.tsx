"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const products = [
  {
    name: "Trading History Analyzer",
    desc: "Full analysis of your trading performance",
    href: "/#how-it-works",
    badge: "Free",
  },
  {
    name: "AI Coach",
    desc: "Personalized coaching powered by AI",
    href: "/#pricing",
    badge: "Pro",
  },
  {
    name: "Trade Checker",
    desc: "Under development",
    href: "/#features",
    badge: "Soon",
  },
];

function ProductsDropdown({
  open,
  onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        Products
        <svg
          className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {open && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full z-50 mt-2 w-72 rounded-lg border bg-popover p-2 shadow-lg">
          {products.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className="flex items-start gap-3 rounded-md px-3 py-2.5 transition-colors hover:bg-muted"
              onClick={onToggle}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{item.name}</span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                    {item.badge}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {item.desc}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function MarketingNav() {
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 max-w-6xl items-center px-4">
        {/* Left: Logo */}
        <Link href="/" className="text-lg font-bold">
          TradingCoach
        </Link>

        {/* Center: Nav links */}
        <nav className="hidden flex-1 items-center justify-center gap-6 md:flex">
          <ProductsDropdown
            open={openDropdown === "products"}
            onToggle={() =>
              setOpenDropdown(
                openDropdown === "products" ? null : "products"
              )
            }
          />
        </nav>

        {/* Right: Auth buttons */}
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link href="/login">Sign In</Link>
          </Button>
          <Button
            asChild
            size="sm"
            style={{ backgroundColor: "var(--brand-gold, #d4a843)", color: "#000" }}
          >
            <Link href="/signup">Try Free</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
