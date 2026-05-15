"""Tests for tz_utils — broker offset, UTC storage, IANA session buckets."""

from datetime import datetime, timedelta, timezone

import pytest

from tradecoach.api import upload as upload_api
from tradecoach.services.tz_utils import (
    DEFAULT_BROKER_TIMEZONE,
    broker_local_hour,
    naive_broker_wall_to_utc,
    resolve_broker_tz,
    session_label_for_utc,
    trade_instant_utc,
)


def test_default_broker_timezone_is_utc_plus_two():
    assert DEFAULT_BROKER_TIMEZONE == "UTC+2"


def test_resolve_broker_tz_utc_offset_and_iana():
    tz = resolve_broker_tz("UTC+2")
    assert tz.utcoffset(datetime(2024, 1, 1)) == timedelta(hours=2)
    tz0 = resolve_broker_tz("UTC-5")
    assert tz0.utcoffset(datetime(2024, 1, 1)) == timedelta(hours=-5)
    london = resolve_broker_tz("Europe/London")
    assert "Europe" in str(london) or hasattr(london, "key")


def test_naive_broker_wall_to_utc_subtracts_positive_offset():
    wall = datetime(2024, 1, 15, 14, 30, 0)
    utc = naive_broker_wall_to_utc(wall, "UTC+2")
    assert utc.tzinfo is timezone.utc
    assert utc == datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)


def test_trade_instant_utc_naive_is_utc_wall():
    dt = trade_instant_utc("2024-01-15T10:00:00")
    assert dt == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


def test_trade_instant_utc_z_suffix():
    dt = trade_instant_utc("2024-01-15T10:00:00Z")
    assert dt == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "iso_utc,expected",
    [
        # Non-DST (January): noon UTC → London only (NY local hour 7, outside 08–17)
        ("2024-01-15T12:00:00+00:00", "London"),
        # Tokyo-anchored Asian bucket (midnight UTC → 09:00 JST same calendar day)
        ("2024-01-15T00:00:00+00:00", "Asian"),
        # Summer (July, US DST): 17:00 UTC → New York session
        ("2024-07-15T17:00:00+00:00", "New York"),
        # Same Asian UTC slot in July (DST in US/Europe; Tokyo rule unchanged)
        ("2024-07-15T00:00:00+00:00", "Asian"),
    ],
)
def test_session_label_for_utc_iana_windows(iso_utc: str, expected: str):
    dt = datetime.fromisoformat(iso_utc)
    assert session_label_for_utc(dt) == expected


def test_session_overlap_non_dst_labels_new_york_first():
    """London and NY windows both match; New York is checked first."""
    dt = datetime.fromisoformat("2025-01-15T14:00:00+00:00")
    assert session_label_for_utc(dt) == "New York"


def test_session_overlap_dst_labels_new_york_first():
    """London and NY windows both match during US/EU DST; New York wins."""
    dt = datetime.fromisoformat("2025-07-15T13:00:00+00:00")
    assert session_label_for_utc(dt) == "New York"


def test_broker_local_hour_under_utc_plus_two():
    dt = trade_instant_utc("2024-01-15T10:00:00+00:00")
    assert broker_local_hour(dt, "UTC+2") == 12


def test_upload_parsed_row_times_to_utc_importer_edge():
    """Importer path: journal wall clock in broker TZ → aware UTC datetimes."""
    row = {
        "opened_at": "2024-01-15T14:30:00",
        "closed_at": "2024-01-15T16:00:00",
        "symbol": "EURUSD",
    }
    out = upload_api._parsed_row_times_to_utc(row, "UTC+2")
    assert out["opened_at"] == datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
    assert out["closed_at"] == datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
