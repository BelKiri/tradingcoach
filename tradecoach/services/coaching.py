"""
AI coaching — assembles ALL RAG data (trade stats, behavioral patterns,
calendar impact, volatility analysis, news context) into a prompt for
Claude Sonnet to produce personalized coaching.

Supports first-time analysis and repeat analysis with previous session comparison.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tradecoach.services import trade_analyzer as ta
from tradecoach.services._helpers import _net_profit, _to_dt
from tradecoach.services.tz_utils import trade_instant_utc
from tradecoach.utils.json_helpers import parse_json_field
from tradecoach.services.calendar import (
    calculate_news_impact,
    load_calendar,
)
from tradecoach.services.llm import LLMError, LLMUsage, deep_analysis
from tradecoach.services.market_data import (
    build_volatility_context_for_coaching,
)
from tradecoach.services.news import build_news_context_for_coaching

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


def _build_calendar_section(trades: list[dict]) -> str:
    """Section c) ECONOMIC CALENDAR IMPACT."""
    if not trades:
        return ""

    dates_utc = [trade_instant_utc(t.get("opened_at")) for t in trades]
    dates_utc = [d for d in dates_utc if d]
    if not dates_utc:
        return ""

    date_from = min(dates_utc).astimezone(timezone.utc).strftime("%Y-%m-%d")
    date_to = max(dates_utc).astimezone(timezone.utc).strftime("%Y-%m-%d")

    events = load_calendar(date_from=date_from, date_to=date_to, impact="high")
    if not events:
        return "=== ECONOMIC CALENDAR IMPACT ===\nNo high-impact events in this period."

    impact = calculate_news_impact(
        trades,
        events,
        window_before_minutes=30,
        window_after_minutes=60,
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

    return "\n".join(lines)


def _build_volatility_section(
    trades: list[dict],
    news: list[dict[str, str]] | None = None,
    ohlc_by_symbol: dict[str, list[dict]] | None = None,
) -> str:
    """Section d) VOLATILITY ANALYSIS."""
    ctx = build_volatility_context_for_coaching(
        trades,
        news=news,
        ohlc_by_symbol=ohlc_by_symbol,
    )
    if ctx:
        return f"=== {ctx}"
    return "=== VOLATILITY ANALYSIS ===\nNo volatile days detected in this period."


def _build_news_section(
    trades: list[dict],
    news: list[dict[str, str]] | None,
    broker_timezone: str,
) -> str:
    """Section e) NEWS CONTEXT."""
    if not news:
        return "=== NEWS CONTEXT ===\nNo news data available for this period."

    ctx = build_news_context_for_coaching(trades, news)
    if ctx:
        return f"=== {ctx}"
    return "=== NEWS CONTEXT ===\nNo trades matched any news in this period."


def _build_trade_log(trades: list[dict]) -> str:
    """Last 50 trades with behavioral tags."""
    revenge_list = ta.detect_revenge_trades(trades)
    mart_list = ta.detect_martingale(trades)
    quick_list = ta.detect_quick_exits(trades)

    revenge_keys = {_trade_key(r["trade"]) for r in revenge_list}
    mart_keys = {_trade_key(m["trade"]) for m in mart_list}
    quick_keys = {_trade_key(q["trade"]) for q in quick_list}

    sorted_trades = sorted(
        trades,
        key=lambda t: trade_instant_utc(t.get("opened_at")) or _EPOCH_COACH,
    )
    recent = sorted_trades[-50:]

    lines = [f"=== TRADE LOG (last {len(recent)} of {len(trades)}) ==="]
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
    return "\n".join(lines)


# ===================================================================
# FULL COACHING PROMPT BUILDER
# ===================================================================

def build_full_coaching_prompt(
    trades: list[dict],
    account: dict | None = None,
    previous_session: dict | None = None,
    *,
    news: list[dict[str, str]] | None = None,
    ohlc_by_symbol: dict[str, list[dict]] | None = None,
) -> tuple[str, str]:
    """Assemble all RAG data into a coaching prompt.

    Args:
        trades: Trade dicts.
        account: Account dict with broker_timezone, starting_balance, name.
        previous_session: Previous coaching session dict (if repeat analysis).
        news: News items for context.
        ohlc_by_symbol: Pre-fetched OHLC data per symbol (for testing).

    Returns:
        Tuple of (system_prompt, context_data).
    """
    if not trades:
        raise LLMError("No trades to analyze")

    broker_tz = (account or {}).get("broker_timezone", "UTC+2")
    balance = (account or {}).get("starting_balance")

    # Build all sections
    statistics = _build_statistics_section(trades, balance)
    behavioral = _build_behavioral_section(trades)
    calendar = _build_calendar_section(trades)
    volatility = _build_volatility_section(trades, news, ohlc_by_symbol)
    news_section = _build_news_section(trades, news, broker_tz)
    trade_log = _build_trade_log(trades)

    context = "\n\n".join([
        statistics, behavioral, calendar, volatility, news_section, trade_log,
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
You are a personal trading coach analyzing a trader's complete history.

IMPORTANT RULES:
- All numbers below are calculated programmatically and verified. Trust them completely.
- Never recalculate or estimate numbers. Use exactly what is provided.
- You are an analyst, not an advisor. Show facts and patterns.
- Never say "buy" or "sell". Say "your data shows X, the decision is yours."
- Be direct and specific. No generic advice.
- Never use these words: amygdala, prefrontal cortex, cognitive bias, loss aversion, intermittent reinforcement, dopamine, neural, psychology

YOUR TASK:
1. MAIN PROBLEM: What is the #1 issue costing this trader the most money? \
Be specific with $ amounts. Connect behavioral patterns with timing/volatility data. \
Example: "You traded 59 times on normal-volatility days with 32% WR, losing $2,338. \
Meanwhile your 22 volatile-day trades had 36% WR and made $1,375. You trade too much \
when there's no catalyst."

2. HIDDEN PATTERN: Find one non-obvious connection across the data layers. \
Cross-reference behavior + timing + volatility. \
Example: "Your revenge trades happen mostly on normal days in London session. \
When the market is calm, you overtrade out of boredom, then revenge-trade the losses."

3. STRENGTH: What does this trader do well? Be specific with numbers.

4. ACTION PLAN: Give exactly 3 concrete rules for next week. \
Each rule must be: \
- Specific (not "trade less" but "maximum 3 trades per day") \
- Measurable (the trader can check yes/no at end of week) \
- Based on data (cite the specific numbers that justify the rule) \
- Include estimated savings in $ if followed

5. PROJECTED SAVINGS: If the trader follows all 3 rules, how much $ would they save \
per month based on their historical data?

Format: 300 words max. Direct language. No fluff. Start with the main problem immediately. \
Use the trader's actual numbers throughout."""


