"""
Trade CRUD and stats endpoints.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from tradecoach.api.auth import get_current_user, require_self
from tradecoach.db.models import Trade
from tradecoach.db.queries import get_client, get_trades
from tradecoach.services.trade_analyzer import (
    expectancy,
    profit_factor,
    total_pnl,
    win_rate,
)

router = APIRouter()


class TradeListResponse(BaseModel):
    trades: list[Trade]
    count: int


class TradeStatsResponse(BaseModel):
    total_trades: int
    win_rate: float | None
    total_pnl: float
    profit_factor: float | None
    expectancy: float | None


@router.get("/{user_id}", response_model=TradeListResponse)
def list_trades(
    user_id: str,
    since: date | None = Query(None),
    until: date | None = Query(None),
    symbol: str | None = Query(None),
    limit: int = Query(100, le=1000),
    auth_user: str = Depends(get_current_user),
):
    """Get trades for a user with optional filters."""
    require_self(auth_user, user_id)
    client = get_client()
    trades = get_trades(
        client, user_id,
        since=since, until=until, symbol=symbol, limit=limit,
    )
    return TradeListResponse(trades=trades, count=len(trades))


@router.get("/{user_id}/stats", response_model=TradeStatsResponse)
def trade_stats(
    user_id: str,
    since: date | None = Query(None),
    until: date | None = Query(None),
    symbol: str | None = Query(None),
    auth_user: str = Depends(get_current_user),
):
    """Quick trade statistics summary."""
    require_self(auth_user, user_id)
    client = get_client()
    trades = get_trades(client, user_id, since=since, until=until, symbol=symbol)
    trade_dicts = [t.model_dump() for t in trades]

    return TradeStatsResponse(
        total_trades=len(trade_dicts),
        win_rate=win_rate(trade_dicts),
        total_pnl=total_pnl(trade_dicts),
        profit_factor=profit_factor(trade_dicts),
        expectancy=expectancy(trade_dicts),
    )
