"""Tests for emotion_tracker.py — emotion-performance correlation analysis."""

import pytest

from tradecoach.services.emotion_tracker import (
    ALL_EMOTIONS,
    NEGATIVE_EMOTIONS,
    POSITIVE_EMOTIONS,
    best_emotion,
    detect_emotional_streaks,
    emotion_by_day_of_week,
    emotion_by_hour,
    emotion_by_session,
    emotion_by_symbol,
    emotion_summary,
    stats_by_emotion,
    worst_emotion,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trade(
    *,
    ticket=1,
    symbol="EURUSD",
    direction="buy",
    lot=0.10,
    profit_money=20.0,
    commission=-0.70,
    swap=0.0,
    opened_at="2024-01-15T10:00:00",
    closed_at="2024-01-15T14:00:00",
):
    return {
        "id": ticket,
        "ticket": ticket,
        "symbol": symbol,
        "direction": direction,
        "lot": lot,
        "open_price": 1.08750,
        "close_price": 1.08950,
        "stop_loss": 1.08500,
        "take_profit": 1.09000,
        "profit_money": profit_money,
        "commission": commission,
        "swap": swap,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "source": "csv",
    }


def _emotion(trade_id, emotion="calm", context="post_trade"):
    return {
        "trade_id": trade_id,
        "emotion": emotion,
        "context": context,
    }


# A realistic dataset: 8 trades across emotions, symbols, sessions, days
TRADES = [
    # Mon London, EURUSD, win, calm
    _trade(ticket=1, profit_money=30.0, opened_at="2024-01-15T10:00:00",
           symbol="EURUSD"),
    # Mon NY, GBPUSD, loss, fear
    _trade(ticket=2, profit_money=-25.0, opened_at="2024-01-15T15:00:00",
           symbol="GBPUSD"),
    # Tue Asian, USDJPY, win, confident
    _trade(ticket=3, profit_money=40.0, opened_at="2024-01-16T03:00:00",
           symbol="USDJPY"),
    # Tue London, EURUSD, loss, revenge
    _trade(ticket=4, profit_money=-50.0, opened_at="2024-01-16T11:00:00",
           symbol="EURUSD"),
    # Wed London, EURUSD, win, calm
    _trade(ticket=5, profit_money=20.0, opened_at="2024-01-17T09:30:00",
           symbol="EURUSD"),
    # Wed NY, GBPUSD, loss, boredom
    _trade(ticket=6, profit_money=-15.0, opened_at="2024-01-17T16:00:00",
           symbol="GBPUSD"),
    # Thu London, EURUSD, win, confident
    _trade(ticket=7, profit_money=35.0, opened_at="2024-01-18T10:30:00",
           symbol="EURUSD"),
    # Fri London, GBPUSD, loss, fear
    _trade(ticket=8, profit_money=-20.0, opened_at="2024-01-19T09:00:00",
           symbol="GBPUSD"),
]

EMOTIONS = [
    _emotion(1, "calm"),
    _emotion(2, "fear"),
    _emotion(3, "confident"),
    _emotion(4, "revenge"),
    _emotion(5, "calm"),
    _emotion(6, "boredom"),
    _emotion(7, "confident"),
    _emotion(8, "fear"),
]


# ---------------------------------------------------------------------------
# Stats by emotion
# ---------------------------------------------------------------------------

class TestStatsByEmotion:
    def test_all_emotions_present(self):
        stats = stats_by_emotion(TRADES, EMOTIONS)
        for em in ALL_EMOTIONS:
            assert em in stats

    def test_calm_stats(self):
        stats = stats_by_emotion(TRADES, EMOTIONS)
        calm = stats["calm"]
        assert calm["trades"] == 2
        assert calm["wins"] == 2
        assert calm["win_rate"] == 100.0

    def test_fear_stats(self):
        stats = stats_by_emotion(TRADES, EMOTIONS)
        fear = stats["fear"]
        assert fear["trades"] == 2
        assert fear["wins"] == 0
        assert fear["win_rate"] == 0.0

    def test_confident_stats(self):
        stats = stats_by_emotion(TRADES, EMOTIONS)
        conf = stats["confident"]
        assert conf["trades"] == 2
        assert conf["wins"] == 2
        assert conf["win_rate"] == 100.0

    def test_revenge_stats(self):
        stats = stats_by_emotion(TRADES, EMOTIONS)
        rev = stats["revenge"]
        assert rev["trades"] == 1
        assert rev["losses"] == 1

    def test_boredom_stats(self):
        stats = stats_by_emotion(TRADES, EMOTIONS)
        bor = stats["boredom"]
        assert bor["trades"] == 1
        assert bor["win_rate"] == 0.0

    def test_avg_pnl(self):
        stats = stats_by_emotion(TRADES, EMOTIONS)
        calm = stats["calm"]
        # Trades 1 and 5: (30-0.7) + (20-0.7) = 48.6, avg = 24.3
        assert calm["avg_pnl"] == pytest.approx(24.3, abs=0.1)

    def test_total_pnl(self):
        stats = stats_by_emotion(TRADES, EMOTIONS)
        fear = stats["fear"]
        # Trades 2 and 8: (-25-0.7) + (-20-0.7) = -46.4
        assert fear["total_pnl"] == pytest.approx(-46.4, abs=0.1)

    def test_unused_emotion_has_zero_trades(self):
        trades = [_trade(ticket=1)]
        emotions = [_emotion(1, "calm")]
        stats = stats_by_emotion(trades, emotions)
        assert stats["revenge"]["trades"] == 0
        assert stats["revenge"]["win_rate"] is None

    def test_empty(self):
        stats = stats_by_emotion([], [])
        for em in ALL_EMOTIONS:
            assert stats[em]["trades"] == 0


# ---------------------------------------------------------------------------
# Best / worst emotion
# ---------------------------------------------------------------------------

class TestBestWorstEmotion:
    def test_best_emotion(self):
        result = best_emotion(TRADES, EMOTIONS)
        assert result is not None
        # calm and confident both have 100% win rate
        assert result["emotion"] in ("calm", "confident")
        assert result["win_rate"] == 100.0

    def test_worst_emotion(self):
        result = worst_emotion(TRADES, EMOTIONS)
        assert result is not None
        # fear and boredom both have 0% win rate
        assert result["emotion"] in ("fear", "boredom", "revenge")
        assert result["win_rate"] == 0.0

    def test_best_with_single_emotion(self):
        trades = [_trade(ticket=1, profit_money=10.0)]
        emotions = [_emotion(1, "fear")]
        result = best_emotion(trades, emotions)
        assert result["emotion"] == "fear"

    def test_empty_returns_none(self):
        assert best_emotion([], []) is None
        assert worst_emotion([], []) is None

    def test_no_emotions_returns_none(self):
        trades = [_trade(ticket=1)]
        assert best_emotion(trades, []) is None
        assert worst_emotion(trades, []) is None


# ---------------------------------------------------------------------------
# Emotional streaks
# ---------------------------------------------------------------------------

class TestEmotionalStreaks:
    def test_detects_streak(self):
        trades = [
            _trade(ticket=i, profit_money=-10.0,
                   opened_at=f"2024-01-{15+i}T10:00:00")
            for i in range(1, 5)
        ]
        emotions = [_emotion(i, "fear") for i in range(1, 5)]
        streaks = detect_emotional_streaks(trades, emotions)
        assert len(streaks) == 1
        assert streaks[0]["emotion"] == "fear"
        assert streaks[0]["length"] == 4

    def test_no_streak_below_min(self):
        trades = [
            _trade(ticket=1, opened_at="2024-01-15T10:00:00"),
            _trade(ticket=2, opened_at="2024-01-16T10:00:00"),
        ]
        emotions = [_emotion(1, "fear"), _emotion(2, "fear")]
        streaks = detect_emotional_streaks(trades, emotions)
        assert len(streaks) == 0

    def test_positive_emotion_not_a_streak(self):
        trades = [
            _trade(ticket=i, opened_at=f"2024-01-{15+i}T10:00:00")
            for i in range(1, 5)
        ]
        emotions = [_emotion(i, "calm") for i in range(1, 5)]
        streaks = detect_emotional_streaks(trades, emotions)
        assert len(streaks) == 0  # calm is positive

    def test_mixed_breaks_streak(self):
        trades = [
            _trade(ticket=i, opened_at=f"2024-01-{15+i}T10:00:00")
            for i in range(1, 6)
        ]
        emotions = [
            _emotion(1, "fear"),
            _emotion(2, "fear"),
            _emotion(3, "calm"),  # breaks streak
            _emotion(4, "fear"),
            _emotion(5, "fear"),
        ]
        streaks = detect_emotional_streaks(trades, emotions)
        assert len(streaks) == 0  # neither sub-streak reaches 3

    def test_total_pnl_in_streak(self):
        trades = [
            _trade(ticket=i, profit_money=-10.0, commission=0.0,
                   opened_at=f"2024-01-{15+i}T10:00:00")
            for i in range(1, 4)
        ]
        emotions = [_emotion(i, "revenge") for i in range(1, 4)]
        streaks = detect_emotional_streaks(trades, emotions)
        assert streaks[0]["total_pnl"] == -30.0

    def test_custom_min_streak(self):
        trades = [
            _trade(ticket=i, opened_at=f"2024-01-{15+i}T10:00:00")
            for i in range(1, 3)
        ]
        emotions = [_emotion(i, "boredom") for i in range(1, 3)]
        assert len(detect_emotional_streaks(trades, emotions, min_streak=3)) == 0
        assert len(detect_emotional_streaks(trades, emotions, min_streak=2)) == 1

    def test_multiple_streaks(self):
        trades = [
            _trade(ticket=i, opened_at=f"2024-01-{10+i}T10:00:00")
            for i in range(1, 8)
        ]
        emotions = [
            _emotion(1, "fear"),
            _emotion(2, "fear"),
            _emotion(3, "fear"),
            _emotion(4, "calm"),  # break
            _emotion(5, "boredom"),
            _emotion(6, "boredom"),
            _emotion(7, "boredom"),
        ]
        streaks = detect_emotional_streaks(trades, emotions)
        assert len(streaks) == 2
        assert streaks[0]["emotion"] == "fear"
        assert streaks[1]["emotion"] == "boredom"

    def test_empty(self):
        assert detect_emotional_streaks([], []) == []


# ---------------------------------------------------------------------------
# Correlations: by symbol
# ---------------------------------------------------------------------------

class TestEmotionBySymbol:
    def test_symbols_present(self):
        result = emotion_by_symbol(TRADES, EMOTIONS)
        assert "EURUSD" in result
        assert "GBPUSD" in result

    def test_eurusd_emotions(self):
        result = emotion_by_symbol(TRADES, EMOTIONS)
        eur = result["EURUSD"]
        # Trades 1,4,5,7 → calm, revenge, calm, confident
        assert "calm" in eur
        assert eur["calm"]["trades"] == 2

    def test_win_rate_per_symbol_emotion(self):
        result = emotion_by_symbol(TRADES, EMOTIONS)
        # GBPUSD fear: trades 2,8 → both losses
        gbp_fear = result["GBPUSD"]["fear"]
        assert gbp_fear["win_rate"] == 0.0

    def test_empty(self):
        result = emotion_by_symbol([], [])
        assert result == {}


# ---------------------------------------------------------------------------
# Correlations: by session
# ---------------------------------------------------------------------------

class TestEmotionBySession:
    def test_sessions_present(self):
        result = emotion_by_session(TRADES, EMOTIONS)
        assert "London" in result
        assert "New York" in result
        assert "Asian" in result

    def test_london_emotions(self):
        result = emotion_by_session(TRADES, EMOTIONS)
        london = result["London"]
        # London-only opens: 10:00, 11:00, 09:30 UTC (15:00 UTC → New York first)
        assert sum(data["trades"] for data in london.values()) == 5

    def test_empty(self):
        result = emotion_by_session([], [])
        assert result == {}


# ---------------------------------------------------------------------------
# Correlations: by hour
# ---------------------------------------------------------------------------

class TestEmotionByHour:
    def test_hours_present(self):
        result = emotion_by_hour(TRADES, EMOTIONS, broker_timezone="UTC+0")
        assert 10 in result  # trades at 10:00
        assert 3 in result   # trade at 03:00

    def test_trade_count(self):
        result = emotion_by_hour(TRADES, EMOTIONS, broker_timezone="UTC+0")
        # Hour 10: trades 1 (calm) and 7 (confident, at 10:30)
        hour_10 = result[10]
        total = sum(data["trades"] for data in hour_10.values())
        assert total == 2

    def test_empty(self):
        result = emotion_by_hour([], [])
        assert result == {}


# ---------------------------------------------------------------------------
# Correlations: by day of week
# ---------------------------------------------------------------------------

class TestEmotionByDayOfWeek:
    def test_days_present(self):
        result = emotion_by_day_of_week(TRADES, EMOTIONS)
        assert "Monday" in result
        assert "Tuesday" in result

    def test_monday_emotions(self):
        result = emotion_by_day_of_week(TRADES, EMOTIONS)
        mon = result["Monday"]
        # Trade 1 (calm) and 2 (fear)
        assert "calm" in mon
        assert "fear" in mon

    def test_empty(self):
        result = emotion_by_day_of_week([], [])
        assert result == {}


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestEmotionSummary:
    def test_returns_all_keys(self):
        result = emotion_summary(TRADES, EMOTIONS)
        expected_keys = {
            "stats_by_emotion", "best_emotion", "worst_emotion",
            "emotional_streaks", "by_symbol", "by_session",
            "by_hour", "by_day_of_week",
        }
        assert set(result.keys()) == expected_keys

    def test_empty(self):
        result = emotion_summary([], [])
        assert result["best_emotion"] is None
        assert result["worst_emotion"] is None
        assert result["emotional_streaks"] == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_trade_without_emotion_excluded(self):
        trades = [_trade(ticket=1), _trade(ticket=2)]
        emotions = [_emotion(1, "calm")]  # only trade 1 has emotion
        stats = stats_by_emotion(trades, emotions)
        assert stats["calm"]["trades"] == 1

    def test_emotion_without_matching_trade_ignored(self):
        trades = [_trade(ticket=1)]
        emotions = [_emotion(999, "calm")]
        stats = stats_by_emotion(trades, emotions)
        assert stats["calm"]["trades"] == 0

    def test_multiple_emotions_per_trade_prefers_post_trade(self):
        trades = [_trade(ticket=1)]
        emotions = [
            _emotion(1, "fear", context="pre_trade"),
            _emotion(1, "calm", context="post_trade"),
        ]
        stats = stats_by_emotion(trades, emotions)
        assert stats["calm"]["trades"] == 1
        assert stats["fear"]["trades"] == 0

    def test_zero_trade_id_handled(self):
        """Trade ID 0 should not be treated as falsy."""
        trades = [_trade(ticket=0, profit_money=10.0)]
        emotions = [_emotion(0, "calm")]
        stats = stats_by_emotion(trades, emotions)
        assert stats["calm"]["trades"] == 1

    def test_constants(self):
        assert set(ALL_EMOTIONS) == POSITIVE_EMOTIONS | NEGATIVE_EMOTIONS
        assert len(ALL_EMOTIONS) == 5
