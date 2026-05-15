"""
News service — fetch headlines, match to instruments, build coaching context.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from tradecoach.services._helpers import _net_profit, _to_dt
from tradecoach.services.tz_utils import trade_instant_utc

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_KEYWORDS_FILE = _DATA_DIR / "instrument_keywords.json"
_NEWS_CACHE_FILE = _DATA_DIR / "news_cache.json"

_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


# ---------------------------------------------------------------------------
# Load keywords (singleton)
# ---------------------------------------------------------------------------

_keywords_cache: dict | None = None


def _load_keywords() -> dict:
    global _keywords_cache
    if _keywords_cache is None:
        with open(_KEYWORDS_FILE, encoding="utf-8") as f:
            _keywords_cache = json.load(f)
    return _keywords_cache


# ---------------------------------------------------------------------------
# News cache helpers
# ---------------------------------------------------------------------------

def _load_news_cache() -> dict:
    if not _NEWS_CACHE_FILE.exists():
        return {}
    with open(_NEWS_CACHE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_news_cache(cache: dict) -> None:
    with open(_NEWS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _cache_key(date_from: str, date_to: str, category: str) -> str:
    return f"{date_from}|{date_to}|{category}"


def _is_cache_valid(entry: dict) -> bool:
    fetched_at = entry.get("fetched_at", 0)
    return (time.time() - fetched_at) < _CACHE_TTL_SECONDS


# ---------------------------------------------------------------------------
# Finnhub news fetching
# ---------------------------------------------------------------------------

def _get_finnhub_key() -> str:
    from tradecoach.config import get_settings
    key = get_settings().finnhub_api_key
    if not key:
        raise RuntimeError(
            "FINNHUB_API_KEY not set. Add it to your .env file: "
            "FINNHUB_API_KEY=your_key_here  "
            "(Get a free key at https://finnhub.io/register)"
        )
    return key


def fetch_news_finnhub(
    date_from: str,
    date_to: str,
    category: str = "forex",
) -> list[dict[str, str]]:
    """Fetch news from Finnhub API for a given category and date range.

    Args:
        date_from: ISO date "YYYY-MM-DD".
        date_to: ISO date "YYYY-MM-DD".
        category: "forex", "general", or "crypto".

    Returns:
        List of {date, headline, summary, source, url, category}.
    """
    # Check cache first
    cache = _load_news_cache()
    key = _cache_key(date_from, date_to, category)
    if key in cache and _is_cache_valid(cache[key]):
        return cache[key]["data"]

    api_key = _get_finnhub_key()

    resp = httpx.get(
        "https://finnhub.io/api/v1/news",
        params={"category": category, "token": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    raw: list[dict] = resp.json()

    dt_from = datetime.fromisoformat(date_from)
    dt_to = datetime.fromisoformat(date_to) + timedelta(days=1)  # inclusive

    results: list[dict[str, str]] = []
    for item in raw:
        ts = item.get("datetime", 0)
        dt = datetime.utcfromtimestamp(ts)
        if dt < dt_from or dt >= dt_to:
            continue
        results.append({
            "date": dt.strftime("%Y-%m-%d %H:%M"),
            "headline": item.get("headline", ""),
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "category": category,
        })

    # Save to cache
    cache[key] = {"fetched_at": time.time(), "data": results}
    _save_news_cache(cache)

    return results


def fetch_all_news(
    date_from: str,
    date_to: str,
) -> list[dict[str, str]]:
    """Fetch news from all categories, deduplicate, sort by date.

    Categories: forex, general, crypto.
    """
    all_news: list[dict[str, str]] = []
    seen_headlines: set[str] = set()

    for category in ("forex", "general", "crypto"):
        items = fetch_news_finnhub(date_from, date_to, category)
        for item in items:
            headline = item["headline"]
            if headline not in seen_headlines:
                seen_headlines.add(headline)
                all_news.append(item)

    all_news.sort(key=lambda x: x["date"])
    return all_news


# ---------------------------------------------------------------------------
# Instrument matching (keyword-based)
# ---------------------------------------------------------------------------

def match_news_to_instruments(news_item: dict[str, str]) -> list[str]:
    """Match a single news item to trading instruments via keywords.

    Checks headline + summary against instrument keywords and cross-asset
    keywords. Returns deduplicated list of matched instrument symbols.
    """
    kw_data = _load_keywords()
    text = (
        (news_item.get("headline", "") + " " + news_item.get("summary", ""))
        .lower()
    )

    matched: set[str] = set()

    # Direct instrument keywords
    for symbol, keywords in kw_data["instruments"].items():
        for kw in keywords:
            if kw in text:
                matched.add(symbol)
                break

    # Cross-asset keywords
    for _group_name, group in kw_data["cross_asset"].items():
        for kw in group["keywords"]:
            if kw in text:
                matched.update(group["affects"])
                break

    return sorted(matched)


# ---------------------------------------------------------------------------
# Match news to trades
# ---------------------------------------------------------------------------

def get_relevant_news_for_trades(
    trades: list[dict],
    news: list[dict[str, str]],
    window_hours: int = 2,
) -> list[dict[str, Any]]:
    """For each trade, find news published within window_hours BEFORE the trade.

    Trade open and news timestamps are compared in true UTC.
    """
    if not trades or not news:
        return []

    kw_data = _load_keywords()
    window = timedelta(hours=window_hours)

    # Pre-parse news datetimes and their matched instruments
    parsed_news: list[tuple[dict[str, str], datetime, list[str], str]] = []
    for item in news:
        try:
            news_dt = datetime.strptime(
                item["date"], "%Y-%m-%d %H:%M",
            ).replace(tzinfo=timezone.utc)
        except (ValueError, KeyError):
            continue

        instruments = match_news_to_instruments(item)
        # Determine match type for each instrument
        # We'll store the raw instruments list and resolve match type per trade
        parsed_news.append((item, news_dt, instruments, _match_type(item, kw_data)))

    results: list[dict[str, Any]] = []

    for trade in trades:
        trade_utc = trade_instant_utc(trade.get("opened_at"))
        if not trade_utc:
            continue
        symbol = (trade.get("symbol") or "").upper()
        relevant: list[dict[str, str]] = []

        for item, news_dt, instruments, match_type in parsed_news:
            # News must be within window_hours BEFORE trade open
            diff = trade_utc - news_dt
            if diff < timedelta(0) or diff > window:
                continue

            # News must match trade's instrument
            if symbol not in instruments:
                continue

            # Determine if match is direct or cross-asset for this symbol
            via = _match_via_for_symbol(symbol, item, kw_data)

            relevant.append({
                "headline": item["headline"],
                "source": item.get("source", ""),
                "date": item["date"],
                "category": item.get("category", ""),
                "matched_via": via,
            })

        if relevant:
            results.append({"trade": trade, "relevant_news": relevant})

    return results


def _match_type(item: dict[str, str], kw_data: dict) -> str:
    """Determine primary match type for a news item."""
    text = (item.get("headline", "") + " " + item.get("summary", "")).lower()
    for _group_name, group in kw_data["cross_asset"].items():
        for kw in group["keywords"]:
            if kw in text:
                return "cross-asset"
    return "direct"


def _match_via_for_symbol(
    symbol: str, item: dict[str, str], kw_data: dict
) -> str:
    """Determine if a symbol was matched via direct keyword or cross-asset."""
    text = (item.get("headline", "") + " " + item.get("summary", "")).lower()

    # Check direct match first
    if symbol in kw_data["instruments"]:
        for kw in kw_data["instruments"][symbol]:
            if kw in text:
                return "direct"

    # Check cross-asset
    for _group_name, group in kw_data["cross_asset"].items():
        if symbol in group["affects"]:
            for kw in group["keywords"]:
                if kw in text:
                    return "cross-asset"

    return "direct"


# ---------------------------------------------------------------------------
# Build coaching context
# ---------------------------------------------------------------------------

def build_news_context_for_coaching(
    trades: list[dict],
    news: list[dict[str, str]],
) -> str:
    """Build a formatted string of news context for AI coaching prompts.

    Groups trades by instrument, shows which had relevant news nearby,
    and compares WR/PnL for trades with vs without news.
    """
    matched = get_relevant_news_for_trades(trades, news)
    if not matched:
        return ""

    # Build set of trade IDs that had news
    news_trade_ids: set[int] = set()
    # Group by instrument
    by_instrument: dict[str, list[dict[str, Any]]] = {}

    for m in matched:
        trade = m["trade"]
        news_trade_ids.add(id(trade))
        symbol = (trade.get("symbol") or "UNKNOWN").upper()

        if symbol not in by_instrument:
            by_instrument[symbol] = []
        by_instrument[symbol].append(m)

    # Calculate WR/PnL splits
    news_trades = [t for t in trades if id(t) in news_trade_ids]
    normal_trades = [t for t in trades if id(t) not in news_trade_ids]

    def _wr(group: list[dict]) -> float | None:
        if not group:
            return None
        wins = sum(1 for t in group if _net_profit(t) > 0)
        return round(wins / len(group) * 100, 1)

    def _pnl(group: list[dict]) -> float:
        return round(sum(_net_profit(t) for t in group), 2)

    news_wr = _wr(news_trades)
    news_pnl = _pnl(news_trades)
    normal_wr = _wr(normal_trades)
    normal_pnl = _pnl(normal_trades)

    # Build output
    lines: list[str] = ["NEWS CONTEXT:", ""]

    # Count total trades per instrument
    trades_by_symbol: dict[str, int] = {}
    for t in trades:
        s = (t.get("symbol") or "UNKNOWN").upper()
        trades_by_symbol[s] = trades_by_symbol.get(s, 0) + 1

    for symbol in sorted(by_instrument.keys()):
        entries = by_instrument[symbol]
        total = trades_by_symbol.get(symbol, 0)
        lines.append(
            f"{symbol} ({total} trades, {len(entries)} had relevant news nearby):"
        )
        for entry in entries:
            trade = entry["trade"]
            opened = _to_dt(trade.get("opened_at"))
            date_str = opened.strftime("%b %d") if opened else "?"
            direction = (trade.get("direction") or "?").upper()
            pnl = _net_profit(trade)
            pnl_str = f"${pnl:+,.0f}"

            for n in entry["relevant_news"]:
                via = n["matched_via"]
                lines.append(
                    f"- {date_str}: {direction} {pnl_str} | "
                    f"News: '{n['headline']}' ({via})"
                )
        lines.append("")

    lines.append(
        f"Trades with nearby news: WR {news_wr:.0f}%, P&L ${news_pnl:+,.0f}"
        if news_wr is not None
        else f"Trades with nearby news: WR N/A, P&L ${news_pnl:+,.0f}"
    )
    lines.append(
        f"Trades without news: WR {normal_wr:.0f}%, P&L ${normal_pnl:+,.0f}"
        if normal_wr is not None
        else f"Trades without news: WR N/A, P&L ${normal_pnl:+,.0f}"
    )
    lines.append("")
    lines.append(
        "Note: news context is informational. "
        "Do not assume direction from headlines."
    )

    return "\n".join(lines)
