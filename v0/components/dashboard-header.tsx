"use client"

import { useState } from "react"
import { ChevronDown, Upload, Brain } from "lucide-react"

const periodOptions = [
  "All time",
  "Last 7 days",
  "Last 30 days",
  "This month",
  "Custom range",
]

export function DashboardHeader() {
  const [selectedPeriod, setSelectedPeriod] = useState("All time")
  const [dropdownOpen, setDropdownOpen] = useState(false)

  return (
    <div className="w-full px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      {/* Left side */}
      <div className="flex items-center gap-4">
        <div className="flex items-baseline gap-3">
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <span className="text-sm text-gray-500">81 trades</span>
        </div>

        {/* Period Dropdown */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 bg-[#1a1a1a] border border-[#262626] rounded hover:border-[#3a3a3a] transition-colors"
          >
            {selectedPeriod}
            <ChevronDown className="w-4 h-4" />
          </button>

          {dropdownOpen && (
            <div className="absolute top-full left-0 mt-1 w-40 bg-[#1a1a1a] border border-[#262626] rounded shadow-lg z-10">
              {periodOptions.map((option) => (
                <button
                  key={option}
                  onClick={() => {
                    setSelectedPeriod(option)
                    setDropdownOpen(false)
                  }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                    selectedPeriod === option
                      ? "text-white bg-[#262626]"
                      : "text-gray-400 hover:text-white hover:bg-[#262626]"
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        <button className="flex items-center gap-2 px-4 py-2 text-sm text-gray-300 border border-[#262626] rounded hover:border-[#3a3a3a] hover:text-white transition-colors">
          <Upload className="w-4 h-4" />
          Upload file
        </button>
        <button className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-emerald-500 rounded hover:bg-emerald-600 transition-colors">
          <Brain className="w-4 h-4" />
          AI Coach
        </button>
      </div>
    </div>
  )
}
