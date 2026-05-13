"""Tests for risk_checker.py — pre-trade validation."""

import pytest

from tradecoach.services.risk_checker import (
    CheckItem,
    ChecklistResult,
    calculate_risk,
    run_pre_trade_check,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "max_risk_pct": 2.0,
    "max_trades_per_day": 5,
    "watchlist": ["EURUSD", "GBPUSD", "USDJPY"],
}


def _today_trade(
    *,
    ticket=1,
    profit_money=20.0,
    commission=-0.70,
    swap=0.0,
    closed_at="2024-01-15T14:00:00",
):
    return {
        "ticket": ticket,
        "symbol": "EURUSD",
        "direction": "buy",
        "lot": 0.10,
        "profit_money": profit_money,
        "commission": commission,
        "swap": swap,
        "opened_at": "2024-01-15T10:00:00",
        "closed_at": closed_at,
    }


_SAMPLE_TRADES = [
    {
        "ticket": 100, "symbol": "EURUSD", "direction": "buy", "lot": 0.10,
        "open_price": 1.08750, "close_price": 1.08950, "profit_money": 20.0,
        "commission": 0.0, "swap": 0.0,
    },
]


def _check(**overrides):
    """Run a pre-trade check with sensible defaults."""
    params = {
        "symbol": "EURUSD",
        "direction": "buy",
        "lot": 0.10,
        "stop_loss": 1.08500,
        "open_price": 1.08750,
        "account_balance": 10_000,
        "settings": DEFAULT_SETTINGS,
        "today_trades": [],
        "all_trades": _SAMPLE_TRADES,
    }
    params.update(overrides)
    return run_pre_trade_check(**params)


# ---------------------------------------------------------------------------
# ChecklistResult structure
# ---------------------------------------------------------------------------

class TestChecklistResult:
    def test_all_passed(self):
        result = _check()
        assert result.all_passed is True

    def test_has_five_checks(self):
        result = _check()
        assert result.total_count == 5

    def test_to_dict(self):
        result = _check()
        d = result.to_dict()
        assert "all_passed" in d
        assert "passed" in d
        assert "total" in d
        assert "items" in d
        assert "warnings" in d
        assert d["total"] == 5

    def test_warnings_empty_when_all_pass(self):
        result = _check()
        assert result.warnings == []

    def test_rules_present(self):
        result = _check()
        rules = {item.rule for item in result.items}
        assert rules == {"risk_size", "stop_loss", "daily_limit",
                         "watchlist", "losing_streak"}


# ---------------------------------------------------------------------------
# Risk size check
# ---------------------------------------------------------------------------

class TestRiskSize:
    def test_within_limit(self):
        result = _check(lot=0.10, stop_loss=1.08500, open_price=1.08750)
        risk_item = _find(result, "risk_size")
        assert risk_item.passed is True
        assert "within" in risk_item.message

    def test_exceeds_limit(self):
        # 2.0 lot, 75 pips SL → $1500 risk on $10K = 15%
        result = _check(lot=2.0, stop_loss=1.08000, open_price=1.08750)
        risk_item = _find(result, "risk_size")
        assert risk_item.passed is False
        assert "exceeds" in risk_item.message

    def test_no_stop_loss_fails_risk(self):
        result = _check(stop_loss=None)
        risk_item = _find(result, "risk_size")
        assert risk_item.passed is False
        assert "Cannot calculate" in risk_item.message

    def test_custom_max_risk(self):
        settings = {**DEFAULT_SETTINGS, "max_risk_pct": 1.0}
        # 0.10 lot, 25 pips → $25 on $10K = 0.25% → OK at 1%
        result = _check(settings=settings)
        risk_item = _find(result, "risk_size")
        assert risk_item.passed is True

    def test_zero_balance_fails(self):
        result = _check(account_balance=0)
        risk_item = _find(result, "risk_size")
        assert risk_item.passed is False


# ---------------------------------------------------------------------------
# Stop loss check
# ---------------------------------------------------------------------------

class TestStopLoss:
    def test_sl_set_passes(self):
        result = _check(stop_loss=1.08500)
        sl_item = _find(result, "stop_loss")
        assert sl_item.passed is True

    def test_no_sl_fails(self):
        result = _check(stop_loss=None)
        sl_item = _find(result, "stop_loss")
        assert sl_item.passed is False
        assert "No stop loss" in sl_item.message


# ---------------------------------------------------------------------------
# Daily trade count
# ---------------------------------------------------------------------------

