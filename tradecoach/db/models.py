"""
Pydantic models matching the Supabase database schema.

Used for request/response validation and as the contract between
the API layer, services, and database queries.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    id: str  # UUID from Supabase Auth
    telegram_id: int | None = None
    username: str | None = None
    email: str | None = None
    timezone: str = "UTC"


class UserUpdate(BaseModel):
    telegram_id: int | None = None
    username: str | None = None
    email: str | None = None
    tier: Literal["free", "pro"] | None = None
    timezone: str | None = None


class User(BaseModel):
    id: str
    telegram_id: int | None = None
    username: str | None = None
    email: str | None = None
    tier: Literal["free", "pro"] = "free"
    timezone: str = "UTC"
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class AccountCreate(BaseModel):
    user_id: str
    name: str
    broker: str | None = None
    starting_balance: float | None = None
    broker_timezone: str = "UTC+2"


class Account(AccountCreate):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

class TradeCreate(BaseModel):
    user_id: str
    account_id: str | None = None
    source: Literal["csv", "excel", "telegram", "api"] = "csv"
    broker_source: str | None = None
    ticket: int | None = None
    symbol: str
    direction: Literal["buy", "sell"]
    lot: float = Field(gt=0)
    open_price: float | None = None
    close_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    profit_pips: float | None = None
    profit_money: float | None = None
    commission: float = 0.0
    swap: float = 0.0
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    followed_plan: bool | None = None
    moved_stop: bool | None = None
    notes: str | None = None


class Trade(TradeCreate):
    id: str
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Emotions
# ---------------------------------------------------------------------------

EMOTION_VALUES = ("calm", "confident", "fear", "boredom", "revenge")
EMOTION_CONTEXTS = ("pre_trade", "post_trade", "check_in")

EmotionType = Literal["calm", "confident", "fear", "boredom", "revenge"]
EmotionContext = Literal["pre_trade", "post_trade", "check_in"]


class EmotionCreate(BaseModel):
    user_id: str
    trade_id: str | None = None
    emotion: EmotionType
    context: EmotionContext | None = None


class Emotion(EmotionCreate):
    id: str
    logged_at: datetime | None = None


# ---------------------------------------------------------------------------
# User Settings
# ---------------------------------------------------------------------------

class UserSettingsCreate(BaseModel):
    user_id: str
    max_risk_pct: float = 2.0
    max_trades_per_day: int = 5
    watchlist: list[str] = Field(default_factory=list)
    preferred_sessions: list[str] = Field(default_factory=list)
    briefing_time: time = time(7, 0)
    strategy_name: str | None = None
    strategy_rules: str | None = None
    account_balance: float | None = None
    broker_name: str | None = None


class UserSettingsUpdate(BaseModel):
    max_risk_pct: float | None = None
    max_trades_per_day: int | None = None
    watchlist: list[str] | None = None
    preferred_sessions: list[str] | None = None
    briefing_time: time | None = None
    strategy_name: str | None = None
    strategy_rules: str | None = None
    account_balance: float | None = None
    broker_name: str | None = None


class UserSettings(UserSettingsCreate):
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Habit Scores
# ---------------------------------------------------------------------------

class HabitScoreCreate(BaseModel):
    user_id: str
    score: int = Field(ge=0, le=100)
    plan_adherence: float | None = None
    emotional_stability: float | None = None
    risk_discipline: float | None = None
    consistency: float | None = None
    journal_completion: float | None = None
    period_start: date
    period_end: date


class HabitScore(HabitScoreCreate):
    id: str
    created_at: datetime | None = None
