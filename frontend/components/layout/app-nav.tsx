"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUser } from "@/lib/hooks/useUser";
import { createClient } from "@/lib/supabase/client";
import { fetchAccounts } from "@/lib/api";

export function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useUser();
  const [dashboardHref, setDashboardHref] = useState("/app/onboarding");
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    fetchAccounts(user.id)
      .then((accounts) => {
        if (accounts.length > 0) {
          setDashboardHref(`/app/dashboard/${accounts[0].id}`);
        }
      })
      .catch(() => {});
  }, [user]);

  // Close menu on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  const navItems = [
    { href: "/app", label: "Home", exact: true },
    { href: dashboardHref, label: "Dashboard", match: "/app/dashboard" },
    { href: "/app/coaching", label: "AI Coach", match: "/app/coaching" },
  ];

  const initial = user?.email?.[0]?.toUpperCase() || "?";

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-50 w-full h-12 bg-[#0a0a0a] border-b border-[#262626]">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-6">
        {/* Left: Logo */}
        <Link href="/app" className="font-bold text-white text-base">
          TradingCoach
        </Link>

        {/* Center: Nav Links */}
        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.match || item.href);
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "px-3 py-1.5 text-sm rounded transition-colors",
                  isActive
                    ? "bg-[#262626] text-white"
                    : "text-gray-400 hover:text-white"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right: Profile menu */}
        <div className="relative flex items-center gap-3" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-3 cursor-pointer"
          >
            <span className="text-sm text-gray-400 hover:text-white transition-colors">
              Sign out
            </span>
            <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center text-white text-xs font-medium">
              {initial}
            </div>
          </button>

          {menuOpen && (
            <div className="absolute top-full right-0 mt-1 w-40 bg-[#1a1a1a] border border-[#262626] rounded shadow-lg z-10">
              <Link
                href="/app/settings"
                onClick={() => setMenuOpen(false)}
                className="block w-full text-left px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-[#262626] transition-colors"
              >
                Settings
              </Link>
              <button
                onClick={() => {
                  setMenuOpen(false);
                  handleSignOut();
                }}
                className="block w-full text-left px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-[#262626] transition-colors"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
