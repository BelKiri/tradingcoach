"""
Market data service — OHLC fetching, ATR calculation, volatility analysis.

Key design: ATR is calculated from the 14 days BEFORE each target date,
not including the target date itself. This represents what the trader could
actually see on their chart before entering a trade.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from tradecoach.services._helpers import _net_profit
from tradecoach.services.tz_utils import trade_instant_utc

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PRICE_CACHE_DIR = _DATA_DIR / "price_cache"

# TwelveData symbol mapping: our format → API format
SYMBOL_MAP: dict[str, str] = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USDCAD": "USD/CAD",
    "AUDUSD": "AUD/USD",
    "NZDUSD": "NZD/USD",
    "USDCHF": "USD/CHF",
    "XAUUSD": "XAU/USD",
    "XAGUSD": "XAG/USD",
    "BTCUSD": "BTC/USD",
    "XRPUSD": "XRP/USD",
    "USOIL": "WTI/USD",
    "US500": "SPX",
    "US100": "NDX",
    "GER40": "DAX",
}

_RATE_LIMIT_SECONDS = 8  # TwelveData free: 8 req/min
_last_request_time: float = 0.0


# ---------------------------------------------------------------------------
# TwelveData API key
# ---------------------------------------------------------------------------

def _get_twelvedata_key() -> str:
    from tradecoach.config import get_settings
    key = get_settings().twelvedata_api_key
    if not key:
        raise RuntimeError(
            "TWELVEDATA_API_KEY not set. Add it to your .env file: "
            "TWELVEDATA_API_KEY=your_key_here  "
            "(Get a free key at https://twelvedata.com)"
        )
    return key


# ---------------------------------------------------------------------------
# Price cache
# ---------------------------------------------------------------------------

def _cache_path(symbol: str, date_from: str, date_to: str) -> Path:
    _PRICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("/", "")
    return _PRICE_CACHE_DIR / f"{safe}_{date_from}_{date_to}.json"


def _load_price_cache(
    symbol: str, date_from: str, date_to: str,
) -> list[dict] | None:
    p = _cache_path(symbol, date_from, date_to)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save_price_cache(
    symbol: str, date_from: str, date_to: str, data: list[dict],
) -> None:
    p = _cache_path(symbol, date_from, date_to)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Fetch OHLC from TwelveData
# ---------------------------------------------------------------------------

def _rate_limit() -> None:
    """Enforce TwelveData rate limit (8 req/min)."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _RATE_LIMIT_SECONDS:
        time.sleep(_RATE_LIMIT_SECONDS - elapsed)
    _last_request_time = time.time()


def fetch_daily_ohlc(
    symbol: str,
    date_from: str,
    date_to: str,
) -> list[dict[str, Any]]:
    """Fetch daily OHLC from TwelveData API.

    Args:
        symbol: Our format, e.g. "XAUUSD", "EURUSD".
        date_from: ISO date "YYYY-MM-DD".
        date_to: ISO date "YYYY-MM-DD".

    Returns:
        List of {date, open, high, low, close} sorted chronologically.
    """
    td_symbol = SYMBOL_MAP.get(symbol.upper())
    if not td_symbol:
        return []

    # Check cache
    cached = _load_price_cache(symbol.upper(), date_from, date_to)
    if cached is not None:
        return cached

    api_key = _get_twelvedata_key()
    _rate_limit()

    resp = httpx.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": td_symbol,
            "interval": "1day",
            "start_date": date_from,
            "end_date": date_to,
            "apikey": api_key,
            "outputsize": 5000,
        },
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()

    if "values" not in body:
        return []

    results: list[dict[str, Any]] = []
    for v in body["values"]:
        results.append({
            "date": v["datetime"][:10],
            "open": float(v["open"]),
            "high": float(v["high"]),
            "low": float(v["low"]),
            "close": float(v["close"]),
        })

    # TwelveData returns newest first — reverse to chronological
    results.sort(key=lambda x: x["date"])

    _save_price_cache(symbol.upper(), date_from, date_to, results)
    return results


# ---------------------------------------------------------------------------
# True Range helpers
# ---------------------------------------------------------------------------

