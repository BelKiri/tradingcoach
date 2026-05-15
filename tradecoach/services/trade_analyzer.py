"""
Trade analytics engine — pure math, no AI.

All statistics for the dashboard and "Why you lose" analysis.
Input: list of trade dicts (from DB or parser).
Each trade dict has: ticket, symbol, direction, lot, open_price, close_price,
stop_loss, take_profit, profit_pips, profit_money, commission, swap,
opened_at (ISO str or datetime), closed_at (ISO str or datetime),
source, followed_plan, moved_stop.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from tradecoach.services._helpers import (
    _is_loser,
    _is_winner,
    _net_profit,
)
from tradecoach.services.tz_utils import (
    DEFAULT_BROKER_TIMEZONE,
    broker_calendar_date_str,
    broker_local_hour,
    broker_local_weekday,
    resolve_broker_tz,
    session_label_for_utc,
    trade_instant_utc,
)


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def win_rate(trades: list[dict]) -> float | None:
    """Win rate as percentage (0-100). None if no trades."""
    if not trades:
        return None
    wins = sum(1 for t in trades if _is_winner(t))
    return round(wins / len(trades) * 100, 2)


def total_pnl(trades: list[dict]) -> float:
    """Total net P&L (profit + commission + swap)."""
    return round(sum(_net_profit(t) for t in trades), 2)


def gross_profit(trades: list[dict]) -> float:
    """Sum of all winning trades' net profit."""
    return round(sum(_net_profit(t) for t in trades if _is_winner(t)), 2)


def gross_loss(trades: list[dict]) -> float:
    """Sum of all losing trades' net profit (negative number)."""
    return round(sum(_net_profit(t) for t in trades if _is_loser(t)), 2)


def profit_factor(trades: list[dict]) -> float | None:
    """Gross profit / |gross loss|. None if no losses."""
    gp = gross_profit(trades)
    gl = gross_loss(trades)
    if gl == 0:
        return None
    return round(gp / abs(gl), 2)


def avg_win(trades: list[dict]) -> float | None:
    """Average net profit of winning trades."""
    winners = [_net_profit(t) for t in trades if _is_winner(t)]
    if not winners:
        return None
    return round(sum(winners) / len(winners), 2)


def avg_loss(trades: list[dict]) -> float | None:
    """Average net profit of losing trades (negative)."""
    losers = [_net_profit(t) for t in trades if _is_loser(t)]
    if not losers:
        return None
    return round(sum(losers) / len(losers), 2)


def expectancy(trades: list[dict]) -> float | None:
    """Expected profit per trade."""
    if not trades:
        return None
    return round(total_pnl(trades) / len(trades), 2)


# ---------------------------------------------------------------------------
# Equity curve & drawdown
# ---------------------------------------------------------------------------

def equity_curve(
    trades: list[dict], *, broker_timezone: str | None = None,
) -> list[dict[str, Any]]:
    """Cumulative equity by broker-local calendar day (sorted by close time).

    Returns list of {day, label, equity} — one row per broker-local date
    with end-of-day cumulative equity after each close on that day.
    """
    tz_name = broker_timezone or DEFAULT_BROKER_TIMEZONE
    sorted_trades = _sort_by_close(trades)
    cumulative = 0.0
    by_day: dict[str, float] = {}
    for t in sorted_trades:
        pnl = _net_profit(t)
        cumulative += pnl
        c_utc = trade_instant_utc(t.get("closed_at"))
        if c_utc:
            day_key = broker_calendar_date_str(c_utc, tz_name)
            by_day[day_key] = round(cumulative, 2)
    out: list[dict[str, Any]] = []
    for day_key in sorted(by_day.keys()):
        d = datetime.fromisoformat(day_key + "T12:00:00+00:00")
        label = d.strftime("%b %d")
        out.append({"day": day_key, "label": label, "equity": by_day[day_key]})
    return out


