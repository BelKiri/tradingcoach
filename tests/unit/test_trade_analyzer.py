"""Tests for trade_analyzer.py — all pure math, no AI."""

from datetime import timedelta

import pytest

from tradecoach.services.trade_analyzer import (
    build_contract_lookup,
    avg_hold_time,
    avg_loss,
    avg_win,
    detect_averaging_down,
    detect_martingale,
    detect_overtrading,
    detect_quick_exits,
    detect_revenge_trades,
    detect_weekend_holds,
    equity_curve,
    expectancy,
    full_analysis,
    gross_loss,
    gross_profit,
    hold_time_stats,
    max_drawdown,
    pnl_by_day_of_week,
    pnl_by_hour,
    pnl_by_session,
    pnl_by_symbol,
    profit_factor,
    revenge_trade_cost,
    risk_per_trade,
    sl_usage,
    streaks,
    total_pnl,
    win_rate,
    win_rate_after_n_losses,
    worst_hours,
)

# ---------------------------------------------------------------------------
# Sample trade data
# ---------------------------------------------------------------------------


def _trade(
    *,
    ticket=1,
    symbol="EURUSD",
    direction="buy",
    lot=0.10,
    open_price=1.08750,
    close_price=1.08950,
    stop_loss=1.08500,
    take_profit=1.09000,
    profit_pips=20.0,
    profit_money=20.0,
    commission=-0.70,
    swap=0.0,
    opened_at="2024-01-15T09:30:00",
    closed_at="2024-01-15T14:20:00",
    followed_plan=True,
    moved_stop=False,
    source="csv",
):
    return {
        "ticket": ticket,
        "symbol": symbol,
        "direction": direction,
        "lot": lot,
        "open_price": open_price,
        "close_price": close_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "profit_pips": profit_pips,
        "profit_money": profit_money,
        "commission": commission,
        "swap": swap,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "followed_plan": followed_plan,
        "moved_stop": moved_stop,
        "source": source,
    }


# A realistic set of 6 trades across different symbols, sessions, days
TRADES = [
    # Monday, London session, EURUSD, win
    _trade(
        ticket=1, symbol="EURUSD", direction="buy", lot=0.10,
        profit_money=20.0, commission=-0.70, swap=0.0,
        opened_at="2024-01-15T10:00:00", closed_at="2024-01-15T14:00:00",
    ),
    # Monday, NY session, GBPUSD, loss
    _trade(
        ticket=2, symbol="GBPUSD", direction="sell", lot=0.20,
        profit_money=-35.0, commission=-1.40, swap=0.0,
        opened_at="2024-01-15T15:00:00", closed_at="2024-01-15T18:30:00",
    ),
    # Tuesday, Asian session, USDJPY, win
    _trade(
        ticket=3, symbol="USDJPY", direction="buy", lot=0.10,
        open_price=148.250, close_price=148.800, stop_loss=147.800,
        profit_money=55.0, commission=-0.70, swap=-0.15,
        opened_at="2024-01-16T03:00:00", closed_at="2024-01-16T07:30:00",
    ),
    # Wednesday, London session, EURUSD, loss
    _trade(
        ticket=4, symbol="EURUSD", direction="buy", lot=0.10,
        profit_money=-15.0, commission=-0.70, swap=0.0,
        opened_at="2024-01-17T11:00:00", closed_at="2024-01-17T12:00:00",
    ),
    # Thursday, NY session, GBPUSD, win
    _trade(
        ticket=5, symbol="GBPUSD", direction="buy", lot=0.15,
        profit_money=45.0, commission=-1.05, swap=-0.20,
        opened_at="2024-01-18T16:00:00", closed_at="2024-01-18T19:00:00",
    ),
    # Friday, London session, EURUSD, loss
    _trade(
        ticket=6, symbol="EURUSD", direction="sell", lot=0.30,
        profit_money=-50.0, commission=-2.10, swap=0.0,
        opened_at="2024-01-19T09:30:00", closed_at="2024-01-19T10:30:00",
    ),
]


# ---------------------------------------------------------------------------
# Win rate
# ---------------------------------------------------------------------------


class TestWinRate:
    def test_basic(self):
        assert win_rate(TRADES) == 50.0  # 3 wins out of 6

    def test_all_winners(self):
        winners = [_trade(profit_money=10.0) for _ in range(5)]
        assert win_rate(winners) == 100.0

    def test_all_losers(self):
        losers = [_trade(profit_money=-10.0) for _ in range(3)]
        assert win_rate(losers) == 0.0

    def test_empty(self):
        assert win_rate([]) is None

    def test_breakeven_not_a_win(self):
        # profit_money=0.70 exactly cancels commission=-0.70 → net 0
        trades = [_trade(profit_money=0.70, commission=-0.70)]
        assert win_rate(trades) == 0.0


# ---------------------------------------------------------------------------
# P&L
# ---------------------------------------------------------------------------


