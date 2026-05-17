"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/* ---------- Hero ---------- */
function Hero() {
  return (
    <section className="mx-auto max-w-4xl px-4 pb-12 pt-16 text-center">
      <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
        Winners and losers use the same strategies.
        <br />
        <span style={{ color: "var(--brand-gold, #d4a843)" }}>
          The difference is behavior.
        </span>
      </h1>
      <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
        Upload your trades. Get a comprehensive performance analysis and a
        personal fix plan in 2&nbsp;minutes.
      </p>
      <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
        <Button
          asChild
          size="lg"
          className="text-base px-8 h-12 font-bold"
          style={{
            backgroundColor: "var(--brand-gold, #d4a843)",
            color: "#000",
          }}
        >
          <Link href="/signup">
            Start Analyzing Your Performance
          </Link>
        </Button>
      </div>
      <p className="mt-4 text-xs text-muted-foreground">
        CSV &amp; Excel from MT4, MT5, cTrader, Binance, Bybit, any broker
      </p>
    </section>
  );
}

/* ---------- Social proof ---------- */
function AnimatedCounter({ target }: { target: string }) {
  const [count, setCount] = useState(0);
  const [started, setStarted] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const targetNum = parseInt(target.replace(/,/g, ""), 10);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          setStarted(true);
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [started]);

  useEffect(() => {
    if (!started) return;
    const duration = 1500;
    const steps = 40;
    const increment = targetNum / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= targetNum) {
        setCount(targetNum);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [started, targetNum]);

  return (
    <div ref={ref}>
      <p className="text-5xl font-bold text-white tabular-nums">
        {count.toLocaleString()}
      </p>
    </div>
  );
}

function SocialProof() {
  return (
    <section className="border-y bg-card/50 py-12">
      <div className="mx-auto max-w-4xl px-4 text-center">
        <p
          className="text-sm font-medium uppercase tracking-wider"
          style={{ color: "var(--brand-gold, #d4a843)" }}
        >
          Total trades analyzed
        </p>
        <div className="mt-4">
          <AnimatedCounter target="12,847" />
        </div>
      </div>
    </section>
  );
}

