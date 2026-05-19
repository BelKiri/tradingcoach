"""
AI coaching — assembles ALL RAG data (trade stats, behavioral patterns,
calendar impact, volatility analysis) into a prompt for
Claude Sonnet to produce personalized coaching.

Supports first-time analysis and repeat analysis with previous session comparison.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

from tradecoach.services import trade_analyzer as ta
from tradecoach.services._helpers import _net_profit, _to_dt
from tradecoach.services.tz_utils import trade_instant_utc
from tradecoach.utils.json_helpers import parse_json_field
from tradecoach.services.calendar import (
    calculate_news_impact,
    load_calendar,
    match_trades_to_events,
)
from tradecoach.services.llm import LLMError, LLMUsage, deep_analysis
from tradecoach.services.market_data import (
    build_volatility_context_for_coaching,
)

_EPOCH_COACH = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ===================================================================
# Helpers
# ===================================================================

def _fmt_dt(val: str | datetime | None) -> str:
    if val is None:
        return "?"
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val)
        except (ValueError, TypeError):
            return val
    return val.strftime("%b %d %H:%M")


def _trade_key(t: dict) -> tuple:
    return (
        t.get("symbol"), t.get("opened_at"), t.get("direction"),
        t.get("lot"), t.get("profit_money"),
    )


def _trade_line(t: dict, *, tag: str = "") -> str:
    symbol = t.get("symbol", "?")
    direction = t.get("direction", "?")
    lot = t.get("lot", 0)
    pnl = _net_profit(t)
    opened = _fmt_dt(t.get("opened_at"))
    sl = t.get("stop_loss")
    sl_str = f" SL={sl}" if sl else " no-SL"
    tag_str = f" [{tag}]" if tag else ""
    return f"  {opened} | {symbol} {direction} {lot} lot | ${pnl:+.2f}{sl_str}{tag_str}"


# ===================================================================
# SECTION BUILDERS
# ===================================================================

def _build_statistics_section(trades: list[dict], account_balance: float | None) -> str:
    """Section a) TRADE STATISTICS."""
    lines: list[str] = ["=== TRADE STATISTICS ==="]

    wr = ta.win_rate(trades)
    pnl = ta.total_pnl(trades)
    pf = ta.profit_factor(trades)
    exp = ta.expectancy(trades)
    aw = ta.avg_win(trades)
    al = ta.avg_loss(trades)

    lines.append(f"Trades: {len(trades)} | Win rate: {wr:.1f}% | P&L: ${pnl:,.2f}")
    if pf is not None:
        lines.append(f"Profit factor: {pf:.2f} | Expectancy: ${exp or 0:.2f}")
    if aw is not None and al is not None:
        lines.append(f"Avg win: ${aw:.2f} | Avg loss: ${al:.2f}")
    if account_balance and account_balance > 0:
        lines.append(f"Account balance: ${account_balance:,.2f}")

    # Best/worst pairs
    symbols = ta.pnl_by_symbol(trades)
    if symbols:
        best_sym = max(symbols.items(), key=lambda x: x[1]["pnl"])
        worst_sym = min(symbols.items(), key=lambda x: x[1]["pnl"])
        lines.append(
            f"\nBest pair: {best_sym[0]} — ${best_sym[1]['pnl']:+,.2f} "
            f"({best_sym[1]['win_rate']:.0f}% WR, {best_sym[1]['trades']} trades)"
        )
        lines.append(
            f"Worst pair: {worst_sym[0]} — ${worst_sym[1]['pnl']:+,.2f} "
            f"({worst_sym[1]['win_rate']:.0f}% WR, {worst_sym[1]['trades']} trades)"
        )
        if len(symbols) > 2:
            lines.append("All pairs:")
            for sym, data in sorted(symbols.items(), key=lambda x: x[1]["pnl"]):
                lines.append(
                    f"  {sym}: ${data['pnl']:+,.2f} ({data['win_rate']:.0f}% WR, {data['trades']} trades)"
                )

    # Best/worst sessions
    sessions = ta.pnl_by_session(trades)
    known = {k: v for k, v in sessions.items() if k != "Unknown"}
    if known:
        best_ses = max(known.items(), key=lambda x: x[1]["pnl"])
        worst_ses = min(known.items(), key=lambda x: x[1]["pnl"])
        lines.append(
            f"\nBest session: {best_ses[0]} — ${best_ses[1]['pnl']:+,.2f} "
            f"({best_ses[1]['win_rate']:.0f}% WR, {best_ses[1]['trades']} trades)"
        )
        lines.append(
            f"Worst session: {worst_ses[0]} — ${worst_ses[1]['pnl']:+,.2f} "
            f"({worst_ses[1]['win_rate']:.0f}% WR, {worst_ses[1]['trades']} trades)"
        )

    # Best/worst days
    days = ta.pnl_by_day_of_week(trades)
    if days:
        best_day = max(days.items(), key=lambda x: x[1]["pnl"])
        worst_day = min(days.items(), key=lambda x: x[1]["pnl"])
        lines.append(
            f"\nBest day: {best_day[0]} — ${best_day[1]['pnl']:+,.2f} "
            f"({best_day[1]['win_rate']:.0f}% WR, {best_day[1]['trades']} trades)"
        )
        lines.append(
            f"Worst day: {worst_day[0]} — ${worst_day[1]['pnl']:+,.2f} "
            f"({worst_day[1]['win_rate']:.0f}% WR, {worst_day[1]['trades']} trades)"
        )

    # Streaks
    st = ta.streaks(trades)
    lines.append(f"\nStreaks: best win {st['max_win_streak']}, worst loss {st['max_loss_streak']}")

    return "\n".join(lines)


def _build_behavioral_section(trades: list[dict]) -> str:
    """Section b) BEHAVIORAL ANALYSIS."""
    lines: list[str] = ["=== BEHAVIORAL PATTERNS ==="]

    # Revenge
    revenge_list = ta.detect_revenge_trades(trades)
    if revenge_list:
        cost = ta.revenge_trade_cost(trades)
        r_wins = sum(1 for r in revenge_list if _net_profit(r["trade"]) > 0)
        r_losses = len(revenge_list) - r_wins
        r_pnl = sum(_net_profit(r["trade"]) for r in revenge_list)
        lines.append(
            f"Revenge trading: {len(revenge_list)} instances, "
            f"{r_wins}W/{r_losses}L, net P&L ${r_pnl:+,.2f}, "
            f"loser cost ${cost:+,.2f}"
        )
    else:
        lines.append("Revenge trading: none detected")

    # Martingale
    mart_list = ta.detect_martingale(trades)
    if mart_list:
        m_pnl = sum(_net_profit(m["trade"]) for m in mart_list)
        lines.append(f"Martingale: {len(mart_list)} instances, net P&L ${m_pnl:+,.2f}")
    else:
        lines.append("Martingale: none detected")

    # Overtrading
    ot = ta.detect_overtrading(trades)
    if ot["overtrading_days"] > 0 and ot["overtrading_wr"] is not None:
        lines.append(
            f"Overtrading: {ot['overtrading_days']} days with 5+ trades, "
            f"WR {ot['overtrading_wr']:.0f}% vs normal {(ot['normal_wr'] or 0):.0f}%, "
            f"P&L ${ot['overtrading_pnl']:,.2f}"
        )
    else:
        lines.append("Overtrading: none detected")

    # Averaging down
    avg_down = ta.detect_averaging_down(trades)
    if avg_down:
        ad_pnl = sum(_net_profit(a["trade"]) for a in avg_down)
        lines.append(f"Averaging down: {len(avg_down)} instances, net P&L ${ad_pnl:+,.2f}")
    else:
        lines.append("Averaging down: none detected")

    # Quick exits
    quick_list = ta.detect_quick_exits(trades)
    if quick_list:
        q_pnl = sum(_net_profit(q["trade"]) for q in quick_list)
        lines.append(f"Quick exits (<2 min): {len(quick_list)} trades, net P&L ${q_pnl:+,.2f}")
    else:
        lines.append("Quick exits: none detected")

    # SL usage
    sl = ta.sl_usage(trades)
    no_sl_losers = [
        t for t in trades
        if (not t.get("stop_loss") or float(t.get("stop_loss", 0)) == 0)
        and _net_profit(t) < 0
    ]
    no_sl_cost = sum(_net_profit(t) for t in no_sl_losers)
    lines.append(
        f"SL usage: {sl['with_sl']} with SL, {sl['without_sl']} without. "
        f"Cost of no-SL losers: ${no_sl_cost:+,.2f}"
    )

    return "\n".join(lines)


def _calendar_event_sort_key(event: dict[str, str]) -> str:
    return f"{event['date']}T{event['time_utc']}"


def _build_calendar_section(
    trades: list[dict],
) -> tuple[str, list[dict[str, Any]]]:
    """Section c) ECONOMIC CALENDAR IMPACT and per-trade event matches."""
    if not trades:
        return "", []

    dates_utc = [trade_instant_utc(t.get("opened_at")) for t in trades]
    dates_utc = [d for d in dates_utc if d]
    if not dates_utc:
        return "", []

    date_from = min(dates_utc).astimezone(timezone.utc).strftime("%Y-%m-%d")
    date_to = max(dates_utc).astimezone(timezone.utc).strftime("%Y-%m-%d")

    events = load_calendar(date_from=date_from, date_to=date_to, impact="high")
    if not events:
        return (
            "=== ECONOMIC CALENDAR IMPACT ===\nNo high-impact events in this period.",
            [],
        )

    matched = match_trades_to_events(
        trades,
        events,
        window_before_minutes=30,
        window_after_minutes=60,
    )
    impact = calculate_news_impact(
        trades,
        events,
        window_before_minutes=30,
        window_after_minutes=60,
        matched=matched,
    )

    lines: list[str] = ["=== ECONOMIC CALENDAR IMPACT ==="]

    n_wr = f"{impact['news_wr']:.0f}%" if impact["news_wr"] is not None else "N/A"
    norm_wr = f"{impact['normal_wr']:.0f}%" if impact["normal_wr"] is not None else "N/A"

    lines.append(
        f"Trades near high-impact events: {impact['news_trades_count']} trades, "
        f"WR {n_wr}, P&L ${impact['news_pnl']:+,.2f}"
    )
    lines.append(
        f"Normal trades: {impact['normal_trades_count']} trades, "
        f"WR {norm_wr}, P&L ${impact['normal_pnl']:+,.2f}"
    )

    if impact["money_lost_to_news"] < 0:
        lines.append(f"News cost: ${abs(impact['money_lost_to_news']):,.2f} lost to news-time trades")
    elif impact["money_lost_to_news"] > 0:
        lines.append(f"News benefit: ${impact['money_lost_to_news']:,.2f} gained from news-time trades")

    if impact["worst_events"]:
        lines.append("\nWorst events:")
        for evt in impact["worst_events"][:5]:
            lines.append(
                f"  {evt['date']} {evt['event_name']}: "
                f"{evt['trades_count']} trades, P&L ${evt['pnl']:+,.2f}"
            )

    return "\n".join(lines), matched


def _build_volatility_section(
    trades: list[dict],
    ohlc_by_symbol: dict[str, list[dict]] | None = None,
) -> str:
    """Section d) VOLATILITY ANALYSIS."""
    ctx = build_volatility_context_for_coaching(
        trades,
        ohlc_by_symbol=ohlc_by_symbol,
    )
    if ctx:
        return f"=== {ctx}"
    return "=== VOLATILITY ANALYSIS ===\nNo volatile days detected in this period."


def _near_event_tags_by_trade(
    event_matches: list[dict[str, Any]],
) -> dict[tuple, list[str]]:
    near_by_key: dict[tuple, list[str]] = {}
    for m in event_matches:
        tk = _trade_key(m["trade"])
        sorted_events = sorted(
            m["matched_events"],
            key=lambda me: _calendar_event_sort_key(me["event"]),
        )
        near_by_key[tk] = [
            f"NEAR-{me['event']['event_name']}" for me in sorted_events
        ]
    return near_by_key


def _build_trade_log(
    trades: list[dict],
    event_matches: list[dict[str, Any]] | None = None,
) -> str:
    """Full trade history with behavioral and calendar proximity tags."""
    revenge_list = ta.detect_revenge_trades(trades)
    mart_list = ta.detect_martingale(trades)
    quick_list = ta.detect_quick_exits(trades)

    revenge_keys = {_trade_key(r["trade"]) for r in revenge_list}
    mart_keys = {_trade_key(m["trade"]) for m in mart_list}
    quick_keys = {_trade_key(q["trade"]) for q in quick_list}
    near_by_key = _near_event_tags_by_trade(event_matches or [])

    sorted_trades = sorted(
        trades,
        key=lambda t: trade_instant_utc(t.get("opened_at")) or _EPOCH_COACH,
    )

    lines = [f"=== TRADE LOG ({len(sorted_trades)} trades) ==="]
    for t in sorted_trades:
        tk = _trade_key(t)
        tags: list[str] = []
        if tk in revenge_keys:
            tags.append("REVENGE")
        if tk in mart_keys:
            tags.append("MARTINGALE")
        if tk in quick_keys:
            tags.append("QUICK-EXIT")
        tags.extend(near_by_key.get(tk, []))
        lines.append(_trade_line(t, tag=",".join(tags)))
    return "\n".join(lines)


# ===================================================================
# FULL COACHING PROMPT BUILDER
# ===================================================================

def build_full_coaching_prompt(
    trades: list[dict],
    account: dict | None = None,
    previous_session: dict | None = None,
    *,
    ohlc_by_symbol: dict[str, list[dict]] | None = None,
) -> tuple[str, str]:
    """Assemble all RAG data into a coaching prompt.

    Args:
        trades: Trade dicts.
        account: Account dict with broker_timezone, starting_balance, name.
        previous_session: Previous coaching session dict (if repeat analysis).
        ohlc_by_symbol: Pre-fetched OHLC data per symbol (for testing).

    Returns:
        Tuple of (system_prompt, context_data).
    """
    if not trades:
        raise LLMError("No trades to analyze")

    balance = (account or {}).get("starting_balance")

    # Build all sections
    statistics = _build_statistics_section(trades, balance)
    behavioral = _build_behavioral_section(trades)
    calendar, event_matches = _build_calendar_section(trades)
    volatility = _build_volatility_section(trades, ohlc_by_symbol)
    trade_log = _build_trade_log(trades, event_matches)

    context = "\n\n".join([
        statistics, behavioral, calendar, volatility, trade_log,
    ])

    if previous_session:
        prompt = _build_repeat_prompt(previous_session)
    else:
        prompt = _FIRST_ANALYSIS_PROMPT

    account_name = (account or {}).get("name", "")
    if account_name:
        prompt += f'\n\nAccount: "{account_name}"'

    return prompt, context


# ===================================================================
# PROMPTS
# ===================================================================

_FIRST_ANALYSIS_PROMPT = """\
You are a personal trading coach analyzing a trader's complete history for the first time.