class TestPnL:
    def test_total_pnl(self):
        # Sum of all (profit + commission + swap)
        expected = sum(
            t["profit_money"] + t["commission"] + t["swap"] for t in TRADES
        )
        assert total_pnl(TRADES) == round(expected, 2)

    def test_gross_profit(self):
        # Only winning trades' net profit
        gp = gross_profit(TRADES)
        assert gp > 0

    def test_gross_loss_is_negative(self):
        gl = gross_loss(TRADES)
        assert gl < 0

    def test_profit_factor(self):
        pf = profit_factor(TRADES)
        assert pf is not None
        gp = gross_profit(TRADES)
        gl = gross_loss(TRADES)
        assert pf == round(gp / abs(gl), 2)

    def test_profit_factor_no_losses(self):
        winners = [_trade(profit_money=10.0, commission=0.0) for _ in range(3)]
        assert profit_factor(winners) is None

    def test_avg_win(self):
        aw = avg_win(TRADES)
        assert aw is not None
        assert aw > 0

    def test_avg_loss(self):
        al = avg_loss(TRADES)
        assert al is not None
        assert al < 0

    def test_avg_win_no_winners(self):
        losers = [_trade(profit_money=-10.0)]
        assert avg_win(losers) is None

    def test_avg_loss_no_losers(self):
        winners = [_trade(profit_money=10.0, commission=0.0)]
        assert avg_loss(winners) is None

    def test_expectancy(self):
        e = expectancy(TRADES)
        assert e is not None
        assert e == round(total_pnl(TRADES) / len(TRADES), 2)

    def test_expectancy_empty(self):
        assert expectancy([]) is None


# ---------------------------------------------------------------------------
# Equity curve & drawdown
# ---------------------------------------------------------------------------


class TestEquityCurve:
    def test_length_matches_trades(self):
        curve = equity_curve(TRADES)
        assert len(curve) == len(TRADES)

    def test_cumulative(self):
        curve = equity_curve(TRADES)
        # Last point equity should equal total_pnl
        assert curve[-1]["equity"] == total_pnl(TRADES)

    def test_has_required_keys(self):
        curve = equity_curve(TRADES)
        for point in curve:
            assert "closed_at" in point
            assert "equity" in point
            assert "trade_pnl" in point

    def test_sorted_by_close_time(self):
        curve = equity_curve(TRADES)
        times = [c["closed_at"] for c in curve if c["closed_at"]]
        assert times == sorted(times)

    def test_empty(self):
        assert equity_curve([]) == []


class TestMaxDrawdown:
    def test_returns_dict(self):
        dd = max_drawdown(TRADES)
        assert "amount" in dd
        assert "percent" in dd
        assert "peak" in dd
        assert "trough" in dd

    def test_drawdown_positive(self):
        dd = max_drawdown(TRADES)
        assert dd["amount"] >= 0

    def test_all_winners_no_drawdown(self):
        winners = [
            _trade(ticket=i, profit_money=10.0, commission=0.0,
                   closed_at=f"2024-01-{15+i}T12:00:00")
            for i in range(5)
        ]
        dd = max_drawdown(winners)
        assert dd["amount"] == 0.0

    def test_single_loss_drawdown(self):
        trades = [
            _trade(ticket=1, profit_money=100.0, commission=0.0,
                   closed_at="2024-01-15T12:00:00"),
            _trade(ticket=2, profit_money=-30.0, commission=0.0,
                   closed_at="2024-01-16T12:00:00"),
        ]
        dd = max_drawdown(trades)
        assert dd["amount"] == 30.0
        assert dd["peak"] == 100.0
        assert dd["trough"] == 70.0

    def test_empty(self):
        dd = max_drawdown([])
        assert dd["amount"] == 0.0

    def test_drawdown_with_balance(self):
        """Drawdown % is from peak balance, not starting balance."""
        trades = [
            _trade(ticket=1, profit_money=1000.0, commission=0.0,
                   closed_at="2024-01-15T12:00:00"),
            _trade(ticket=2, profit_money=-500.0, commission=0.0,
                   closed_at="2024-01-16T12:00:00"),
        ]
        dd = max_drawdown(trades, account_balance=10_000)
        assert dd["amount"] == 500.0
        # peak = 10000 + 1000 = 11000, trough = 10500
        assert dd["peak"] == 11000.0
        assert dd["trough"] == 10500.0
        # percent = 500 / 11000 * 100 ≈ 4.55%
        assert dd["percent"] == pytest.approx(4.55, abs=0.01)

    def test_drawdown_percent_from_peak_not_balance(self):
        """Verify drawdown % uses peak equity, not starting balance."""
        trades = [
            _trade(ticket=1, profit_money=5000.0, commission=0.0,
                   closed_at="2024-01-15T12:00:00"),
            _trade(ticket=2, profit_money=-2000.0, commission=0.0,
                   closed_at="2024-01-16T12:00:00"),
        ]
        # Balance $25k: peak = $30k, trough = $28k
        dd = max_drawdown(trades, account_balance=25_000)
        assert dd["amount"] == 2000.0
        assert dd["peak"] == 30000.0
        # 2000/30000 = 6.67%, NOT 2000/25000 = 8%
        assert dd["percent"] == pytest.approx(6.67, abs=0.01)


# ---------------------------------------------------------------------------
# Breakdowns
# ---------------------------------------------------------------------------


class TestPnlBySymbol:
    def test_symbols_present(self):
        by_sym = pnl_by_symbol(TRADES)
        assert "EURUSD" in by_sym
        assert "GBPUSD" in by_sym
        assert "USDJPY" in by_sym

    def test_trade_counts(self):
        by_sym = pnl_by_symbol(TRADES)
        assert by_sym["EURUSD"]["trades"] == 3
        assert by_sym["GBPUSD"]["trades"] == 2
        assert by_sym["USDJPY"]["trades"] == 1

    def test_has_win_rate(self):
        by_sym = pnl_by_symbol(TRADES)
        for data in by_sym.values():
            assert "win_rate" in data
            assert 0 <= data["win_rate"] <= 100