def max_drawdown(
    trades: list[dict], *, account_balance: float | None = None,
) -> dict[str, float]:
    """Maximum drawdown in absolute and percentage terms.

    If account_balance is provided, equity starts from that value and
    drawdown % is calculated from peak balance: (peak - trough) / peak × 100.
    Without balance, uses cumulative P&L (peak defaults to 0).

    Returns {amount, percent, peak, trough}.
    Peak/trough are equity values (including balance if provided).
    """
    sorted_trades = _sort_by_close(trades)
    if not sorted_trades:
        return {"amount": 0.0, "percent": 0.0, "peak": 0.0, "trough": 0.0}

    start = account_balance or 0.0
    cumulative = start
    peak = start
    max_dd = 0.0
    dd_peak = start
    dd_trough = start

    for t in sorted_trades:
        cumulative += _net_profit(t)
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
            dd_peak = peak
            dd_trough = cumulative

    pct = (max_dd / dd_peak * 100) if dd_peak > 0 else 0.0

    return {
        "amount": round(max_dd, 2),
        "percent": round(pct, 2),
        "peak": round(dd_peak, 2),
        "trough": round(dd_trough, 2),
    }


# ---------------------------------------------------------------------------
# Breakdowns
# ---------------------------------------------------------------------------

def pnl_by_symbol(trades: list[dict]) -> dict[str, dict[str, Any]]:
    """P&L breakdown per symbol.

    Returns {symbol: {pnl, trades, wins, win_rate}}.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        groups[t.get("symbol", "UNKNOWN")].append(t)

    result = {}
    for sym, group in sorted(groups.items()):
        wins = sum(1 for t in group if _is_winner(t))
        result[sym] = {
            "pnl": round(sum(_net_profit(t) for t in group), 2),
            "trades": len(group),
            "wins": wins,
            "win_rate": round(wins / len(group) * 100, 2),
        }
    return result


def pnl_by_session(trades: list[dict]) -> dict[str, dict[str, Any]]:
    """P&L by trading session (Asian / London / New York).

    Uses trade open time in true UTC mapped to IANA session windows
    (Asia/Tokyo, Europe/London, America/New_York). No broker_timezone —
    external-system convention.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        dt = trade_instant_utc(t.get("opened_at")) or trade_instant_utc(
            t.get("closed_at")
        )
        if dt:
            session = session_label_for_utc(dt)
        else:
            session = "Unknown"
        groups[session].append(t)

    result = {}
    for session, group in sorted(groups.items()):
        wins = sum(1 for t in group if _is_winner(t))
        result[session] = {
            "pnl": round(sum(_net_profit(t) for t in group), 2),
            "trades": len(group),
            "wins": wins,
            "win_rate": round(wins / len(group) * 100, 2),
        }
    return result


def pnl_by_day_of_week(
    trades: list[dict], broker_timezone: str | None = None,
) -> dict[str, dict[str, Any]]:
    """P&L by weekday in broker-local calendar (open time)."""
    tz_name = broker_timezone or DEFAULT_BROKER_TIMEZONE
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        dt = trade_instant_utc(t.get("opened_at"))
        if dt:
            wd = broker_local_weekday(dt, tz_name)
            groups[day_names[wd]].append(t)

    result = {}
    for day in day_names:
        group = groups.get(day, [])
        if not group:
            continue
        wins = sum(1 for t in group if _is_winner(t))
        result[day] = {
            "pnl": round(sum(_net_profit(t) for t in group), 2),
            "trades": len(group),
            "wins": wins,
            "win_rate": round(wins / len(group) * 100, 2),
        }
    return result


def pnl_by_hour(
    trades: list[dict], broker_timezone: str | None = None,
) -> dict[int, dict[str, Any]]:
    """P&L by hour of day (0-23) in broker-local time from open instant (UTC)."""
    tz_name = broker_timezone or DEFAULT_BROKER_TIMEZONE
    groups: dict[int, list[dict]] = defaultdict(list)
    for t in trades:
        dt = trade_instant_utc(t.get("opened_at"))
        if dt:
            h = broker_local_hour(dt, tz_name)
            groups[h].append(t)

    result = {}
    for hour in sorted(groups.keys()):
        group = groups[hour]
        wins = sum(1 for t in group if _is_winner(t))
        result[hour] = {
            "pnl": round(sum(_net_profit(t) for t in group), 2),
            "trades": len(group),
            "wins": wins,
            "win_rate": round(wins / len(group) * 100, 2),
        }
    return result


