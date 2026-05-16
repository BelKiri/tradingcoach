"""
Quota checks for accounts, file uploads, and coaching sessions.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from tradecoach.db.queries import get_accounts

MAX_BETA_ACCOUNTS = 3
MAX_BETA_COACHING_SESSIONS = 3

ACCOUNT_LIMIT_DETAIL = (
    "Account limit reached for the beta. Contact @BMNCap for expanded access."
)
UPLOAD_LIMIT_DETAIL = (
    "File upload per account is currently limited to one. "
    "You can delete this account and create a new one."
)
COACHING_LIMIT_DETAIL = (
    "One AI Coach session per account during beta. "
    "Want more insights? Create another account."
)
COACHING_LIFETIME_LIMIT_DETAIL = (
    "All AI Coach sessions used for the beta. Contact @BMNCap for expanded access."
)


class BetaQuotaError(Exception):
    """Raised when a beta quota limit blocks an action."""


def get_user_beta_fields(client: Client, user_id: str) -> tuple[bool, int]:
    """Return (is_beta_exempt, coaching_sessions_used)."""
    result = (
        client.table("users")
        .select("is_beta_exempt, coaching_sessions_used")
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        return False, 0
    row = result.data[0]
    return bool(row.get("is_beta_exempt")), int(row.get("coaching_sessions_used") or 0)


def account_has_any_trades(client: Client, user_id: str, account_id: str) -> bool:
    if not (account_id or "").strip():
        return False
    result = (
        client.table("trades")
        .select("id")
        .eq("user_id", user_id)
        .eq("account_id", account_id)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def account_has_coaching_session(client: Client, user_id: str, account_id: str) -> bool:
    result = (
        client.table("coaching_sessions")
        .select("id")
        .eq("user_id", user_id)
        .eq("account_id", account_id)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def assert_can_create_account(client: Client, user_id: str) -> None:
    exempt, _ = get_user_beta_fields(client, user_id)
    if exempt:
        return
    if len(get_accounts(client, user_id)) >= MAX_BETA_ACCOUNTS:
        raise BetaQuotaError(ACCOUNT_LIMIT_DETAIL)


def assert_can_upload_file(client: Client, user_id: str, account_id: str) -> None:
    if not (account_id or "").strip():
        return
    exempt, _ = get_user_beta_fields(client, user_id)
    if exempt:
        return
    if account_has_any_trades(client, user_id, account_id):
        raise BetaQuotaError(UPLOAD_LIMIT_DETAIL)


def assert_can_generate_coaching(client: Client, user_id: str, account_id: str) -> None:
    exempt, used = get_user_beta_fields(client, user_id)
    if exempt:
        return
    if used >= MAX_BETA_COACHING_SESSIONS:
        raise BetaQuotaError(COACHING_LIFETIME_LIMIT_DETAIL)
    if account_has_coaching_session(client, user_id, account_id):
        raise BetaQuotaError(COACHING_LIMIT_DETAIL)


def increment_coaching_sessions_used(client: Client, user_id: str) -> bool:
    """Atomically increment lifetime counter. Returns False if cap already reached."""
    exempt, _ = get_user_beta_fields(client, user_id)
    if exempt:
        return True

    for _ in range(5):
        result = (
            client.table("users")
            .select("coaching_sessions_used")
            .eq("id", user_id)
            .execute()
        )
        if not result.data:
            return False
        current = int(result.data[0].get("coaching_sessions_used") or 0)
        if current >= MAX_BETA_COACHING_SESSIONS:
            return False
        updated = (
            client.table("users")
            .update({"coaching_sessions_used": current + 1})
            .eq("id", user_id)
            .eq("coaching_sessions_used", current)
            .execute()
        )
        if updated.data:
            return True
    return False


def rollback_coaching_session(client: Client, session_id: str) -> None:
    client.table("coaching_sessions").delete().eq("id", session_id).execute()


def build_user_quota(client: Client, user_id: str) -> dict[str, Any]:
    exempt, coaching_used = get_user_beta_fields(client, user_id)
    accounts = get_accounts(client, user_id)
    account_rows: list[dict[str, Any]] = []
    for acct in accounts:
        account_rows.append({
            "id": acct.id,
            "upload_used": account_has_any_trades(client, user_id, acct.id),
            "coaching_used": account_has_coaching_session(client, user_id, acct.id),
        })
    return {
        "is_beta_exempt": exempt,
        "coaching_sessions_used": coaching_used,
        "accounts": account_rows,
    }
