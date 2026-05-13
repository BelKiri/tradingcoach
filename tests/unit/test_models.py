"""Tests for Pydantic models — validation and serialization."""

from datetime import date, datetime, time

import pytest
from pydantic import ValidationError

from tradecoach.db.models import (
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
# User models
# ---------------------------------------------------------------------------

class TestUserModels:
    def test_user_create_minimal(self):
        u = UserCreate(id="abc-123")
        assert u.id == "abc-123"
        assert u.timezone == "UTC"
        assert u.telegram_id is None

    def test_user_create_full(self):
        u = UserCreate(
            id="abc-123", telegram_id=12345678,
            username="trader1", email="t@example.com", timezone="Europe/London",
        )
        assert u.telegram_id == 12345678
        assert u.timezone == "Europe/London"

    def test_user_defaults(self):
        u = User(id="abc-123")
        assert u.tier == "free"
        assert u.timezone == "UTC"

    def test_user_update_partial(self):
        u = UserUpdate(tier="pro")
        d = u.model_dump(exclude_none=True)
        assert d == {"tier": "pro"}

    def test_user_update_empty(self):
        u = UserUpdate()
        d = u.model_dump(exclude_none=True)
        assert d == {}

    def test_user_invalid_tier(self):
        with pytest.raises(ValidationError):
            User(id="x", tier="premium")


# ---------------------------------------------------------------------------
# Trade models
# ---------------------------------------------------------------------------

class TestTradeModels:
    def test_trade_create_minimal(self):
        t = TradeCreate(
            user_id="u1", symbol="EURUSD", direction="buy", lot=0.10,
        )
        assert t.source == "csv"
        assert t.commission == 0.0
        assert t.swap == 0.0

    def test_trade_create_full(self):
        t = TradeCreate(
            user_id="u1", source="telegram", ticket=12345,
            symbol="GBPJPY", direction="sell", lot=0.50,
            open_price=188.500, close_price=188.250,
            stop_loss=189.000, take_profit=188.000,
            profit_pips=25.0, profit_money=50.0,
            commission=-1.40, swap=-0.32,
            opened_at=datetime(2024, 1, 15, 10, 0),
            closed_at=datetime(2024, 1, 15, 14, 0),
            followed_plan=True, moved_stop=False,
            notes="Good setup",
        )
        assert t.ticket == 12345
        assert t.profit_money == 50.0

    def test_trade_lot_must_be_positive(self):
        with pytest.raises(ValidationError):
            TradeCreate(user_id="u1", symbol="EURUSD", direction="buy", lot=0)

    def test_trade_lot_negative_rejected(self):
        with pytest.raises(ValidationError):
            TradeCreate(user_id="u1", symbol="EURUSD", direction="buy", lot=-0.1)

    def test_trade_invalid_direction(self):
        with pytest.raises(ValidationError):
            TradeCreate(user_id="u1", symbol="EURUSD", direction="long", lot=0.1)

    def test_trade_invalid_source(self):
        with pytest.raises(ValidationError):
            TradeCreate(user_id="u1", symbol="EURUSD", direction="buy",
                        lot=0.1, source="manual")

    def test_trade_model_has_id(self):
        t = Trade(
            id="t-1", user_id="u1", symbol="EURUSD",
            direction="buy", lot=0.10,
        )
        assert t.id == "t-1"

    def test_trade_serialization(self):
        t = TradeCreate(
            user_id="u1", symbol="EURUSD", direction="buy", lot=0.10,
            opened_at=datetime(2024, 1, 15, 10, 0),
        )
        d = t.model_dump()
        assert d["user_id"] == "u1"
        assert d["opened_at"] == datetime(2024, 1, 15, 10, 0)
        assert d["stop_loss"] is None


# ---------------------------------------------------------------------------
# Emotion models
# ---------------------------------------------------------------------------

class TestEmotionModels:
    def test_emotion_create(self):
        e = EmotionCreate(user_id="u1", emotion="calm")
        assert e.trade_id is None
        assert e.context is None

    def test_emotion_create_full(self):
        e = EmotionCreate(
            user_id="u1", trade_id="t-1",
            emotion="revenge", context="post_trade",
        )
        assert e.emotion == "revenge"
        assert e.context == "post_trade"

    def test_emotion_invalid_value(self):
        with pytest.raises(ValidationError):
            EmotionCreate(user_id="u1", emotion="happy")

    def test_emotion_invalid_context(self):
        with pytest.raises(ValidationError):
            EmotionCreate(user_id="u1", emotion="calm", context="during_trade")

    def test_all_valid_emotions(self):
        for em in ("calm", "confident", "fear", "boredom", "revenge"):
            e = EmotionCreate(user_id="u1", emotion=em)
            assert e.emotion == em

    def test_all_valid_contexts(self):
        for ctx in ("pre_trade", "post_trade", "check_in"):
            e = EmotionCreate(user_id="u1", emotion="calm", context=ctx)
            assert e.context == ctx

    def test_emotion_model_has_id(self):
        e = Emotion(id="e-1", user_id="u1", emotion="calm")
        assert e.id == "e-1"


# ---------------------------------------------------------------------------
# UserSettings models
# ---------------------------------------------------------------------------

class TestUserSettingsModels:
    def test_settings_defaults(self):
        s = UserSettingsCreate(user_id="u1")
        assert s.max_risk_pct == 2.0
        assert s.max_trades_per_day == 5
        assert s.watchlist == []
        assert s.preferred_sessions == []
        assert s.briefing_time == time(7, 0)

    def test_settings_custom(self):
        s = UserSettingsCreate(
            user_id="u1",
            max_risk_pct=1.5,
            max_trades_per_day=3,
            watchlist=["EURUSD", "GBPUSD"],
            preferred_sessions=["London", "New York"],
            briefing_time=time(8, 30),
            strategy_name="ICT",
            strategy_rules="Only trade during killzones",
        )
        assert s.max_risk_pct == 1.5
        assert s.watchlist == ["EURUSD", "GBPUSD"]
        assert s.strategy_name == "ICT"

    def test_settings_update_partial(self):
        u = UserSettingsUpdate(max_risk_pct=1.0)
        d = u.model_dump(exclude_none=True)
        assert d == {"max_risk_pct": 1.0}

    def test_settings_update_empty(self):
        u = UserSettingsUpdate()
        d = u.model_dump(exclude_none=True)
        assert d == {}

    def test_settings_serialization_time(self):
        s = UserSettingsCreate(user_id="u1", briefing_time=time(6, 45))
        d = s.model_dump()
        assert d["briefing_time"] == time(6, 45)

    def test_settings_model_timestamps(self):
        s = UserSettings(
            user_id="u1",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 2),
        )
        assert s.created_at == datetime(2024, 1, 1)


