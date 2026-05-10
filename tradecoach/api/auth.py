"""
Authentication dependency for FastAPI endpoints.

Extracts Supabase JWT from Authorization header, verifies it,
and returns the authenticated user_id.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from supabase import Client, create_client

from tradecoach.config import get_settings

_auth_client: Client | None = None


def _get_auth_client() -> Client:
    """Separate Supabase client for auth verification (uses anon key + JWT)."""
    global _auth_client
    if _auth_client is None:
        settings = get_settings()
        _auth_client = create_client(settings.supabase_url, settings.supabase_key)
    return _auth_client


def _extract_token(request: Request) -> str:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


def get_current_user(request: Request) -> str:
    """FastAPI dependency: verify Supabase JWT and return user_id.

    Usage:
        @router.get("/something")
        def endpoint(user_id: str = Depends(get_current_user)):
            ...
    """
    token = _extract_token(request)
    client = _get_auth_client()
    try:
        resp = client.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not resp or not resp.user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return resp.user.id


def require_self(authenticated_user_id: str, url_user_id: str) -> None:
    """Verify the authenticated user matches the user_id in the URL path."""
    if authenticated_user_id != url_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")


def require_account_owner(authenticated_user_id: str, account_id: str) -> None:
    """Verify the authenticated user owns the given account."""
    from tradecoach.db.queries import get_account, get_client

    client = get_client()
    acct = get_account(client, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    if acct.user_id != authenticated_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
