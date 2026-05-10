"use client"

import Link from "next/link"

const navLinks = [
  { name: "Home", href: "/" },
  { name: "Dashboard", href: "/dashboard", active: true },
  { name: "AI Coach", href: "/ai-coach" },
]

export function Navbar() {
  return (
    <nav className="sticky top-0 z-50 w-full h-12 bg-[#0a0a0a] border-b border-[#262626] px-6 flex items-center justify-between">
      {/* Left: Logo */}
      <div className="font-bold text-white text-base">TradeCoach</div>

      {/* Center: Nav Links */}
      <div className="flex items-center gap-1">
        {navLinks.map((link) => (
          <Link
            key={link.name}
            href={link.href}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              link.active
                ? "bg-[#262626] text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {link.name}
          </Link>
        ))}
      </div>

      {/* Right: Sign out + User initial */}
      <div className="flex items-center gap-3">
        <button className="text-sm text-gray-400 hover:text-white transition-colors">
          Sign out
        </button>
        <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center text-white text-xs font-medium">
          K
        </div>
      </div>
    </nav>
  )
}
