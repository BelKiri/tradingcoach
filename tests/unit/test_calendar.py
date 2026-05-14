"""Tests for economic calendar service — timezone, matching, news impact."""

from datetime import datetime

import pytest

from tradecoach.services.calendar import (
    calculate_news_impact,
    convert_trade_time_to_utc,
    load_calendar,
    match_trades_to_events,
)


# ---------------------------------------------------------------------------
# Timezone conversion
# ---------------------------------------------------------------------------

class TestConvertTradeTimeToUtc:
    def test_utc_plus_2(self):
        """15:30 UTC+2 → 13:30 UTC."""
        dt = datetime(2025, 1, 10, 15, 30)
        result = convert_trade_time_to_utc(dt, "UTC+2")
        assert result == datetime(2025, 1, 10, 13, 30)

    def test_utc_plus_0(self):
        """13:30 UTC+0 → 13:30 UTC (no change)."""
        dt = datetime(2025, 1, 10, 13, 30)
        result = convert_trade_time_to_utc(dt, "UTC+0")
        assert result == datetime(2025, 1, 10, 13, 30)

    def test_utc_plus_3(self):
        """16:30 UTC+3 → 13:30 UTC."""
        dt = datetime(2025, 1, 10, 16, 30)
        result = convert_trade_time_to_utc(dt, "UTC+3")
        assert result == datetime(2025, 1, 10, 13, 30)

    def test_string_input(self):
        """Accept ISO string as input."""
        result = convert_trade_time_to_utc("2025-01-10T15:30:00", "UTC+2")
        assert result == datetime(2025, 1, 10, 13, 30)

    def test_midnight_crossing(self):
        """01:30 UTC+3 → 22:30 previous day UTC."""
        dt = datetime(2025, 1, 10, 1, 30)
        result = convert_trade_time_to_utc(dt, "UTC+3")
        assert result == datetime(2025, 1, 9, 22, 30)

    def test_invalid_tz_defaults_zero(self):
        """Invalid timezone string defaults to UTC+0."""
        dt = datetime(2025, 1, 10, 13, 30)
        result = convert_trade_time_to_utc(dt, "invalid")
        assert result == datetime(2025, 1, 10, 13, 30)


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
        assert len(events) >= 4  # NFP, CPI, FOMC, GDP at minimum

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
# Match trades to events
# ---------------------------------------------------------------------------

