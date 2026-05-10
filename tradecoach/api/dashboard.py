"""
Dashboard endpoint — full analytics, no AI, pure math.

Returns all trade_analyzer metrics in one call.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from tradecoach.api.auth import get_current_user, require_self
from tradecoach.db.queries import get_account, get_client, get_trades
from tradecoach.services import trade_analyzer as ta

router = APIRouter()


class BehavioralData(BaseModel):
    revenge_count: int = 0
    revenge_cost: float = 0.0
    martingale_count: int = 0
    martingale_pnl: float = 0.0
    overtrading_days: int = 0
    overtrading_pnl: float = 0.0
    overtrading_wr: float | None = None
    averaging_count: int = 0
    averaging_pnl: float = 0.0
    quick_exits_count: int = 0
    quick_exits_pnl: float = 0.0
    sl_with: int = 0
    sl_without: int = 0
    no_sl_pnl: float = 0.0


class DashboardResponse(BaseModel):
    total_trades: int
    win_rate: float | None
    total_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    avg_win: float | None
    avg_loss: float | None
    expectancy: float | None
    max_drawdown: dict[str, float]
    equity_curve: list[dict[str, Any]]
    pnl_by_symbol: dict[str, Any]
    pnl_by_session: dict[str, Any]
    pnl_by_day_of_week: dict[str, Any]
    pnl_by_hour: dict[Any, Any]
    hold_time: dict[str, Any] | None
    streaks: dict[str, Any]
    revenge_trades_count: int
    revenge_trade_cost: float
    behavioral: BehavioralData
    risk_per_trade: list[dict[str, Any]]
    trades: list[dict[str, Any]]


@router.get("/{user_id}", response_model=DashboardResponse)
def get_dashboard(
    user_id: str,
    account_id: str | None = Query(None),
    since: date | None = Query(None),
    until: date | None = Query(None),
    auth_user: str = Depends(get_current_user),
):
    """Full dashboard analytics for a user, optionally filtered by account."""
    require_self(auth_user, user_id)
    client = get_client()
    trades = get_trades(
        client, user_id, account_id=account_id,
        since=since, until=until, limit=5000,
    )
    trade_dicts = [t.model_dump() for t in trades]

    # Get account balance and timezone for calculations
    account_balance: float | None = None
    broker_timezone: str = "UTC+0"
    if account_id:
        acct = get_account(client, account_id)
        if acct:
            account_balance = acct.starting_balance
            broker_timezone = acct.broker_timezone or "UTC+0"

    result = ta.full_analysis(
        trade_dicts,
        account_balance=account_balance,
        broker_timezone=broker_timezone,
    )

    # Behavioral analysis
    revenge = ta.detect_revenge_trades(trade_dicts)
    mart = ta.detect_martingale(trade_dicts)
    ot = ta.detect_overtrading(trade_dicts)
    avg_down = ta.detect_averaging_down(trade_dicts)
    quick = ta.detect_quick_exits(trade_dicts)
    sl = ta.sl_usage(trade_dicts)

    from tradecoach.services._helpers import _net_profit
    mart_pnl = sum(_net_profit(m["trade"]) for m in mart)
    avg_down_pnl = sum(_net_profit(a["trade"]) for a in avg_down)
    quick_pnl = sum(q["pnl"] for q in quick)

    # P&L for trades without stop loss
    no_sl_pnl = 0.0
    for t in trade_dicts:
        sl_val = t.get("stop_loss")
        if sl_val is None or float(sl_val) == 0:
            no_sl_pnl += _net_profit(t)

    behavioral = BehavioralData(
        revenge_count=len(revenge),
        revenge_cost=result["revenge_trade_cost"],
        martingale_count=len(mart),
        martingale_pnl=mart_pnl,
        overtrading_days=ot["overtrading_days"],
        overtrading_pnl=ot["overtrading_pnl"],
        overtrading_wr=ot["overtrading_wr"],
        averaging_count=len(avg_down),
        averaging_pnl=round(avg_down_pnl, 2),
        quick_exits_count=len(quick),
        quick_exits_pnl=round(quick_pnl, 2),
        sl_with=sl["with_sl"],
        sl_without=sl["without_sl"],
        no_sl_pnl=round(no_sl_pnl, 2),
    )

    # Risk per trade (for risk distribution)
    risk = ta.risk_per_trade(trade_dicts, account_balance) if account_balance else []

    # Serialize trades for table (last 200)
    sorted_trades = sorted(
        trade_dicts,
        key=lambda t: t.get("closed_at") or "",
        reverse=True,
    )

    return DashboardResponse(
        total_trades=result["total_trades"],
        win_rate=result["win_rate"],
        total_pnl=result["total_pnl"],
        gross_profit=result["gross_profit"],
        gross_loss=result["gross_loss"],
        profit_factor=result["profit_factor"],
        avg_win=result["avg_win"],
        avg_loss=result["avg_loss"],
        expectancy=result["expectancy"],
        max_drawdown=result["max_drawdown"],
        equity_curve=result["equity_curve"],
        pnl_by_symbol=result["pnl_by_symbol"],
        pnl_by_session=result["pnl_by_session"],
        pnl_by_day_of_week=result["pnl_by_day_of_week"],
        pnl_by_hour=result["pnl_by_hour"],
        hold_time=result["hold_time"],
        streaks=result["streaks"],
        revenge_trades_count=len(revenge),
        revenge_trade_cost=result["revenge_trade_cost"],
        behavioral=behavioral,
        risk_per_trade=risk,
        trades=sorted_trades[:200],
    )
