"""Upload deduplication and upload endpoint size limits."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from tradecoach.api.upload import MAX_UPLOAD_SIZE_BYTES, UPLOAD_TOO_LARGE_DETAIL
from tradecoach.db.queries import trade_dedup_key
from tradecoach.main import app

UTC = timezone.utc


def _legacy_db_timestamp_key(opened_at: str) -> str:
    """Pre-fix DB path: fromisoformat + isoformat (keeps offset)."""
    dt = datetime.fromisoformat(opened_at)
    return dt.replace(second=0, microsecond=0).isoformat()


def _legacy_incoming_timestamp_key(opened_at: datetime) -> str:
    """Pre-fix incoming path: strip tz, then str()."""
    naive = opened_at.replace(tzinfo=None)
    return str(naive.replace(second=0, microsecond=0))


@pytest.fixture
def same_trade_db_row() -> dict:
    """Shape returned by Supabase select on trades."""
    return {
        "symbol": "EURUSD",
        "opened_at": "2024-01-15T10:30:45+00:00",
        "direction": "buy",
        "lot": 1.0,
    }


@pytest.fixture
def same_trade_incoming_row() -> dict:
    """Shape from parser + TradeCreate.model_dump() after UTC conversion."""
    return {
        "symbol": "EURUSD",
        "opened_at": datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC),
        "direction": "buy",
        "lot": 1,  # int lot from parser; same size as 0.1 after float()
    }


def test_trade_dedup_key_matches_db_and_incoming_shapes(
    same_trade_db_row: dict,
    same_trade_incoming_row: dict,
) -> None:
    db_key = trade_dedup_key(same_trade_db_row)
    incoming_key = trade_dedup_key(same_trade_incoming_row)

    assert db_key == incoming_key
    assert db_key == (
        "EURUSD",
        "2024-01-15T10:30:00+00:00",
        "buy",
        1.0,
    )


def test_trade_dedup_key_normalizes_missing_symbol_and_int_lot() -> None:
    row = {
        "symbol": None,
        "opened_at": "2024-01-15T10:30:00+00:00",
        "direction": None,
        "lot": 1,
    }
    assert trade_dedup_key(row) == (
        "",
        "2024-01-15T10:30:00+00:00",
        "",
        1.0,
    )


def test_legacy_timestamp_formats_would_not_match() -> None:
    """Regression guard: pre-fix paths produced unequal timestamp strings."""
    opened_db = "2024-01-15T10:30:45+00:00"
    opened_incoming = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)

    assert _legacy_db_timestamp_key(opened_db) != _legacy_incoming_timestamp_key(
        opened_incoming
    )


def test_trade_dedup_key_incoming_matches_existing_set(
    same_trade_db_row: dict,
    same_trade_incoming_row: dict,
) -> None:
    """Incoming key is recognized as duplicate when existing set uses DB rows."""
    existing = {trade_dedup_key(same_trade_db_row)}
    assert trade_dedup_key(same_trade_incoming_row) in existing


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file_with_413() -> None:
    oversized = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/upload/test-user-1",
            data={"account_id": ""},
            files={"file": ("trades.csv", oversized, "text/csv")},
        )

    assert resp.status_code == 413
    assert resp.json()["detail"] == UPLOAD_TOO_LARGE_DETAIL


@pytest.mark.asyncio
async def test_upload_happy_path_small_csv_returns_200() -> None:
    sample_trade = {
        "symbol": "EURUSD",
        "direction": "buy",
        "lot": 0.1,
        "opened_at": "2024-01-01T10:00:00",
        "closed_at": "2024-01-01T11:00:00",
    }
    with (
        patch("tradecoach.api.upload.get_client"),
        patch("tradecoach.api.upload.assert_can_upload_file"),
        patch("tradecoach.api.upload.parse_mt4_csv", return_value=[sample_trade]),
        patch("tradecoach.api.upload.find_existing_trade_keys", return_value=set()),
        patch("tradecoach.api.upload.insert_trades", return_value=[]),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/upload/test-user-1",
                data={"account_id": ""},
                files={"file": ("trades.csv", b"ticket,symbol\n", "text/csv")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["trades_parsed"] == 1
    assert body["trades_new"] == 1
    assert body["trades_saved"] == 0