def _build_repeat_prompt(prev: dict) -> str:
    """Build repeat analysis prompt with previous session comparison."""
    created = prev.get("created_at", "unknown date")
    main_problem = prev.get("main_problem", "not recorded")
    recommendations = parse_json_field(prev.get("recommendations")) or []
    metrics = parse_json_field(prev.get("metrics_snapshot")) or {}

    rec_text = ""
    if recommendations:
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

4. UPDATED PLAN: Keep rules that worked, replace rules that didn't. \
Same format: specific, measurable, data-backed, with $ estimate.

5. PROGRESS SCORE: Rate improvement 1-10 with justification.

Format: 300 words max. Start with verdict emoji immediately. \
Use the trader's actual numbers throughout."""


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
    news: list[dict[str, str]] | None = None,
    ohlc_by_symbol: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    """Generate AI coaching with full RAG context, save session to DB.

    Args:
        user_id: Supabase user ID.
        account_id: Supabase account ID.
        period_from: ISO date string for trade filter (optional).
        period_to: ISO date string for trade filter (optional).
        news: News items (optional, for testing).
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
    trade_models = get_trades(client, user_id, **kwargs)
    trades = [t.model_dump() for t in trade_models]

    if not trades:
        raise LLMError("No trades found for this account/period")

    # Fetch previous coaching session
    prev_session = _get_latest_coaching_session(client, user_id, account_id)

    # Build prompt
    prompt, context = build_full_coaching_prompt(
        trades, account_dict, prev_session,
        news=news, ohlc_by_symbol=ohlc_by_symbol,
    )

    # Call LLM
    ai_text, usage = await deep_analysis(prompt, context)

    # Build metrics snapshot
    metrics = _build_metrics_snapshot(trades)

    # Parse recommendations from AI response
    recommendations = _parse_recommendations(ai_text)
    main_problem = _parse_main_problem(ai_text)
    verdict = _parse_verdict(ai_text) if prev_session else None

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
            "news": news is not None,
        },
        recommendations=recommendations,
        ai_response=ai_text,
        verdict=verdict,
        main_problem=main_problem,
        new_trades_count=len(trades),
        model_used=usage.model,
    )

    return {
        "session_id": session_id,
        "ai_response": ai_text,
        "metrics_snapshot": metrics,
        "verdict": verdict,
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
    recommendations: list[str],
    ai_response: str,
    verdict: str | None,
    main_problem: str | None,
    new_trades_count: int,
    model_used: str,
) -> str:
    """Insert a coaching session row. Returns the session ID."""
    import json

    row = {
        "user_id": user_id,
        "account_id": account_id,
        "period_from": period_from,
        "period_to": period_to,
        "metrics_snapshot": json.dumps(metrics_snapshot),
        "rag_context": json.dumps(rag_context),
        "recommendations": json.dumps(recommendations),
        "ai_response": ai_response,
        "verdict": verdict,
        "main_problem": main_problem,
        "new_trades_count": new_trades_count,
        "model_used": model_used,
    }
    result = client.table("coaching_sessions").insert(row).execute()
    return result.data[0]["id"]


# ===================================================================
# Parsers for AI response
# ===================================================================

def _parse_recommendations(text: str) -> list[str]:
    """Extract numbered rules from AI response."""
    import re

    recs: list[str] = []
    # Look for patterns like "1." "2." "3." in the ACTION PLAN section
    # or "Rule 1:" etc.
    lines = text.split("\n")
    in_plan = False
    for line in lines:
        stripped = line.strip()
        if any(k in stripped.upper() for k in ["ACTION PLAN", "UPDATED PLAN", "RULES"]):
            in_plan = True
            continue
        if in_plan:
            # Match numbered items
            m = re.match(r"^\d+[\.\)]\s*(.+)", stripped)
            if m:
                recs.append(m.group(1).strip())
            elif stripped.startswith("- ") and len(recs) < 3:
                recs.append(stripped[2:].strip())
            # Stop after getting 3 or hitting next section
            if len(recs) >= 3:
                break
            if stripped and stripped[0] in "0123456789" and "." not in stripped[:3]:
                continue
            if re.match(r"^[A-Z]{2,}", stripped) and ":" in stripped:
                break

    return recs[:3]


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