class TestPnlBySession:
    def test_sessions_present(self):
        by_sess = pnl_by_session(TRADES)
        assert "London" in by_sess
        assert "New York" in by_sess
        assert "Asian" in by_sess

    def test_trade_counts_sum(self):
        by_sess = pnl_by_session(TRADES)
        total = sum(s["trades"] for s in by_sess.values())
        assert total == len(TRADES)

    def test_session_mapping(self):
        # Trade at 03:00 → Asian, 10:00 → London, 15:00 → London, 16:00 → NY
        # Session boundaries: Asian 00-07, London 08-15, NY 16-23
        by_sess = pnl_by_session(TRADES)
        assert by_sess["Asian"]["trades"] == 1   # USDJPY at 03:00
        assert by_sess["London"]["trades"] == 4  # 10:00, 11:00, 09:30, 15:00
        assert by_sess["New York"]["trades"] == 1  # 16:00


class TestPnlByDayOfWeek:
    def test_days_present(self):
        by_day = pnl_by_day_of_week(TRADES)
        assert "Monday" in by_day
        assert "Tuesday" in by_day

    def test_monday_trades(self):
        by_day = pnl_by_day_of_week(TRADES)
        assert by_day["Monday"]["trades"] == 2  # tickets 1 and 2

    def test_no_weekend(self):
        by_day = pnl_by_day_of_week(TRADES)
        assert "Saturday" not in by_day
        assert "Sunday" not in by_day


class TestPnlByHour:
    def test_hours_present(self):
        by_hour = pnl_by_hour(TRADES)
        assert 10 in by_hour  # EURUSD opened at 10:00
        assert 3 in by_hour   # USDJPY opened at 03:00

    def test_trade_counts(self):
        by_hour = pnl_by_hour(TRADES)
        total = sum(h["trades"] for h in by_hour.values())
        assert total == len(TRADES)


# ---------------------------------------------------------------------------
# Hold time
# ---------------------------------------------------------------------------


class TestHoldTime:
    def test_avg_hold_time(self):
        aht = avg_hold_time(TRADES)
        assert aht is not None
        assert isinstance(aht, timedelta)
        assert aht.total_seconds() > 0

    def test_hold_time_stats(self):
        stats = hold_time_stats(TRADES)
        assert stats is not None
        assert stats["min_seconds"] <= stats["avg_seconds"] <= stats["max_seconds"]
        assert stats["min_seconds"] <= stats["median_seconds"] <= stats["max_seconds"]

    def test_specific_hold_time(self):
        # Single trade: 10:00 to 14:00 = 4 hours = 14400 seconds
        trades = [_trade(opened_at="2024-01-15T10:00:00",
                         closed_at="2024-01-15T14:00:00")]
        aht = avg_hold_time(trades)
        assert aht == timedelta(hours=4)

    def test_empty(self):
        assert avg_hold_time([]) is None
        assert hold_time_stats([]) is None

    def test_missing_dates_skipped(self):
        trades = [_trade(opened_at=None, closed_at=None)]
        assert avg_hold_time(trades) is None


# ---------------------------------------------------------------------------
# Risk per trade
# ---------------------------------------------------------------------------


class TestBuildContractLookup:
    def test_eurusd_detection(self):
        """EURUSD: abs(20) / 0.002 / 0.10 = 100000."""
        trades = [_trade()]
        contracts = build_contract_lookup(trades)
        assert round(contracts["EURUSD"]) == 100_000

    def test_xauusd_detection(self):
        """XAUUSD: abs(150) / 15.0 / 0.10 = 100."""
        trades = [_trade(
            symbol="XAUUSD", open_price=2000.0, close_price=2015.0,
            lot=0.10, profit_money=150.0, commission=-1.0,
        )]
        contracts = build_contract_lookup(trades)
        assert round(contracts["XAUUSD"]) == 100

    def test_usoil_detection(self):
        """USOIL: 34.72 / 0.248 / 1.40 = 100."""
        trades = [_trade(
            symbol="USOIL", open_price=71.767, close_price=72.015,
            lot=1.40, profit_money=34.72,
        )]
        contracts = build_contract_lookup(trades)
        assert round(contracts["USOIL"]) == 100

    def test_btcusd_detection(self):
        """BTCUSD: 541.45 / 2165.80 / 0.25 ≈ 1."""
        trades = [_trade(
            symbol="BTCUSD", open_price=67130.03, close_price=69295.83,
            lot=0.25, profit_money=541.45,
        )]
        contracts = build_contract_lookup(trades)
        assert round(contracts["BTCUSD"]) == 1

    def test_median_used(self):
        """Multiple trades → median contract size."""
        trades = [
            _trade(symbol="XAUUSD", open_price=2000.0, close_price=2010.0,
                   lot=0.10, profit_money=100.0, commission=0.0),
            _trade(symbol="XAUUSD", open_price=2010.0, close_price=2015.0,
                   lot=0.10, profit_money=50.0, commission=0.0, ticket=2),
            _trade(symbol="XAUUSD", open_price=2020.0, close_price=2025.0,
                   lot=0.20, profit_money=100.0, commission=0.0, ticket=3),
        ]
        contracts = build_contract_lookup(trades)
        assert round(contracts["XAUUSD"]) == 100

    def test_zero_profit_skipped(self):
        """profit=0 (breakeven) → uses other trades on same symbol."""
        trades = [
            _trade(profit_money=0.0),  # breakeven, skipped for detection
            _trade(profit_money=20.0, ticket=2),  # valid
        ]
        contracts = build_contract_lookup(trades)
        assert round(contracts["EURUSD"]) == 100_000

    def test_same_open_close_no_pips_skipped(self):
        """close == open and no pips fallback → excluded."""
        trades = [_trade(open_price=1.08750, close_price=1.08750,
                         profit_pips=0.0)]
        contracts = build_contract_lookup(trades)
        assert "EURUSD" not in contracts

    def test_pips_fallback(self):
        """No price data → falls back to pips-based detection."""
        trades = [_trade(
            symbol="NEWPAIR", open_price=1.0, close_price=1.0,
            lot=0.10, profit_money=50.0, profit_pips=25.0,
        )]
        contracts = build_contract_lookup(trades)
        # pip_val = 50 / 25 / 0.10 = 20
        assert contracts["NEWPAIR"] == 20.0

    def test_no_data_symbol_excluded(self):
        """Symbol with only breakeven trades → excluded from lookup."""
        trades = [_trade(
            symbol="XYZABC", open_price=100.0, close_price=100.0,
            lot=1.0, profit_money=0.0, profit_pips=0.0,
        )]
        contracts = build_contract_lookup(trades)
        assert "XYZABC" not in contracts

    def test_none_fields_no_crash(self):
        """Trades with None fields don't crash."""
        trades = [
            {"ticket": 1, "symbol": "EURUSD"},
            {"ticket": 2, "symbol": "EURUSD", "profit_money": None,
             "open_price": None, "close_price": None, "lot": None},
            {"ticket": 3, "symbol": "EURUSD", "profit_money": 10.0,
             "open_price": 1.1, "close_price": 1.1, "lot": 0},
        ]
        contracts = build_contract_lookup(trades)
        assert "EURUSD" not in contracts