class TestDailyLimit:
    def test_under_limit(self):
        trades = [_today_trade(ticket=i) for i in range(3)]
        result = _check(today_trades=trades)
        item = _find(result, "daily_limit")
        assert item.passed is True
        assert "4 of 5" in item.message

    def test_at_limit(self):
        trades = [_today_trade(ticket=i) for i in range(5)]
        result = _check(today_trades=trades)
        item = _find(result, "daily_limit")
        assert item.passed is False
        assert "limit reached" in item.message

    def test_over_limit(self):
        trades = [_today_trade(ticket=i) for i in range(7)]
        result = _check(today_trades=trades)
        item = _find(result, "daily_limit")
        assert item.passed is False

    def test_no_trades_yet(self):
        result = _check(today_trades=[])
        item = _find(result, "daily_limit")
        assert item.passed is True
        assert "1 of 5" in item.message

    def test_custom_max_trades(self):
        settings = {**DEFAULT_SETTINGS, "max_trades_per_day": 3}
        trades = [_today_trade(ticket=i) for i in range(3)]
        result = _check(settings=settings, today_trades=trades)
        item = _find(result, "daily_limit")
        assert item.passed is False


# ---------------------------------------------------------------------------
# Watchlist check
# ---------------------------------------------------------------------------

class TestWatchlist:
    def test_in_watchlist(self):
        result = _check(symbol="EURUSD")
        item = _find(result, "watchlist")
        assert item.passed is True

    def test_not_in_watchlist(self):
        result = _check(symbol="AUDNZD")
        item = _find(result, "watchlist")
        assert item.passed is False
        assert "NOT in your watchlist" in item.message

    def test_case_insensitive(self):
        result = _check(symbol="eurusd")
        item = _find(result, "watchlist")
        assert item.passed is True

    def test_empty_watchlist_passes_all(self):
        settings = {**DEFAULT_SETTINGS, "watchlist": []}
        result = _check(symbol="XAUUSD", settings=settings)
        item = _find(result, "watchlist")
        assert item.passed is True
        assert "No watchlist" in item.message

    def test_no_watchlist_key_passes(self):
        settings = {"max_risk_pct": 2.0, "max_trades_per_day": 5}
        result = _check(symbol="ANYTHING", settings=settings)
        item = _find(result, "watchlist")
        assert item.passed is True


# ---------------------------------------------------------------------------
# Losing streak detection
# ---------------------------------------------------------------------------

class TestLosingStreak:
    def test_no_trades_no_streak(self):
        result = _check(today_trades=[])
        item = _find(result, "losing_streak")
        assert item.passed is True
        assert "Fresh start" in item.message

    def test_one_loss_no_streak(self):
        trades = [_today_trade(ticket=1, profit_money=-20.0)]
        result = _check(today_trades=trades)
        item = _find(result, "losing_streak")
        assert item.passed is True
        assert "1 consecutive" in item.message

    def test_two_losses_no_streak(self):
        trades = [
            _today_trade(ticket=1, profit_money=-20.0, closed_at="2024-01-15T11:00:00"),
            _today_trade(ticket=2, profit_money=-15.0, closed_at="2024-01-15T13:00:00"),
        ]
        result = _check(today_trades=trades)
        item = _find(result, "losing_streak")
        assert item.passed is True

    def test_three_losses_triggers_streak(self):
        trades = [
            _today_trade(ticket=1, profit_money=-20.0, closed_at="2024-01-15T11:00:00"),
            _today_trade(ticket=2, profit_money=-15.0, closed_at="2024-01-15T13:00:00"),
            _today_trade(ticket=3, profit_money=-30.0, closed_at="2024-01-15T15:00:00"),
        ]
        result = _check(today_trades=trades)
        item = _find(result, "losing_streak")
        assert item.passed is False
        assert "3-trade losing streak" in item.message

    def test_streak_broken_by_win(self):
        trades = [
            _today_trade(ticket=1, profit_money=-20.0, closed_at="2024-01-15T11:00:00"),
            _today_trade(ticket=2, profit_money=-15.0, closed_at="2024-01-15T13:00:00"),
            _today_trade(ticket=3, profit_money=50.0, commission=0.0,
                         closed_at="2024-01-15T14:00:00"),
            _today_trade(ticket=4, profit_money=-10.0, closed_at="2024-01-15T15:00:00"),
        ]
        result = _check(today_trades=trades)
        item = _find(result, "losing_streak")
        assert item.passed is True  # only 1 loss at the end

    def test_streak_includes_dollar_amount(self):
        trades = [
            _today_trade(ticket=1, profit_money=-20.0, commission=0.0, swap=0.0,
                         closed_at="2024-01-15T11:00:00"),
            _today_trade(ticket=2, profit_money=-15.0, commission=0.0, swap=0.0,
                         closed_at="2024-01-15T13:00:00"),
            _today_trade(ticket=3, profit_money=-30.0, commission=0.0, swap=0.0,
                         closed_at="2024-01-15T15:00:00"),
        ]
        result = _check(today_trades=trades)
        item = _find(result, "losing_streak")
        assert "$-65.0" in item.message or "$-65" in item.message

    def test_last_trade_winner_no_streak(self):
        trades = [
            _today_trade(ticket=1, profit_money=-20.0, closed_at="2024-01-15T11:00:00"),
            _today_trade(ticket=2, profit_money=-15.0, closed_at="2024-01-15T13:00:00"),
            _today_trade(ticket=3, profit_money=-30.0, closed_at="2024-01-15T14:00:00"),
            _today_trade(ticket=4, profit_money=50.0, commission=0.0,
                         closed_at="2024-01-15T15:00:00"),
        ]
        result = _check(today_trades=trades)
        item = _find(result, "losing_streak")
        assert item.passed is True
        assert "Last trade was a winner" in item.message