def _true_ranges(ohlc_data: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """Compute (date, true_range) for every day in the series.

    First day uses high-low only (no previous close).
    """
    if not ohlc_data:
        return []

    result: list[tuple[str, float]] = []
    first = ohlc_data[0]
    result.append((first["date"], first["high"] - first["low"]))

    for i in range(1, len(ohlc_data)):
        h = ohlc_data[i]["high"]
        low = ohlc_data[i]["low"]
        prev_c = ohlc_data[i - 1]["close"]
        tr = max(h - low, abs(h - prev_c), abs(low - prev_c))
        result.append((ohlc_data[i]["date"], tr))

    return result


# ---------------------------------------------------------------------------
# ATR at a specific date (lookback only)
# ---------------------------------------------------------------------------

def calculate_atr_at_date(
    ohlc_data: list[dict[str, Any]],
    target_date: str,
    period: int = 14,
) -> float | None:
    """Calculate ATR using ONLY the `period` days BEFORE target_date.

    This is what the trader could see on their chart before entering.
    The target_date's own range is NOT included in the ATR.

    Args:
        ohlc_data: Chronologically sorted OHLC list.
        target_date: "YYYY-MM-DD" date to compute ATR for.
        period: Lookback window (default 14).

    Returns:
        ATR value, or None if not enough history.
    """
    trs = _true_ranges(ohlc_data)
    date_to_idx = {d: i for i, (d, _) in enumerate(trs)}

    target_idx = date_to_idx.get(target_date)
    if target_idx is None:
        return None

    # We need `period` true range values BEFORE target_idx
    if target_idx < period:
        return None

    lookback_trs = [trs[j][1] for j in range(target_idx - period, target_idx)]
    return sum(lookback_trs) / period


# ---------------------------------------------------------------------------
# Find volatile days (ATR > median * multiplier)
# ---------------------------------------------------------------------------

def find_volatile_days(
    symbol: str,
    date_from: str,
    date_to: str,
    atr_multiplier: float = 1.5,
    ohlc_data: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Find days where ATR(14) was elevated (> median_atr * multiplier).

    Requests 20 extra days before date_from for ATR warmup.

    A day is "volatile" if the 14-day ATR leading into it exceeds the
    median ATR across the entire range by the multiplier. This means the
    market was already in a volatile state when the day started.

    Returns:
        List of {date, atr, median_atr, atr_ratio, day_range, day_ratio}
        for volatile days only.
    """
    if ohlc_data is None:
        # Fetch extra 20 calendar days for ATR warmup
        warmup_from = (
            datetime.fromisoformat(date_from) - timedelta(days=20)
        ).strftime("%Y-%m-%d")
        ohlc_data = fetch_daily_ohlc(symbol, warmup_from, date_to)

    if len(ohlc_data) < 15:
        return []

    trs = _true_ranges(ohlc_data)

    # Compute ATR for ALL days with enough lookback (for a robust median)
    all_atrs: list[float] = []
    for i in range(14, len(trs)):
        lookback = [trs[j][1] for j in range(i - 14, i)]
        all_atrs.append(sum(lookback) / 14)

    if not all_atrs:
        return []

    # Median ATR from the full OHLC dataset (robust baseline)
    median_atr = statistics.median(all_atrs)

    # Now collect ATRs only for days in [date_from, date_to]
    day_atrs: list[tuple[str, float, int]] = []
    for i in range(14, len(trs)):
        date = trs[i][0]
        if date < date_from or date > date_to:
            continue
        lookback = [trs[j][1] for j in range(i - 14, i)]
        atr_val = sum(lookback) / 14
        day_atrs.append((date, atr_val, i))

    if not day_atrs:
        return []
    if median_atr <= 0:
        return []

    volatile: list[dict[str, Any]] = []
    for date, atr_val, idx in day_atrs:
        atr_ratio = atr_val / median_atr
        if atr_ratio >= atr_multiplier:
            day_range = trs[idx][1]
            day_ratio = round(day_range / atr_val, 2) if atr_val > 0 else 0.0
            volatile.append({
                "date": date,
                "atr": round(atr_val, 6),
                "median_atr": round(median_atr, 6),
                "atr_ratio": round(atr_ratio, 2),
                "day_range": round(day_range, 6),
                "day_ratio": day_ratio,
            })

    return volatile


# ---------------------------------------------------------------------------
# Analyze trader volatility
# ---------------------------------------------------------------------------

def analyze_trader_volatility(
    trades: list[dict],
    ohlc_by_symbol: dict[str, list[dict[str, Any]]] | None = None,
    atr_multiplier: float = 1.5,
) -> dict[str, Any]:
    """Analyze trader performance on high-volatility vs normal days.

    For each instrument the trader traded, computes the rolling 14-day ATR
    and the median ATR. Days where ATR > median * multiplier are "volatile".
    Trades are split by whether they opened on a volatile day.

    Returns:
        {high_vol: {count, wr, pnl, avg_pnl,
                    days: [{date, symbol, atr_ratio, day_range, day_ratio,
                            trades_count, day_pnl}]},
         normal: {count, wr, pnl, avg_pnl},
         money_lost_to_volatility: float}
    """
    if not trades:
        return _empty_volatility_result()

    symbols: set[str] = set()
    dates: list[datetime] = []
    for t in trades:
        s = (t.get("symbol") or "").upper()
        if s:
            symbols.add(s)
        dt = trade_instant_utc(t.get("opened_at"))
        if dt:
            dates.append(dt)

    if not symbols or not dates:
        return _empty_volatility_result()

    # Extra 20 days for ATR warmup
    date_from = min(dates).astimezone(timezone.utc).strftime("%Y-%m-%d")
    date_to = max(dates).astimezone(timezone.utc).strftime("%Y-%m-%d")

    # Find volatile days per symbol
    vol_days_by_symbol: dict[str, set[str]] = {}
    vol_details: dict[str, dict[str, dict]] = {}

    for symbol in symbols:
        ohlc = (ohlc_by_symbol or {}).get(symbol)
        vol_days = find_volatile_days(
            symbol, date_from, date_to, atr_multiplier, ohlc_data=ohlc,
        )
        vol_dates: set[str] = set()
        for vd in vol_days:
            vol_dates.add(vd["date"])
            vol_details.setdefault(symbol, {})[vd["date"]] = vd
        vol_days_by_symbol[symbol] = vol_dates

    # Split trades
    high_vol_trades: list[dict] = []
    normal_trades: list[dict] = []
    day_stats: dict[str, dict[str, Any]] = {}

    for trade in trades:
        symbol = (trade.get("symbol") or "").upper()
        opened = trade_instant_utc(trade.get("opened_at"))
        if not opened:
            normal_trades.append(trade)
            continue

        trade_date = opened.astimezone(timezone.utc).strftime("%Y-%m-%d")

        if trade_date in vol_days_by_symbol.get(symbol, set()):
            high_vol_trades.append(trade)
            key = f"{trade_date}|{symbol}"
            if key not in day_stats:
                detail = vol_details.get(symbol, {}).get(trade_date, {})
                day_stats[key] = {
                    "date": trade_date,
                    "symbol": symbol,
                    "atr_ratio": detail.get("atr_ratio", 0),
                    "day_range": detail.get("day_range", 0),
                    "day_ratio": detail.get("day_ratio", 0),
                    "trades_count": 0,
                    "day_pnl": 0.0,
                }
            day_stats[key]["trades_count"] += 1
            day_stats[key]["day_pnl"] += _net_profit(trade)
        else:
            normal_trades.append(trade)

    # Stats
    def _group_stats(group: list[dict]) -> dict[str, Any]:
        count = len(group)
        if count == 0:
            return {"count": 0, "wr": None, "pnl": 0.0, "avg_pnl": 0.0}
        wins = sum(1 for t in group if _net_profit(t) > 0)
        pnl = round(sum(_net_profit(t) for t in group), 2)
        return {
            "count": count,
            "wr": round(wins / count * 100, 2),
            "pnl": pnl,
            "avg_pnl": round(pnl / count, 2),
        }

    hv_stats = _group_stats(high_vol_trades)
    nm_stats = _group_stats(normal_trades)

    days_list = sorted(day_stats.values(), key=lambda x: x["date"])
    for d in days_list:
        d["day_pnl"] = round(d["day_pnl"], 2)
    hv_stats["days"] = days_list

    money_lost = 0.0
    if nm_stats["count"] > 0 and hv_stats["count"] > 0:
        money_lost = round(
            hv_stats["pnl"] - (hv_stats["count"] * nm_stats["avg_pnl"]), 2,
        )

    return {
        "high_vol": hv_stats,
        "normal": nm_stats,
        "money_lost_to_volatility": money_lost,
    }


def _empty_volatility_result() -> dict[str, Any]:
    return {
        "high_vol": {
            "count": 0, "wr": None, "pnl": 0.0, "avg_pnl": 0.0, "days": [],
        },
        "normal": {"count": 0, "wr": None, "pnl": 0.0, "avg_pnl": 0.0},
        "money_lost_to_volatility": 0.0,
    }


# ---------------------------------------------------------------------------
# Build coaching context
# ---------------------------------------------------------------------------

def build_volatility_context_for_coaching(
    trades: list[dict],
    news: list[dict[str, str]] | None = None,
    ohlc_by_symbol: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    """Build formatted volatility analysis for AI coaching prompts."""
    result = analyze_trader_volatility(
        trades, ohlc_by_symbol=ohlc_by_symbol,
    )

    hv = result["high_vol"]
    nm = result["normal"]

    if hv["count"] == 0:
        return ""

    lines: list[str] = ["VOLATILITY ANALYSIS:", ""]
    lines.append(
        "Your performance on high-volatility days "
        "(ATR was 1.5x+ above normal BEFORE you entered):"
    )
    lines.append("")

    hv_wr = f"{hv['wr']:.0f}%" if hv["wr"] is not None else "N/A"
    nm_wr = f"{nm['wr']:.0f}%" if nm["wr"] is not None else "N/A"

    lines.append(
        f"High-volatility days: {hv['count']} trades, "
        f"WR {hv_wr}, P&L ${hv['pnl']:+,.0f}"
    )
    lines.append(
        f"Normal days: {nm['count']} trades, "
        f"WR {nm_wr}, P&L ${nm['pnl']:+,.0f}"
    )

    money = result["money_lost_to_volatility"]
    if money < 0:
        lines.append(
            f"Difference: you lose ${abs(money):,.0f} more on volatile days"
        )
    elif money > 0:
        lines.append(
            f"Difference: you gain ${money:,.0f} more on volatile days"
        )
    else:
        lines.append("Difference: no significant difference")

    if hv.get("days"):
        lines.append("")
        lines.append("Volatile day details:")

        for day in hv["days"]:
            date = day["date"]
            symbol = day["symbol"]
            atr_ratio = day["atr_ratio"]
            day_range = day["day_range"]
            day_ratio = day["day_ratio"]
            tc = day["trades_count"]
            dp = day["day_pnl"]

            # Count W/L for this day
            wins = 0
            losses = 0
            for t in trades:
                s = (t.get("symbol") or "").upper()
                opened = trade_instant_utc(t.get("opened_at"))
                if not opened or s != symbol:
                    continue
                t_date = opened.astimezone(timezone.utc).strftime("%Y-%m-%d")
                if t_date == date:
                    if _net_profit(t) > 0:
                        wins += 1
                    else:
                        losses += 1

            lines.append(
                f"- {date}: When you entered {symbol}, "
                f"ATR(14) was {atr_ratio:.1f}x normal."
            )
            lines.append(
                f"  That day price moved {day_ratio:.1f}x the elevated ATR."
            )
            lines.append(
                f"  You: {tc} trades, {wins}W/{losses}L, ${dp:+,.0f}"
            )

            context_line = _find_news_for_date(date, symbol, news)
            lines.append(f"  Context: {context_line}")

    lines.append("")
    lines.append(
        "Note: ATR calculated from 14 days before each trade. "
        "News context is informational."
    )

    return "\n".join(lines)


def _find_news_for_date(
    date: str,
    symbol: str,
    news: list[dict[str, str]] | None,
) -> str:
    """Find a news headline for a given date and symbol."""
    if not news:
        return "no data available"

    from tradecoach.services.news import match_news_to_instruments

    for item in news:
        news_date = item.get("date", "")[:10]
        if news_date != date:
            continue
        instruments = match_news_to_instruments(item)
        if symbol in instruments:
            headline = item.get("headline", "")
            return f"'{headline}'"

    return "no data available"