/* ---------- How it works ---------- */
function HowItWorks() {
  const steps = [
    {
      step: "1",
      title: "Provide Data",
      desc: "Upload your CSV or Excel trading history. Works with any broker or exchange.",
    },
    {
      step: "2",
      title: "Analyze",
      desc: "We detect behavior patterns affecting your trading performance \u2014 with exact $ amounts.",
    },
    {
      step: "3",
      title: "AI Coach",
      desc: "Finds the surprising patterns causing losses you haven\u2019t noticed and provides a specific action plan to fix them.",
    },
  ];

  return (
    <section id="how-it-works" className="mx-auto max-w-5xl px-4 py-12">
      <h2 className="text-center text-3xl font-bold">How it works</h2>
      <div className="mt-12 grid gap-8 md:grid-cols-3">
        {steps.map((s) => (
          <div key={s.step} className="text-center">
            <div
              className="mx-auto text-5xl font-bold"
              style={{ color: "var(--brand-gold, #d4a843)", opacity: 0.7 }}
            >
              {s.step}
            </div>
            <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{s.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ---------- What we detect ---------- */
function WhatWeDetect() {
  const patterns = [
    { name: "Revenge Trading", desc: "Trading impulsively after a loss" },
    { name: "Martingale", desc: "Doubling down after losing trades" },
    { name: "Overtrading", desc: "Too many trades in a single day" },
    { name: "Averaging Down", desc: "Adding to losing positions" },
    { name: "Quick Exits", desc: "Closing trades within seconds" },
    { name: "Risk Discipline", desc: "Stop loss usage and position sizing" },
    { name: "Volatility Effect", desc: "How market volatility impacts your results" },
    { name: "Macro Events Impact", desc: "Trading around major news releases" },
    { name: "Session Mismatch", desc: "Trading at the wrong time of day" },
  ];

  return (
    <section id="features" className="bg-card/30 py-12">
      <div className="mx-auto max-w-5xl px-4">
        <h2
          className="text-center text-3xl font-bold"
          style={{ color: "var(--brand-gold, #d4a843)" }}
        >
          What We Detect
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-muted-foreground">
          Every pattern is backed by exact dollar amounts and specific trade
          references.
        </p>
        <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {patterns.map((p) => (
            <div
              key={p.name}
              className="rounded-lg p-4 transition-all duration-200 cursor-default hover:-translate-y-0.5"
              style={{
                backgroundColor: "#141414",
                border: "1px solid #262626",
                borderLeft: "3px solid rgba(212, 168, 67, 0.5)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderLeftColor = "#d4a843";
                e.currentTarget.style.boxShadow = "0 4px 12px rgba(212,168,67,0.15)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderLeftColor = "rgba(212, 168, 67, 0.5)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <p className="text-[14px] font-bold text-white">{p.name}</p>
              <p className="mt-1 text-xs text-gray-500">{p.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Pricing preview ---------- */
function PricingPreview() {
  return (
    <section id="pricing" className="py-12">
      <div className="mx-auto max-w-4xl px-4">
        <h2 className="text-center text-3xl font-bold">Simple pricing</h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-muted-foreground">
          Start free. Upgrade when you&apos;re ready.
        </p>

        <div className="mt-12 grid gap-6 md:grid-cols-2">
          {/* Free */}
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Free</CardTitle>
              <p className="text-3xl font-bold mt-2">
                $0
                <span className="text-base font-normal text-muted-foreground">
                  /forever
                </span>
              </p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {[
                  "Unlimited trade uploads (CSV/Excel)",
                  "Full performance dashboard",
                  "Behavioral analysis",
                  "1 AI coaching session",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <span className="text-primary">{"\u2713"}</span>
                    {f}
                  </li>
                ))}
              </ul>
            </CardContent>
            <CardFooter>
              <Button asChild variant="outline" className="w-full">
                <Link href="/signup">Start Free</Link>
              </Button>
            </CardFooter>
          </Card>

          {/* Pro */}
          <Card className="relative" style={{ border: "1px solid var(--brand-gold, #d4a843)" }}>
            <CardHeader>
              <CardTitle>Pro</CardTitle>
              <p className="text-3xl font-bold mt-2">
                ***
                <span className="text-base font-normal text-muted-foreground">
                  /month
                </span>
              </p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2 text-muted-foreground">
                  <span className="text-primary">{"\u2713"}</span>
                  Everything in Free, plus:
                </li>
                {[
                  "Unlimited AI coaching sessions",
                  "Progress tracking",
                  "Multiple trading accounts",
                  "Weekly AI action plan (Monday briefing)",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <span className="text-primary">{"\u2713"}</span>
                    {f}
                  </li>
                ))}
              </ul>
            </CardContent>
            <CardFooter>
              <Button
                asChild
                className="w-full font-bold"
                style={{ backgroundColor: "var(--brand-gold, #d4a843)", color: "#000" }}
              >
                <Link href="/signup">Start Free, Upgrade Later</Link>
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </section>
  );
}

/* ---------- FAQ ---------- */
function FAQ() {
  const faqs = [
    {
      q: "What file formats do you support?",
      a: "CSV and Excel (.xlsx) from any broker or exchange. Our parser auto-detects columns, date formats, and header rows. Works with MetaTrader 4/5, cTrader, Binance, Bybit, and any platform that exports trade history.",
    },
    {
      q: "Is my trading data safe?",
      a: "Yes. Your data is stored in a secure database with row-level security \u2014 only you can see your trades. We never share or sell your data. You can delete everything at any time.",
    },
    {
      q: "How is TradingCoach different from other trading analyzers?",
      a: "Most analyzers show you what happened \u2014 win rate, P&L, basic stats. TradingCoach shows you why. We detect 9 behavioral patterns, analyze how volatility and macro events affect your performance, and provide AI-powered coaching with specific rules to fix your mistakes. No other tool combines behavioral analysis with AI coaching.",
    },
    {
      q: "How does the AI coaching work?",
      a: "Our AI analyzes your trades by cross-referencing timestamps, lot sizes, P&L, and behavioral patterns. It surfaces the most surprising insights you may have missed and suggests practical ways to improve your trading strategy.",
    },
    {
      q: "Do I need to connect my broker?",
      a: "No. Just export your trade history as CSV or Excel and upload it. No API keys, no broker access needed. Your broker credentials stay with you.",
    },
    {
      q: "What if I have multiple accounts?",
      a: "TradingCoach supports multiple accounts. Create separate accounts (e.g. \u2018Exness Main\u2019, \u2018Binance Futures\u2019) and analyze each one independently.",
    },
  ];

  return (
    <section className="bg-card/30 py-12">
      <div className="mx-auto max-w-3xl px-4">
        <h2 className="text-center text-3xl font-bold">
          Frequently asked questions
        </h2>
        <div className="mt-12 space-y-4">
          {faqs.map((faq) => (
            <details
              key={faq.q}
              className="group rounded-lg border px-6 py-4 [&_summary::-webkit-details-marker]:hidden"
            >
              <summary className="flex cursor-pointer items-center justify-between text-sm font-medium">
                {faq.q}
                <span className="ml-4 text-muted-foreground transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-3 text-sm text-muted-foreground">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- CTA ---------- */
function FinalCTA() {
  return (
    <section className="py-12">
      <div className="mx-auto max-w-2xl px-4 text-center">
        <h2 className="text-3xl font-bold">
          Stop guessing. Start fixing.
        </h2>
        <p className="mt-4 text-muted-foreground">
          Upload your trades and see exactly what&apos;s costing you money.
          Free, no credit card needed.
        </p>
        <div className="mt-8">
          <Button
            asChild
            size="lg"
            className="text-base px-8 h-12 font-bold"
            style={{
              backgroundColor: "var(--brand-gold, #d4a843)",
              color: "#000",
            }}
          >
            <Link href="/signup">
              Start Analyzing Your Performance
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

/* ---------- Page ---------- */
const SHOW_PRICING_ON_LANDING = false;

export default function LandingPage() {
  return (
    <>
      <Hero />
      <SocialProof />
      <HowItWorks />
      <WhatWeDetect />
      {SHOW_PRICING_ON_LANDING && <PricingPreview />}
      <FinalCTA />
      <FAQ />
    </>
  );
}