def _make_trade(opened_at: str, pnl: float = 0.0) -> dict:
    """Helper to build a trade dict."""
    return {
        "opened_at": datetime.fromisoformat(opened_at),
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
        """Trade at 13:00 UTC, event at 13:30 UTC → match, offset -30."""
        trade = _make_trade("2025-01-10T13:00:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == -30

    def test_trade_after_event_within_window(self):
        """Trade at 14:00 UTC, event at 13:30 UTC → match, offset +30."""
        trade = _make_trade("2025-01-10T14:00:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == 30

    def test_trade_outside_window_after(self):
        """Trade at 14:31 UTC, event at 13:30 UTC → NOT match (61 min)."""
        trade = _make_trade("2025-01-10T14:31:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 0

    def test_trade_outside_window_before(self):
        """Trade at 12:29 UTC, event at 13:30 UTC → NOT match (61 min before)."""
        trade = _make_trade("2025-01-10T12:29:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 0

    def test_boundary_30_min_before_included(self):
        """Trade exactly on event_time - 30 min → match (inclusive lower bound)."""
        trade = _make_trade("2025-01-10T13:00:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == -30

    def test_boundary_60_min_after_included(self):
        """Trade exactly on event_time + 60 min → match (inclusive upper bound)."""
        trade = _make_trade("2025-01-10T14:30:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == 60

    def test_trade_60_min_before_does_not_match(self):
        """60 min before event is outside the default 30 min pre-window."""
        trade = _make_trade("2025-01-10T12:30:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 0

    def test_trade_45_min_after_event_matches(self):
        """Trade 45 min after NFP (within 60 min after) matches."""
        trade = _make_trade("2025-01-10T14:15:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == 45

    def test_trade_50_min_after_event_matches(self):
        """Trade 50 min after NFP (within 60 min after) matches."""
        trade = _make_trade("2025-01-10T14:20:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == 50

    def test_trade_65_min_after_event_does_not_match(self):
        """Trade 65 min after NFP is outside the 60 min post-window."""
        trade = _make_trade("2025-01-10T14:35:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 0

    def test_trade_25_min_before_event_matches(self):
        """Trade 25 min before NFP (within 30 min before) matches."""
        trade = _make_trade("2025-01-10T13:05:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == -25

    def test_trade_35_min_before_event_does_not_match(self):
        """Trade 35 min before NFP is outside the 30 min pre-window."""
        trade = _make_trade("2025-01-10T12:55:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+0")
        assert len(result) == 0

    def test_broker_timezone_conversion(self):
        """Trade at 15:00 broker time (UTC+2) = 13:00 UTC → match NFP at 13:30."""
        trade = _make_trade("2025-01-10T15:00:00")
        result = match_trades_to_events([trade], [NFP_EVENT], "UTC+2")
        assert len(result) == 1
        assert result[0]["matched_events"][0]["minutes_offset"] == -30


class TestDeduplication:
    def test_trade_matches_two_events_appears_once(self):
        """Two events at 13:30 and 14:00, trade at 13:45 → matches both, trade appears once."""
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
        result = match_trades_to_events([trade], events, "UTC+0")
        assert len(result) == 1  # trade appears once
        assert len(result[0]["matched_events"]) == 2  # matched to both events

    def test_no_duplicate_trades(self):
        """Multiple events, each trade only in result once."""
        events = [NFP_EVENT] * 3  # same event duplicated
        trade = _make_trade("2025-01-10T13:30:00")
        result = match_trades_to_events([trade], events, "UTC+0")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# News impact calculation
# ---------------------------------------------------------------------------

class TestCalculateNewsImpact:
    def _build_scenario(self):
        """10 trades: 3 near NFP (1 win, 2 loss), 7 normal (5 win, 2 loss)."""
        events = [NFP_EVENT]

        # News trades: opened near 13:30 UTC on NFP day (using UTC+0)
        news_trades = [
            _make_trade("2025-01-10T13:25:00", pnl=50.0),   # win
            _make_trade("2025-01-10T13:35:00", pnl=-100.0),  # loss
            _make_trade("2025-01-10T14:00:00", pnl=-80.0),   # loss
        ]
        # Normal trades: different day, no event
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
        result = calculate_news_impact(trades, events, "UTC+0")
        assert result["news_trades_count"] == 3
        assert result["normal_trades_count"] == 7

    def test_news_win_rate(self):
        trades, events = self._build_scenario()
        result = calculate_news_impact(trades, events, "UTC+0")
        # 1 win out of 3 = 33.33%
        assert result["news_wr"] == pytest.approx(33.33, abs=0.01)

    def test_normal_win_rate(self):
        trades, events = self._build_scenario()
        result = calculate_news_impact(trades, events, "UTC+0")
        # 5 wins out of 7 = 71.43%
        assert result["normal_wr"] == pytest.approx(71.43, abs=0.01)

    def test_news_pnl(self):
        trades, events = self._build_scenario()
        result = calculate_news_impact(trades, events, "UTC+0")
        # 50 - 100 - 80 = -130
        assert result["news_pnl"] == pytest.approx(-130.0, abs=0.01)

    def test_normal_pnl(self):
        trades, events = self._build_scenario()
        result = calculate_news_impact(trades, events, "UTC+0")
        # 40 + 30 + 60 - 50 + 45 + 35 - 40 = 120
        assert result["normal_pnl"] == pytest.approx(120.0, abs=0.01)

    def test_worst_events_sorted(self):
        trades, events = self._build_scenario()
        result = calculate_news_impact(trades, events, "UTC+0")
        assert len(result["worst_events"]) == 1
        assert result["worst_events"][0]["event_name"] == "Non-Farm Payrolls"
        assert result["worst_events"][0]["pnl"] == pytest.approx(-130.0, abs=0.01)

    def test_empty_trades(self):
        result = calculate_news_impact([], [NFP_EVENT], "UTC+0")
        assert result["news_trades_count"] == 0
        assert result["normal_trades_count"] == 0

    def test_no_events(self):
        trades = [_make_trade("2025-01-10T13:30:00", pnl=50.0)]
        result = calculate_news_impact(trades, [], "UTC+0")
        assert result["news_trades_count"] == 0
        assert result["normal_trades_count"] == 1
