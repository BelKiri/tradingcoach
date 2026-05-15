"""
Shared helpers used across multiple service modules.

Canonical definitions of _to_dt, _net_profit, _is_winner, _is_loser.
Session labels use tradecoach.services.tz_utils.session_label_for_utc.
"""

from __future__ import annotations

from datetime import datetime


def _to_dt(val: str | datetime | None) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            val = val.replace(tzinfo=None)
        return val
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def _net_profit(t: dict) -> float:
    """Net profit including commission and swap."""
    p = t.get("profit_money") or 0.0
    c = t.get("commission") or 0.0
    s = t.get("swap") or 0.0
    return p + c + s


def _is_winner(t: dict) -> bool:
    return _net_profit(t) > 0


def _is_loser(t: dict) -> bool:
    return _net_profit(t) < 0
