"""
Timezone helpers for UTC storage + broker_timezone (IANA or UTC±N).

Uses stdlib zoneinfo + datetime.timezone only (no pytz).
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

UTC = timezone.utc

# Single shared fallback for null / empty broker_timezone (Task 018)
DEFAULT_BROKER_TIMEZONE = "UTC+2"

_BROKER_OFFSET = re.compile(r"^UTC([+-]?\d+)$", re.IGNORECASE)

# IANA anchors for session buckets (external / UTC-anchored)
_Z_TOKYO = ZoneInfo("Asia/Tokyo")
_Z_LONDON = ZoneInfo("Europe/London")
_Z_NY = ZoneInfo("America/New_York")


def resolve_broker_tz(broker_timezone: str | None) -> timezone | ZoneInfo:
    """Resolve broker_timezone string to a tzinfo (IANA or fixed UTC offset)."""
    s = (broker_timezone or "").strip() or DEFAULT_BROKER_TIMEZONE
    if not s:
        s = DEFAULT_BROKER_TIMEZONE
    try:
        return ZoneInfo(s)
    except Exception:
        pass
    m = _BROKER_OFFSET.match(s)
    if not m:
        return UTC
    inner = m.group(1)
    if inner.startswith(("+", "-")):
        hours = int(inner)
    elif inner == "":
        hours = 0
    else:
        hours = int(inner)
    return timezone(timedelta(hours=hours))


def naive_broker_wall_to_utc(naive: datetime, broker_timezone: str | None) -> datetime:
    """Interpret naive datetime as broker-local wall clock; return aware UTC."""
    tz = resolve_broker_tz(broker_timezone)
    if naive.tzinfo is not None:
        naive = naive.replace(tzinfo=None)
    local = naive.replace(tzinfo=tz)
    return local.astimezone(UTC)


def trade_instant_utc(val: str | datetime | None) -> datetime | None:
    """Parse trade opened_at/closed_at from DB/API as timezone-aware UTC."""
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val
    else:
        s = str(val).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def broker_calendar_date_str(dt_utc: datetime, broker_timezone: str | None) -> str:
    """Calendar date YYYY-MM-DD in the account broker timezone."""
    tz = resolve_broker_tz(broker_timezone)
    return dt_utc.astimezone(tz).strftime("%Y-%m-%d")


def broker_local_hour(dt_utc: datetime, broker_timezone: str | None) -> int:
    return dt_utc.astimezone(resolve_broker_tz(broker_timezone)).hour


def broker_local_weekday(dt_utc: datetime, broker_timezone: str | None) -> int:
    """Monday=0 .. Sunday=6 in broker-local calendar."""
    return dt_utc.astimezone(resolve_broker_tz(broker_timezone)).weekday()


def session_label_for_utc(dt_utc: datetime) -> str:
    """Map trade instant (UTC) to Asian / London / New York using IANA windows.

    New York window checked first, then London, then Tokyo (Asian).
    """
    dt_utc = dt_utc.astimezone(UTC)
    ny = dt_utc.astimezone(_Z_NY)
    if 8 <= ny.hour < 17:
        return "New York"
    lon = dt_utc.astimezone(_Z_LONDON)
    if 8 <= lon.hour < 16:
        return "London"
    tyo = dt_utc.astimezone(_Z_TOKYO)
    if 9 <= tyo.hour < 18:
        return "Asian"
    return "Asian"


def broker_today_utc_window(broker_timezone: str | None) -> tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of broker-local today, as aware UTC."""
    tz = resolve_broker_tz(broker_timezone)
    now_local = datetime.now(tz)
    start_local = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def format_broker_date_range(
    first_utc: datetime, last_utc: datetime, broker_timezone: str | None,
) -> str:
    """Human-readable period string using broker-local calendar."""
    tz = resolve_broker_tz(broker_timezone)
    a = first_utc.astimezone(tz)
    b = last_utc.astimezone(tz)
    first_s = a.strftime("%b %d") if a.year == b.year else a.strftime("%b %d, %Y")
    last_s = b.strftime("%b %d, %Y")
    return f"{first_s} — {last_s}"
