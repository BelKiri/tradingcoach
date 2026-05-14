"""
Accounts CRUD endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from tradecoach.api.auth import get_current_user, require_account_owner, require_self
from tradecoach.db.models import AccountCreate, validate_broker_timezone_value
from tradecoach.db.queries import (
    create_account,
    delete_account,
    delete_account_trades,
    delete_user_data,
    get_account,
    get_accounts,
    get_client,
    get_trades,
    update_account_name,
)
from tradecoach.services import trade_analyzer as ta

router = APIRouter()


class CreateAccountRequest(BaseModel):
    user_id: str
    name: str
    broker: str | None = None
    starting_balance: float | None = None
    broker_timezone: str | None = None

    @field_validator("broker_timezone")
    @classmethod
    def broker_timezone_ok(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_broker_timezone_value(v)


class RenameAccountRequest(BaseModel):
    name: str


class AccountResponse(BaseModel):
    id: str
    name: str
    broker: str | None
    starting_balance: float | None
    trades: int = 0
    pnl: float = 0.0
    win_rate: float | None = None


class AccountListResponse(BaseModel):
    accounts: list[AccountResponse]


@router.get("/{user_id}", response_model=AccountListResponse)
def list_accounts(user_id: str, auth_user: str = Depends(get_current_user)):
    """List all accounts for a user with summary stats."""
    require_self(auth_user, user_id)
    client = get_client()
    accounts = get_accounts(client, user_id)

    result = []
    for acct in accounts:
        trades = get_trades(client, user_id, account_id=acct.id)
        trade_dicts = [t.model_dump() for t in trades]
        result.append(AccountResponse(
            id=acct.id,
            name=acct.name,
            broker=acct.broker,
            starting_balance=acct.starting_balance,
            trades=len(trade_dicts),
            pnl=ta.total_pnl(trade_dicts) if trade_dicts else 0.0,
            win_rate=ta.win_rate(trade_dicts) if trade_dicts else None,
        ))

    return AccountListResponse(accounts=result)


@router.post("", response_model=AccountResponse)
def create_new_account(req: CreateAccountRequest, auth_user: str = Depends(get_current_user)):
    """Create a new trading account."""
    require_self(auth_user, req.user_id)
    client = get_client()

    # Ensure user exists in public.users (FK constraint)
    from tradecoach.db.queries import get_user, create_user
    from tradecoach.db.models import UserCreate
    if not get_user(client, req.user_id):
        create_user(client, UserCreate(id=req.user_id))

    try:
        payload = dict(
            user_id=req.user_id,
            name=req.name,
            broker=req.broker,
            starting_balance=req.starting_balance,
        )
        if req.broker_timezone is not None:
            payload["broker_timezone"] = req.broker_timezone
        acct = create_account(client, AccountCreate(**payload))
    except Exception as exc:
        msg = str(exc)
        if "23505" in msg or "duplicate key" in msg.lower():
            raise HTTPException(
                status_code=409,
                detail="Account with this name already exists. Please choose a different name.",
            )
        raise

    return AccountResponse(
        id=acct.id,
        name=acct.name,
        broker=acct.broker,
        starting_balance=acct.starting_balance,
    )


@router.get("/detail/{account_id}", response_model=AccountResponse)
def get_account_detail(account_id: str, auth_user: str = Depends(get_current_user)):
    """Get single account with stats."""
    require_account_owner(auth_user, account_id)
    client = get_client()
    acct = get_account(client, account_id)
    if not acct:
        raise HTTPException(404, "Account not found")

    trades = get_trades(client, acct.user_id, account_id=account_id)
    trade_dicts = [t.model_dump() for t in trades]

    return AccountResponse(
        id=acct.id,
        name=acct.name,
        broker=acct.broker,
        starting_balance=acct.starting_balance,
        trades=len(trade_dicts),
        pnl=ta.total_pnl(trade_dicts) if trade_dicts else 0.0,
        win_rate=ta.win_rate(trade_dicts) if trade_dicts else None,
    )


@router.patch("/{account_id}", response_model=AccountResponse)
def rename_account(account_id: str, req: RenameAccountRequest, auth_user: str = Depends(get_current_user)):
    """Rename a trading account."""
    require_account_owner(auth_user, account_id)
    client = get_client()
    acct = get_account(client, account_id)
    if not acct:
        raise HTTPException(404, "Account not found")

    updated = update_account_name(client, account_id, req.name)
    if not updated:
        raise HTTPException(500, "Failed to update account")

    trades = get_trades(client, updated.user_id, account_id=account_id)
    trade_dicts = [t.model_dump() for t in trades]

    return AccountResponse(
        id=updated.id,
        name=updated.name,
        broker=updated.broker,
        starting_balance=updated.starting_balance,
        trades=len(trade_dicts),
        pnl=ta.total_pnl(trade_dicts) if trade_dicts else 0.0,
        win_rate=ta.win_rate(trade_dicts) if trade_dicts else None,
    )


@router.delete("/{account_id}")
def delete_account_endpoint(account_id: str, auth_user: str = Depends(get_current_user)):
    """Delete a trading account and all its trades."""
    require_account_owner(auth_user, account_id)
    client = get_client()
    acct = get_account(client, account_id)
    if not acct:
        raise HTTPException(404, "Account not found")

    trades_deleted = delete_account_trades(client, account_id)
    delete_account(client, account_id)

    return {"status": "deleted", "trades_deleted": trades_deleted}


@router.delete("/user/{user_id}/all")
def delete_all_user_data(user_id: str, auth_user: str = Depends(get_current_user)):
    """Delete all accounts, trades, and coaching sessions for a user."""
    require_self(auth_user, user_id)
    client = get_client()
    counts = delete_user_data(client, user_id)
    return {"status": "deleted", "counts": counts}