IMPORTANT RULES:
- All numbers below are calculated programmatically and verified. Trust them completely.
- Never recalculate or estimate numbers. Use exactly what is provided.
- You are an analyst, not an advisor. Show facts and patterns.
- Never say "buy" or "sell". Say "your data shows X, the decision is yours."
- Be direct and specific. No generic advice. No motivational phrases. No closing fluff.
- Respond in English.
- Never use these words: amygdala, prefrontal cortex, cognitive bias, loss aversion, intermittent reinforcement, dopamine, neural, psychology.

DOLLAR AMOUNT FORMATTING (strict):
- Always include a sign on every dollar amount: positive values as +$NNN, negative values as -$NNN.
- Never write a dollar amount without a sign (no $300, no $1,234).
- Never use the form $-NNN. The minus sign always precedes the dollar sign: -$NNN.
- Examples: +$1,234 (gain), -$567 (loss), -$3,200 (loss).

YOUR TASK:
Produce an analytical narrative in three sections, in this exact order, each with a bold markdown header.

## Your Strength

Identify the strongest signal in this trader's history. Pick one from:
- Best-performing pair (highest +$ P&L by symbol, or smallest -$ P&L if all are negative)
- Best-performing session
- Best-performing day of the week
- Longest winning streak
- Strongest behavioral discipline (e.g., consistent stop-loss usage, absence of revenge trading, absence of martingale, absence of averaging down, or a behavioral pattern with positive net +$ P&L)

