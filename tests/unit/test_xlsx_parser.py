"""
Tests for the universal Excel trade history parser.

Tests verify:
  - Header row auto-detection (skip preamble)
  - Column mapping with various naming conventions
  - Date format detection (string and datetime objects)
  - Dual Price and Time columns
  - Non-trade row skipping (summaries, orders section, empty rows)
  - Symbol suffix stripping
  - Pips from file vs calculated
  - Error handling for invalid files
"""

from __future__ import annotations

import io
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from tradecoach.parsers.xlsx_parser import (
    XlsxParseError,
    _clean_symbol,
    _find_header_row,
    _map_columns,
    _parse_number,
    _validate_columns,
    parse_xlsx,
)


# ===================================================================
# Helper: create in-memory Excel files
# ===================================================================

def _make_xlsx(rows: list[list], sheet_name: str = "Sheet1") -> bytes:
    """Create an xlsx file in memory from a list of rows."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ===================================================================
# Unit tests for helpers
# ===================================================================


class TestParseNumber:
    def test_int(self):
        assert _parse_number(42) == 42.0

    def test_float(self):
        assert _parse_number(3.14) == 3.14

    def test_string(self):
        assert _parse_number("1.5") == 1.5

    def test_negative(self):
        assert _parse_number("-50.3") == -50.3

    def test_comma_decimal(self):
        assert _parse_number("1,5") == 1.5

    def test_thousand_separator(self):
        assert _parse_number("1,234.56") == 1234.56

    def test_dollar_sign(self):
        assert _parse_number("$100") == 100.0

    def test_none(self):
        assert _parse_number(None) is None

    def test_empty(self):
        assert _parse_number("") is None

    def test_dash(self):
        assert _parse_number("-") is None
        assert _parse_number("—") is None

    def test_na(self):
        assert _parse_number("N/A") is None


class TestCleanSymbol:
    def test_plain(self):
        assert _clean_symbol("EURUSD") == "EURUSD"

    def test_cash_suffix(self):
        assert _clean_symbol("USOIL.cash") == "USOIL"

    def test_ecn_suffix(self):
        assert _clean_symbol("EURUSD.ecn") == "EURUSD"

    def test_trailing_m(self):
        assert _clean_symbol("EURUSDm") == "EURUSD"

    def test_hash_prefix(self):
        assert _clean_symbol("#AAPL") == "AAPL"

    def test_lowercase(self):
        assert _clean_symbol("eurusd") == "EURUSD"


class TestFindHeaderRow:
    def test_header_at_top(self):
        rows = [
            ["Ticket", "Open Time", "Symbol", "Type", "Volume", "Price"],
            [12345, "2024-01-01", "EURUSD", "buy", 0.1, 1.095],
        ]
        assert _find_header_row(rows) == 0

    def test_header_with_preamble(self):
        rows = [
            ["Trade History Report", None, None],
            ["Name:", None, "MainTrading"],
            ["Account:", None, "123456"],
            ["Positions", None, None],
            ["Time", "Position", "Symbol", "Type", "Volume", "Price", "S / L", "T / P"],
            ["2024-01-01", 12345, "EURUSD", "buy", 0.1, 1.095, None, None],
        ]
        assert _find_header_row(rows) == 4

    def test_no_header_found(self):
        rows = [
            ["random", "data", "here"],
            [1, 2, 3],
        ]
        assert _find_header_row(rows) is None


class TestMapColumns:
    def test_standard_headers(self):
        header = ["Ticket", "Open Time", "Symbol", "Type", "Volume", "Price"]
        col_map = _map_columns(header)
        assert col_map["ticket"] == 0
        assert col_map["open_time"] == 1
        assert col_map["symbol"] == 2
        assert col_map["type"] == 3
        assert col_map["lot"] == 4
        assert col_map["open_price"] == 5

    def test_dual_price_columns(self):
        header = ["Symbol", "Type", "Volume", "Price", "S / L", "T / P", "Price"]
        col_map = _map_columns(header)
        assert col_map["open_price"] == 3
        assert col_map["close_price"] == 6

    def test_dual_time_columns(self):
        header = ["Time", "Position", "Symbol", "Type", "Volume", "Price", "Time", "Price"]
        col_map = _map_columns(header)
        assert col_map["open_time"] == 0
        assert col_map["close_time"] == 6

    def test_explicit_open_close(self):
        header = ["Ticket", "Open", "Type", "Volume", "Symbol", "Price",
                   "SL", "TP", "Close", "Price", "Swap", "Commissions", "Profit", "Pips"]
        col_map = _map_columns(header)
        assert col_map["open_time"] == 1
        assert col_map["close_time"] == 8
        assert col_map["pips"] == 13


class TestValidateColumns:
    def test_valid(self):
        _validate_columns({"symbol": 0, "type": 1, "lot": 2})

    def test_missing(self):
        with pytest.raises(XlsxParseError, match="Missing required"):
            _validate_columns({"symbol": 0})


# ===================================================================
# Integration tests with in-memory Excel files
# ===================================================================


class TestParseXlsx:
    def test_basic_trades(self):
        rows = [
            ["Ticket", "Open Time", "Close Time", "Type", "Volume",
             "Symbol", "Price", "S / L", "T / P", "Price",
             "Commission", "Swap", "Profit"],
            [12345, "2024-01-15 10:30:00", "2024-01-15 14:00:00", "buy", 0.1,
             "EURUSD", 1.095, 1.09, 1.10, 1.098,
             -2.0, 0.0, 30.0],
            [12346, "2024-01-16 09:00:00", "2024-01-16 12:00:00", "sell", 0.2,
             "GBPUSD", 1.27, 1.275, 1.265, 1.267,
             -3.0, -0.5, 60.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert len(trades) == 2

        t1 = trades[0]
        assert t1["ticket"] == 12345
        assert t1["symbol"] == "EURUSD"
        assert t1["direction"] == "buy"
        assert t1["lot"] == 0.1
        assert t1["open_price"] == 1.095
        assert t1["close_price"] == 1.098
        assert t1["stop_loss"] == 1.09
        assert t1["take_profit"] == 1.10
        assert t1["profit_money"] == 30.0
        assert t1["commission"] == -2.0
        assert t1["swap"] == 0.0
        assert t1["source"] == "csv"

    def test_preamble_skipped(self):
        rows = [
            ["Trade History Report", None, None, None, None, None],
            ["Name:", None, None, "Test", None, None],
            ["Account:", None, None, "123 (USD)", None, None],
            ["Date:", None, None, "2024.03.06", None, None],
            ["Positions", None, None, None, None, None],
            ["Time", "Position", "Symbol", "Type", "Volume", "Price",
             "S / L", "T / P", "Time", "Price", "Commission", "Swap", "Profit"],
            ["2024.01.15 10:30:00", 12345, "EURUSD", "buy", 0.1,
             1.095, None, None, "2024.01.15 14:00:00", 1.098,
             0.0, 0.0, 30.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert len(trades) == 1
        assert trades[0]["symbol"] == "EURUSD"

    def test_summary_rows_skipped(self):
        rows = [
            ["Ticket", "Symbol", "Type", "Volume", "Profit"],
            [1, "EURUSD", "buy", 0.1, 30.0],
            [2, "GBPUSD", "sell", 0.2, -10.0],
            [None, None, "Total:", None, 20.0],  # summary row — no symbol
            [None, "Average:", None, None, 10.0],  # no valid type
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert len(trades) == 2

    def test_balance_rows_skipped(self):
        rows = [
            ["Ticket", "Symbol", "Type", "Volume", "Profit"],
            [1, "EURUSD", "buy", 0.1, 30.0],
            [None, None, "balance", 0, 5000.0],
            [None, None, "deposit", 0, 1000.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert len(trades) == 1

    def test_symbol_suffix_stripped(self):
        rows = [
            ["Ticket", "Symbol", "Type", "Volume", "Profit"],
            [1, "USOIL.cash", "buy", 1.0, 50.0],
            [2, "EURUSDm", "sell", 0.1, -10.0],
            [3, "GBPUSD.ecn", "buy", 0.2, 20.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert trades[0]["symbol"] == "USOIL"
        assert trades[1]["symbol"] == "EURUSD"
        assert trades[2]["symbol"] == "GBPUSD"

    def test_pips_from_file(self):
        rows = [
            ["Ticket", "Symbol", "Type", "Volume", "Profit", "Pips"],
            [1, "XAUUSD", "buy", 0.1, 50.0, 5.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert trades[0]["profit_pips"] == 5.0

    def test_pips_calculated_when_not_in_file(self):
        rows = [
            ["Ticket", "Symbol", "Type", "Volume", "Price", "Price", "Profit"],
            [1, "EURUSD", "buy", 0.1, 1.095, 1.098, 30.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert trades[0]["profit_pips"] == 30.0  # (1.098 - 1.095) * 10000

    def test_datetime_objects_handled(self):
        """When Excel stores dates as datetime objects, not strings."""
        rows = [
            ["Ticket", "Open Time", "Close Time", "Symbol", "Type", "Volume", "Profit"],
            [1, datetime(2024, 1, 15, 10, 30), datetime(2024, 1, 15, 14, 0),
             "EURUSD", "buy", 0.1, 30.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert trades[0]["opened_at"] == "2024-01-15T10:30:00"
        assert trades[0]["closed_at"] == "2024-01-15T14:00:00"

    def test_zero_sl_tp_treated_as_none(self):
        rows = [
            ["Ticket", "Symbol", "Type", "Volume", "SL", "TP", "Profit"],
            [1, "EURUSD", "buy", 0.1, 0.0, 0.0, 30.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert trades[0]["stop_loss"] is None
        assert trades[0]["take_profit"] is None

    def test_empty_file_raises(self):
        rows = []
        xlsx = _make_xlsx(rows)
        with pytest.raises(XlsxParseError):
            parse_xlsx(xlsx)

    def test_no_header_raises(self):
        rows = [
            ["random", "data"],
            [1, 2],
        ]
        xlsx = _make_xlsx(rows)
        with pytest.raises(XlsxParseError, match="Cannot find header"):
            parse_xlsx(xlsx)

    def test_missing_columns_raises(self):
        """Too few known columns — can't find header or missing required cols."""
        rows = [
            ["Ticket", "Profit"],
            [1, 30.0],
        ]
        xlsx = _make_xlsx(rows)
        with pytest.raises(XlsxParseError):
            parse_xlsx(xlsx)

    def test_invalid_file_raises(self):
        with pytest.raises(XlsxParseError, match="Cannot open"):
            parse_xlsx(b"not an excel file")

    def test_lot_as_string(self):
        """Some brokers store Volume as string like '0.03'."""
        rows = [
            ["Ticket", "Symbol", "Type", "Volume", "Profit"],
            [1, "EURUSD", "buy", "0.03", 10.0],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert trades[0]["lot"] == 0.03

    def test_orders_section_skipped(self):
        """After Positions section, an Orders section with different format should be skipped."""
        rows = [
            ["Time", "Position", "Symbol", "Type", "Volume", "Price",
             "S / L", "T / P", "Time", "Price", "Commission", "Swap", "Profit"],
            ["2024.01.15 10:30:00", 12345, "EURUSD", "buy", 0.1,
             1.095, None, None, "2024.01.15 14:00:00", 1.098,
             0, 0, 30.0],
            ["Orders", None, None, None, None, None,
             None, None, None, None, None, None, None],
            ["Open Time", "Order", "Symbol", "Type", "Volume", "Price",
             "S / L", "T / P", "Time", "State", None, "Comment", None],
            ["2024.01.15 10:30:00", 12345, "EURUSD", "buy", "0.10 / 0.10", "market",
             None, None, "2024.01.15 10:30:00", "filled", None, None, None],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        # Only the real trade row should be parsed
        assert len(trades) == 1
        assert trades[0]["symbol"] == "EURUSD"

    def test_trading_journal_format(self):
        """Test format with Pips and Trade duration columns."""
        rows = [
            ["Ticket", "Open", "Type", "Volume", "Symbol", "Price",
             "SL", "TP", "Close", "Price", "Swap", "Commissions",
             "Profit", "Pips", "Trade duration in seconds"],
            [12345, "2026-03-02 16:29:03", "buy", 0.15, "XAUUSD",
             5332.41, 5302.41, 5412.41, "2026-03-02 16:32:02", 5323.29,
             0, -1.12, -136.8, -9.1, 179],
            [12346, "2026-03-02 08:12:23", "buy", 1.4, "USOIL.cash",
             71.767, 70.0, 75.35, "2026-03-02 16:26:43", 72.015,
             0, 0, 34.72, 0.2, 29660],
        ]
        xlsx = _make_xlsx(rows)
        trades = parse_xlsx(xlsx)
        assert len(trades) == 2

        t1 = trades[0]
        assert t1["symbol"] == "XAUUSD"
        assert t1["profit_pips"] == -9.1  # from file, not calculated
        assert t1["profit_money"] == -136.8

        t2 = trades[1]
        assert t2["symbol"] == "USOIL"  # .cash stripped
        assert t2["profit_pips"] == 0.2  # from file
