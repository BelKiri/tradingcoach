"""
User ensure endpoint — syncs Supabase Auth users to public.users table.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tradecoach.api.auth import get_current_user, require_self
from tradecoach.db.models import UserCreate
from tradecoach.db.queries import create_user, get_client, get_user
from tradecoach.services.beta_quota import build_user_quota

router = APIRouter()


class EnsureUserRequest(BaseModel):
    user_id: str
    email: str | None = None


class AccountQuotaFlags(BaseModel):
    id: str
    upload_used: bool
    coaching_used: bool


class UserQuotaResponse(BaseModel):
    is_beta_exempt: bool
    coaching_sessions_used: int
    accounts: list[AccountQuotaFlags]


@router.get("/{user_id}/quota", response_model=UserQuotaResponse)
def get_user_quota(user_id: str, auth_user: str = Depends(get_current_user)):
    """Beta quota snapshot for banner and disabled UI states."""
    require_self(auth_user, user_id)
    client = get_client()
    payload = build_user_quota(client, user_id)
    return UserQuotaResponse(**payload)


@router.post("/ensure")
def ensure_user(req: EnsureUserRequest, auth_user: str = Depends(get_current_user)):
    """Create user in public.users if not exists."""
    require_self(auth_user, req.user_id)
    client = get_client()
    existing = get_user(client, req.user_id)
    if existing:
        return {"status": "exists", "user_id": existing.id}

    user = create_user(client, UserCreate(
        id=req.user_id,
        email=req.email,
    ))
    return {"status": "created", "user_id": user.id}
