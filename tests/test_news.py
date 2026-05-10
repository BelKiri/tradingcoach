"""Tests for news service — keyword matching, trade-news matching, context building."""

from datetime import datetime

import pytest

from tradecoach.services.news import (
    build_news_context_for_coaching,
    get_relevant_news_for_trades,
    match_news_to_instruments,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _news(headline: str, date: str = "2025-01-10 13:00", summary: str = "",
          category: str = "forex") -> dict:
    return {
        "date": date,
        "headline": headline,
        "summary": summary,
        "source": "Reuters",
        "url": "",
        "category": category,
    }


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


# ---------------------------------------------------------------------------
# Keyword matching — direct instrument
# ---------------------------------------------------------------------------

class TestMatchNewsToInstrumentsDirect:
    def test_gold_headline(self):
        result = match_news_to_instruments(_news("Gold surges to new highs"))
        assert "XAUUSD" in result

    def test_ecb_matches_eurusd(self):
        result = match_news_to_instruments(_news("ECB raises rates by 25 bps"))
        assert "EURUSD" in result

    def test_bitcoin_matches_btcusd(self):
        result = match_news_to_instruments(_news("Bitcoin rallies past 100k"))
        assert "BTCUSD" in result

    def test_oil_matches_usoil(self):
        result = match_news_to_instruments(_news("Crude oil prices drop on OPEC news"))
        assert "USOIL" in result

    def test_nasdaq_matches_us100(self):
        result = match_news_to_instruments(_news("Nasdaq tech stocks rally"))
        assert "US100" in result

    def test_no_match_irrelevant(self):
        result = match_news_to_instruments(_news("Apple announces new iPhone"))
        assert result == []

    def test_summary_also_checked(self):
        result = match_news_to_instruments(
            _news("Market update", summary="Gold price hits record")
        )
        assert "XAUUSD" in result

    def test_case_insensitive(self):
        result = match_news_to_instruments(_news("GOLD PRICE SURGES"))
        assert "XAUUSD" in result


# ---------------------------------------------------------------------------
# Keyword matching — cross-asset
# ---------------------------------------------------------------------------

class TestMatchNewsToInstrumentsCrossAsset:
    def test_nfp_matches_usd_basket(self):
        result = match_news_to_instruments(_news("NFP beats expectations"))
        assert "EURUSD" in result
        assert "GBPUSD" in result
        assert "USDJPY" in result
        assert "USDCAD" in result
        assert "AUDUSD" in result
        assert "XAUUSD" in result
        assert "US500" in result

    def test_fomc_matches_usd_basket(self):
        result = match_news_to_instruments(_news("FOMC holds rates steady"))
        assert "EURUSD" in result
        assert "XAUUSD" in result

    def test_iran_matches_geopolitics(self):
        result = match_news_to_instruments(_news("Iran launches missiles"))
        assert "XAUUSD" in result
        assert "USOIL" in result
        assert "US500" in result
        assert "USDJPY" in result

    def test_recession_matches_risk_sentiment(self):
        result = match_news_to_instruments(_news("US recession fears grow"))
        assert "XAUUSD" in result
        assert "US500" in result
        assert "BTCUSD" in result

    def test_crypto_regulation(self):
        result = match_news_to_instruments(
            _news("SEC crypto regulation tightens")
        )
        assert "BTCUSD" in result
        assert "XRPUSD" in result


# ---------------------------------------------------------------------------
# Keyword matching — combined direct + cross-asset
# ---------------------------------------------------------------------------

class TestMatchNewsCombined:
    def test_gold_and_iran_deduplicated(self):
        """'Gold surges on Iran tensions' → direct gold + cross geopolitics."""
        result = match_news_to_instruments(
            _news("Gold surges on Iran tensions")
        )
        assert "XAUUSD" in result  # direct + geopolitics
        assert "USOIL" in result   # geopolitics
        assert "US500" in result   # geopolitics
        assert "USDJPY" in result  # geopolitics
        # XAUUSD should appear only once (deduplicated)
        assert result.count("XAUUSD") == 1

    def test_bitcoin_etf_combined(self):
        """'Bitcoin ETF approved by SEC' → direct bitcoin + cross crypto."""
        result = match_news_to_instruments(
            _news("Bitcoin ETF approved by SEC", summary="etf bitcoin milestone")
        )
        assert "BTCUSD" in result
        assert "XRPUSD" in result


# ---------------------------------------------------------------------------
# News-trade matching — time window
# ---------------------------------------------------------------------------

class TestGetRelevantNewsForTrades:
    def test_news_within_window(self):
        """Trade at 14:00, news at 13:00 → matched (1 hour before)."""
        trades = [_trade("XAUUSD", "2025-01-10T14:00:00")]
        news = [_news("Gold rises sharply", date="2025-01-10 13:00")]
        result = get_relevant_news_for_trades(trades, news, "UTC+0")
        assert len(result) == 1
        assert result[0]["relevant_news"][0]["headline"] == "Gold rises sharply"

    def test_news_outside_window(self):
        """Trade at 14:00, news at 11:59 → NOT matched (>2 hours)."""
        trades = [_trade("XAUUSD", "2025-01-10T14:00:00")]
        news = [_news("Gold rises sharply", date="2025-01-10 11:59")]
        result = get_relevant_news_for_trades(trades, news, "UTC+0")
        assert len(result) == 0

    def test_wrong_instrument(self):
        """Trade EURUSD at 14:00, news 'gold rises' at 13:00 → NOT matched."""
        trades = [_trade("EURUSD", "2025-01-10T14:00:00")]
        news = [_news("Gold rises sharply", date="2025-01-10 13:00")]
        result = get_relevant_news_for_trades(trades, news, "UTC+0")
        assert len(result) == 0

    def test_cross_asset_match(self):
        """Trade XAUUSD at 14:00, news 'Iran attacks' at 13:30 → matched via cross-asset."""
        trades = [_trade("XAUUSD", "2025-01-10T14:00:00")]
        news = [_news("Iran launches attack on base", date="2025-01-10 13:30")]
        result = get_relevant_news_for_trades(trades, news, "UTC+0")
        assert len(result) == 1
        assert result[0]["relevant_news"][0]["matched_via"] == "cross-asset"

    def test_news_after_trade_not_matched(self):
        """News at 15:00, trade at 14:00 → NOT matched (news is after trade)."""
        trades = [_trade("XAUUSD", "2025-01-10T14:00:00")]
        news = [_news("Gold rises sharply", date="2025-01-10 15:00")]
        result = get_relevant_news_for_trades(trades, news, "UTC+0")
        assert len(result) == 0

    def test_broker_timezone_applied(self):
        """Trade at 16:00 broker (UTC+2) = 14:00 UTC, news at 13:00 UTC → matched."""
        trades = [_trade("XAUUSD", "2025-01-10T16:00:00")]
        news = [_news("Gold rises sharply", date="2025-01-10 13:00")]
        result = get_relevant_news_for_trades(trades, news, "UTC+2")
        assert len(result) == 1

    def test_multiple_news_for_one_trade(self):
        """Two news items within window for the same trade."""
        trades = [_trade("XAUUSD", "2025-01-10T14:00:00")]
        news = [
            _news("Gold rises sharply", date="2025-01-10 13:00"),
            _news("Gold demand increases", date="2025-01-10 13:30"),
        ]
        result = get_relevant_news_for_trades(trades, news, "UTC+0")
        assert len(result) == 1
        assert len(result[0]["relevant_news"]) == 2

    def test_empty_trades(self):
        result = get_relevant_news_for_trades([], [_news("Gold")], "UTC+0")
        assert result == []

    def test_empty_news(self):
        result = get_relevant_news_for_trades(
            [_trade("XAUUSD", "2025-01-10T14:00:00")], [], "UTC+0"
        )
        assert result == []

    def test_exact_boundary_included(self):
        """Trade at 14:00, news at 12:00 → exactly 2 hours → included."""
        trades = [_trade("XAUUSD", "2025-01-10T14:00:00")]
        news = [_news("Gold rises sharply", date="2025-01-10 12:00")]
        result = get_relevant_news_for_trades(trades, news, "UTC+0")
        assert len(result) == 1

    def test_direct_match_via(self):
        """Direct keyword match shows matched_via='direct'."""
        trades = [_trade("XAUUSD", "2025-01-10T14:00:00")]
        news = [_news("Gold price hits new high", date="2025-01-10 13:00")]
        result = get_relevant_news_for_trades(trades, news, "UTC+0")
        assert result[0]["relevant_news"][0]["matched_via"] == "direct"


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------

class TestBuildNewsContextForCoaching:
    def test_basic_output(self):
        """5 trades + 3 news items → formatted string with correct groupings."""
        trades = [
            _trade("XAUUSD", "2025-01-10T14:00:00", pnl=-312, direction="sell"),
            _trade("XAUUSD", "2025-01-11T10:00:00", pnl=445, direction="buy"),
            _trade("EURUSD", "2025-01-12T14:30:00", pnl=-487, direction="buy"),
            _trade("GBPUSD", "2025-01-13T10:00:00", pnl=120, direction="buy"),
            _trade("XAUUSD", "2025-01-14T10:00:00", pnl=200, direction="buy"),
        ]
        news = [
            _news(
                "Iran-Israel military escalation",
                date="2025-01-10 13:00",
                category="general",
            ),
            _news(
                "Gold demand surges in Asian markets",
                date="2025-01-11 09:00",
            ),
            _news(
                "Strong NFP data boosts dollar",
                date="2025-01-12 13:30",
            ),
        ]
        ctx = build_news_context_for_coaching(trades, news, "UTC+0")
        assert "NEWS CONTEXT:" in ctx
        assert "XAUUSD" in ctx
        assert "EURUSD" in ctx
        assert "Iran-Israel" in ctx
        assert "Gold demand" in ctx
        assert "NFP" in ctx
        assert "Trades with nearby news" in ctx
        assert "Trades without news" in ctx
        assert "Do not assume direction" in ctx

    def test_empty_trades(self):
        ctx = build_news_context_for_coaching([], [_news("Gold")], "UTC+0")
        assert ctx == ""

    def test_no_matching_news(self):
        """Trades with no matching news → empty string."""
        trades = [_trade("XAUUSD", "2025-01-10T14:00:00")]
        news = [_news("Apple announces iPhone", date="2025-01-10 13:00")]
        ctx = build_news_context_for_coaching(trades, news, "UTC+0")
        assert ctx == ""

    def test_wr_pnl_in_output(self):
        """WR and PnL stats appear in output."""
        trades = [
            _trade("XAUUSD", "2025-01-10T14:00:00", pnl=100),
            _trade("XAUUSD", "2025-01-10T15:00:00", pnl=-50),
            _trade("EURUSD", "2025-01-11T10:00:00", pnl=30),
        ]
        news = [
            _news("Gold price surges", date="2025-01-10 13:00"),
            _news("Gold price continues rally", date="2025-01-10 14:00"),
        ]
        ctx = build_news_context_for_coaching(trades, news, "UTC+0")
        # 2 trades with news, 1 without
        assert "Trades with nearby news: WR 50%" in ctx
        assert "Trades without news: WR 100%" in ctx

    def test_instrument_grouping(self):
        """Multiple instruments are grouped separately."""
        trades = [
            _trade("XAUUSD", "2025-01-10T14:00:00", pnl=100),
            _trade("USOIL", "2025-01-10T14:00:00", pnl=-50),
        ]
        news = [
            _news("Iran launches missiles at base", date="2025-01-10 13:00"),
        ]
        ctx = build_news_context_for_coaching(trades, news, "UTC+0")
        assert "XAUUSD" in ctx
        assert "USOIL" in ctx
