# Behavioral Patterns PRD (MVP)

**Last updated:** 2026-06-04 

**Stakeholders:** Solo founder 

## 0. TL;DR

Retail traders see their P&L but not the behaviors that produced it. Behavioral Patterns is the deterministic detection layer that reads each trader's uploaded journal and surfaces recurring patterns — each with trade count and dollar impact — directly on the dashboard. 

Target: 0–2 year retail trader who needs an objective mirror before acting on advice. 

Primary metric: first-session activation, measured by return to the dashboard within 7 days of first upload.

## 1. Problem & Opportunity

Existing trading dashboards report on outcomes — win rate, P&L, drawdown. They do not name the behaviors that produced the outcome.

The result: newer retail traders see a losing month and reach for explanations that don't match the data — "bad luck", "the market was choppy", "the news was unusual". They cannot tell themselves the truth about their own trading until something external names the pattern back to them.

Internal user research conducted at a previous fintech role identified this missing mirror as a foundational gap. Behavioral Patterns is the layer that closes it — and the grounded substrate that any downstream coaching narrative depends on.

## 2. Goals & Success Metrics

- **Business goal:** Drive first-session activation by making Behavioral Patterns the moment a trader recognizes the product sees something they themselves do not. As the only behavioral signal free-tier users get, it is what turns one-time uploaders into returning users — and the foundation paid coaching converts on top of.
- **User goal:** On the first upload, the trader sees a clear, numbered breakdown of their recurring behavioral patterns with exact dollar impact — no text generation, no waiting, no extra clicks.

**Success metrics (measurable; targets are proposed, to confirm):**

- **Primary (activation):** ≥40% of first-time uploaders open the dashboard a second time within 7 days. Cleanest signal that Behavioral Patterns delivered enough value in the first session to be worth returning to.
- **Secondary (engagement):** ≥60% of free-tier users in their first session interact with the behavioral analysis section (hover, expand, or open a related view). Leading indicator for the primary metric.
- **Conversion link:** ≥20% of free-tier users who viewed at least one non-zero pattern request an AI Coaching session within 14 days. Demonstrates that BP earns the runway for paid coaching to convert on.
- **Guardrail (detection accuracy):** ≥80% of uploads with ≥20 trades surface at least one pattern with non-zero dollar impact, and <5% of detected patterns are flagged by users as "not my behavior" via in-product feedback.
- **Performance guardrail:** pattern computation completes within a low single-digit number of seconds for typical journal sizes (specific target to confirm with engineering).

## 3. Target Personas & Use Cases

**Primary segment:** Newbie-amateur retail trader, 0–2 years of active trading experience, account size typically $500–50K. Has just uploaded a journal export and is looking at the dashboard for the first time. May or may not pay for coaching; behavioral patterns are visible regardless.

**Top use cases:**

1. When the trader finishes uploading a journal for the first time, they want to see a numbered, objective summary of what they keep doing wrong, so they can recognize themselves in the data before reading any interpretation.
2. When the trader has an assumption they "trade revenge" or "overtrade", they want a yes-or-no answer with a dollar number attached, so they can stop guessing and confirm the suspicion concretely.
3. When the trader returns after more trading activity, they want to see whether the named patterns got better or worse in raw counts, so they can judge their own progress without needing a coaching session.

## 4. Solution Overview

After the trader uploads or imports their trade journal, the system runs deterministic detection on the trade data and produces, for each known behavioral pattern, a count of occurrences and a dollar impact. The output is structured data — no text generation, no LLM, no narrative.

The dashboard renders the result as a compact behavioral analysis section alongside the existing performance metrics, with a short label per pattern, dollar impact, and trade count. The same structured output is also the substrate that AI Coaching consumes when generating its narrative — but Behavioral Patterns is fully usable on its own and is the only behavioral signal visible to free-tier users.

**Key capabilities:**

- Detection of a defined set of recurring behavioral patterns from trade history, each with a stable name and a tooltip definition the trader can read in plain language.
- Dollar impact and trade count per pattern, computed from the trader's own data — no estimates, no LLM math.
- Dashboard rendering of the full pattern set in a single compact section, readable at a glance without requesting any further action.
- Recomputation on every new upload, so the numbers reflect the trader's most recent behavior without manual refresh.

## 5. User Stories & Acceptance Criteria

**Flow 1: First upload reveals behavior**

1. Trader uploads or imports their journal.
2. System parses the journal and runs deterministic behavioral detection across the full set of patterns.
3. Trader lands on the dashboard and sees the behavioral analysis section populated with each known pattern, its trade count, and its dollar impact.
4. Each pattern has a hover or tap tooltip giving a plain-language definition.
5. No coaching request is needed for the trader to see this — it is visible on free tier by default.

**Flow 2: Clean behavior**

1. Trader uploads a journal in which one or more patterns simply do not occur.
2. System reports each absent pattern with a zero count and zero dollar impact — the absence is itself the signal, not an error.
3. Patterns with non-zero impact remain visible alongside the clean ones, so the trader can see at a glance which behaviors apply to them and which do not.

## 6. Scope & Non-Goals

**In scope (v1):**

- Deterministic detection of the defined behavioral pattern set: revenge trading, martingale, overtrading, averaging down, quick exits, missing stop-loss.
- Dollar impact and trade count per pattern, derived from the trader's own data.
- Dashboard display alongside existing performance metrics.
- Plain-language tooltip definition per pattern.

**Out of scope (explicitly NOT in v1):**

- Recomputation on every new upload.
- Narrative explanation, recommendations, or action plans. Behavioral Patterns reports the numbers; turning those numbers into a personalized coaching narrative is AI Coaching's job, not this layer's. The split is deliberate: deterministic data here, generated text there.
- Volatility regime analysis and macro event proximity. These behavioral context signals exist in the product but are consumed only by the AI Coaching pipeline. They are not part of the dashboard's behavioral analysis section in v1 and are not shown to free-tier users.
- Real-time, intra-trade pattern alerts. Detection in v1 runs on the uploaded journal after the fact, not on live positions.
- Cross-account behavioral aggregation. v1 detects patterns per account.
- User-defined custom patterns. The set of detected patterns is fixed in v1.
- Predictive scoring or "risk of next trade" estimates. Patterns describe what already happened; they do not forecast.
- AI or LLM involvement in detection. The deterministic nature of this layer is its architectural value — it is what gives any downstream narrative its grounding. Introducing an LLM into detection would defeat the point.

