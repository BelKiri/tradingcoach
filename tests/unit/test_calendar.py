"""Tests for economic calendar service — matching, news impact."""

from datetime import datetime, timezone

import pytest

from tradecoach.services.calendar import (
    calculate_news_impact,
    load_calendar,
    match_trades_to_events,
)


# ---------------------------------------------------------------------------
# Load calendar
# ---------------------------------------------------------------------------

class TestLoadCalendar:
    def test_load_all(self):
        events = load_calendar()
        assert len(events) > 100

    def test_filter_date_range(self):
        events = load_calendar(date_from="2025-01-01", date_to="2025-01-31")
        assert all(e["date"].startswith("2025-01") for e in events)
        assert len(events) >= 4

    def test_all_high_impact(self):
        events = load_calendar()
        assert all(e["impact"] == "high" for e in events)

    def test_required_fields(self):
        events = load_calendar(date_from="2025-01-01", date_to="2025-01-31")
        for e in events:
            assert "date" in e
            assert "time_utc" in e
            assert "currency" in e
            assert "event_name" in e
            assert "impact" in e


# ---------------------------------------------------------------------------
# Match trades to events (true UTC trade opens vs UTC event times)
# ---------------------------------------------------------------------------

def _make_trade(opened_at: str, pnl: float = 0.0) -> dict:
    """opened_at is naive local clock in tests; append UTC for stored convention."""
    s = opened_at
    if "+" not in s and "Z" not in s:
        s = s + "+00:00"
    return {
        "opened_at": s,
        "symbol": "EURUSD",
        "direction": "buy",
        "lot": 0.1,
        "profit_money": pnl,
        "commission": 0.0,
        "swap": 0.0,
    }


NFP_EVENT = {
    "date": "2025-01-10",
    "time_utc": "13:30",
    "currency": "USD",
    "event_name": "Non-Farm Payrolls",
    "impact": "high",
}


class TestMatchTradesToEvents:
    def test_trade_before_event_within_window(self):
        trade = _make_trade("2025-01-10T13:00:00")
        result = match_trades_to_events([trade], [NFP_EVENT])
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == -30

    def test_trade_after_event_within_window(self):
        trade = _make_trade("2025-01-10T14:00:00")
        result = match_trades_to_events([trade], [NFP_EVENT])
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == 30

    def test_trade_outside_window_after(self):
        trade = _make_trade("2025-01-10T14:31:00")
        result = match_trades_to_events([trade], [NFP_EVENT])
        assert len(result) == 0

    def test_trade_outside_window_before(self):
        trade = _make_trade("2025-01-10T12:29:00")
        result = match_trades_to_events([trade], [NFP_EVENT])
        assert len(result) == 0

    def test_boundary_30_min_before_included(self):
        trade = _make_trade("2025-01-10T13:00:00")
        result = match_trades_to_events([trade], [NFP_EVENT])
        assert len(result) == 1

    def test_boundary_60_min_after_included(self):
        trade = _make_trade("2025-01-10T14:30:00")
        result = match_trades_to_events([trade], [NFP_EVENT])
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == 60

    def test_trade_60_min_before_does_not_match(self):
        trade = _make_trade("2025-01-10T12:30:00")
        result = match_trades_to_events([trade], [NFP_EVENT])
        assert len(result) == 0

    def test_datetime_object_trade_open(self):
        dt = datetime(2025, 1, 10, 13, 0, tzinfo=timezone.utc)
        trade = {
            "opened_at": dt,
            "symbol": "EURUSD",
            "direction": "buy",
            "lot": 0.1,
            "profit_money": 0.0,
            "commission": 0.0,
            "swap": 0.0,
        }
        result = match_trades_to_events([trade], [NFP_EVENT])
        assert len(result) == 1


class TestDeduplication:
    def test_trade_matches_two_events_appears_once(self):
        events = [
            NFP_EVENT,
            {
                "date": "2025-01-10",
                "time_utc": "14:00",
                "currency": "USD",
                "event_name": "CPI",
                "impact": "high",
            },
        ]
        trade = _make_trade("2025-01-10T13:45:00")
        result = match_trades_to_events([trade], events)
        assert len(result) == 1
        assert len(result[0]["matched_events"]) == 2


class TestCalculateNewsImpact:
    def _build_scenario(self):
        events = [NFP_EVENT]
        news_trades = [
            _make_trade("2025-01-10T13:25:00", pnl=50.0),
            _make_trade("2025-01-10T13:35:00", pnl=-100.0),
            _make_trade("2025-01-10T14:00:00", pnl=-80.0),
        ]
        normal_trades = [
            _make_trade("2025-01-06T10:00:00", pnl=40.0),
            _make_trade("2025-01-06T11:00:00", pnl=30.0),
            _make_trade("2025-01-07T10:00:00", pnl=60.0),
            _make_trade("2025-01-07T11:00:00", pnl=-50.0),
            _make_trade("2025-01-08T10:00:00", pnl=45.0),
            _make_trade("2025-01-08T11:00:00", pnl=35.0),
            _make_trade("2025-01-09T10:00:00", pnl=-40.0),
        ]
        return news_trades + normal_trades, events

    def test_split_counts(self):
        trades, events = self._build_scenario()
        result = calculate_news_impact(trades, events)
        assert result["news_trades_count"] == 3
        assert result["normal_trades_count"] == 7

    def test_empty_trades(self):
        result = calculate_news_impact([], [NFP_EVENT])
        assert result["news_trades_count"] == 0
