"""
Supabase database query functions.

All DB access goes through this module. Uses the supabase-py sync client.
Functions accept a Supabase client as the first argument for testability.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from supabase import Client

from tradecoach.db.models import (
    Account,
    AccountCreate,
    Emotion,
    EmotionCreate,
    HabitScore,
    HabitScoreCreate,
    Trade,
    TradeCreate,
    User,
    UserCreate,
    UserSettings,
    UserSettingsCreate,
    UserSettingsUpdate,
    UserUpdate,
)


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

_client: Client | None = None


def get_client() -> Client:
    """Get or create the Supabase client singleton."""
    global _client
    if _client is None:
        from supabase import create_client
        from tradecoach.config import get_settings

        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def set_client(client: Client) -> None:
    """Override the client (for testing)."""
    global _client
    _client = client


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user(client: Client, data: UserCreate) -> User:
    result = (
        client.table("users")
        .insert(data.model_dump())
        .execute()
    )
    return User(**result.data[0])


def get_user(client: Client, user_id: str) -> User | None:
    result = (
        client.table("users")
        .select("*")
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        return None
    return User(**result.data[0])


def get_user_by_telegram_id(client: Client, telegram_id: int) -> User | None:
    result = (
        client.table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    if not result.data:
        return None
    return User(**result.data[0])


def update_user(client: Client, user_id: str, data: UserUpdate) -> User | None:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_user(client, user_id)
    result = (
        client.table("users")
        .update(payload)
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        return None
    return User(**result.data[0])


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

def create_account(client: Client, data: AccountCreate) -> Account:
    result = (
        client.table("accounts")
        .insert(data.model_dump())
        .execute()
    )
    return Account(**result.data[0])


def get_accounts(client: Client, user_id: str) -> list[Account]:
    result = (
        client.table("accounts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return [Account(**r) for r in result.data]


def get_account(client: Client, account_id: str) -> Account | None:
    result = (
        client.table("accounts")
        .select("*")
        .eq("id", account_id)
        .execute()
    )
    if not result.data:
        return None
    return Account(**result.data[0])


def update_account_name(client: Client, account_id: str, name: str) -> Account | None:
    result = (
        client.table("accounts")
        .update({"name": name})
        .eq("id", account_id)
        .execute()
    )
    if not result.data:
        return None
    return Account(**result.data[0])


def delete_account(client: Client, account_id: str) -> bool:
    result = (
        client.table("accounts")
        .delete()
        .eq("id", account_id)
        .execute()
    )
    return bool(result.data)


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

def insert_trades(client: Client, trades: list[TradeCreate]) -> list[Trade]:
    """Bulk insert trades. Returns the inserted trades with IDs."""
    if not trades:
        return []
    rows = [_serialize_trade(t) for t in trades]
    result = client.table("trades").insert(rows).execute()
    return [Trade(**r) for r in result.data]


def get_trades(
    client: Client,
    user_id: str,
    *,
    account_id: str | None = None,
    since: date | datetime | None = None,
    until: date | datetime | None = None,
    symbol: str | None = None,
    limit: int = 1000,
) -> list[Trade]:
    """Get trades with optional filters."""
    query = (
        client.table("trades")
        .select("*")
        .eq("user_id", user_id)
        .order("closed_at", desc=True)
        .limit(limit)
    )
    if account_id:
        query = query.eq("account_id", account_id)
    if since:
        query = query.gte("closed_at", _to_iso(since))
    if until:
        query = query.lte("closed_at", _to_iso(until))
    if symbol:
        query = query.eq("symbol", symbol.upper())

    result = query.execute()
    return [Trade(**r) for r in result.data]


def get_trades_today(client: Client, user_id: str) -> list[Trade]:
    """Get all trades opened today (UTC)."""
    today = datetime.utcnow().date()
    return get_trades(client, user_id, since=today)


def find_existing_trade_keys(
    client: Client, user_id: str, *, account_id: str | None = None,
) -> set[tuple[str, str | None, str, float]]:
    """Get (symbol, opened_at_minute, direction, lot) tuples for deduplication.

    opened_at is rounded to the nearest minute so that the same trade
    imported from different formats (CSV vs Excel) with slightly different
    timestamps still matches.
    """
    query = (
        client.table("trades")
        .select("symbol,opened_at,direction,lot")
        .eq("user_id", user_id)
        .limit(10000)
    )
    if account_id:
        query = query.eq("account_id", account_id)
    result = query.execute()
    keys: set[tuple[str, str | None, str, float]] = set()
    for r in result.data:
        keys.add((
            r.get("symbol", ""),
            _round_to_minute(r.get("opened_at")),
            r.get("direction", ""),
            float(r.get("lot", 0)),
        ))
    return keys


def _round_to_minute(iso_str: str | None) -> str | None:
    """Round an ISO datetime string to the nearest minute."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        dt = dt.replace(second=0, microsecond=0)
        return dt.isoformat()
    except (ValueError, TypeError):
        return iso_str