# ---------------------------------------------------------------------------
# Hold time
# ---------------------------------------------------------------------------

def avg_hold_time(trades: list[dict]) -> timedelta | None:
    """Average trade hold time (closed_at - opened_at)."""
    durations = _hold_times(trades)
    if not durations:
        return None
    total_secs = sum(d.total_seconds() for d in durations)
    return timedelta(seconds=total_secs / len(durations))


def hold_time_stats(trades: list[dict]) -> dict[str, Any] | None:
    """Hold time statistics: avg, min, max, median in seconds."""
    durations = _hold_times(trades)
    if not durations:
        return None
    secs = sorted(d.total_seconds() for d in durations)
    n = len(secs)
    median = secs[n // 2] if n % 2 == 1 else (secs[n // 2 - 1] + secs[n // 2]) / 2
    return {
        "avg_seconds": round(sum(secs) / n, 0),
        "min_seconds": round(secs[0], 0),
        "max_seconds": round(secs[-1], 0),
        "median_seconds": round(median, 0),
    }


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _hold_times(trades: list[dict]) -> list[timedelta]:
    durations = []
    for t in trades:
        opened = trade_instant_utc(t.get("opened_at"))
        closed = trade_instant_utc(t.get("closed_at"))
        if opened and closed and closed > opened:
            durations.append(closed - opened)
    return durations


# ---------------------------------------------------------------------------
# Stop loss usage
# ---------------------------------------------------------------------------

def sl_usage(trades: list[dict]) -> dict[str, Any]:
    """Count trades with and without stop loss.

    SL is valid when not None and != 0.
    Returns {with_sl, without_sl, total, warning}.
    """
    with_sl = 0
    without_sl = 0
    for t in trades:
        sl = t.get("stop_loss")
        if sl is not None and float(sl) != 0:
            with_sl += 1
        else:
            without_sl += 1
    return {
        "with_sl": with_sl,
        "without_sl": without_sl,
        "total": len(trades),
        "warning": without_sl > 0,
    }


# ---------------------------------------------------------------------------
# Risk per trade distribution
# ---------------------------------------------------------------------------

def build_contract_lookup(trades: list[dict]) -> dict[str, float]:
    """Auto-detect contract size per symbol from real trade P&L.

    Fallback chain:
    1. BEST: profit + open + close all available, close != open, profit != 0
       contract = abs(profit_money) / abs(close - open) / lot
    2. FALLBACK: pips column available and profit != 0
       pip_value_per_lot = abs(profit_money) / abs(pips) / lot
       (stored separately, converted to contract later if needed)
    3. Breakeven trades (profit=0 or close=open) use contracts from
       other trades on the same symbol.
    4. LAST RESORT: symbol skipped, risk shows N/A.

    Groups by symbol and takes the median.
    """
    import logging
    from statistics import median

    logger = logging.getLogger(__name__)

    by_symbol: dict[str, list[float]] = defaultdict(list)
    pips_by_symbol: dict[str, list[float]] = defaultdict(list)
    all_symbols: set[str] = set()

    for t in trades:
        symbol = (t.get("symbol") or "").upper()
        if not symbol:
            continue
        all_symbols.add(symbol)

        profit = t.get("profit_money")
        op = t.get("open_price")
        cp = t.get("close_price")
        lot = t.get("lot")

        # Skip if essential fields missing or lot is zero
        if lot is None or float(lot) == 0:
            continue
        lot_f = float(lot)

        # --- Primary: from price movement ---
        if profit is not None and op is not None and cp is not None:
            profit_f = float(profit)
            price_diff = abs(float(cp) - float(op))
            if price_diff > 0 and profit_f != 0:
                contract = abs(profit_f) / price_diff / lot_f
                by_symbol[symbol].append(contract)
                continue

        # --- Fallback: from pips column ---
        pips = t.get("profit_pips")
        if profit is not None and pips is not None:
            profit_f = float(profit)
            pips_f = float(pips)
            if abs(pips_f) > 0 and profit_f != 0:
                pip_val = abs(profit_f) / abs(pips_f) / lot_f
                pips_by_symbol[symbol].append(pip_val)

    result: dict[str, float] = {}
    for sym in all_symbols:
        if by_symbol.get(sym):
            result[sym] = median(by_symbol[sym])
        elif pips_by_symbol.get(sym):
            logger.warning(
                "contract_lookup: %s — fallback to pips-based detection", sym
            )
            result[sym] = median(pips_by_symbol[sym])
        else:
            logger.warning(
                "contract_lookup: %s — no valid data, risk will show N/A", sym
            )

    return result


def risk_per_trade(
    trades: list[dict],
    account_balance: float,
    contract_lookup: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Estimate risk % per trade.

    If SL is set and != 0:
      risk_money = abs(open_price - stop_loss) * contract_size * lot
    If NO SL and trade is a loser:
      risk_money = abs(profit_money)  (actual loss as risk)

    Returns list of {ticket, symbol, risk_pct, risk_money, lot}.
    """
    if contract_lookup is None:
        contract_lookup = build_contract_lookup(trades)
    results = []
    for t in trades:
        sl = t.get("stop_loss")
        op = t.get("open_price")
        lot = t.get("lot")
        symbol = (t.get("symbol") or "").upper()
        risk_money = None
        risk_pct = None

        if sl and float(sl) != 0 and op and lot and account_balance > 0:
            if symbol in contract_lookup:
                contract = contract_lookup[symbol]
                risk_money = round(
                    abs(float(op) - float(sl)) * contract * float(lot), 2
                )
                risk_pct = round(risk_money / account_balance * 100, 2)
        elif not sl or float(sl or 0) == 0:
            # No SL — if loser, use actual loss as risk
            net = _net_profit(t)
            if net < 0 and account_balance > 0:
                risk_money = round(abs(net), 2)
                risk_pct = round(risk_money / account_balance * 100, 2)

        has_sl = bool(sl and float(sl) != 0)
        results.append({
            "ticket": t.get("ticket"),
            "symbol": t.get("symbol"),
            "risk_pct": risk_pct,
            "risk_money": risk_money,
            "lot": lot,
            "has_sl": has_sl,
        })
    return results


# ---------------------------------------------------------------------------
# Streaks
# ---------------------------------------------------------------------------

def streaks(trades: list[dict]) -> dict[str, Any]:
    """Analyze win/loss streaks.

    Returns {max_win_streak, max_loss_streak, current_streak,
             current_streak_type}.
    """
    sorted_trades = _sort_by_close(trades)
    if not sorted_trades:
        return {
            "max_win_streak": 0,
            "max_loss_streak": 0,
            "current_streak": 0,
            "current_streak_type": None,
        }

    max_win = 0
    max_loss = 0
    current = 0
    current_type: str | None = None

    for t in sorted_trades:
        if _is_winner(t):
            if current_type == "win":
                current += 1
            else:
                current = 1
                current_type = "win"
            max_win = max(max_win, current)
        elif _is_loser(t):
            if current_type == "loss":
                current += 1
            else:
                current = 1
                current_type = "loss"
            max_loss = max(max_loss, current)
        else:
            # breakeven — resets streak
            current = 0
            current_type = None

    return {
        "max_win_streak": max_win,
        "max_loss_streak": max_loss,
        "current_streak": current,
        "current_streak_type": current_type,
    }


# ---------------------------------------------------------------------------
# Behavioral: revenge trading detection
# ---------------------------------------------------------------------------

def detect_revenge_trades(
    trades: list[dict], *, max_gap_minutes: int = 5
) -> list[dict[str, Any]]:
    """Detect revenge trades: any trade opened within N minutes after a loss.

    Sorted by close time. After a trade CLOSES with a net loss, if any new
    trade OPENS within max_gap_minutes → revenge. No lot size requirement.
    Each trade can only be flagged as revenge once.

    Returns list of {trade, previous_loss, gap_seconds}.
    """
    sorted_by_close = _sort_by_close(trades)
    revenge: list[dict[str, Any]] = []
    flagged_ids: set[int] = set()  # set of id(trade_dict)

    for loss in sorted_by_close:
        if not _is_loser(loss):
            continue
        loss_closed = trade_instant_utc(loss.get("closed_at"))
        if not loss_closed:
            continue

        for t in trades:
            if t is loss or id(t) in flagged_ids:
                continue
            t_opened = trade_instant_utc(t.get("opened_at"))
            if not t_opened:
                continue
            gap = (t_opened - loss_closed).total_seconds()
            if 0 <= gap <= max_gap_minutes * 60:
                revenge.append({
                    "trade": t,
                    "previous_loss": loss,
                    "gap_seconds": round(gap),
                })
                flagged_ids.add(id(t))

    return revenge


def revenge_trade_cost(trades: list[dict], **kwargs: Any) -> float:
    """Total net P&L of all revenge trades (winners + losers)."""
    revenge = detect_revenge_trades(trades, **kwargs)
    return round(
        sum(_net_profit(r["trade"]) for r in revenge),
        2,
    )


# ---------------------------------------------------------------------------
# Behavioral: overtrading detection
# ---------------------------------------------------------------------------

def detect_overtrading(
    trades: list[dict], *, threshold: int = 5, broker_timezone: str | None = None,
) -> dict[str, Any]:
    """Detect broker-local calendar days with too many trades (threshold+)."""
    tz_name = broker_timezone or DEFAULT_BROKER_TIMEZONE
    by_day: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        dt = trade_instant_utc(t.get("opened_at"))
        if dt:
            day_key = broker_calendar_date_str(dt, tz_name)
            by_day[day_key].append(t)

    ot_trades: list[dict] = []
    normal_trades: list[dict] = []
    ot_days = 0
    normal_days = 0

    for day_str, day_trades in by_day.items():
        if len(day_trades) >= threshold:
            ot_trades.extend(day_trades)
            ot_days += 1
        else:
            normal_trades.extend(day_trades)
            normal_days += 1

    return {
        "overtrading_days": ot_days,
        "normal_days": normal_days,
        "overtrading_wr": win_rate(ot_trades),
        "normal_wr": win_rate(normal_trades),
        "overtrading_pnl": total_pnl(ot_trades),
        "normal_pnl": total_pnl(normal_trades),
        "overtrading_trades": len(ot_trades),
    }


# ---------------------------------------------------------------------------
# Behavioral: martingale detection
# ---------------------------------------------------------------------------

def detect_martingale(trades: list[dict]) -> list[dict[str, Any]]:
    """Detect martingale patterns: increasing lot after losses on the SAME symbol.

    Sorted by open_dt, tracks last closed trade per symbol.
    Conditions (all must be true):
    - Previous trade on the SAME symbol CLOSED with a net loss
    - New trade OPENS within 1 hour of the previous close
    - New trade lot >= previous lot * 1.4

    Gap = curr.opened_at - prev.closed_at.

    Returns list of {trade, previous_trade, lot_increase_pct}.
    """
    sorted_trades = _sort_by_open(trades)
    results: list[dict[str, Any]] = []

    last_closed_by_symbol: dict[str, dict] = {}

    for t in sorted_trades:
        sym = (t.get("symbol") or "").upper()
        if not sym:
            continue

        t_opened = trade_instant_utc(t.get("opened_at"))
        prev = last_closed_by_symbol.get(sym)
        if prev is not None and _is_loser(prev) and t_opened:
            prev_closed = trade_instant_utc(prev.get("closed_at"))
            if prev_closed:
                gap = (t_opened - prev_closed).total_seconds()
                if 0 <= gap <= 3600:
                    prev_lot = prev.get("lot") or 0
                    curr_lot = t.get("lot") or 0
                    if prev_lot > 0 and curr_lot >= prev_lot * 1.4:
                        increase = round((curr_lot / prev_lot - 1) * 100)
                        results.append({
                            "trade": t,
                            "previous_trade": prev,
                            "lot_increase_pct": increase,
                        })

        last_closed_by_symbol[sym] = t

    return results


# ---------------------------------------------------------------------------
# Behavioral: quick exits (panic closing)
# ---------------------------------------------------------------------------

def detect_quick_exits(
    trades: list[dict], *, max_minutes: int = 2
) -> list[dict[str, Any]]:
    """Detect trades closed within N minutes — potential panic exits.

    Returns list of {trade, hold_seconds, pnl}.
    """
    results: list[dict[str, Any]] = []
    for t in trades:
        opened = trade_instant_utc(t.get("opened_at"))
        closed = trade_instant_utc(t.get("closed_at"))
        if not opened or not closed:
            continue
        hold = (closed - opened).total_seconds()
        if 0 < hold <= max_minutes * 60:
            results.append({
                "trade": t,
                "hold_seconds": round(hold),
                "pnl": round(_net_profit(t), 2),
            })
    return results


# ---------------------------------------------------------------------------
# Behavioral: averaging down
# ---------------------------------------------------------------------------

def detect_averaging_down(trades: list[dict]) -> list[dict[str, Any]]:
    """Detect averaging down: overlapping positions on same symbol/direction.

    Trade B is averaging down on Trade A when:
    - Same symbol, same direction
    - A opened before B (A.opened_at < B.opened_at)
    - A still open when B opens (B.opened_at < A.closed_at)

    No requirement that A is losing. Any overlapping same-symbol
    same-direction positions = averaging.
    Each trade flagged only once.

    Returns list of {trade, original_trade, symbol, direction}.
    """
    sorted_trades = _sort_by_open(trades)
    results: list[dict[str, Any]] = []
    flagged_ids: set[int] = set()

    for b in sorted_trades:
        if id(b) in flagged_ids:
            continue
        b_opened = trade_instant_utc(b.get("opened_at"))
        if not b_opened:
            continue
        b_sym = (b.get("symbol") or "")
        b_dir = b.get("direction")

        for a in sorted_trades:
            if a is b:
                continue
            a_opened = trade_instant_utc(a.get("opened_at"))
            a_closed = trade_instant_utc(a.get("closed_at"))
            if not a_opened or not a_closed:
                continue
            if (a.get("symbol") or "") != b_sym or a.get("direction") != b_dir:
                continue
            # A opened before B, and A still open when B opens
            if a_opened < b_opened < a_closed:
                results.append({
                    "trade": b,
                    "original_trade": a,
                    "symbol": b_sym,
                    "direction": b_dir,
                })
                flagged_ids.add(id(b))
                break  # found one overlapping trade, move to next B

    return results


# ---------------------------------------------------------------------------
# Behavioral: weekend holding
# ---------------------------------------------------------------------------

def detect_weekend_holds(
    trades: list[dict], broker_timezone: str | None = None,
) -> list[dict]:
    """Trades held over a weekend (opened Fri broker-local, closed Mon+)."""
    tz = resolve_broker_tz(broker_timezone or DEFAULT_BROKER_TIMEZONE)
    results: list[dict] = []
    for t in trades:
        opened = trade_instant_utc(t.get("opened_at"))
        closed = trade_instant_utc(t.get("closed_at"))
        if not opened or not closed:
            continue
        o_loc = opened.astimezone(tz)
        c_loc = closed.astimezone(tz)
        if o_loc.weekday() == 4 and c_loc.weekday() in (0, 1, 2, 3, 4):
            if (closed - opened).days >= 2:
                results.append(t)
    return results


# ---------------------------------------------------------------------------
# Win rate after N consecutive losses
# ---------------------------------------------------------------------------

def win_rate_after_n_losses(
    trades: list[dict], n: int = 3, broker_timezone: str | None = None,
) -> dict[str, Any]:
    """Win rate of trades taken after N consecutive losses in a broker-local day.

    Returns {trades_after_streak, win_rate, pnl}.
    """
    tz_name = broker_timezone or DEFAULT_BROKER_TIMEZONE
    sorted_trades = _sort_by_open(trades)
    by_day: dict[str, list[dict]] = defaultdict(list)
    for t in sorted_trades:
        dt = trade_instant_utc(t.get("opened_at"))
        if dt:
            day_key = broker_calendar_date_str(dt, tz_name)
            by_day[day_key].append(t)

    after_streak: list[dict] = []
    for day_key in sorted(by_day.keys()):
        day_trades = sorted(
            by_day[day_key],
            key=lambda x: trade_instant_utc(x.get("opened_at")) or _EPOCH,
        )
        loss_count = 0
        for t in day_trades:
            if loss_count >= n:
                after_streak.append(t)
            if _is_loser(t):
                loss_count += 1
            elif _is_winner(t):
                loss_count = 0

    return {
        "trades_after_streak": len(after_streak),
        "win_rate": win_rate(after_streak),
        "pnl": total_pnl(after_streak),
    }


# ---------------------------------------------------------------------------
# Worst hours
# ---------------------------------------------------------------------------

def worst_hours(
    trades: list[dict], *, min_trades: int = 3,
    broker_timezone: str | None = None,
) -> list[dict[str, Any]]:
    """Find hours with negative P&L and enough trades.

    Returns sorted list of {hour, pnl, win_rate, trades} (worst first).
    """
    hours = pnl_by_hour(trades, broker_timezone=broker_timezone)
    bad = []
    for hour, data in hours.items():
        if data["pnl"] < 0 and data["trades"] >= min_trades:
            bad.append({"hour": hour, **data})
    return sorted(bad, key=lambda x: x["pnl"])


# ---------------------------------------------------------------------------
# Full dashboard
# ---------------------------------------------------------------------------

def full_analysis(
    trades: list[dict],
    *,
    account_balance: float | None = None,
    broker_timezone: str | None = None,
) -> dict[str, Any]:
    """Compute all dashboard metrics in one call.

    Returns a dict with all analysis results.
    """
    bt = broker_timezone or DEFAULT_BROKER_TIMEZONE
    return {
        "total_trades": len(trades),
        "win_rate": win_rate(trades),
        "total_pnl": total_pnl(trades),
        "gross_profit": gross_profit(trades),
        "gross_loss": gross_loss(trades),
        "profit_factor": profit_factor(trades),
        "avg_win": avg_win(trades),
        "avg_loss": avg_loss(trades),
        "expectancy": expectancy(trades),
        "max_drawdown": max_drawdown(trades, account_balance=account_balance),
        "equity_curve": equity_curve(trades, broker_timezone=bt),
        "pnl_by_symbol": pnl_by_symbol(trades),
        "pnl_by_session": pnl_by_session(trades),
        "pnl_by_day_of_week": pnl_by_day_of_week(trades, broker_timezone=bt),
        "pnl_by_hour": pnl_by_hour(trades, broker_timezone=bt),
        "hold_time": hold_time_stats(trades),
        "streaks": streaks(trades),
        "revenge_trades": detect_revenge_trades(trades),
        "revenge_trade_cost": revenge_trade_cost(trades),
    }


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

def _sort_by_close(trades: list[dict]) -> list[dict]:
    def key(t: dict) -> datetime:
        dt = trade_instant_utc(t.get("closed_at"))
        return dt if dt else _EPOCH
    return sorted(trades, key=key)


def _sort_by_open(trades: list[dict]) -> list[dict]:
    def key(t: dict) -> datetime:
        dt = trade_instant_utc(t.get("opened_at"))
        return dt if dt else _EPOCH
    return sorted(trades, key=key)
