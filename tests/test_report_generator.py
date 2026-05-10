"""
Tests for the full analysis report generator.
"""

from __future__ import annotations

import pytest

from tradecoach.services.report_generator import (
    generate_full_report,
    _fmt_pnl,
    _date_range,
    _section_overview,
    _section_strengths,
    _section_weaknesses,
    _section_behavioral,
    _section_risk,
)


# ---------------------------------------------------------------------------
# Test data factory
# ---------------------------------------------------------------------------

def _trade(
    symbol="EURUSD", profit_money=100.0, direction="buy",
    opened_at="2024-01-15T10:00:00", closed_at="2024-01-15T11:00:00",
    lot=0.1, commission=-2.0, swap=0.0, stop_loss=1.09,
    open_price=1.095, trade_id="t1", followed_plan=None,
):
    return {
        "id": trade_id, "symbol": symbol, "direction": direction,
        "profit_money": profit_money, "commission": commission, "swap": swap,
        "opened_at": opened_at, "closed_at": closed_at,
        "lot": lot, "followed_plan": followed_plan,
        "stop_loss": stop_loss, "open_price": open_price,
    }


MIXED_TRADES = [
    _trade("EURUSD", 100, opened_at="2024-01-15T10:00:00",
           closed_at="2024-01-15T11:00:00", trade_id="t1"),
    _trade("EURUSD", 50, opened_at="2024-01-16T09:00:00",
           closed_at="2024-01-16T10:00:00", trade_id="t2"),
    _trade("GBPUSD", -80, opened_at="2024-01-17T03:00:00",
           closed_at="2024-01-17T04:00:00", trade_id="t3"),
    _trade("GBPJPY", -120, opened_at="2024-01-18T03:30:00",
           closed_at="2024-01-18T04:30:00", trade_id="t4"),
    _trade("EURUSD", 60, opened_at="2024-01-19T14:00:00",
           closed_at="2024-01-19T15:00:00", trade_id="t5"),
    _trade("GBPUSD", -30, opened_at="2024-01-22T18:00:00",
           closed_at="2024-01-22T19:00:00", trade_id="t6"),
]

