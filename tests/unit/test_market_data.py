"""Tests for market data service — ATR lookback, median-based volatility, trader analysis."""

from datetime import datetime

import pytest

from tradecoach.services.market_data import (
    SYMBOL_MAP,
    analyze_trader_volatility,
    build_volatility_context_for_coaching,
    calculate_atr_at_date,
    find_volatile_days,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ohlc(date: str, o: float, h: float, l: float, c: float) -> dict:
    return {"date": date, "open": o, "high": h, "low": l, "close": c}


def _trade(symbol: str, opened_at: str, pnl: float = 0.0,
           direction: str = "buy") -> dict:
    return {
        "opened_at": datetime.fromisoformat(opened_at),
        "symbol": symbol,
        "direction": direction,
        "lot": 0.1,
        "profit_money": pnl,
        "commission": 0.0,
        "swap": 0.0,
    }


def _make_ohlc_series(
    n: int = 30,
    base: float = 100.0,
    normal_range: float = 2.0,
    start_day: int = 1,
) -> list[dict]:
    """Generate n days of OHLC with consistent range.

    Dates: 2025-01-{start_day}, incrementing. Wraps to 2025-02-xx at day 29.
    close ≈ open so gaps are negligible and TR ≈ normal_range.
    """
    data = []
    for i in range(n):
        day_num = start_day + i
        month = 1 + (day_num - 1) // 28
        day_in_month = ((day_num - 1) % 28) + 1
        date = f"2025-{month:02d}-{day_in_month:02d}"
        o = base + i * 0.05
        h = o + normal_range / 2
        l_val = o - normal_range / 2
        c = o + 0.05
        data.append(_ohlc(date, o, h, l_val, c))
    return data


def _make_volatile_scenario():
    """Build 30-day OHLC where the LAST few days are volatile.

    Days 1-14: range=2 (normal baseline).
    Days 15-28: range=12 (elevated). ATR into these days ramps up.
    Days 29-30: range=2 (back to normal, but ATR still high from lookback).

    After the ramp-up, days 28-30 have ATR ≈ 11-12 while median ATR ≈ 7.
    Ratio ≈ 1.5-1.6 → these are the volatile days.
    """
    data = _make_ohlc_series(30, normal_range=2.0)
    for i in range(14, 28):
        d = data[i]["date"]
        data[i] = _ohlc(d, 100, 106, 94, 100)  # range = 12
    return data


def _get_volatile_dates(data: list[dict]) -> list[str]:
    """Return dates flagged as volatile by find_volatile_days."""
    result = find_volatile_days(
        "XAUUSD", data[14]["date"], data[-1]["date"], ohlc_data=data,
    )
    return [d["date"] for d in result]


# ---------------------------------------------------------------------------
# Symbol mapping
# ---------------------------------------------------------------------------

class TestSymbolMap:
    def test_forex_pairs(self):
        assert SYMBOL_MAP["EURUSD"] == "EUR/USD"
        assert SYMBOL_MAP["GBPUSD"] == "GBP/USD"
        assert SYMBOL_MAP["USDJPY"] == "USD/JPY"

    def test_commodities(self):
        assert SYMBOL_MAP["XAUUSD"] == "XAU/USD"
        assert SYMBOL_MAP["USOIL"] == "WTI/USD"

    def test_indices(self):
        assert SYMBOL_MAP["US500"] == "SPX"
        assert SYMBOL_MAP["US100"] == "NDX"

    def test_crypto(self):
        assert SYMBOL_MAP["BTCUSD"] == "BTC/USD"
        assert SYMBOL_MAP["XRPUSD"] == "XRP/USD"


# ---------------------------------------------------------------------------
# calculate_atr_at_date
# ---------------------------------------------------------------------------

class TestCalculateAtrAtDate:
    def test_uses_only_prior_days(self):
        """ATR at day 15 uses days 1-14, NOT day 15 itself."""
        data = _make_ohlc_series(20, normal_range=2.0)
        # Inject a huge spike on day 15 (index 14)
        data[14] = _ohlc(data[14]["date"], 100, 200, 50, 100)  # range 150
        target_date = data[14]["date"]
        atr = calculate_atr_at_date(data, target_date, period=14)
        # ATR should be ~2.0 (from the normal days), NOT inflated by the spike
        assert atr is not None
        assert atr == pytest.approx(2.0, abs=0.3)

    def test_not_enough_history(self):
        """Target day 5 with period=14 → None."""
        data = _make_ohlc_series(10, normal_range=2.0)
        target_date = data[4]["date"]
        atr = calculate_atr_at_date(data, target_date, period=14)
        assert atr is None

    def test_exact_minimum_history(self):
        """Target at index 14 → exactly 14 days before → valid."""
        data = _make_ohlc_series(20, normal_range=2.0)
        target_date = data[14]["date"]
        atr = calculate_atr_at_date(data, target_date, period=14)
        assert atr is not None
        assert atr == pytest.approx(2.0, abs=0.3)

    def test_known_atr_value(self):
        """14 days of range=10 before target → ATR = 10."""
        data = _make_ohlc_series(20, normal_range=10.0)
        target_date = data[14]["date"]
        atr = calculate_atr_at_date(data, target_date, period=14)
        assert atr is not None
        assert atr == pytest.approx(10.0, abs=0.5)

    def test_nonexistent_date_returns_none(self):
        data = _make_ohlc_series(20)
        atr = calculate_atr_at_date(data, "2099-12-31", period=14)
        assert atr is None

    def test_gap_up_included(self):
        """True range accounts for gaps."""
        data = _make_ohlc_series(16, normal_range=2.0)
        data[14] = _ohlc(data[14]["date"], 103, 108, 103, 105)
        target_date = data[15]["date"]
        atr = calculate_atr_at_date(data, target_date, period=14)
        assert atr is not None
        assert atr > 2.0  # slightly elevated by the gap


# ---------------------------------------------------------------------------
# find_volatile_days (median-based)
# ---------------------------------------------------------------------------

class TestFindVolatileDays:
    def test_spikes_create_volatile_days(self):
        """High-range block causes late days to have ATR > 1.5x median."""
        data = _make_volatile_scenario()
        result = find_volatile_days(
            "XAUUSD", data[14]["date"], data[-1]["date"], ohlc_data=data,
        )
        assert len(result) >= 1
        # All flagged days should have atr_ratio >= 1.5
        for vd in result:
            assert vd["atr_ratio"] >= 1.5

    def test_all_normal_no_volatile(self):
        """Uniform data → no volatile days."""
        data = _make_ohlc_series(30, normal_range=2.0)
        result = find_volatile_days(
            "XAUUSD", data[14]["date"], data[-1]["date"], ohlc_data=data,
        )
        assert len(result) == 0

    def test_boundary_below_threshold(self):
        """A single small bump doesn't push ATR to 1.5x median."""
        data = _make_ohlc_series(30, normal_range=10.0)
        data[19] = _ohlc(data[19]["date"], 100, 107, 93, 100)  # range 14
        result = find_volatile_days(
            "XAUUSD", data[14]["date"], data[-1]["date"], ohlc_data=data,
        )
        assert len(result) == 0

    def test_too_few_days(self):
        data = _make_ohlc_series(5)
        result = find_volatile_days(
            "XAUUSD", data[0]["date"], data[-1]["date"], ohlc_data=data,
        )
        assert result == []

    def test_result_fields(self):
        """Volatile days include all required fields."""
        data = _make_volatile_scenario()
        result = find_volatile_days(
            "XAUUSD", data[14]["date"], data[-1]["date"], ohlc_data=data,
        )
        assert len(result) >= 1
        vd = result[0]
        assert "atr" in vd
        assert "median_atr" in vd
        assert "atr_ratio" in vd
        assert "day_range" in vd
        assert "day_ratio" in vd


# ---------------------------------------------------------------------------
# analyze_trader_volatility
# ---------------------------------------------------------------------------

class TestAnalyzeTraderVolatility:
    def _build_scenario(self):
        """10 trades: 3 on volatile days, 7 on normal days."""
        data = _make_volatile_scenario()
        vol_dates = _get_volatile_dates(data)
        assert len(vol_dates) >= 1, "Test setup: need at least 1 volatile day"
        vol_date = vol_dates[0]

        # Find a normal date (early in series, before high-range block)
        normal_dates = [
            data[i]["date"] for i in range(4, 11)
            if data[i]["date"] not in vol_dates
        ]

        vol_trades = [
            _trade("XAUUSD", f"{vol_date}T10:00:00", pnl=-100),
            _trade("XAUUSD", f"{vol_date}T11:00:00", pnl=-150),
            _trade("XAUUSD", f"{vol_date}T14:00:00", pnl=50),
        ]
        normal = [
            _trade("XAUUSD", f"{normal_dates[0]}T10:00:00", pnl=40),
            _trade("XAUUSD", f"{normal_dates[0]}T11:00:00", pnl=30),
            _trade("XAUUSD", f"{normal_dates[1]}T10:00:00", pnl=60),
            _trade("XAUUSD", f"{normal_dates[1]}T11:00:00", pnl=-50),
            _trade("XAUUSD", f"{normal_dates[2]}T10:00:00", pnl=45),
            _trade("XAUUSD", f"{normal_dates[2]}T11:00:00", pnl=35),
            _trade("XAUUSD", f"{normal_dates[3]}T10:00:00", pnl=-40),
        ]

        return vol_trades + normal, {"XAUUSD": data}, vol_date

    def test_split_counts(self):
        trades, ohlc, _ = self._build_scenario()
        result = analyze_trader_volatility(trades, ohlc_by_symbol=ohlc)
        assert result["high_vol"]["count"] == 3
        assert result["normal"]["count"] == 7

    def test_high_vol_wr(self):
        trades, ohlc, _ = self._build_scenario()
        result = analyze_trader_volatility(trades, ohlc_by_symbol=ohlc)
        # 1 win / 3 = 33.33%
        assert result["high_vol"]["wr"] == pytest.approx(33.33, abs=0.01)

    def test_normal_wr(self):
        trades, ohlc, _ = self._build_scenario()
        result = analyze_trader_volatility(trades, ohlc_by_symbol=ohlc)
        # 5 wins / 7 = 71.43%
        assert result["normal"]["wr"] == pytest.approx(71.43, abs=0.01)

    def test_high_vol_pnl(self):
        trades, ohlc, _ = self._build_scenario()
        result = analyze_trader_volatility(trades, ohlc_by_symbol=ohlc)
        assert result["high_vol"]["pnl"] == pytest.approx(-200.0, abs=0.01)

    def test_normal_pnl(self):
        trades, ohlc, _ = self._build_scenario()
        result = analyze_trader_volatility(trades, ohlc_by_symbol=ohlc)
        # 40+30+60-50+45+35-40 = 120
        assert result["normal"]["pnl"] == pytest.approx(120.0, abs=0.01)

    def test_money_lost_to_volatility(self):
        trades, ohlc, _ = self._build_scenario()
        result = analyze_trader_volatility(trades, ohlc_by_symbol=ohlc)
        # normal avg_pnl = 120/7 ≈ 17.14
        # money_lost = -200 - 3*17.14 ≈ -251.43
        assert result["money_lost_to_volatility"] < 0
        assert result["money_lost_to_volatility"] == pytest.approx(-251.43, abs=1.0)

    def test_volatile_day_details(self):
        trades, ohlc, vol_date = self._build_scenario()
        result = analyze_trader_volatility(trades, ohlc_by_symbol=ohlc)
        days = result["high_vol"]["days"]
        assert len(days) >= 1
        vol_day = [d for d in days if d["date"] == vol_date]
        assert len(vol_day) == 1
        assert vol_day[0]["symbol"] == "XAUUSD"
        assert vol_day[0]["trades_count"] == 3
        assert vol_day[0]["day_pnl"] == pytest.approx(-200.0, abs=0.01)
        assert "atr_ratio" in vol_day[0]
        assert "day_range" in vol_day[0]
        assert "day_ratio" in vol_day[0]

    def test_empty_trades(self):
        result = analyze_trader_volatility([])
        assert result["high_vol"]["count"] == 0
        assert result["normal"]["count"] == 0

    def test_opens_use_utc_calendar_date(self):
        """opened_at naive is interpreted as UTC; same calendar day for vol split."""
        data = _make_volatile_scenario()
        vol_dates = _get_volatile_dates(data)
        assert len(vol_dates) >= 1
        vol_date = vol_dates[0]

        # 12:00 naive = 12:00 UTC wall clock; same calendar date as vol_date
        trades = [_trade("XAUUSD", f"{vol_date}T12:00:00", pnl=-100)]
        result = analyze_trader_volatility(
            trades, ohlc_by_symbol={"XAUUSD": data},
        )
        assert result["high_vol"]["count"] == 1


# ---------------------------------------------------------------------------
# build_volatility_context_for_coaching
# ---------------------------------------------------------------------------

class TestBuildVolatilityContext:
    def _build_scenario(self):
        data = _make_volatile_scenario()
        vol_dates = _get_volatile_dates(data)
        vol_date = vol_dates[0]
        norm_date = data[4]["date"]

        trades = [
            _trade("XAUUSD", f"{vol_date}T10:00:00", pnl=-100),
            _trade("XAUUSD", f"{vol_date}T11:00:00", pnl=-150),
            _trade("XAUUSD", f"{norm_date}T10:00:00", pnl=40),
            _trade("XAUUSD", f"{data[5]['date']}T10:00:00", pnl=60),
        ]
        return trades, {"XAUUSD": data}, vol_date

    def test_basic_output(self):
        trades, ohlc, vol_date = self._build_scenario()
        ctx = build_volatility_context_for_coaching(
            trades, ohlc_by_symbol=ohlc,
        )
        assert "VOLATILITY ANALYSIS:" in ctx
        assert "High-volatility days:" in ctx
        assert "Normal days:" in ctx
        assert vol_date in ctx
        assert "XAUUSD" in ctx

    def test_atr_language(self):
        trades, ohlc, _ = self._build_scenario()
        ctx = build_volatility_context_for_coaching(
            trades, ohlc_by_symbol=ohlc,
        )
        assert "ATR was 1.5x+ above normal BEFORE you entered" in ctx
        assert "ATR(14)" in ctx

    def test_contains_wr_and_pnl(self):
        trades, ohlc, _ = self._build_scenario()
        ctx = build_volatility_context_for_coaching(
            trades, ohlc_by_symbol=ohlc,
        )
        assert "WR" in ctx
        assert "P&L" in ctx

    def test_empty_trades(self):
        ctx = build_volatility_context_for_coaching([])
        assert ctx == ""

    def test_no_volatile_days(self):
        """All trades on normal days → empty string."""
        data = _make_ohlc_series(30, normal_range=2.0)
        trades = [_trade("XAUUSD", f"{data[15]['date']}T10:00:00", pnl=40)]
        ctx = build_volatility_context_for_coaching(
            trades, ohlc_by_symbol={"XAUUSD": data},
        )
        assert ctx == ""

    def test_money_lost_in_output(self):
        trades, ohlc, _ = self._build_scenario()
        ctx = build_volatility_context_for_coaching(
            trades, ohlc_by_symbol=ohlc,
        )
        assert "Difference:" in ctx

    def test_day_ratio_in_output(self):
        trades, ohlc, _ = self._build_scenario()
        ctx = build_volatility_context_for_coaching(
            trades, ohlc_by_symbol=ohlc,
        )
        assert "elevated ATR" in ctx

    def test_note_at_end(self):
        trades, ohlc, _ = self._build_scenario()
        ctx = build_volatility_context_for_coaching(
            trades, ohlc_by_symbol=ohlc,
        )
        assert "ATR calculated from 14 days before each trade" in ctx