Pick the slice that most clearly distinguishes this trader. Use whichever signal type carries the strongest evidence. State it as fact with specific numbers where applicable.

If the strongest signal is a P&L-based slice that is still negative overall, state it factually without framing it as a strength. Example phrasing: "The best-performing pair was XYZ with -$NNN — still negative, but the smallest loss across your symbols. This is your relative edge in this dataset."

If the strongest signal is a behavioral discipline (e.g., high SL usage, no revenge trading detected, no martingale detected), state it as positive evidence of trader discipline with the specific count or percentage from the data.

If the trader is overall profitable, name the best slice with its numbers.

Format: 2-4 sentences of prose. No bullets in this section.

## Main Problems

Identify up to 3 of the most important problems in this trader's history. Draw evidence only from these context sections:
- TRADE STATISTICS (worst pair, worst session, worst day-of-week, profit factor, expectancy, streaks)
- BEHAVIORAL PATTERNS (revenge trading, martingale, overtrading, averaging down, quick exits, SL usage)

Do not draw problems from VOLATILITY ANALYSIS or ECONOMIC CALENDAR IMPACT — those go in the next section.

Rules:
- If the data shows 1 problem, output 1 bullet. If 2, output 2. If 3, output 3. Never inflate the count. Maximum 3.
- If neither behavioral nor strategic problems exist after honest examination, output a single bullet: "No significant problems detected — the trading pattern is consistent with profitability."
- Each bullet has a short label followed by 1-2 sentences of evidence with specific numbers.

