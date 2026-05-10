"""
News collector — fetch headlines from Finnhub, match to instruments, store in Supabase.

Runs on startup and every 30 minutes via FastAPI background task.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from tradecoach.db.queries import get_client
from tradecoach.services.news import fetch_all_news, match_news_to_instruments

logger = logging.getLogger(__name__)


def collect_and_store_news() -> int:
    """Fetch news from Finnhub (forex, general, crypto), match instruments, save to DB.

    Deduplicates by headline + date (truncated to minute).
    Returns count of newly inserted items.
    """
    today = datetime.now(tz=None).date()
    date_from = (today - timedelta(days=1)).isoformat()
    date_to = today.isoformat()

    news_items = fetch_all_news(date_from, date_to)
    if not news_items:
        logger.info("News collector: no items fetched")
        return 0

    client = get_client()

    # Load existing headlines for dedup
    existing = (
        client.table("news")
        .select("headline,date")
        .gte("date", f"{date_from}T00:00:00")
        .execute()
    )
    existing_keys: set[tuple[str, str]] = set()
    for row in existing.data:
        # Truncate to minute for matching
        d = row.get("date", "")[:16]  # "2026-03-12T14:30"
        existing_keys.add((row.get("headline", ""), d))

    rows_to_insert: list[dict] = []
    for item in news_items:
        # Parse date from "YYYY-MM-DD HH:MM" to ISO
        date_str = item["date"]  # "2026-03-12 14:30"
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            continue

        iso_date = dt.isoformat()
        dedup_key = (item["headline"], iso_date[:16])
        if dedup_key in existing_keys:
            continue

        instruments = match_news_to_instruments(item)

        rows_to_insert.append({
            "date": iso_date,
            "headline": item["headline"],
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "category": item.get("category", ""),
            "matched_instruments": instruments,
        })
        existing_keys.add(dedup_key)

    if not rows_to_insert:
        logger.info("News collector: all items already exist, 0 new")
        return 0

    # Batch insert
    client.table("news").insert(rows_to_insert).execute()
    count = len(rows_to_insert)
    logger.info("Collected %d new news items", count)
    return count


def get_news_for_period(
    date_from: str,
    date_to: str,
    instruments: list[str] | None = None,
) -> list[dict]:
    """Query stored news from Supabase for a date range.

    Args:
        date_from: ISO date "YYYY-MM-DD".
        date_to: ISO date "YYYY-MM-DD".
        instruments: Optional list of symbols to filter by (uses overlaps).

    Returns:
        List of news rows as dicts.
    """
    client = get_client()
    query = (
        client.table("news")
        .select("*")
        .gte("date", f"{date_from}T00:00:00")
        .lte("date", f"{date_to}T23:59:59")
        .order("date", desc=True)
        .limit(500)
    )

    if instruments:
        query = query.overlaps("matched_instruments", instruments)

    result = query.execute()
    return result.data