class TestRiskPerTrade:
    def test_basic_risk(self):
        """EURUSD: abs(1.08750 - 1.08500) * 100000 * 0.10 = $25 → 0.25%"""
        trades = [_trade(
            open_price=1.08750, close_price=1.08950, stop_loss=1.08500,
            lot=0.10, direction="buy", profit_money=20.0, commission=0.0,
        )]
        results = risk_per_trade(trades, account_balance=10_000)
        assert len(results) == 1
        assert results[0]["risk_money"] == 25.0
        assert results[0]["risk_pct"] == 0.25

    def test_sell_risk(self):
        """GBPUSD sell: abs(1.26200 - 1.26500) * 100000 * 0.20 = $60"""
        trades = [_trade(
            symbol="GBPUSD", direction="sell", lot=0.20,
            open_price=1.26200, close_price=1.25900, stop_loss=1.26500,
            profit_money=60.0, commission=0.0,
        )]
        results = risk_per_trade(trades, account_balance=10_000)
        assert results[0]["risk_money"] == 60.0
        assert results[0]["risk_pct"] == 0.6

    def test_no_stop_loss_winner(self):
        """Winner without SL → risk_pct=None (no risk to measure)."""
        trades = [_trade(stop_loss=None, profit_money=50.0, commission=0.0)]
        results = risk_per_trade(trades, account_balance=10_000)
        assert results[0]["risk_pct"] is None

    def test_no_stop_loss_loser(self):
        """Loser without SL → actual loss used as risk."""
        trades = [_trade(
            stop_loss=None, profit_money=-200.0, commission=-5.0, swap=-2.0,
        )]
        results = risk_per_trade(trades, account_balance=10_000)
        # net = -200 + (-5) + (-2) = -207, risk_money = 207
        assert results[0]["risk_money"] == 207.0
        assert results[0]["risk_pct"] == 2.07

    def test_stop_loss_zero_treated_as_no_sl(self):
        """SL=0 treated same as no SL."""
        trades = [_trade(stop_loss=0, profit_money=-100.0, commission=0.0, swap=0.0)]
        results = risk_per_trade(trades, account_balance=10_000)
        assert results[0]["risk_money"] == 100.0
        assert results[0]["risk_pct"] == 1.0

    def test_xauusd_risk(self):
        """Gold contract=100: abs(2000 - 1990) * 100 * 0.10 = $100 → 1.0%"""
        trades = [_trade(
            symbol="XAUUSD", direction="buy",
            open_price=2000.00, close_price=2015.00, stop_loss=1990.00,
            lot=0.10, profit_money=150.0, commission=0.0,
        )]
        results = risk_per_trade(trades, account_balance=10_000)
        assert results[0]["risk_money"] == 100.0
        assert results[0]["risk_pct"] == 1.0

    def test_xauusd_risk_realistic(self):
        """Real gold: abs(5332.41 - 5302.41) * 100 * 0.15 = $450 → 1.8%

        Uses a separate calibration trade to auto-detect contract=100.
        """
        calibration = _trade(
            symbol="XAUUSD", direction="buy", ticket=99,
            open_price=2000.0, close_price=2010.0, lot=0.10,
            profit_money=100.0, commission=0.0,
        )
        target = _trade(
            symbol="XAUUSD", direction="buy",
            open_price=5332.41, close_price=5335.33, stop_loss=5302.41,
            lot=0.15, profit_money=43.8, commission=0.0,
        )
        results = risk_per_trade([calibration, target], account_balance=25_000)
        assert results[1]["risk_money"] == 450.0
        assert results[1]["risk_pct"] == 1.8

    def test_usoil_risk(self):
        """Oil contract=100: abs(71.767 - 70.0) * 100 * 1.4 = $247.38"""
        trades = [_trade(
            symbol="USOIL", direction="buy",
            open_price=71.767, close_price=72.015, stop_loss=70.0,
            lot=1.40, profit_money=34.72, commission=0.0,
        )]
        results = risk_per_trade(trades, account_balance=25_000)
        assert results[0]["risk_money"] == 247.38
        assert results[0]["risk_pct"] == 0.99

    def test_unknown_symbol_returns_none(self):
        """Symbol with no P&L data for contract detection → risk_pct=None."""
        trades = [_trade(
            symbol="XYZABC", open_price=100.0, close_price=100.0,
            stop_loss=99.0, lot=1.0, profit_money=0.0,
        )]
        results = risk_per_trade(trades, account_balance=10_000)
        assert results[0]["risk_pct"] is None