Format each bullet as:
- **Short label of the problem.** Evidence with specific numbers from the data.

(The label-and-evidence shape above is illustrative; derive yours from the actual data, do not copy phrasing.)

## Hidden Patterns

Show how external market conditions interacted with the trader's behavior. Exactly 2 bullets — one on volatility, one on economic events. Both bullets are mandatory. If the data shows zero exposure to a factor, that absence is itself the finding.

Bullet 1 — Volatility: How did the trader perform on high-volatility days vs normal-volatility days? Use the VOLATILITY ANALYSIS section. In the bullet, briefly explain in plain language that high-volatility days are days where the instrument's Average True Range (ATR) — a standard market-volatility indicator — was 1.5x or more above its normal level. Compare counts, win rates, and P&L between the two regimes. State which regime the trader performed better in.

Bullet 2 — Economic events: How did the trader perform on trades near high-impact news events vs trades outside news windows? Use the ECONOMIC CALENDAR IMPACT section. If no high-impact events overlapped with the trader's trades in this period, write: "No high-impact news events overlapped with your trades in this period — your trading was independent of scheduled catalysts."

Format each bullet as:
- **Volatility:** Brief ATR-based definition, then finding with specific numbers.
- **Economic events:** Finding with specific numbers, or zero-exposure statement.