# ---------------------------------------------------------------------------
# HabitScore models
# ---------------------------------------------------------------------------

class TestHabitScoreModels:
    def test_habit_score_create(self):
        h = HabitScoreCreate(
            user_id="u1", score=75,
            period_start=date(2024, 1, 8),
            period_end=date(2024, 1, 14),
        )
        assert h.score == 75
        assert h.plan_adherence is None

    def test_habit_score_full(self):
        h = HabitScoreCreate(
            user_id="u1", score=85,
            plan_adherence=90.0,
            emotional_stability=80.0,
            risk_discipline=95.0,
            consistency=70.0,
            journal_completion=85.0,
            period_start=date(2024, 1, 8),
            period_end=date(2024, 1, 14),
        )
        assert h.plan_adherence == 90.0

    def test_score_min_boundary(self):
        h = HabitScoreCreate(
            user_id="u1", score=0,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 7),
        )
        assert h.score == 0

    def test_score_max_boundary(self):
        h = HabitScoreCreate(
            user_id="u1", score=100,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 7),
        )
        assert h.score == 100

    def test_score_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            HabitScoreCreate(
                user_id="u1", score=-1,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 7),
            )

    def test_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            HabitScoreCreate(
                user_id="u1", score=101,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 7),
            )

    def test_habit_score_model_has_id(self):
        h = HabitScore(
            id="h-1", user_id="u1", score=50,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 7),
        )
        assert h.id == "h-1"

    def test_serialization_dates(self):
        h = HabitScoreCreate(
            user_id="u1", score=50,
            period_start=date(2024, 1, 8),
            period_end=date(2024, 1, 14),
        )
        d = h.model_dump()
        assert d["period_start"] == date(2024, 1, 8)
        assert d["period_end"] == date(2024, 1, 14)


# ---------------------------------------------------------------------------
# Cross-model: model_dump for DB insertion
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_trade_create_dump_has_all_fields(self):
        t = TradeCreate(
            user_id="u1", symbol="EURUSD", direction="buy", lot=0.10,
        )
        d = t.model_dump()
        assert "user_id" in d
        assert "symbol" in d
        assert "direction" in d
        assert "lot" in d
        assert "source" in d
        assert "commission" in d
        assert "swap" in d

    def test_user_update_excludes_none(self):
        u = UserUpdate(tier="pro")
        d = u.model_dump(exclude_none=True)
        assert "tier" in d
        assert "username" not in d

    def test_emotion_create_dump(self):
        e = EmotionCreate(
            user_id="u1", trade_id="t-1",
            emotion="fear", context="pre_trade",
        )
        d = e.model_dump()
        assert d["emotion"] == "fear"
        assert d["context"] == "pre_trade"