# ---------------------------------------------------------------------------
# Streaks
# ---------------------------------------------------------------------------


class TestStreaks:
    def test_basic(self):
        s = streaks(TRADES)
        assert s["max_win_streak"] >= 1
        assert s["max_loss_streak"] >= 1

    def test_all_wins(self):
        winners = [
            _trade(ticket=i, profit_money=10.0, commission=0.0,
                   closed_at=f"2024-01-{15+i}T12:00:00")
            for i in range(5)
        ]
        s = streaks(winners)
        assert s["max_win_streak"] == 5
        assert s["max_loss_streak"] == 0
        assert s["current_streak"] == 5
        assert s["current_streak_type"] == "win"

    def test_all_losses(self):
        losers = [
            _trade(ticket=i, profit_money=-10.0,
                   closed_at=f"2024-01-{15+i}T12:00:00")
            for i in range(3)
        ]
        s = streaks(losers)
        assert s["max_loss_streak"] == 3
        assert s["current_streak_type"] == "loss"

    def test_alternating(self):
        trades = [
            _trade(ticket=1, profit_money=10.0, commission=0.0,
                   closed_at="2024-01-15T12:00:00"),
            _trade(ticket=2, profit_money=-10.0,
                   closed_at="2024-01-16T12:00:00"),
            _trade(ticket=3, profit_money=10.0, commission=0.0,
                   closed_at="2024-01-17T12:00:00"),
        ]
        s = streaks(trades)
        assert s["max_win_streak"] == 1
        assert s["max_loss_streak"] == 1

    def test_empty(self):
        s = streaks([])
        assert s["max_win_streak"] == 0
        assert s["current_streak"] == 0
        assert s["current_streak_type"] is None


# ---------------------------------------------------------------------------
# Revenge trading detection
# ---------------------------------------------------------------------------


