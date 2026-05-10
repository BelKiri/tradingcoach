"""Tests for news_collector — collect, deduplicate, store, query."""

from unittest.mock import MagicMock, patch

import pytest

from tradecoach.services.news_collector import collect_and_store_news, get_news_for_period


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finnhub_item(headline: str, date: str = "2026-03-12 10:00",
                  category: str = "forex") -> dict:
    return {
        "date": date,
        "headline": headline,
        "summary": "Some summary text",
        "source": "Reuters",
        "url": "https://example.com",
        "category": category,
    }


def _mock_client(existing_rows=None):
    """Create a mock Supabase client."""
    client = MagicMock()
    # Chain for select (dedup check)
    select_result = MagicMock()
    select_result.data = existing_rows or []
    client.table.return_value.select.return_value.gte.return_value.execute.return_value = select_result
    # Chain for insert
    insert_result = MagicMock()
    insert_result.data = []
    client.table.return_value.insert.return_value.execute.return_value = insert_result
    return client


# ---------------------------------------------------------------------------
# collect_and_store_news
# ---------------------------------------------------------------------------

class TestCollectAndStoreNews:

    @patch("tradecoach.services.news_collector.get_client")
    @patch("tradecoach.services.news_collector.fetch_all_news")
    def test_inserts_new_items(self, mock_fetch, mock_get_client):
        mock_fetch.return_value = [
            _finnhub_item("Fed raises rates"),
            _finnhub_item("Oil prices surge", category="general"),
        ]
        client = _mock_client()
        mock_get_client.return_value = client

        count = collect_and_store_news()

        assert count == 2
        client.table.return_value.insert.assert_called_once()
        rows = client.table.return_value.insert.call_args[0][0]
        assert len(rows) == 2
        assert rows[0]["headline"] == "Fed raises rates"
        assert rows[1]["headline"] == "Oil prices surge"

    @patch("tradecoach.services.news_collector.get_client")
    @patch("tradecoach.services.news_collector.fetch_all_news")
    def test_deduplicates_existing(self, mock_fetch, mock_get_client):
        mock_fetch.return_value = [
            _finnhub_item("Fed raises rates", "2026-03-12 10:00"),
            _finnhub_item("New headline", "2026-03-12 11:00"),
        ]
        client = _mock_client(existing_rows=[
            {"headline": "Fed raises rates", "date": "2026-03-12T10:00:00+00:00"},
        ])
        mock_get_client.return_value = client

        count = collect_and_store_news()

        assert count == 1
        rows = client.table.return_value.insert.call_args[0][0]
        assert rows[0]["headline"] == "New headline"

    @patch("tradecoach.services.news_collector.get_client")
    @patch("tradecoach.services.news_collector.fetch_all_news")
    def test_all_duplicates_returns_zero(self, mock_fetch, mock_get_client):
        mock_fetch.return_value = [
            _finnhub_item("Fed raises rates", "2026-03-12 10:00"),
        ]
        client = _mock_client(existing_rows=[
            {"headline": "Fed raises rates", "date": "2026-03-12T10:00:00+00:00"},
        ])
        mock_get_client.return_value = client

        count = collect_and_store_news()

        assert count == 0
        client.table.return_value.insert.assert_not_called()

    @patch("tradecoach.services.news_collector.get_client")
    @patch("tradecoach.services.news_collector.fetch_all_news")
    def test_no_items_fetched(self, mock_fetch, mock_get_client):
        mock_fetch.return_value = []
        count = collect_and_store_news()
        assert count == 0

    @patch("tradecoach.services.news_collector.get_client")
    @patch("tradecoach.services.news_collector.fetch_all_news")
    def test_matched_instruments_stored(self, mock_fetch, mock_get_client):
        mock_fetch.return_value = [
            _finnhub_item("ECB cuts eurozone interest rates"),
        ]
        client = _mock_client()
        mock_get_client.return_value = client

        collect_and_store_news()

        rows = client.table.return_value.insert.call_args[0][0]
        # ECB + eurozone should match EUR pairs
        assert isinstance(rows[0]["matched_instruments"], list)

    @patch("tradecoach.services.news_collector.get_client")
    @patch("tradecoach.services.news_collector.fetch_all_news")
    def test_deduplicates_within_batch(self, mock_fetch, mock_get_client):
        """Same headline+date appearing twice in fetched data should only insert once."""
        mock_fetch.return_value = [
            _finnhub_item("Fed raises rates", "2026-03-12 10:00"),
            _finnhub_item("Fed raises rates", "2026-03-12 10:00"),
        ]
        client = _mock_client()
        mock_get_client.return_value = client

        count = collect_and_store_news()

        assert count == 1


# ---------------------------------------------------------------------------
# get_news_for_period
# ---------------------------------------------------------------------------

class TestGetNewsForPeriod:

    @patch("tradecoach.services.news_collector.get_client")
    def test_basic_query(self, mock_get_client):
        client = MagicMock()
        mock_get_client.return_value = client

        query_chain = MagicMock()
        client.table.return_value.select.return_value = query_chain
        query_chain.gte.return_value = query_chain
        query_chain.lte.return_value = query_chain
        query_chain.order.return_value = query_chain
        query_chain.limit.return_value = query_chain
        query_chain.execute.return_value.data = [
            {"headline": "Test", "date": "2026-03-12T10:00:00"}
        ]

        result = get_news_for_period("2026-03-12", "2026-03-12")

        assert len(result) == 1
        assert result[0]["headline"] == "Test"

    @patch("tradecoach.services.news_collector.get_client")
    def test_with_instruments_filter(self, mock_get_client):
        client = MagicMock()
        mock_get_client.return_value = client

        query_chain = MagicMock()
        client.table.return_value.select.return_value = query_chain
        query_chain.gte.return_value = query_chain
        query_chain.lte.return_value = query_chain
        query_chain.order.return_value = query_chain
        query_chain.limit.return_value = query_chain
        query_chain.overlaps.return_value = query_chain
        query_chain.execute.return_value.data = []

        result = get_news_for_period("2026-03-12", "2026-03-12", instruments=["EURUSD"])

        query_chain.overlaps.assert_called_once_with("matched_instruments", ["EURUSD"])
        assert result == []