REVENGE_TRADES = [
    _trade("EURUSD", -50, opened_at="2024-01-15T10:00:00",
           closed_at="2024-01-15T10:30:00", trade_id="r1", lot=0.1),
    _trade("EURUSD", -30, opened_at="2024-01-15T10:31:00",
           closed_at="2024-01-15T11:00:00", trade_id="r2", lot=0.2),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestFmtPnl:
    def test_positive(self):
        assert _fmt_pnl(100.0) == "+$100.00"

    def test_negative(self):
        assert _fmt_pnl(-50.0) == "-$50.00"

    def test_zero(self):
        assert _fmt_pnl(0.0) == "+$0.00"

    def test_large_number(self):
        assert _fmt_pnl(1234567.89) == "+$1,234,567.89"


class TestDateRange:
    def test_with_dates(self):
        trades = [
            _trade(opened_at="2024-01-15T10:00:00"),
            _trade(opened_at="2024-03-20T10:00:00"),
        ]
        result = _date_range(trades)
        assert "Jan 15" in result
        assert "Mar 20" in result
        assert "2024" in result

    def test_no_dates(self):
        trades = [_trade(opened_at=None, closed_at=None)]
        assert _date_range(trades) == "Unknown"

    def test_fallback_to_closed_at(self):
        trades = [_trade(opened_at=None, closed_at="2024-06-01T12:00:00")]
        assert "Jun" in _date_range(trades)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

class TestOverview:
    def test_contains_all_metrics(self):
        lines = _section_overview(MIXED_TRADES)
        text = "\n".join(lines)
        assert "OVERVIEW" in text
        assert "Total trades: 6" in text
        assert "Win rate:" in text
        assert "Total P&L:" in text
        assert "Profit factor:" in text
        assert "Avg win:" in text
        assert "Avg loss:" in text
        assert "Expectancy:" in text

    def test_win_loss_breakdown(self):
        lines = _section_overview(MIXED_TRADES)
        text = "\n".join(lines)
        assert "3W / 3L" in text

    def test_period(self):
        lines = _section_overview(MIXED_TRADES)
        text = "\n".join(lines)
        assert "Jan 15" in text
        assert "Jan 22" in text
        assert "2024" in text


class TestStrengths:
    def test_best_pairs(self):
        lines = _section_strengths(MIXED_TRADES)
        text = "\n".join(lines)
        assert "STRENGTHS" in text
        assert "EURUSD" in text

    def test_best_session(self):
        lines = _section_strengths(MIXED_TRADES)
        text = "\n".join(lines)
        assert "Best session:" in text

    def test_winning_streak(self):
        all_winners = [
            _trade("EURUSD", 50, trade_id="w1",
                   closed_at="2024-01-01T10:00:00"),
            _trade("EURUSD", 30, trade_id="w2",
                   closed_at="2024-01-02T10:00:00"),
            _trade("EURUSD", 20, trade_id="w3",
                   closed_at="2024-01-03T10:00:00"),
        ]
        lines = _section_strengths(all_winners)
        text = "\n".join(lines)
        assert "win streak: 3" in text

    def test_no_strengths_still_has_header(self):
        losers = [_trade("EURUSD", -100, trade_id="l1")]
        lines = _section_strengths(losers)
        text = "\n".join(lines)
        assert "STRENGTHS" in text


class TestWeaknesses:
    def test_worst_pairs(self):
        lines = _section_weaknesses(MIXED_TRADES)
        text = "\n".join(lines)
        assert "WEAKNESSES" in text
        assert "GBPJPY" in text or "GBPUSD" in text

    def test_worst_session(self):
        lines = _section_weaknesses(MIXED_TRADES)
        text = "\n".join(lines)
        assert "Worst session:" in text

    def test_losing_streak(self):
        losers = [
            _trade("EURUSD", -50, trade_id="l1",
                   closed_at="2024-01-01T10:00:00"),
            _trade("EURUSD", -30, trade_id="l2",
                   closed_at="2024-01-02T10:00:00"),
            _trade("EURUSD", -20, trade_id="l3",
                   closed_at="2024-01-03T10:00:00"),
        ]
        lines = _section_weaknesses(losers)
        text = "\n".join(lines)
        assert "loss streak: 3" in text


class TestBehavioral:
    def test_revenge_trading_detected(self):
        lines = _section_behavioral(REVENGE_TRADES)
        text = "\n".join(lines)
        assert "BEHAVIORAL" in text
        assert "Revenge trading" in text

    def test_no_issues(self):
        clean = [
            _trade("EURUSD", 50, trade_id="c1",
                   opened_at="2024-01-15T10:00:00",
                   closed_at="2024-01-15T14:00:00"),
        ]
        lines = _section_behavioral(clean)
        text = "\n".join(lines)
        assert "No major behavioral issues" in text

    def test_losing_session_highlighted(self):
        # 3 losing trades in Asian session
        asian_losers = [
            _trade("EURUSD", -50, trade_id="a1",
                   opened_at="2024-01-15T03:00:00",
                   closed_at="2024-01-15T04:00:00"),
            _trade("EURUSD", -30, trade_id="a2",
                   opened_at="2024-01-16T04:00:00",
                   closed_at="2024-01-16T05:00:00"),
            _trade("EURUSD", -20, trade_id="a3",
                   opened_at="2024-01-17T05:00:00",
                   closed_at="2024-01-17T06:00:00"),
        ]
        lines = _section_behavioral(asian_losers)
        text = "\n".join(lines)
        assert "Asian" in text
        assert "costs you" in text


class TestRisk:
    def test_max_drawdown(self):
        lines = _section_risk(MIXED_TRADES)
        text = "\n".join(lines)
        assert "RISK ASSESSMENT" in text
        assert "Max drawdown:" in text

    def test_stop_loss_usage(self):
        lines = _section_risk(MIXED_TRADES)
        text = "\n".join(lines)
        assert "Stop loss" in text

    def test_no_sl_warns(self):
        no_sl = [_trade("EURUSD", 50, stop_loss=None, trade_id="ns1")]
        lines = _section_risk(no_sl)
        text = "\n".join(lines)
        assert "0%" in text or "0/1" in text

    def test_lot_stats(self):
        lines = _section_risk(MIXED_TRADES)
        text = "\n".join(lines)
        assert "Avg lot:" in text



# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------

class TestGenerateFullReport:
    def test_empty_trades(self):
        report = generate_full_report([])
        assert "No trades" in report

    def test_contains_all_sections(self):
        report = generate_full_report(MIXED_TRADES)
        assert "OVERVIEW" in report
        assert "STRENGTHS" in report
        assert "WEAKNESSES" in report
        assert "BEHAVIORAL" in report
        assert "RISK ASSESSMENT" in report
        assert "RECOMMENDATIONS" not in report

    def test_no_formatting_bugs(self):
        report = generate_full_report(MIXED_TRADES)
        assert "+$-" not in report  # no double-sign
        assert "Unknown" not in report  # no Unknown sessions

    def test_single_trade(self):
        single = [_trade("EURUSD", 50, trade_id="s1")]
        report = generate_full_report(single)
        assert "OVERVIEW" in report
        assert "1" in report  # total trades

    def test_all_losers(self):
        losers = [
            _trade("EURUSD", -50, trade_id="l1",
                   closed_at="2024-01-01T10:00:00"),
            _trade("GBPUSD", -30, trade_id="l2",
                   closed_at="2024-01-02T10:00:00"),
        ]
        report = generate_full_report(losers)
        assert "OVERVIEW" in report
        assert "Win rate: 0.0%" in report

    def test_with_emotions(self):
        trades = [
            _trade("EURUSD", 100, trade_id="t1"),
            _trade("EURUSD", -50, trade_id="t2"),
        ]
        emotions = [
            {"emotion": "calm", "trade_id": "t1", "context": "post_trade"},
            {"emotion": "revenge", "trade_id": "t2", "context": "post_trade"},
        ]
        report = generate_full_report(trades, emotions)
        assert "EMOTION INSIGHTS" in report
        assert "calm" in report
        assert "revenge" in report

    def test_without_emotions(self):
        report = generate_full_report(MIXED_TRADES)
        assert "EMOTION" not in report

    def test_pnl_formatting_negative(self):
        losers = [_trade("EURUSD", -500, trade_id="l1")]
        report = generate_full_report(losers)
        assert "-$502.00" in report  # -500 + -2 commission
        assert "+$-" not in report