class TestRevengeTrades:
    def test_detects_revenge(self):
        trades = [
            _trade(
                ticket=1, profit_money=-50.0, lot=0.10,
                opened_at="2024-01-15T13:00:00",
                closed_at="2024-01-15T14:00:00",
            ),
            # New trade opened 2 minutes after loss closed — revenge
            _trade(
                ticket=2, profit_money=-30.0, lot=0.20,
                opened_at="2024-01-15T14:02:00",
                closed_at="2024-01-15T15:00:00",
            ),
        ]
        revenge = detect_revenge_trades(trades)
        assert len(revenge) == 1
        assert revenge[0]["trade"]["ticket"] == 2
        assert revenge[0]["previous_loss"]["ticket"] == 1
        assert revenge[0]["gap_seconds"] == 120

    def test_smaller_lot_still_revenge(self):
        """Revenge is emotional — lot size doesn't matter."""
        trades = [
            _trade(
                ticket=1, profit_money=-50.0, lot=0.20,
                opened_at="2024-01-15T13:00:00",
                closed_at="2024-01-15T14:00:00",
            ),
            _trade(
                ticket=2, profit_money=-10.0, lot=0.05,
                opened_at="2024-01-15T14:02:00",
                closed_at="2024-01-15T15:00:00",
            ),
        ]
        revenge = detect_revenge_trades(trades)
        assert len(revenge) == 1

    def test_no_revenge_if_gap_too_large(self):
        trades = [
            _trade(
                ticket=1, profit_money=-50.0, lot=0.10,
                opened_at="2024-01-15T13:00:00",
                closed_at="2024-01-15T14:00:00",
            ),
            _trade(
                ticket=2, profit_money=-30.0, lot=0.20,
                opened_at="2024-01-15T14:10:00",
                closed_at="2024-01-15T15:00:00",
            ),
        ]
        revenge = detect_revenge_trades(trades)
        assert len(revenge) == 0

    def test_no_revenge_after_win(self):
        trades = [
            _trade(
                ticket=1, profit_money=50.0, commission=0.0, lot=0.10,
                opened_at="2024-01-15T13:00:00",
                closed_at="2024-01-15T14:00:00",
            ),
            _trade(
                ticket=2, profit_money=-30.0, lot=0.20,
                opened_at="2024-01-15T14:02:00",
                closed_at="2024-01-15T15:00:00",
            ),
        ]
        revenge = detect_revenge_trades(trades)
        assert len(revenge) == 0

    def test_each_trade_flagged_once(self):
        """Two losses close back-to-back, one trade opens after both."""
        trades = [
            _trade(
                ticket=1, profit_money=-50.0,
                opened_at="2024-01-15T13:00:00",
                closed_at="2024-01-15T14:00:00",
            ),
            _trade(
                ticket=2, profit_money=-30.0,
                opened_at="2024-01-15T13:30:00",
                closed_at="2024-01-15T14:01:00",
            ),
            _trade(
                ticket=3, profit_money=-10.0,
                opened_at="2024-01-15T14:02:00",
                closed_at="2024-01-15T15:00:00",
            ),
        ]
        revenge = detect_revenge_trades(trades)
        # ticket 3 flagged once (from loss ticket 1), not twice
        assert len([r for r in revenge if r["trade"]["ticket"] == 3]) == 1

    def test_custom_gap(self):
        trades = [
            _trade(
                ticket=1, profit_money=-50.0,
                opened_at="2024-01-15T13:00:00",
                closed_at="2024-01-15T14:00:00",
            ),
            _trade(
                ticket=2, profit_money=-30.0,
                opened_at="2024-01-15T14:08:00",
                closed_at="2024-01-15T15:00:00",
            ),
        ]
        assert len(detect_revenge_trades(trades, max_gap_minutes=5)) == 0
        assert len(detect_revenge_trades(trades, max_gap_minutes=10)) == 1

    def test_revenge_trade_cost(self):
        trades = [
            _trade(
                ticket=1, profit_money=-50.0, commission=0.0,
                opened_at="2024-01-15T13:00:00",
                closed_at="2024-01-15T14:00:00",
            ),
            _trade(
                ticket=2, profit_money=-30.0, commission=-1.0,
                opened_at="2024-01-15T14:02:00",
                closed_at="2024-01-15T15:00:00",
            ),
        ]
        cost = revenge_trade_cost(trades)
        assert cost == -31.0


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    def test_returns_all_keys(self):
        result = full_analysis(TRADES)
        expected_keys = {
            "total_trades", "win_rate", "total_pnl", "gross_profit",
            "gross_loss", "profit_factor", "avg_win", "avg_loss",
            "expectancy", "max_drawdown", "equity_curve",
            "pnl_by_symbol", "pnl_by_session", "pnl_by_day_of_week",
            "pnl_by_hour", "hold_time", "streaks",
            "revenge_trades", "revenge_trade_cost",
        }
        assert set(result.keys()) == expected_keys

    def test_total_trades(self):
        result = full_analysis(TRADES)
        assert result["total_trades"] == 6

    def test_empty_trades(self):
        result = full_analysis([])
        assert result["total_trades"] == 0
        assert result["win_rate"] is None
        assert result["total_pnl"] == 0


# ---------------------------------------------------------------------------
# Overtrading detection
# ---------------------------------------------------------------------------