NARRATIVE FORMAT:
- Target length: 500 words across all three sections combined.
- Use bold markdown headers (##) for each section title, exactly as written above.
- Use markdown bullets (- ) for items in Main Problems and Hidden Patterns.
- Your Strength is prose, not bullets.
- Use the trader's actual numbers throughout, in the +$NNN / -$NNN format.
- Do not include any "Action Plan", "Recommendations", "Projected Savings", or call-to-action content in the narrative. The action plan is generated separately in the rules block below.

After the narrative, end your response with a <rules> block containing a JSON array of exactly 3 rule objects. No text after </rules>.

Each rule object MUST address a DIFFERENT aspect of the trader's behavior or strategy. Do not produce three rules on the same topic. Different aspects include:
- Volatility regime
- Session
- Day of week
- Instrument / pair
- Behavioral pattern (revenge, overtrading, averaging down, quick exits, etc.)
- Frequency / trade count
- Risk management (stop-loss usage, position sizing)

Selection method (read this carefully — the Action Plan is generated INDEPENDENTLY of the Main Problems section above):

The 3 rules in the Action Plan are NOT obliged to map onto the 3 problems from Main Problems. Rules may overlap with problems, or address entirely different aspects, depending on where the data shows the highest projected dollar impact.

For each candidate aspect supported by the data — whether it represents an avoided loss (e.g., stop trading an instrument that loses money) or a captured gain (e.g., concentrate trades during a regime where the trader makes money) — estimate the monthly dollar impact if the corresponding rule is followed.

Then select the 3 aspects with the highest projected dollar impact. Do NOT default to selecting only negative aspects. If a positive aspect (e.g., a high-performing volatility regime, session, or instrument) shows higher projected impact than a negative aspect, include the positive one and drop the lower-impact negative one.

The savings_estimate_usd field below is where you record that estimate; use it as your ranking criterion. Mixing negative-constraint and positive-constraint rules in the same Action Plan is expected and encouraged when the data supports it.

Rule wording style:
- For negative constraints (avoiding loss-generating behavior), use direct imperatives: "Stop trading X", "Avoid Y session", "Never add to losing positions", "Maximum N trades per day".
- For positive constraints (capturing gain-generating behavior), use recommendation form, not imperative: "Consider concentrating trades during X", "Explore trading more in Y regime". Do NOT command "trade only on X" or "trade exclusively during Y" — historical correlation does not guarantee future causation, and the recommendation form respects that uncertainty.

Each rule object:
- "action": short imperative (for negative constraints) or recommendation (for positive constraints), 5-12 words
- "rationale": 1-2 sentences with specific numbers from the data, using the +$NNN / -$NNN format
- "savings_estimate_usd": integer, projected monthly savings in dollars if this rule is followed (0 if not estimable). Used internally to rank the rules — the 3 rules you return must be the 3 with highest projected impact.

Example structure (illustrative — derive your own actions and rationales from THIS trader's data, do not copy these phrases):

<rules>
[
  {"action": "Stop trading GBPUSD", "rationale": "GBPUSD returned -$890 over 18 trades with 28% win rate.", "savings_estimate_usd": 400},
  {"action": "Consider concentrating trades during high-volatility regimes", "rationale": "Your 22 high-volatility trades returned +$1,375 vs -$340 on normal-volatility days; the regime gap is +$1,715.", "savings_estimate_usd": 350},
  {"action": "Maximum 3 trades per day", "rationale": "On days with 5+ trades you returned -$1,200; on days with 3 or fewer you returned +$450.", "savings_estimate_usd": 250}
]
</rules>
"""


def _build_repeat_prompt(prev: dict) -> str:
    """Build repeat analysis prompt with previous session comparison."""
    created = prev.get("created_at", "unknown date")
    main_problem = prev.get("main_problem", "not recorded")
    prev_rules = parse_json_field(prev.get("rules")) or []
    recommendations = parse_json_field(prev.get("recommendations")) or []
    metrics = parse_json_field(prev.get("metrics_snapshot")) or {}

    rec_text = ""
    if prev_rules:
        for i, rule in enumerate(prev_rules, 1):
            action = rule.get("action", "?") if isinstance(rule, dict) else str(rule)
            rec_text += f"\n   {i}. {action}"
    elif recommendations:
        for i, r in enumerate(recommendations, 1):
            rec_text += f"\n   {i}. {r}"
    else:
        rec_text = "\n   (not recorded)"

    metrics_text = ""
    if metrics:
        for k, v in metrics.items():
            metrics_text += f"\n   {k}: {v}"
    else:
        metrics_text = "\n   (not recorded)"

    return f"""\
You are a personal trading coach. This is a follow-up analysis.

IMPORTANT RULES:
- All numbers are calculated programmatically. Trust them completely.
- Compare current metrics with previous session to show progress.
- Be direct about whether the trader followed recommendations.
- Never use these words: amygdala, prefrontal cortex, cognitive bias, loss aversion, intermittent reinforcement, dopamine, neural, psychology

PREVIOUS SESSION ({created}):
- Main problem was: {main_problem}
- Recommendations were: {rec_text}
- Metrics at that time: {metrics_text}

YOUR TASK:
1. VERDICT: Start with emoji: 👍 progress / 👎 setback / ➡️ no change

2. RULE CHECK: For each of the 3 previous recommendations:
   - Did the trader follow it? YES/NO with evidence from data
   - If YES: how much $ did it save?
   - If NO: how much $ did it cost?

3. NEW INSIGHT: What changed? Any new pattern that wasn't there before? \
Use volatility and calendar data to explain WHY things changed.

4. PROGRESS SCORE: Rate improvement 1-10 with justification.

Format: 300 words max. Start with verdict emoji immediately. \
Use the trader's actual numbers throughout. Do NOT include an updated plan in the narrative.

After the narrative, you MUST end your response with a <rules> block containing a JSON array \
of exactly 3 rule objects (keep rules that worked, replace rules that did not). No text after </rules>.

Each rule object:
- "action": short imperative, 5-12 words
- "rationale": 1-2 sentences with specific numbers from the data
- "savings_estimate_usd": integer, projected monthly savings if followed (0 if not estimable)

Example:
<rules>
[
  {{"action": "Keep maximum 3 trades per day", "rationale": "Average dropped from 5 to 2.8; saved ~$350.", "savings_estimate_usd": 350}},
  {{"action": "Close terminal for 1 hour after any loss", "rationale": "4 revenge trades cost $180 this period.", "savings_estimate_usd": 300}},
  {{"action": "Only trade London session", "rationale": "Asian session trades lost $150 vs London.", "savings_estimate_usd": 150}}
]
</rules>"""


# ===================================================================
# METRICS SNAPSHOT
# ===================================================================

def _build_metrics_snapshot(trades: list[dict]) -> dict[str, Any]:
    """Build a metrics snapshot for storage."""
    return {
        "trades_count": len(trades),
        "win_rate": ta.win_rate(trades),
        "total_pnl": ta.total_pnl(trades),
        "profit_factor": ta.profit_factor(trades),
        "revenge_count": len(ta.detect_revenge_trades(trades)),
        "revenge_cost": ta.revenge_trade_cost(trades),
        "martingale_count": len(ta.detect_martingale(trades)),
        "quick_exits_count": len(ta.detect_quick_exits(trades)),
    }


# ===================================================================
# MAIN COACHING FUNCTION
# ===================================================================

async def get_ai_coaching(
    user_id: str,
    account_id: str,
    *,
    period_from: str | None = None,
    period_to: str | None = None,
    ohlc_by_symbol: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    """Generate AI coaching with full RAG context, save session to DB.

    Args:
        user_id: Supabase user ID.
        account_id: Supabase account ID.
        period_from: ISO date string for trade filter (optional).
        period_to: ISO date string for trade filter (optional).
        ohlc_by_symbol: Pre-fetched OHLC data (optional, for testing).

    Returns:
        Dict with session_id, ai_response, metrics_snapshot, verdict, created_at.
    """
    from tradecoach.db.queries import get_account, get_client, get_trades

    client = get_client()

    # Fetch account
    account = get_account(client, account_id)
    if not account:
        raise LLMError(f"Account {account_id} not found")
    account_dict = account.model_dump()

    # Fetch trades
    kwargs: dict[str, Any] = {"account_id": account_id}
    if period_from:
        kwargs["since"] = datetime.fromisoformat(period_from)
    if period_to:
        kwargs["until"] = datetime.fromisoformat(period_to)
    trade_models = get_trades(client, user_id, limit=None, **kwargs)
    trades = [t.model_dump() for t in trade_models]

    if not trades:
        raise LLMError("No trades found for this account/period")

    from tradecoach.services.beta_quota import (
        BetaQuotaError,
        assert_can_generate_coaching,
        increment_coaching_sessions_used,
        rollback_coaching_session,
    )

    assert_can_generate_coaching(client, user_id, account_id)

    # Fetch previous coaching session
    prev_session = _get_latest_coaching_session(client, user_id, account_id)

    # Build prompt
    prompt, context = build_full_coaching_prompt(
        trades, account_dict, prev_session,
        ohlc_by_symbol=ohlc_by_symbol,
    )

    # Call LLM
    ai_text, usage = await deep_analysis(prompt, context)

    # Build metrics snapshot
    metrics = _build_metrics_snapshot(trades)

    rules = _parse_rules(ai_text)
    narrative = _strip_rules_block(ai_text)
    main_problem = _parse_main_problem(narrative)
    verdict = _parse_verdict(narrative) if prev_session else None

    # Save session
    session_id = _save_coaching_session(
        client,
        user_id=user_id,
        account_id=account_id,
        period_from=period_from,
        period_to=period_to,
        metrics_snapshot=metrics,
        rag_context={
            "statistics": True,
            "behavioral": True,
            "calendar": True,
            "volatility": True,
            "news": False,
        },
        recommendations=None,
        rules=rules,
        ai_response=narrative,
        verdict=verdict,
        main_problem=main_problem,
        new_trades_count=len(trades),
        model_used=usage.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=usage.cost_usd,
        llm_latency_ms=usage.latency_ms,
    )

    if not increment_coaching_sessions_used(client, user_id):
        rollback_coaching_session(client, session_id)
        from tradecoach.services.beta_quota import COACHING_LIFETIME_LIMIT_DETAIL
        raise BetaQuotaError(COACHING_LIFETIME_LIMIT_DETAIL)

    return {
        "session_id": session_id,
        "ai_response": narrative,
        "metrics_snapshot": metrics,
        "verdict": verdict,
        "rules": rules,
        "created_at": datetime.now(tz=None).isoformat(),
        "usage": {
            "model": usage.model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": usage.cost_usd,
        },
    }


# ===================================================================
# DB helpers for coaching sessions
# ===================================================================

def _get_latest_coaching_session(
    client: Any, user_id: str, account_id: str,
) -> dict | None:
    """Get the most recent coaching session for this account."""
    result = (
        client.table("coaching_sessions")
        .select("*")
        .eq("user_id", user_id)
        .eq("account_id", account_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]


def _save_coaching_session(
    client: Any,
    *,
    user_id: str,
    account_id: str,
    period_from: str | None,
    period_to: str | None,
    metrics_snapshot: dict,
    rag_context: dict,
    recommendations: list[str] | None,
    rules: list[dict[str, Any]] | None,
    ai_response: str,
    verdict: str | None,
    main_problem: str | None,
    new_trades_count: int,
    model_used: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    llm_latency_ms: float,
) -> str:
    """Insert a coaching session row. Returns the session ID."""
    row = {
        "user_id": user_id,
        "account_id": account_id,
        "period_from": period_from,
        "period_to": period_to,
        "metrics_snapshot": json.dumps(metrics_snapshot),
        "rag_context": json.dumps(rag_context),
        "recommendations": json.dumps(recommendations) if recommendations is not None else None,
        "rules": json.dumps(rules) if rules is not None else None,
        "ai_response": ai_response,
        "verdict": verdict,
        "main_problem": main_problem,
        "new_trades_count": new_trades_count,
        "model_used": model_used,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "llm_latency_ms": int(round(llm_latency_ms)),
    }
    result = client.table("coaching_sessions").insert(row).execute()
    return result.data[0]["id"]


# ===================================================================
# Parsers for AI response
# ===================================================================

_RULES_BLOCK_RE = re.compile(r"<rules>\s*(.*?)\s*</rules>", re.DOTALL | re.IGNORECASE)
_RULES_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _extract_rules_json(text: str) -> str | None:
    """Return raw JSON string from the last <rules> block, or None."""
    matches = list(_RULES_BLOCK_RE.finditer(text))
    if not matches:
        return None
    content = matches[-1].group(1).strip()
    content = _RULES_FENCE_RE.sub("", content).strip()
    return content or None


def _validate_rules(data: object) -> list[dict[str, Any]] | None:
    """Validate parsed rules array shape. Returns normalized list or None."""
    if not isinstance(data, list) or len(data) != 3:
        return None
    normalized: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            return None
        action = item.get("action")
        rationale = item.get("rationale")
        savings = item.get("savings_estimate_usd")
        if not isinstance(action, str) or not action.strip():
            return None
        if not isinstance(rationale, str) or not rationale.strip():
            return None
        if isinstance(savings, bool) or not isinstance(savings, int):
            return None
        normalized.append({
            "action": action.strip(),
            "rationale": rationale.strip(),
            "savings_estimate_usd": savings,
        })
    return normalized


def _parse_rules(text: str) -> list[dict[str, Any]] | None:
    """Extract and validate structured rules from a <rules> JSON block."""
    raw = _extract_rules_json(text)
    if raw is None:
        logger.warning("rules parse failed: no <rules> block found")
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "rules parse failed: invalid JSON (%s); excerpt=%r",
            exc,
            raw[:300],
        )
        return None
    rules = _validate_rules(data)
    if rules is None:
        logger.warning("rules parse failed: invalid shape; excerpt=%r", raw[:300])
    return rules


def _strip_rules_block(text: str) -> str:
    """Remove all <rules>...</rules> blocks from the narrative."""
    return _RULES_BLOCK_RE.sub("", text).rstrip()


def _parse_main_problem(text: str) -> str | None:
    """Extract the main problem (first paragraph or up to first heading)."""
    lines = text.strip().split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if result:
                break
            continue
        # Stop at next numbered section
        if stripped.startswith("2.") or stripped.startswith("**2"):
            break
        result.append(stripped)
    return " ".join(result)[:500] if result else None


def _parse_verdict(text: str) -> str | None:
    """Extract verdict emoji from repeat analysis."""
    first_line = text.strip().split("\n")[0] if text else ""
    if "👍" in first_line:
        return "progress"
    elif "👎" in first_line:
        return "setback"
    elif "➡️" in first_line:
        return "no_change"
    return None


# ===================================================================
# Legacy function (kept for backward compatibility)
# ===================================================================

_LEGACY_PROMPT = """\
You are a personal trading coach analyzing one specific trader's data. \
Find the ONE most surprising insight that this trader hasn't noticed themselves.

Find something UNEXPECTED. Not the obvious worst pair or worst day. \
Find a hidden connection — a sequence, a trigger, a pattern that only \
appears when you cross-reference multiple data points.

Rules:
- Reference specific dates and dollar amounts from the trade log
- Max 120 words. Telegram message, not an essay.
- Simple language. Like a text from a smart friend who looked at your trades.
- Never use these words: amygdala, prefrontal cortex, cognitive bias, loss aversion, intermittent reinforcement, dopamine, neural, psychology
- End with one specific action and the dollar amount it would save
- No fixed structure. No template. Just say the most important thing.
- Start with the insight, not with pleasantries.
"""


def _build_context(trades: list[dict], account_balance: float | None) -> str:
    """Legacy context builder (for backward compatibility)."""
    if not trades:
        return "No trades to analyze."

    lines: list[str] = []
    wr = ta.win_rate(trades)
    pnl = ta.total_pnl(trades)
    lines.append(f"Trades: {len(trades)} | Win rate: {wr:.1f}% | P&L: ${pnl:,.2f}")
    if account_balance and account_balance > 0:
        lines.append(f"Balance: ${account_balance:,.2f}")

    sessions = ta.pnl_by_session(trades)
    known = {k: v for k, v in sessions.items() if k != "Unknown"}
    if known:
        lines.append("\n=== BY SESSION ===")
        for s, d in sorted(known.items(), key=lambda x: x[1]["pnl"]):
            lines.append(f"  {s}: ${d['pnl']:,.2f} ({d['win_rate']:.0f}% WR, {d['trades']} trades)")

    symbols = ta.pnl_by_symbol(trades)
    if symbols:
        lines.append("\n=== BY PAIR ===")
        for sym, data in sorted(symbols.items(), key=lambda x: x[1]["pnl"]):
            lines.append(f"  {sym}: ${data['pnl']:,.2f} ({data['win_rate']:.0f}% WR, {data['trades']} trades)")

    st = ta.streaks(trades)
    lines.append(f"\nStreaks: best win {st['max_win_streak']}, worst loss {st['max_loss_streak']}")

    # Behavioral
    revenge_list = ta.detect_revenge_trades(trades)
    mart_list = ta.detect_martingale(trades)
    quick_list = ta.detect_quick_exits(trades)
    revenge_keys = {_trade_key(r["trade"]) for r in revenge_list}
    mart_keys = {_trade_key(m["trade"]) for m in mart_list}
    quick_keys = {_trade_key(q["trade"]) for q in quick_list}

    # Trade log
    sorted_trades = sorted(
        trades,
        key=lambda t: trade_instant_utc(t.get("opened_at")) or _EPOCH_COACH,
    )
    recent = sorted_trades[-50:]
    lines.append(f"\n=== TRADE LOG (last {len(recent)} of {len(trades)}) ===")
    for t in recent:
        tk = _trade_key(t)
        tags = []
        if tk in revenge_keys:
            tags.append("REVENGE")
        if tk in mart_keys:
            tags.append("MARTINGALE")
        if tk in quick_keys:
            tags.append("QUICK-EXIT")
        lines.append(_trade_line(t, tag=",".join(tags)))

    # Behavioral sections
    if revenge_list:
        cost = ta.revenge_trade_cost(trades)
        lines.append(f"\n=== REVENGE SEQUENCES ({len(revenge_list)}, total cost ${cost:,.2f}) ===")
        for r in revenge_list:
            lines.append(f"  TRIGGER: {_trade_line(r['previous_loss']).strip()}")
            lines.append(f"  REVENGE {r['gap_seconds']}s later: {_trade_line(r['trade']).strip()}")
            lines.append("")

    if mart_list:
        lines.append(f"\n=== MARTINGALE ({len(mart_list)} instances) ===")
        for m in mart_list:
            lines.append(f"  LOSS: {_trade_line(m['previous_trade']).strip()}")
            lines.append(f"  +{m['lot_increase_pct']}% LOT: {_trade_line(m['trade']).strip()}")
            lines.append("")

    if quick_list:
        lines.append(f"\n=== QUICK EXITS ({len(quick_list)} trades, held <2 min) ===")
        for q in quick_list[:5]:
            lines.append(f"  {_trade_line(q['trade']).strip()} (held {q['hold_seconds']}s)")

    ot = ta.detect_overtrading(trades)
    if ot["overtrading_days"] > 0 and ot["overtrading_wr"] is not None:
        lines.append(
            f"\nOvertrading: {ot['overtrading_days']} days with 5+ trades, "
            f"WR {ot['overtrading_wr']:.0f}% vs normal {(ot['normal_wr'] or 0):.0f}%, "
            f"P&L ${ot['overtrading_pnl']:,.2f}"
        )

    return "\n".join(lines)


async def generate_ai_coaching(
    trades: list[dict],
    account_balance: float | None = None,
    account_name: str = "",
) -> tuple[str, LLMUsage]:
    """Legacy: Generate AI coaching insight (single-insight Telegram format).

    Kept for backward compatibility with Telegram bot.
    """
    if not trades:
        raise LLMError("No trades to analyze")

    context = _build_context(trades, account_balance)

    prompt = _LEGACY_PROMPT
    if account_name:
        prompt += f'\nAccount: "{account_name}"'

    text, usage = await deep_analysis(prompt, context)

    header = "\U0001f9e0 AI COACHING"
    if account_name:
        header += f" — {account_name}"
    header += "\n" + "\u2500" * 20

    footer = f"\n\n\U0001f4b0 ${usage.cost_usd:.4f}"

    return f"{header}\n\n{text}{footer}", usage
