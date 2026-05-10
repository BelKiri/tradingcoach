"""Tests for habit_scorer.py — Trading Habit Score (0-100)."""

import pytest

from tradecoach.services.habit_scorer import (
    WEIGHTS,
    HabitScore,
    calculate_habit_score,
    _plan_adherence,
    _emotional_stability,
    _risk_discipline,
    _consistency,
    _journal_completion,
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
    open_price=1.08750,
    stop_loss=1.08500,
    profit_money=20.0,
    followed_plan=True,
    moved_stop=False,
):
    return {
        "id": ticket,
        "ticket": ticket,
        "symbol": symbol,
        "direction": direction,
        "lot": lot,
        "open_price": open_price,
        "close_price": 1.08950,
        "stop_loss": stop_loss,
        "take_profit": 1.09000,
        "profit_money": profit_money,
        "commission": -0.70,
        "swap": 0.0,
        "opened_at": "2024-01-15T10:00:00",
        "closed_at": "2024-01-15T14:00:00",
        "followed_plan": followed_plan,
        "moved_stop": moved_stop,
        "source": "csv",
    }


def _emotion(trade_id, emotion="calm", context="post_trade"):
    return {
        "trade_id": trade_id,
        "emotion": emotion,
        "context": context,
    }


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

class TestWeights:
    def test_weights_sum_to_one(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_all_sub_scores_have_weight(self):
        expected = {
            "plan_adherence", "emotional_stability",
            "risk_discipline", "consistency", "journal_completion",
        }
        assert set(WEIGHTS.keys()) == expected


# ---------------------------------------------------------------------------
# Plan adherence
# ---------------------------------------------------------------------------

class TestPlanAdherence:
    def test_all_followed(self):
        trades = [_trade(ticket=i, followed_plan=True) for i in range(5)]
        assert _plan_adherence(trades) == 100.0

    def test_none_followed(self):
        trades = [_trade(ticket=i, followed_plan=False) for i in range(3)]
        assert _plan_adherence(trades) == 0.0

    def test_mixed(self):
        trades = [
            _trade(ticket=1, followed_plan=True),
            _trade(ticket=2, followed_plan=False),
            _trade(ticket=3, followed_plan=True),
            _trade(ticket=4, followed_plan=True),
        ]
        assert _plan_adherence(trades) == 75.0

    def test_none_value_counts_as_not_followed(self):
        trades = [
            _trade(ticket=1, followed_plan=True),
            _trade(ticket=2, followed_plan=None),
        ]
        assert _plan_adherence(trades) == 50.0

    def test_empty(self):
        assert _plan_adherence([]) == 0.0


# ---------------------------------------------------------------------------
# Emotional stability
# ---------------------------------------------------------------------------

class TestEmotionalStability:
    def test_all_calm(self):
        trades = [_trade(ticket=i) for i in range(3)]
        emotions = [_emotion(i, "calm") for i in range(3)]
        assert _emotional_stability(trades, emotions) == 100.0

    def test_all_confident(self):
        trades = [_trade(ticket=1)]
        emotions = [_emotion(1, "confident")]
        assert _emotional_stability(trades, emotions) == 100.0

    def test_mixed_emotions(self):
        trades = [_trade(ticket=i) for i in range(4)]
        emotions = [
            _emotion(0, "calm"),
            _emotion(1, "confident"),
            _emotion(2, "fear"),
            _emotion(3, "revenge"),
        ]
        assert _emotional_stability(trades, emotions) == 50.0

    def test_no_emotions_logged(self):
        trades = [_trade(ticket=1)]
        assert _emotional_stability(trades, []) == 0.0

    def test_emotion_for_unknown_trade_ignored(self):
        trades = [_trade(ticket=1)]
        emotions = [_emotion(999, "calm")]  # different trade_id
        assert _emotional_stability(trades, emotions) == 0.0

    def test_multiple_emotions_per_trade(self):
        trades = [_trade(ticket=1)]
        emotions = [
            _emotion(1, "fear"),
            _emotion(1, "calm"),  # at least one stable → counts
        ]
        assert _emotional_stability(trades, emotions) == 100.0

    def test_empty(self):
        assert _emotional_stability([], []) == 0.0


# ---------------------------------------------------------------------------
# Risk discipline
# ---------------------------------------------------------------------------

class TestRiskDiscipline:
    def test_all_within_risk(self):
        # SL 25 pips, 0.10 lot, $10K balance → risk = 25*1 / 10000 * 100 = 0.25%
        trades = [_trade(ticket=i) for i in range(3)]
        settings = {"max_risk_pct": 2.0}
        result = _risk_discipline(trades, settings, 10_000)
        assert result == 100.0

    def test_exceeds_risk(self):
        # Huge lot, tight balance
        trades = [_trade(ticket=1, lot=2.0, stop_loss=1.08000)]
        # SL = 75 pips, lot 2.0 → risk = 75 * 20 / 1000 * 100 = 150%
        settings = {"max_risk_pct": 2.0}
        result = _risk_discipline(trades, settings, 1_000)
        assert result == 0.0

    def test_no_stop_loss_is_violation(self):
        trades = [_trade(ticket=1, stop_loss=None)]
        settings = {"max_risk_pct": 2.0}
        result = _risk_discipline(trades, settings, 10_000)
        assert result == 0.0

    def test_mixed_compliance(self):
        trades = [
            _trade(ticket=1, lot=0.10, stop_loss=1.08500),  # OK
            _trade(ticket=2, stop_loss=None),  # violation
        ]
        settings = {"max_risk_pct": 2.0}
        result = _risk_discipline(trades, settings, 10_000)
        assert result == 50.0

    def test_no_settings_checks_sl_only(self):
        trades = [
            _trade(ticket=1, stop_loss=1.08500),  # has SL → OK
            _trade(ticket=2, stop_loss=None),  # no SL → violation
        ]
        result = _risk_discipline(trades, None, None)
        assert result == 50.0

    def test_jpy_pair_risk(self):
        trades = [_trade(
            ticket=1, symbol="USDJPY", direction="buy",
            open_price=148.250, stop_loss=147.800, lot=0.10,
        )]
        # SL = 45 pips, lot 0.1 → risk = 45 * 1.0 / 10000 * 100 = 0.45%
        settings = {"max_risk_pct": 2.0}
        result = _risk_discipline(trades, settings, 10_000)
        assert result == 100.0

    def test_empty(self):
        assert _risk_discipline([], None, None) == 0.0


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------

class TestConsistency:
    def test_single_pair(self):
        trades = [_trade(ticket=i, symbol="EURUSD") for i in range(5)]
        assert _consistency(trades) == 100.0

    def test_two_pairs(self):
        trades = [
            _trade(ticket=1, symbol="EURUSD"),
            _trade(ticket=2, symbol="GBPUSD"),
        ]
        assert _consistency(trades) == 100.0

    def test_three_pairs(self):
        trades = [
            _trade(ticket=1, symbol="EURUSD"),
            _trade(ticket=2, symbol="GBPUSD"),
            _trade(ticket=3, symbol="USDJPY"),
        ]
        result = _consistency(trades)
        assert result == 85.0  # base for 3 unique

    def test_many_pairs_penalized(self):
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD"]
        trades = [_trade(ticket=i, symbol=s) for i, s in enumerate(symbols)]
        result = _consistency(trades)
        assert result < 55.0  # heavily penalized

    def test_concentration_bonus(self):
        # 8 trades on EURUSD, 1 on GBPUSD, 1 on USDJPY → 3 pairs but concentrated
        trades = (
            [_trade(ticket=i, symbol="EURUSD") for i in range(8)]
            + [_trade(ticket=8, symbol="GBPUSD")]
            + [_trade(ticket=9, symbol="USDJPY")]
        )
        result = _consistency(trades)
        # base=85 for 3 pairs, top_freq=0.8 → bonus = (0.8-0.5)*20 = 6
        assert result == 91.0

    def test_empty(self):
        assert _consistency([]) == 0.0

    def test_score_capped_at_100(self):
        # 1 pair, high concentration — should not exceed 100
        trades = [_trade(ticket=i, symbol="EURUSD") for i in range(20)]
        assert _consistency(trades) == 100.0


# ---------------------------------------------------------------------------
# Journal completion
# ---------------------------------------------------------------------------

class TestJournalCompletion:
    def test_fully_journaled(self):
        trades = [
            _trade(ticket=1, followed_plan=True),
            _trade(ticket=2, followed_plan=False),
        ]
        emotions = [_emotion(1, "calm"), _emotion(2, "fear")]
        assert _journal_completion(trades, emotions) == 100.0

    def test_no_journal(self):
        trades = [_trade(ticket=1, followed_plan=None)]
        assert _journal_completion(trades, []) == 0.0

    def test_emotion_but_no_plan_answer(self):
        trades = [_trade(ticket=1, followed_plan=None)]
        emotions = [_emotion(1, "calm")]
        # Need BOTH plan answer and emotion
        assert _journal_completion(trades, emotions) == 0.0

    def test_plan_answer_but_no_emotion(self):
        trades = [_trade(ticket=1, followed_plan=True)]
        assert _journal_completion(trades, []) == 0.0

    def test_partial(self):
        trades = [
            _trade(ticket=1, followed_plan=True),
            _trade(ticket=2, followed_plan=True),
            _trade(ticket=3, followed_plan=None),
        ]
        emotions = [_emotion(1, "calm")]  # only trade 1 has emotion
        # Trade 1: plan=True, emotion=yes → journaled
        # Trade 2: plan=True, emotion=no → not journaled
        # Trade 3: plan=None → not journaled
        assert _journal_completion(trades, emotions) == pytest.approx(33.33, abs=0.1)

    def test_empty(self):
        assert _journal_completion([], []) == 0.0


# ---------------------------------------------------------------------------
# Full habit score
# ---------------------------------------------------------------------------

class TestCalculateHabitScore:
    def test_returns_habit_score(self):
        trades = [_trade(ticket=1, followed_plan=True)]
        emotions = [_emotion(1, "calm")]
        result = calculate_habit_score(trades, emotions, account_balance=10_000)
        assert isinstance(result, HabitScore)

    def test_perfect_score(self):
        trades = [
            _trade(ticket=i, followed_plan=True, symbol="EURUSD")
            for i in range(5)
        ]
        emotions = [_emotion(i, "calm") for i in range(5)]
        settings = {"max_risk_pct": 2.0}
        result = calculate_habit_score(
            trades, emotions, settings, account_balance=10_000
        )
        assert result.score == 100
        assert result.plan_adherence == 100.0
        assert result.emotional_stability == 100.0
        assert result.risk_discipline == 100.0
        assert result.consistency == 100.0
        assert result.journal_completion == 100.0

    def test_zero_score_empty_trades(self):
        result = calculate_habit_score([], [])
        assert result.score == 0
        assert result.plan_adherence == 0.0

    def test_score_in_range(self):
        trades = [
            _trade(ticket=1, followed_plan=True),
            _trade(ticket=2, followed_plan=False),
            _trade(ticket=3, followed_plan=True, stop_loss=None),
        ]
        emotions = [_emotion(1, "calm"), _emotion(3, "revenge")]
        result = calculate_habit_score(trades, emotions, account_balance=10_000)
        assert 0 <= result.score <= 100

    def test_good_process_bad_pnl(self):
        """Score can be high even with negative P&L — the key differentiator."""
        trades = [
            _trade(ticket=i, followed_plan=True, profit_money=-20.0,
                   symbol="EURUSD")
            for i in range(5)
        ]
        emotions = [_emotion(i, "calm") for i in range(5)]
        settings = {"max_risk_pct": 2.0}
        result = calculate_habit_score(
            trades, emotions, settings, account_balance=10_000
        )
        # All losing trades, but perfect discipline
        assert result.score == 100
        assert result.plan_adherence == 100.0

    def test_bad_process_good_pnl(self):
        """Score can be low even with positive P&L."""
        trades = [
            _trade(
                ticket=i, followed_plan=False, profit_money=100.0,
                stop_loss=None,
                symbol=f"PAIR{i}",  # different symbol each time
            )
            for i in range(6)
        ]
        result = calculate_habit_score(trades, [])
        assert result.score < 50
        assert result.plan_adherence == 0.0
        assert result.risk_discipline == 0.0
        assert result.journal_completion == 0.0

    def test_to_dict(self):
        trades = [_trade(ticket=1, followed_plan=True)]
        emotions = [_emotion(1, "calm")]
        result = calculate_habit_score(trades, emotions, account_balance=10_000)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "score" in d
        assert "plan_adherence" in d
        assert "emotional_stability" in d
        assert "risk_discipline" in d
        assert "consistency" in d
        assert "journal_completion" in d

    def test_weighted_calculation(self):
        """Verify the weighted composite is correct."""
        trades = [_trade(ticket=1, followed_plan=True, symbol="EURUSD")]
        emotions = [_emotion(1, "calm")]
        settings = {"max_risk_pct": 2.0}
        result = calculate_habit_score(
            trades, emotions, settings, account_balance=10_000
        )
        # Manual weighted calculation
        expected = (
            result.plan_adherence * WEIGHTS["plan_adherence"]
            + result.emotional_stability * WEIGHTS["emotional_stability"]
            + result.risk_discipline * WEIGHTS["risk_discipline"]
            + result.consistency * WEIGHTS["consistency"]
            + result.journal_completion * WEIGHTS["journal_completion"]
        )
        assert result.score == round(expected)

    def test_no_settings_still_works(self):
        trades = [_trade(ticket=1, followed_plan=True)]
        emotions = [_emotion(1, "calm")]
        result = calculate_habit_score(trades, emotions)
        assert 0 <= result.score <= 100

    def test_partial_data(self):
        """Some trades journaled, some not, mixed emotions."""
        trades = [
            _trade(ticket=1, followed_plan=True, symbol="EURUSD"),
            _trade(ticket=2, followed_plan=False, symbol="EURUSD"),
            _trade(ticket=3, followed_plan=None, symbol="GBPUSD",
                   stop_loss=None),
        ]
        emotions = [
            _emotion(1, "calm"),
            _emotion(2, "revenge"),
        ]
        settings = {"max_risk_pct": 2.0}
        result = calculate_habit_score(
            trades, emotions, settings, account_balance=10_000
        )

        assert result.plan_adherence == pytest.approx(33.33, abs=0.1)
        assert result.emotional_stability == pytest.approx(33.33, abs=0.1)
        # 2 of 3 have SL and are within risk → 66.67%
        assert result.risk_discipline == pytest.approx(66.67, abs=0.1)
        assert result.consistency == 100.0  # only 2 pairs
        # Trade 1: plan=True + emotion=yes → journaled
        # Trade 2: plan=False + emotion=yes → journaled
        # Trade 3: plan=None → not journaled
        assert result.journal_completion == pytest.approx(66.67, abs=0.1)
