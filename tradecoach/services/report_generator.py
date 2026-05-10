"""
Full analysis report generator — orchestrates all analyzers into
a formatted Telegram message.

This is the CORE product experience: user uploads CSV → gets
comprehensive analysis in one report.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tradecoach.services import trade_analyzer as ta
from tradecoach.services._helpers import _is_loser, _is_winner, _net_profit, _to_dt
from tradecoach.services.emotion_tracker import best_emotion, worst_emotion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_pnl(value: float) -> str:
    if value >= 0:
        return f"+${value:,.2f}"
    return f"-${abs(value):,.2f}"


def _date_range(trades: list[dict]) -> str:
    dates = []
    for t in trades:
        dt = _to_dt(t.get("opened_at")) or _to_dt(t.get("closed_at"))
        if dt:
            dates.append(dt)
    if not dates:
        return "Unknown"
    dates.sort()
    first = dates[0].strftime("%b %d")
    last = dates[-1].strftime("%b %d, %Y")
    if dates[0].year != dates[-1].year:
        first = dates[0].strftime("%b %d, %Y")
    return f"{first} \u2014 {last}"



# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def _section_overview(
    trades: list[dict], account_balance: float | None = None,
) -> list[str]:
    wr = ta.win_rate(trades)
    pnl = ta.total_pnl(trades)
    pf = ta.profit_factor(trades)
    aw = ta.avg_win(trades)
    al = ta.avg_loss(trades)
    exp = ta.expectancy(trades)

    winners = sum(1 for t in trades if _is_winner(t))
    losers = sum(1 for t in trades if _is_loser(t))

    lines = [
        "\U0001f4ca OVERVIEW",
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        f"\U0001f4c5 Period: {_date_range(trades)}",
        f"\U0001f4c8 Total trades: {len(trades)} ({winners}W / {losers}L)",
        f"\U0001f3af Win rate: {wr:.1f}%",
        f"\U0001f4b0 Total P&L: {_fmt_pnl(pnl)}",
        f"\u2696\ufe0f Profit factor: {pf:.2f}" if pf else "\u2696\ufe0f Profit factor: N/A (no losses)",
        f"\U0001f4b5 Avg win: ${aw:,.2f}" if aw else "\U0001f4b5 Avg win: N/A",
        f"\U0001f4b8 Avg loss: ${abs(al):,.2f}" if al else "\U0001f4b8 Avg loss: N/A",
        f"\U0001f9ee Expectancy: {_fmt_pnl(exp)}/trade" if exp is not None else "\U0001f9ee Expectancy: N/A",
    ]
    return lines


def _section_strengths(trades: list[dict]) -> list[str]:
    lines = [
        "",
        "\U0001f4aa STRENGTHS",
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
    ]

    symbols = ta.pnl_by_symbol(trades)
    profitable = sorted(
        [(s, d) for s, d in symbols.items() if d["pnl"] > 0],
        key=lambda x: x[1]["pnl"], reverse=True,
    )
    if profitable:
        top = profitable[:3]
        lines.append("\U0001f4b1 Best pairs:")
        for sym, data in top:
            lines.append(
                f"  \u2705 {sym}: {_fmt_pnl(data['pnl'])} "
                f"({data['win_rate']:.0f}% WR, {data['trades']} trades)"
            )

    sessions = ta.pnl_by_session(trades)
    known = {k: v for k, v in sessions.items() if k != "Unknown"}
    if known:
        best_sess = max(known.items(), key=lambda x: x[1]["pnl"])
        if best_sess[1]["pnl"] > 0:
            s, d = best_sess
            lines.append(
                f"\U0001f552 Best session: {s} "
                f"({_fmt_pnl(d['pnl'])}, {d['win_rate']:.0f}% WR)"
            )

    days = ta.pnl_by_day_of_week(trades)
    if days:
        best_day = max(days.items(), key=lambda x: x[1]["pnl"])
        if best_day[1]["pnl"] > 0:
            d_name, d_data = best_day
            lines.append(
                f"\U0001f4c6 Best day: {d_name} "
                f"({_fmt_pnl(d_data['pnl'])}, {d_data['win_rate']:.0f}% WR)"
            )

    st = ta.streaks(trades)
    if st["max_win_streak"] >= 2:
        lines.append(f"\U0001f525 Best win streak: {st['max_win_streak']} in a row")

    return lines


def _section_weaknesses(trades: list[dict]) -> list[str]:
    lines = [
        "",
        "\u26a0\ufe0f WEAKNESSES",
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
    ]

    symbols = ta.pnl_by_symbol(trades)
    losing = sorted(
        [(s, d) for s, d in symbols.items() if d["pnl"] < 0],
        key=lambda x: x[1]["pnl"],
    )
    if losing:
        worst = losing[:3]
        gl = ta.gross_loss(trades)
        lines.append("\U0001f4b1 Worst pairs:")
        for sym, data in worst:
            pct_str = ""
            if gl != 0:
                pct = abs(data["pnl"]) / abs(gl) * 100
                pct_str = f" \u2014 {pct:.0f}% of losses"
            lines.append(
                f"  \u274c {sym}: {_fmt_pnl(data['pnl'])}{pct_str} "
                f"({data['win_rate']:.0f}% WR, {data['trades']} trades)"
            )

    sessions = ta.pnl_by_session(trades)
    known = {k: v for k, v in sessions.items() if k != "Unknown"}
    if known:
        worst_sess = min(known.items(), key=lambda x: x[1]["pnl"])
        if worst_sess[1]["pnl"] < 0:
            s, d = worst_sess
            lines.append(
                f"\U0001f552 Worst session: {s} "
                f"({_fmt_pnl(d['pnl'])}, {d['win_rate']:.0f}% WR)"
            )

    days = ta.pnl_by_day_of_week(trades)
    if days:
        worst_day = min(days.items(), key=lambda x: x[1]["pnl"])
        if worst_day[1]["pnl"] < 0:
            d_name, d_data = worst_day
            lines.append(
                f"\U0001f4c6 Worst day: {d_name} "
                f"({_fmt_pnl(d_data['pnl'])})"
            )

    st = ta.streaks(trades)
    if st["max_loss_streak"] >= 2:
        lines.append(f"\U0001f4a5 Worst loss streak: {st['max_loss_streak']} in a row")

    return lines


def _behavioral_trading_patterns(trades: list[dict]) -> list[str]:
    """Revenge, overtrading, martingale, quick exits, averaging down."""
    items: list[str] = []

    revenge = ta.detect_revenge_trades(trades)
    if revenge:
        r_trades = [r["trade"] for r in revenge]
        r_wins = sum(1 for t in r_trades if _is_winner(t))
        r_losses = len(r_trades) - r_wins
        r_net = sum(_net_profit(t) for t in r_trades)
        r_loss_cost = sum(_net_profit(t) for t in r_trades if _is_loser(t))
        line = (
            f"\U0001f525 Revenge trading: {len(revenge)} trades "
            f"({r_wins}W / {r_losses}L), net {_fmt_pnl(r_net)}"
        )
        if r_losses > 0:
            line += (
                f" \u26a0\ufe0f {r_losses} losing revenge trades "
                f"cost {_fmt_pnl(r_loss_cost)}"
            )
        items.append(line)

    ot = ta.detect_overtrading(trades)
    if ot["overtrading_days"] > 0 and ot["overtrading_wr"] is not None:
        ot_wr = ot["overtrading_wr"]
        normal_wr = ot["normal_wr"] or 0
        items.append(
            f"\U0001f4c8 Overtrading: {ot['overtrading_days']} days with 5+ trades "
            f"({ot_wr:.0f}% WR vs {normal_wr:.0f}% on normal days, "
            f"{_fmt_pnl(ot['overtrading_pnl'])})"
        )

    mart = ta.detect_martingale(trades)
    if mart:
        mart_pnl = sum(_net_profit(m["trade"]) for m in mart)
        items.append(
            f"\U0001f4c9 Martingale: {len(mart)} times lot increased 40%+ after loss "
            f"({_fmt_pnl(mart_pnl)})"
        )

    quick = ta.detect_quick_exits(trades)
    if len(quick) >= 2:
        quick_pnl = sum(q["pnl"] for q in quick)
        losers = sum(1 for q in quick if q["pnl"] < 0)
        items.append(
            f"\u23f1\ufe0f Quick exits: {len(quick)} trades closed within 2 min "
            f"({losers} losers, {_fmt_pnl(quick_pnl)})"
        )

    weekend = ta.detect_weekend_holds(trades)
    if weekend:
        w_pnl = sum(_net_profit(t) for t in weekend)
        items.append(
            f"\U0001f30d Weekend holds: {len(weekend)} trades held over weekend "
            f"({_fmt_pnl(w_pnl)})"
        )

    avg_down = ta.detect_averaging_down(trades)
    if avg_down:
        ad_pnl = sum(_net_profit(a["trade"]) for a in avg_down)
        items.append(
            f"\u2935\ufe0f Averaging down: {len(avg_down)} times "
            f"({_fmt_pnl(ad_pnl)})"
        )

    return items


def _behavioral_timing(trades: list[dict]) -> list[str]:
    """Worst hours, sessions, and days."""
    items: list[str] = []

    bad_hours = ta.worst_hours(trades)
    if bad_hours:
        worst = bad_hours[0]
        items.append(
            f"\u23f0 Worst hour: {worst['hour']:02d}:00 UTC "
            f"({_fmt_pnl(worst['pnl'])}, {worst['win_rate']:.0f}% WR, "
            f"{worst['trades']} trades)"
        )

    sessions = ta.pnl_by_session(trades)
    known = {k: v for k, v in sessions.items() if k != "Unknown"}
    for session, data in sorted(known.items(), key=lambda x: x[1]["pnl"]):
        if data["pnl"] < 0 and data["trades"] >= 3:
            items.append(
                f"\U0001f552 {session} session costs you {_fmt_pnl(data['pnl'])} "
                f"({data['win_rate']:.0f}% WR, {data['trades']} trades)"
            )

    days = ta.pnl_by_day_of_week(trades)
    for day, data in sorted(days.items(), key=lambda x: x[1]["pnl"]):
        if data["pnl"] < 0 and data["trades"] >= 3:
            items.append(
                f"\U0001f4c6 {day}s cost you {_fmt_pnl(data['pnl'])} "
                f"({data['trades']} trades)"
            )

    return items


def _section_behavioral(trades: list[dict]) -> list[str]:
    lines = [
        "",
        "\U0001f9e0 BEHAVIORAL ANALYSIS",
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
    ]

    patterns = _behavioral_trading_patterns(trades)
    timing = _behavioral_timing(trades)

    lines.extend(patterns)
    lines.extend(timing)

    if not patterns and not timing:
        lines.append("\u2705 No major behavioral issues detected. Nice!")

    return lines


def _section_risk(
    trades: list[dict], account_balance: float | None = None,
) -> list[str]:
    lines = [
        "",
        "\U0001f6e1\ufe0f RISK ASSESSMENT",
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
    ]

    dd = ta.max_drawdown(trades, account_balance=account_balance)
    if account_balance and account_balance > 0:
        lines.append(
            f"\U0001f4c9 Max drawdown: ${dd['amount']:,.2f} "
            f"({dd['percent']:.1f}% from peak ${dd['peak']:,.0f})"
        )
    else:
        lines.append(
            f"\U0001f4c9 Max drawdown: ${dd['amount']:,.2f}"
        )

    # SL usage
    sl = ta.sl_usage(trades)
    if sl["total"] > 0:
        if sl["warning"]:
            sl_pct = sl["with_sl"] / sl["total"] * 100
            lines.append(
                f"\U0001f6d1 Stop loss usage: {sl_pct:.0f}% "
                f"({sl['with_sl']}/{sl['total']} trades)"
            )
            no_sl_losers = [t for t in trades
                            if not t.get("stop_loss") and _is_loser(t)]
            if no_sl_losers:
                no_sl_loss = sum(_net_profit(t) for t in no_sl_losers)
                lines.append(
                    f"  \u274c {len(no_sl_losers)} trades without SL "
                    f"closed at loss: {_fmt_pnl(no_sl_loss)}"
                )
        else:
            lines.append(f"\u2705 Stop loss: used on all trades")

    # Average lot size
    lots = [t.get("lot") for t in trades if t.get("lot")]
    if lots:
        avg_lot = sum(lots) / len(lots)
        max_lot = max(lots)
        lines.append(f"\U0001f4cf Avg lot: {avg_lot:.2f} | Max: {max_lot:.2f}")

    # Risk per trade if balance available (SL-based trades only)
    if account_balance and account_balance > 0:
        risks = ta.risk_per_trade(trades, account_balance)
        valid = [r["risk_pct"] for r in risks
                 if r["risk_pct"] is not None and r.get("has_sl")]
        if valid:
            avg_risk = sum(valid) / len(valid)
            max_risk = max(valid)
            violations = sum(1 for r in valid if r > 2.0)
            lines.append(
                f"\u2696\ufe0f Avg risk: {avg_risk:.1f}% | Max: {max_risk:.1f}%"
            )
            if violations:
                lines.append(
                    f"  \u26a0\ufe0f {violations} trades exceeded 2% risk"
                )

    return lines



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_full_report(
    trades: list[dict],
    emotions: list[dict] | None = None,
    *,
    account_balance: float | None = None,
) -> str:
    """Generate a complete analysis report formatted for Telegram.

    Args:
        trades: Trade dicts from DB.
        emotions: Optional emotion dicts for emotion insights.
        account_balance: User's account balance for risk calculations.

    Returns:
        Formatted report string ready to send via Telegram.
    """
    if not trades:
        return (
            "\U0001f4ca No trades to analyze.\n\n"
            "Upload a CSV or use /log to start tracking."
        )

    parts: list[str] = []
    parts.extend(_section_overview(trades, account_balance))
    parts.extend(_section_strengths(trades))
    parts.extend(_section_weaknesses(trades))
    parts.extend(_section_behavioral(trades))
    parts.extend(_section_risk(trades, account_balance))

    # Emotion insights (if available)
    if emotions:
        best = best_emotion(trades, emotions)
        worst = worst_emotion(trades, emotions)
        if best and worst and best["emotion"] != worst["emotion"]:
            parts.append("")
            parts.append("\U0001f3ad EMOTION INSIGHTS")
            parts.append("\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
            parts.append(
                f"\u2705 Best: {best['emotion']} "
                f"({best['win_rate']:.0f}% WR, {best['trades']} trades)"
            )
            parts.append(
                f"\u274c Worst: {worst['emotion']} "
                f"({worst['win_rate']:.0f}% WR, {worst['trades']} trades)"
            )

    return "\n".join(parts)
