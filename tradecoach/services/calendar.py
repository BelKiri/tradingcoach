"""
Economic calendar service — timezone conversion, event matching, news impact analysis.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Path to static calendar data
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CALENDAR_FILE = _DATA_DIR / "economic_calendar.json"


# ---------------------------------------------------------------------------
# Load calendar
# ---------------------------------------------------------------------------

def load_calendar(
    date_from: str | None = None,
    date_to: str | None = None,
    impact: str = "high",
) -> list[dict[str, str]]:
    """Load economic calendar events from static JSON.

    Args:
        date_from: ISO date string "YYYY-MM-DD" (inclusive).
        date_to: ISO date string "YYYY-MM-DD" (inclusive).
        impact: Filter by impact level ("high" by default).

    Returns:
        List of {date, time_utc, currency, event_name, impact}.
    """
    with open(_CALENDAR_FILE, encoding="utf-8") as f:
        events: list[dict[str, str]] = json.load(f)

    if impact:
        events = [e for e in events if e["impact"] == impact]

    if date_from:
        events = [e for e in events if e["date"] >= date_from]
    if date_to:
        events = [e for e in events if e["date"] <= date_to]

    return events


def fetch_calendar_forexfactory(
    date_from: str, date_to: str
) -> list[dict[str, str]]:
    """Fetch calendar from Forex Factory (future upgrade).

    TODO: Implement scraper or use FF RSS/API when available.
    Falls back to static JSON for now.
    """
    return load_calendar(date_from=date_from, date_to=date_to)


# ---------------------------------------------------------------------------
# Timezone conversion
# ---------------------------------------------------------------------------

def _parse_tz_offset(broker_timezone: str) -> int:
    """Parse "UTC+N" or "UTC-N" string into offset hours.

    Examples: "UTC+0" → 0, "UTC+2" → 2, "UTC-5" → -5.
    """
    m = re.match(r"UTC([+-]?\d+)", broker_timezone.strip())
    if not m:
        return 0
    return int(m.group(1))


def convert_trade_time_to_utc(
    trade_opened_at: datetime | str, broker_timezone: str
) -> datetime:
    """Convert a trade timestamp from broker time to UTC.

    Subtracts the broker UTC offset to get UTC.
    Example: 15:30 in UTC+2 → 13:30 UTC.
    """
    if isinstance(trade_opened_at, str):
        trade_opened_at = datetime.fromisoformat(trade_opened_at)

    # Always work with naive datetimes (strip tzinfo from Supabase ISO strings)
    if trade_opened_at.tzinfo is not None:
        trade_opened_at = trade_opened_at.replace(tzinfo=None)

    offset_hours = _parse_tz_offset(broker_timezone)
    return trade_opened_at - timedelta(hours=offset_hours)


# ---------------------------------------------------------------------------
# Match trades to events
# ---------------------------------------------------------------------------

def _event_dt(event: dict[str, str]) -> datetime:
    """Build a UTC datetime from an event's date + time_utc."""
    return datetime.fromisoformat(f"{event['date']}T{event['time_utc']}:00")


def match_trades_to_events(
    trades: list[dict],
    events: list[dict[str, str]],
    broker_timezone: str = "UTC+2",
    window_before_minutes: int = 30,
    window_after_minutes: int = 60,
) -> list[dict[str, Any]]:
    """Match trades to nearby economic events.

    For each trade, find events where the trade open time (UTC) falls in an
    asymmetric window around the event instant (UTC):

        event_time - window_before_minutes <= trade_time <= event_time + window_after_minutes

    Defaults: 30 minutes before the event, 60 minutes after (news window).

    Each trade appears at most once in results.

    Returns:
        List of {trade, matched_events: [{event, minutes_offset}]}.
        minutes_offset: negative = trade opened before event, positive = after.
    """
    if not trades or not events:
        return []

    # Pre-compute event datetimes
    event_dts = [(e, _event_dt(e)) for e in events]
    results: list[dict[str, Any]] = []

    for trade in trades:
        opened = trade.get("opened_at")
        if not opened:
            continue

        trade_utc = convert_trade_time_to_utc(opened, broker_timezone)
        matched: list[dict[str, Any]] = []

        for event, evt_dt in event_dts:
            win_start = evt_dt - timedelta(minutes=window_before_minutes)
            win_end = evt_dt + timedelta(minutes=window_after_minutes)
            if win_start <= trade_utc <= win_end:
                diff = trade_utc - evt_dt
                diff_minutes = diff.total_seconds() / 60
                matched.append({
                    "event": event,
                    "minutes_offset": round(diff_minutes),
                })

        if matched:
            results.append({"trade": trade, "matched_events": matched})

    return results