def delete_account_trades(client: Client, account_id: str) -> int:
    """Delete all trades for a specific account. Returns count of deleted rows."""
    result = (
        client.table("trades")
        .delete()
        .eq("account_id", account_id)
        .execute()
    )
    return len(result.data) if result.data else 0


def delete_user_data(client: Client, user_id: str) -> dict[str, int]:
    """Delete all trades, emotions, habit_scores, and accounts for a user.

    Returns counts of deleted rows per table.
    """
    counts: dict[str, int] = {}
    for table in ("coaching_sessions", "trades", "emotions", "habit_scores", "accounts"):
        result = (
            client.table(table)
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        counts[table] = len(result.data) if result.data else 0
    return counts


# ---------------------------------------------------------------------------
# Emotions
# ---------------------------------------------------------------------------

def save_emotion(client: Client, data: EmotionCreate) -> Emotion:
    result = (
        client.table("emotions")
        .insert(data.model_dump())
        .execute()
    )
    return Emotion(**result.data[0])


def get_emotions(
    client: Client,
    user_id: str,
    *,
    trade_id: str | None = None,
    since: date | datetime | None = None,
    limit: int = 500,
) -> list[Emotion]:
    query = (
        client.table("emotions")
        .select("*")
        .eq("user_id", user_id)
        .order("logged_at", desc=True)
        .limit(limit)
    )
    if trade_id:
        query = query.eq("trade_id", trade_id)
    if since:
        query = query.gte("logged_at", _to_iso(since))

    result = query.execute()
    return [Emotion(**r) for r in result.data]


# ---------------------------------------------------------------------------
# User Settings
# ---------------------------------------------------------------------------

def save_user_settings(
    client: Client, data: UserSettingsCreate
) -> UserSettings:
    """Upsert user settings (insert or update on conflict)."""
    payload = _serialize_settings(data)
    result = (
        client.table("user_settings")
        .upsert(payload)
        .execute()
    )
    return UserSettings(**result.data[0])


def get_user_settings(
    client: Client, user_id: str
) -> UserSettings | None:
    result = (
        client.table("user_settings")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        return None
    return UserSettings(**result.data[0])


def update_user_settings(
    client: Client, user_id: str, data: UserSettingsUpdate
) -> UserSettings | None:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_user_settings(client, user_id)
    # Serialize time fields
    if "briefing_time" in payload and payload["briefing_time"] is not None:
        payload["briefing_time"] = payload["briefing_time"].isoformat()
    result = (
        client.table("user_settings")
        .update(payload)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        return None
    return UserSettings(**result.data[0])


# ---------------------------------------------------------------------------
# Habit Scores
# ---------------------------------------------------------------------------

def save_habit_score(
    client: Client, data: HabitScoreCreate
) -> HabitScore:
    payload = data.model_dump()
    payload["period_start"] = payload["period_start"].isoformat()
    payload["period_end"] = payload["period_end"].isoformat()
    result = (
        client.table("habit_scores")
        .insert(payload)
        .execute()
    )
    return HabitScore(**result.data[0])


def get_habit_scores(
    client: Client,
    user_id: str,
    *,
    since: date | None = None,
    limit: int = 52,
) -> list[HabitScore]:
    query = (
        client.table("habit_scores")
        .select("*")
        .eq("user_id", user_id)
        .order("period_end", desc=True)
        .limit(limit)
    )
    if since:
        query = query.gte("period_end", since.isoformat())

    result = query.execute()
    return [HabitScore(**r) for r in result.data]


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _to_iso(val: date | datetime) -> str:
    return val.isoformat()


def _serialize_trade(t: TradeCreate) -> dict[str, Any]:
    d = t.model_dump()
    for key in ("opened_at", "closed_at"):
        if d.get(key) is not None:
            d[key] = d[key].isoformat()
    return d


def _serialize_settings(s: UserSettingsCreate) -> dict[str, Any]:
    d = s.model_dump()
    if d.get("briefing_time") is not None:
        d["briefing_time"] = d["briefing_time"].isoformat()
    return d
