# AI Coaching — Lean PRD

## 0. TL;DR

Behavioral patterns on the dashboard tell the trader what they keep doing wrong; AI Coaching tells them what to do about it. It consumes signals from the Behavioral Patterns layer, overlays market context (volatility, macro events), and returns a plain-language diagnostic with verdict, action plan, and comparison vs the prior session. 

Target: 0–2 year retail trader who has seen the patterns and wants the next step. 

Primary metric: % of coached users who return for a second session within 14 days.

## 1. Problem & Opportunity

Active retail traders with 0–2 years of experience now have a dashboard that names their behavioral patterns and quantifies the dollar impact of each one. They can see, in numbers, that specific behaviors cost them money over the past month.

But seeing the patterns is not the same as knowing what to do about them. Which pattern matters most this week? How did volatility and macro events interact with these decisions? What is the one concrete change that would actually move P&L?

Internal user research conducted at a previous fintech role identified this synthesis gap — between detection and decision — as a key driver of disengagement among newer retail traders. They want someone to tell them what to do next, in plain language, grounded in their own data.

## 2. Goals & Success Metrics

- **Business goal:** Drive free-to-paid conversion and sustain paid retention. AI Coaching is the primary reason a free user upgrades — and the recurring value that keeps a paid user subscribed.
- **User goal:** After viewing their behavioral patterns on the dashboard, the trader can request a coaching session that synthesizes those patterns into a plain-language narrative with priority, verdict, and a concrete action plan grounded in their own data.

**Success metrics (measurable; targets are proposed, to confirm):**

- **Primary (paid value signal):** ≥30% of coached users return within 14 days for a second coaching session on the same account. Returning for a follow-up is where the trader signals that the previous coaching was worth the request.
- **Secondary (activation / leading indicator):** ≥60% of new users with ≥10 uploaded trades request their first coaching session within their first product session. Without a first request, there is no second one.
- **Quality guardrail:** <5% of coaching sessions flagged by users as "not actionable" or "wrong about my trading" via in-product feedback.
- **Cost guardrail:** LLM cost per coaching session stays below an acceptable per-user ceiling for the Free tier (specific ceiling to confirm).
- **Performance guardrail:** end-to-end latency from request to displayed diagnostic stays within an agreed budget (specific target to confirm).

**LLM output evals (continuous):**

In addition to the quantitative metrics above, a qualitative LLM output eval suite runs against each coaching prompt iteration before release. The suite catches behaviors that quantitative metrics cannot. 

Examples: the model never gives financial advice, never fabricates numbers or dates outside its structured context, produces the expected sections (verdict, diagnostic, action plan) in the expected order, keeps tone as analyst rather than advisor, and avoids restricted psychological terminology.

Evals run on a fixed set of synthetic and anonymized real trader profiles. A regression on any single check blocks the prompt change from shipping.

## 3. Target Personas & Use Cases

**Primary segment:** Newbie-amateur retail trader, 0–2 years of active trading experience, account size typically $500–50K. Has uploaded their journal and seen the behavioral patterns on the dashboard. Knows their behavior is the issue but cannot prioritize the raw numbers on their own.

**Top use cases:**

1. When the trader finishes a losing week and feels something is wrong, they want a *named* cause rather than a generic warning, so they can stop guessing and try one specific corrective action.
2. After uploading their journal and seeing the raw patterns on the dashboard, the trader wants someone to tell them which pattern matters most and what specific action to take first, so they don't have to interpret the metrics themselves.

## 4. Solution Overview

When the trader requests a coaching session, the product consumes the behavioral signals already detected by the Behavioral Patterns layer and overlays additional market context — volatility regime (ATR-based) and proximity to high-impact macro events — that is not shown on the dashboard.

An LLM receives this pre-computed structured context, not raw trades, and produces a short personalized diagnostic. The diagnostic names the one to three patterns most damaging the trader's recent performance.

**Key capabilities:**

- Plain-language behavioral diagnostic, generated per account and per period, referencing specific dates and amounts from the trader's own data.
- A short, numbered action plan of one to three corrective rules, written in concrete terms (e.g., "don't open new positions within the window around high-impact news").
- Market context layer (volatility regime, macro event proximity) consumed only by the coaching pipeline — not displayed on the dashboard, not visible to free-tier users.

**AI/ML considerations:**

- All quantitative claims come from the deterministic Behavioral Patterns and analytics layers, not the LLM. The LLM is not asked to compute math; it only synthesizes and explains.
- The LLM is given pre-aggregated behavioral context and market context, not raw trade rows, both to control prompt size and to keep output grounded in the same numbers the trader sees on the dashboard.
- The product framing is explicit: the LLM is an analyst, not an advisor. The diagnostic describes observed behavior. It does not tell the trader to buy or sell anything. A legal disclaimer remains visible alongside the output.
- Cost per session and latency per session are tracked as first-class guardrail metrics from day one, not as afterthoughts.
- Hallucination risk is reduced but not eliminated by the split between deterministic math and LLM synthesis. Coaching output is reviewed during beta and the prompt is iterated against actual misbehavior before broad release.

## 5. User Stories & Acceptance Criteria

**Flow 1: First-time coaching after first upload**

1. Trader uploads or imports their journal and sees their behavioral patterns on the dashboard.
2. Trader opens the AI Coaching panel and requests an analysis.
3. System validates that enough trades exist for a meaningful diagnostic (minimum trade threshold).
4. System returns the diagnostic within an agreed latency budget.
5. Trader sees, in order: a one-line verdict, a brief diagnostic naming the one to three most damaging patterns with concrete examples from their data, and a short numbered action plan.
6. Trader can save and revisit the session later from coaching history.

**Flow 2: Insufficient data**

1. Trader requests coaching with too few trades, or no trades in the requested period.
2. System refuses gracefully, explaining what's needed (minimum trade count, date range), rather than producing a low-confidence diagnostic.

## 6. Scope & Non-Goals

**In scope (v1):**

- AI-generated behavioral diagnostic per account and per period.
- Verdict and action-plan structure.
- Coaching history per account, with the ability to revisit sessions of different trading accounts.
- Free-tier quota (a small fixed number of sessions) and paid-tier unlimited quota.
- Market context inputs (deterministic volatility signal and macro event proximity), consumed only by the coaching pipeline.

**Out of scope (explicitly NOT in v1):**

- Comparison against the previous coaching session for the same account.
- **Pattern detection, dollar-impact computation, and dashboard display of behavioral signals.** All of that is the Behavioral Patterns layer's responsibility. AI Coaching consumes those signals; it does not produce them. See the Behavioral Patterns PRD for the split.

- **Real-time, intra-trade coaching alerts.** The coaching loop in v1 is post-trade, after the journal is uploaded — not pre-trade. Pre-trade coaching changes the regulatory and product surface materially and belongs to its own scope.
- **Auto-import directly from broker APIs (MetaTrader, exchanges).** v1 relies on user-uploaded journal exports; auto-import is in the post-launch roadmap.
- **Multi-account portfolio coaching.** v1 coaches one account at a time. Cross-account aggregation introduces identity and netting questions that are not solved here.
- **Languages beyond English.** The LLM diagnostic ships English-only in v1.
- **Direct financial advice or trade recommendations.** The product describes observed behavior; it does not tell users what to buy or sell. This is a permanent product boundary, not a v1 limitation.
- **Charts and visual analytics inside the coaching output.** Coaching is text. The dashboard handles visuals separately.