# ---------------------------------------------------------------------------
# Calculate news impact
# ---------------------------------------------------------------------------

def calculate_news_impact(
    trades: list[dict],
    events: list[dict[str, str]],
    broker_timezone: str = "UTC+2",
    window_before_minutes: int = 30,
    window_after_minutes: int = 60,
) -> dict[str, Any]:
    """Analyze the impact of news events on trading performance.

    Splits trades into news_trades (opened within the news window around an
    event) and normal_trades, then compares metrics. The default window is
    asymmetric: 30 minutes before through 60 minutes after each event (UTC).

    Returns dict with:
        news_trades_count, news_wr, news_pnl,
        normal_trades_count, normal_wr, normal_pnl,
        worst_events: [{event_name, date, trades_count, pnl}],
        money_lost_to_news: excess loss compared to normal win rate.
    """
    from tradecoach.services._helpers import _net_profit

    matched = match_trades_to_events(
        trades,
        events,
        broker_timezone,
        window_before_minutes=window_before_minutes,
        window_after_minutes=window_after_minutes,
    )

    # Build set of trade indices that are news trades
    news_trade_ids: set[int] = set()
    # Track per-event stats
    event_stats: dict[str, dict[str, Any]] = {}

    for m in matched:
        trade = m["trade"]
        trade_id = id(trade)
        news_trade_ids.add(trade_id)

        for me in m["matched_events"]:
            evt = me["event"]
            key = f"{evt['event_name']}|{evt['date']}"
            if key not in event_stats:
                event_stats[key] = {
                    "event_name": evt["event_name"],
                    "date": evt["date"],
                    "trades_count": 0,
                    "pnl": 0.0,
                }
            event_stats[key]["trades_count"] += 1
            event_stats[key]["pnl"] += _net_profit(trade)

    # Split trades
    news_trades = [t for t in trades if id(t) in news_trade_ids]
    normal_trades = [t for t in trades if id(t) not in news_trade_ids]

    def _stats(group: list[dict]) -> tuple[int, float | None, float]:
        count = len(group)
        if count == 0:
            return 0, None, 0.0
        wins = sum(1 for t in group if _net_profit(t) > 0)
        wr = round(wins / count * 100, 2) if count else None
        pnl = round(sum(_net_profit(t) for t in group), 2)
        return count, wr, pnl

    n_count, n_wr, n_pnl = _stats(news_trades)
    norm_count, norm_wr, norm_pnl = _stats(normal_trades)

    # Money lost to news: difference between actual news pnl and expected
    # if news trades had the same win rate as normal trades
    money_lost = 0.0
    if norm_wr is not None and n_count > 0:
        # Expected wins at normal WR
        expected_wins = n_count * (norm_wr / 100)
        actual_wins = sum(1 for t in news_trades if _net_profit(t) > 0)
        # Average win/loss from normal trades
        norm_wins = [_net_profit(t) for t in normal_trades if _net_profit(t) > 0]
        norm_losses = [_net_profit(t) for t in normal_trades if _net_profit(t) <= 0]
        avg_w = sum(norm_wins) / len(norm_wins) if norm_wins else 0
        avg_l = sum(norm_losses) / len(norm_losses) if norm_losses else 0
        expected_pnl = expected_wins * avg_w + (n_count - expected_wins) * avg_l
        money_lost = round(n_pnl - expected_pnl, 2)

    # Sort worst events by PnL ascending (most negative first)
    worst = sorted(event_stats.values(), key=lambda x: x["pnl"])

    return {
        "news_trades_count": n_count,
        "news_wr": n_wr,
        "news_pnl": n_pnl,
        "normal_trades_count": norm_count,
        "normal_wr": norm_wr,
        "normal_pnl": norm_pnl,
        "worst_events": worst,
        "money_lost_to_news": money_lost,
    }