class TestOvertrading:
    def test_detects_overtrading_day(self):
        # 5 trades on same day = overtrading
        trades = [
            _trade(ticket=i, profit_money=(-10 if i % 2 else 10),
                   opened_at=f"2024-01-15T{9+i:02d}:00:00",
                   closed_at=f"2024-01-15T{10+i:02d}:00:00")
            for i in range(5)
        ]
        result = detect_overtrading(trades)
        assert result["overtrading_days"] == 1
        assert result["overtrading_trades"] == 5

    def test_no_overtrading(self):
        # 2 trades on one day is fine
        trades = [
            _trade(ticket=1, opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T11:00:00"),
            _trade(ticket=2, opened_at="2024-01-15T14:00:00",
                   closed_at="2024-01-15T15:00:00"),
        ]
        result = detect_overtrading(trades)
        assert result["overtrading_days"] == 0

    def test_empty(self):
        result = detect_overtrading([])
        assert result["overtrading_days"] == 0


# ---------------------------------------------------------------------------
# Martingale detection
# ---------------------------------------------------------------------------


class TestMartingale:
    def test_detects_lot_increase_after_loss(self):
        """Loss closes at 10:30, next trade opens at 10:40 (10 min gap)."""
        trades = [
            _trade(ticket=1, lot=0.1, profit_money=-20,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:30:00"),
            _trade(ticket=2, lot=0.2, profit_money=-30,
                   opened_at="2024-01-15T10:40:00",
                   closed_at="2024-01-15T11:00:00"),
        ]
        result = detect_martingale(trades)
        assert len(result) == 1
        assert result[0]["lot_increase_pct"] == pytest.approx(100.0)

    def test_no_martingale_after_win(self):
        trades = [
            _trade(ticket=1, lot=0.1, profit_money=20, commission=0.0,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:30:00"),
            _trade(ticket=2, lot=0.2, profit_money=30,
                   opened_at="2024-01-15T10:40:00",
                   closed_at="2024-01-15T11:00:00"),
        ]
        result = detect_martingale(trades)
        assert len(result) == 0

    def test_small_increase_ignored(self):
        trades = [
            _trade(ticket=1, lot=0.1, profit_money=-20,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:30:00"),
            _trade(ticket=2, lot=0.12, profit_money=10,
                   opened_at="2024-01-15T10:40:00",
                   closed_at="2024-01-15T11:00:00"),
        ]
        result = detect_martingale(trades)
        assert len(result) == 0  # 20% increase < 40% threshold

    def test_cross_symbol_not_martingale(self):
        trades = [
            _trade(ticket=1, symbol="XAUUSD", lot=0.05, profit_money=-50,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:20:00"),
            _trade(ticket=2, symbol="EURUSD", lot=0.10, profit_money=20,
                   opened_at="2024-01-15T10:25:00",
                   closed_at="2024-01-15T10:45:00"),
        ]
        result = detect_martingale(trades)
        assert len(result) == 0

    def test_same_symbol_martingale(self):
        """Loss closes at 10:30, next opens at 10:35 (5 min gap)."""
        trades = [
            _trade(ticket=1, symbol="XAUUSD", lot=0.05, profit_money=-50,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:30:00"),
            _trade(ticket=2, symbol="XAUUSD", lot=0.10, profit_money=-30,
                   opened_at="2024-01-15T10:35:00",
                   closed_at="2024-01-15T11:00:00"),
        ]
        result = detect_martingale(trades)
        assert len(result) == 1

    def test_too_far_apart_not_martingale(self):
        """Gap from close to next open > 1 hour."""
        trades = [
            _trade(ticket=1, symbol="XAUUSD", lot=0.05, profit_money=-50,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:30:00"),
            _trade(ticket=2, symbol="XAUUSD", lot=0.10, profit_money=-30,
                   opened_at="2024-01-17T14:00:00",
                   closed_at="2024-01-17T15:00:00"),
        ]
        result = detect_martingale(trades)
        assert len(result) == 0

    def test_non_adjacent_same_symbol(self):
        """Tracks last closed trade per symbol, not globally."""
        trades = [
            _trade(ticket=1, symbol="XAUUSD", lot=0.05, profit_money=-50,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:20:00"),
            _trade(ticket=2, symbol="EURUSD", lot=0.10, profit_money=20,
                   opened_at="2024-01-15T10:10:00",
                   closed_at="2024-01-15T10:30:00"),
            _trade(ticket=3, symbol="XAUUSD", lot=0.10, profit_money=-30,
                   opened_at="2024-01-15T10:25:00",
                   closed_at="2024-01-15T10:45:00"),
        ]
        result = detect_martingale(trades)
        assert len(result) == 1
        assert result[0]["trade"]["ticket"] == 3
        assert result[0]["previous_trade"]["ticket"] == 1

    def test_gap_uses_close_to_open(self):
        """Gap is curr.opened_at - prev.closed_at, NOT opened vs opened."""
        trades = [
            # Opens at 10:00, closes at 11:30 (long hold)
            _trade(ticket=1, symbol="XAUUSD", lot=0.05, profit_money=-50,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T11:30:00"),
            # Opens at 11:35 — only 5 min after prev CLOSED
            _trade(ticket=2, symbol="XAUUSD", lot=0.10, profit_money=-30,
                   opened_at="2024-01-15T11:35:00",
                   closed_at="2024-01-15T12:00:00"),
        ]
        result = detect_martingale(trades)
        assert len(result) == 1  # 5 min gap from close, within 1 hour


# ---------------------------------------------------------------------------
# Quick exits
# ---------------------------------------------------------------------------


class TestQuickExits:
    def test_detects_quick_close(self):
        trades = [
            _trade(ticket=1, profit_money=-5,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:01:30"),
        ]
        result = detect_quick_exits(trades)
        assert len(result) == 1
        assert result[0]["hold_seconds"] == 90

    def test_normal_trade_not_flagged(self):
        trades = [
            _trade(ticket=1,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T10:30:00"),
        ]
        result = detect_quick_exits(trades)
        assert len(result) == 0

    def test_no_dates(self):
        trades = [_trade(opened_at=None, closed_at=None)]
        result = detect_quick_exits(trades)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Averaging down
# ---------------------------------------------------------------------------


class TestAveragingDown:
    def test_detects_overlapping_positions(self):
        """Trade B opens while Trade A still open → averaging down."""
        trades = [
            _trade(ticket=1, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T14:00:00"),
            _trade(ticket=2, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:15:00",
                   closed_at="2024-01-15T14:00:00"),
        ]
        result = detect_averaging_down(trades)
        assert len(result) == 1
        assert result[0]["trade"]["ticket"] == 2
        assert result[0]["original_trade"]["ticket"] == 1
        assert result[0]["symbol"] == "EURUSD"

    def test_winner_also_flagged(self):
        """No loss requirement — any overlap = averaging."""
        trades = [
            _trade(ticket=1, symbol="EURUSD", direction="buy",
                   profit_money=50, commission=0.0,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T14:00:00"),
            _trade(ticket=2, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:15:00",
                   closed_at="2024-01-15T14:00:00"),
        ]
        result = detect_averaging_down(trades)
        assert len(result) == 1

    def test_different_direction_not_flagged(self):
        trades = [
            _trade(ticket=1, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T14:00:00"),
            _trade(ticket=2, symbol="EURUSD", direction="sell",
                   opened_at="2024-01-15T10:15:00",
                   closed_at="2024-01-15T14:00:00"),
        ]
        result = detect_averaging_down(trades)
        assert len(result) == 0

    def test_not_overlapping(self):
        """B opens after A closes → not averaging down."""
        trades = [
            _trade(ticket=1, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T11:00:00"),
            _trade(ticket=2, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T11:30:00",
                   closed_at="2024-01-15T12:00:00"),
        ]
        result = detect_averaging_down(trades)
        assert len(result) == 0

    def test_different_symbol_not_flagged(self):
        trades = [
            _trade(ticket=1, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T14:00:00"),
            _trade(ticket=2, symbol="GBPUSD", direction="buy",
                   opened_at="2024-01-15T10:15:00",
                   closed_at="2024-01-15T14:00:00"),
        ]
        result = detect_averaging_down(trades)
        assert len(result) == 0

    def test_flagged_once(self):
        """Each added trade flagged only once even if multiple originals."""
        trades = [
            _trade(ticket=1, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T14:00:00"),
            _trade(ticket=2, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:05:00",
                   closed_at="2024-01-15T14:00:00"),
            _trade(ticket=3, symbol="EURUSD", direction="buy",
                   opened_at="2024-01-15T10:10:00",
                   closed_at="2024-01-15T14:00:00"),
        ]
        result = detect_averaging_down(trades)
        tickets = [r["trade"]["ticket"] for r in result]
        assert len(tickets) == len(set(tickets))


# ---------------------------------------------------------------------------
# Weekend holds
# ---------------------------------------------------------------------------


class TestWeekendHolds:
    def test_detects_friday_to_monday(self):
        # Friday to Monday
        trades = [
            _trade(ticket=1,
                   opened_at="2024-01-19T15:00:00",  # Friday
                   closed_at="2024-01-22T10:00:00"),  # Monday
        ]
        result = detect_weekend_holds(trades)
        assert len(result) == 1

    def test_weekday_trade_not_flagged(self):
        trades = [
            _trade(ticket=1,
                   opened_at="2024-01-15T10:00:00",  # Monday
                   closed_at="2024-01-16T10:00:00"),  # Tuesday
        ]
        result = detect_weekend_holds(trades)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Win rate after N losses
# ---------------------------------------------------------------------------


class TestWinRateAfterNLosses:
    def test_tracks_after_streak(self):
        # 3 losses then 1 win on same day
        trades = [
            _trade(ticket=1, profit_money=-10,
                   closed_at="2024-01-15T10:00:00"),
            _trade(ticket=2, profit_money=-10,
                   closed_at="2024-01-15T11:00:00"),
            _trade(ticket=3, profit_money=-10,
                   closed_at="2024-01-15T12:00:00"),
            _trade(ticket=4, profit_money=30,
                   closed_at="2024-01-15T13:00:00"),
        ]
        result = win_rate_after_n_losses(trades, n=3)
        assert result["trades_after_streak"] == 1
        assert result["win_rate"] == 100.0

    def test_no_streak(self):
        trades = [
            _trade(ticket=1, profit_money=20, closed_at="2024-01-15T10:00:00"),
            _trade(ticket=2, profit_money=-10, closed_at="2024-01-15T11:00:00"),
        ]
        result = win_rate_after_n_losses(trades, n=3)
        assert result["trades_after_streak"] == 0

    def test_empty(self):
        result = win_rate_after_n_losses([], n=3)
        assert result["trades_after_streak"] == 0


# ---------------------------------------------------------------------------
# Worst hours
# ---------------------------------------------------------------------------


class TestWorstHours:
    def test_finds_losing_hours(self):
        trades = [
            _trade(ticket=1, profit_money=-30,
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T11:00:00"),
            _trade(ticket=2, profit_money=-20,
                   opened_at="2024-01-16T10:30:00",
                   closed_at="2024-01-16T11:00:00"),
            _trade(ticket=3, profit_money=-10,
                   opened_at="2024-01-17T10:15:00",
                   closed_at="2024-01-17T11:00:00"),
        ]
        result = worst_hours(trades, min_trades=3)
        assert len(result) >= 1
        assert result[0]["hour"] == 10
        assert result[0]["pnl"] < 0

    def test_winning_hours_excluded(self):
        trades = [
            _trade(ticket=i, profit_money=50,
                   opened_at=f"2024-01-{15+i}T14:00:00",
                   closed_at=f"2024-01-{15+i}T15:00:00")
            for i in range(3)
        ]
        result = worst_hours(trades, min_trades=3)
        assert len(result) == 0

    def test_empty(self):
        assert worst_hours([]) == []


# ---------------------------------------------------------------------------
# SL usage
# ---------------------------------------------------------------------------

class TestSlUsage:
    def test_all_with_sl(self):
        trades = [
            _trade(ticket=1, stop_loss=1.08500),
            _trade(ticket=2, stop_loss=1.09000),
        ]
        result = sl_usage(trades)
        assert result["with_sl"] == 2
        assert result["without_sl"] == 0
        assert result["total"] == 2
        assert result["warning"] is False

    def test_all_without_sl(self):
        trades = [
            _trade(ticket=1, stop_loss=None),
            _trade(ticket=2, stop_loss=None),
        ]
        result = sl_usage(trades)
        assert result["with_sl"] == 0
        assert result["without_sl"] == 2
        assert result["warning"] is True

    def test_mixed(self):
        trades = [
            _trade(ticket=1, stop_loss=1.08500),
            _trade(ticket=2, stop_loss=None),
            _trade(ticket=3, stop_loss=0),
        ]
        result = sl_usage(trades)
        assert result["with_sl"] == 1
        assert result["without_sl"] == 2  # None and 0 both count as no SL
        assert result["warning"] is True

    def test_empty(self):
        result = sl_usage([])
        assert result["with_sl"] == 0
        assert result["without_sl"] == 0
        assert result["total"] == 0
        assert result["warning"] is False