# ---------------------------------------------------------------------------
# Risk calculator standalone
# ---------------------------------------------------------------------------

class TestCalculateRisk:
    def test_forex(self):
        r = calculate_risk(
            symbol="EURUSD", lot=0.10,
            stop_loss=1.08500, open_price=1.08750,
            account_balance=10_000, contract_size=100_000,
        )
        assert r["risk_money"] == 25.0
        assert r["risk_pct"] == 0.25

    def test_gold(self):
        r = calculate_risk(
            symbol="XAUUSD", lot=0.15,
            stop_loss=5302.41, open_price=5332.41,
            account_balance=25_000, contract_size=100,
        )
        assert r["risk_money"] == 450.0
        assert r["risk_pct"] == 1.8

    def test_oil(self):
        r = calculate_risk(
            symbol="USOIL", lot=1.40,
            stop_loss=70.0, open_price=71.767,
            account_balance=25_000, contract_size=100,
        )
        assert r["risk_money"] == 247.38
        assert r["risk_pct"] == 0.99

    def test_large_position(self):
        r = calculate_risk(
            symbol="EURUSD", lot=1.0,
            stop_loss=1.08000, open_price=1.08750,
            account_balance=5_000, contract_size=100_000,
        )
        assert r["risk_money"] == 750.0
        assert r["risk_pct"] == 15.0


# ---------------------------------------------------------------------------
# Combined scenario tests
# ---------------------------------------------------------------------------

class TestCombinedScenarios:
    def test_perfect_trade_all_pass(self):
        result = _check()
        assert result.all_passed is True
        assert result.passed_count == 5
        assert result.warnings == []

    def test_everything_wrong(self):
        settings = {
            "max_risk_pct": 1.0,
            "max_trades_per_day": 2,
            "watchlist": ["GBPUSD"],
        }
        today = [
            _today_trade(ticket=1, profit_money=-20.0,
                         closed_at="2024-01-15T11:00:00"),
            _today_trade(ticket=2, profit_money=-15.0,
                         closed_at="2024-01-15T13:00:00"),
            _today_trade(ticket=3, profit_money=-30.0,
                         closed_at="2024-01-15T15:00:00"),
        ]
        result = _check(
            symbol="EURUSD",
            lot=2.0,
            stop_loss=None,
            account_balance=1_000,
            settings=settings,
            today_trades=today,
        )
        assert result.all_passed is False
        assert result.passed_count == 0
        assert len(result.warnings) == 5

    def test_partial_failures(self):
        result = _check(
            symbol="AUDNZD",  # not in watchlist
            stop_loss=None,   # no SL
        )
        assert result.all_passed is False
        # risk_size fails (no SL), stop_loss fails, watchlist fails
        assert result.passed_count == 2  # daily_limit + losing_streak pass

    def test_message_includes_numbers(self):
        result = _check(lot=0.10, stop_loss=1.08500, open_price=1.08750,
                        account_balance=10_000)
        risk_item = _find(result, "risk_size")
        assert "0.25%" in risk_item.message
        assert "$25.0" in risk_item.message

    def test_no_trade_history_passes(self):
        """No trade history → can't detect contract → passes with message."""
        result = _check(all_trades=[])
        risk_item = _find(result, "risk_size")
        assert risk_item.passed is True
        assert "no trade history" in risk_item.message


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------

def _find(result: ChecklistResult, rule: str) -> CheckItem:
    for item in result.items:
        if item.rule == rule:
            return item
    raise ValueError(f"Rule {rule} not found")
