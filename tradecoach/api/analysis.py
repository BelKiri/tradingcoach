"""
Analysis endpoints — habit score, emotion analysis, pre-trade risk check.

No AI/LLM here. All pure math from existing services.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from tradecoach.api.auth import get_current_user, require_self

from tradecoach.db.models import EmotionCreate, EmotionType
from tradecoach.db.queries import (
    get_client,
    get_emotions,
    get_trades,
    get_trades_today,
    get_user_settings,
    save_emotion,
)
from tradecoach.services.emotion_tracker import emotion_summary, stats_by_emotion
from tradecoach.services.habit_scorer import calculate_habit_score
from tradecoach.services.risk_checker import ChecklistResult, run_pre_trade_check
from tradecoach.services.tz_utils import DEFAULT_BROKER_TIMEZONE

router = APIRouter()


# ---------------------------------------------------------------------------
# Habit Score
# ---------------------------------------------------------------------------

class HabitScoreResponse(BaseModel):
    score: int
    plan_adherence: float
    emotional_stability: float
    risk_discipline: float
    consistency: float
    journal_completion: float


@router.get("/{user_id}/habit-score", response_model=HabitScoreResponse)
def get_habit_score(
    user_id: str,
    since: date | None = Query(None),
    until: date | None = Query(None),
    account_balance: float | None = Query(None),
    auth_user: str = Depends(get_current_user),
):
    """Calculate current habit score."""
    require_self(auth_user, user_id)
    client = get_client()
    trades = get_trades(client, user_id, since=since, until=until)
    trade_dicts = [t.model_dump() for t in trades]

    emotions = get_emotions(client, user_id, since=since)
    emotion_dicts = [e.model_dump() for e in emotions]

    settings = get_user_settings(client, user_id)
    settings_dict = settings.model_dump() if settings else {}

    result = calculate_habit_score(
        trade_dicts, emotion_dicts, settings_dict,
        account_balance=account_balance,
    )
    return HabitScoreResponse(**result.to_dict())


# ---------------------------------------------------------------------------
# Emotion Analysis
# ---------------------------------------------------------------------------

class EmotionStatsResponse(BaseModel):
    stats_by_emotion: dict[str, Any]
    best_emotion: dict[str, Any] | None
    worst_emotion: dict[str, Any] | None
    emotional_streaks: list[dict[str, Any]]


@router.get("/{user_id}/emotions", response_model=EmotionStatsResponse)
def get_emotion_analysis(
    user_id: str,
    since: date | None = Query(None),
    broker_timezone: str | None = Query(None),
    auth_user: str = Depends(get_current_user),
):
    """Emotion correlation analysis."""
    require_self(auth_user, user_id)
    client = get_client()
    trades = get_trades(client, user_id, since=since)
    trade_dicts = [t.model_dump() for t in trades]

    emotions = get_emotions(client, user_id, since=since)
    emotion_dicts = [e.model_dump() for e in emotions]

    result = emotion_summary(
        trade_dicts, emotion_dicts,
        broker_timezone=broker_timezone or DEFAULT_BROKER_TIMEZONE,
    )

    return EmotionStatsResponse(
        stats_by_emotion=result["stats_by_emotion"],
        best_emotion=result["best_emotion"],
        worst_emotion=result["worst_emotion"],
        emotional_streaks=result["emotional_streaks"],
    )


# ---------------------------------------------------------------------------
# Log Emotion
# ---------------------------------------------------------------------------

class LogEmotionRequest(BaseModel):
    emotion: EmotionType
    trade_id: str | None = None
    context: Literal["pre_trade", "post_trade", "check_in"] | None = None


class LogEmotionResponse(BaseModel):
    id: str
    emotion: str
    trade_id: str | None


@router.post("/{user_id}/emotions", response_model=LogEmotionResponse)
def log_emotion(user_id: str, body: LogEmotionRequest, auth_user: str = Depends(get_current_user)):
    """Log an emotion for a trade or check-in."""
    require_self(auth_user, user_id)
    client = get_client()
    emotion = save_emotion(client, EmotionCreate(
        user_id=user_id,
        trade_id=body.trade_id,
        emotion=body.emotion,
        context=body.context,
    ))
    return LogEmotionResponse(
        id=emotion.id,
        emotion=emotion.emotion,
        trade_id=emotion.trade_id,
    )


# ---------------------------------------------------------------------------
# Pre-trade Risk Check
# ---------------------------------------------------------------------------

class RiskCheckRequest(BaseModel):
    symbol: str
    direction: Literal["buy", "sell"]
    lot: float = Field(gt=0)
    stop_loss: float | None = None
    open_price: float
    account_balance: float = Field(gt=0)


class RiskCheckResponse(BaseModel):
    all_passed: bool
    passed: int
    total: int
    items: list[dict[str, Any]]
    warnings: list[str]


@router.post("/{user_id}/risk-check", response_model=RiskCheckResponse)
def pre_trade_risk_check(
    user_id: str,
    body: RiskCheckRequest,
    broker_timezone: str | None = Query(None),
    auth_user: str = Depends(get_current_user),
):
    """Run pre-trade validation checklist."""
    require_self(auth_user, user_id)
    client = get_client()
    settings = get_user_settings(client, user_id)
    settings_dict = settings.model_dump() if settings else {}

    today_trades = get_trades_today(
        client, user_id, broker_timezone=broker_timezone,
    )
    today_dicts = [t.model_dump() for t in today_trades]

    result: ChecklistResult = run_pre_trade_check(
        symbol=body.symbol,
        direction=body.direction,
        lot=body.lot,
        stop_loss=body.stop_loss,
        open_price=body.open_price,
        account_balance=body.account_balance,
        settings=settings_dict,
        today_trades=today_dicts,
    )

    return RiskCheckResponse(**result.to_dict())
