"""
MT4 CSV trade history parser.

Handles CSV exports from MT4 terminal (Account History → copy/export).
Supports broker variations: FBS, IC Markets, Exness, Pepperstone, XM.
Auto-detects delimiters, date formats, and column naming conventions.
Returns standardized trade dicts matching the `trades` table schema.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from tradecoach.parsers._format_spec import (
    ALIASES,
    BUY_TYPES,
    DATE_FORMATS,
    PRICE_NAMES,
    REQUIRED_CANONICAL_FIELDS,
    SELL_TYPES,
    SKIP_TYPES,
    TIME_HEADER_DUPLICATE_LABEL,
    has_mapped_time_column,
    header_detection_keywords,
    normalize_header_label,
    primary_date_sample_column,
)

# Order in which "price" columns appear. The first is open, second is close.
# This resolves ambiguity when both columns are just called "Price".
_PRICE_OCCURRENCE = 0  # incremented per row during mapping

# Trade types that represent actual market trades (not balance/credit ops)
_TRADE_TYPES = BUY_TYPES | SELL_TYPES


class MT4ParseError(Exception):
    """Raised when a CSV file cannot be parsed as MT4 trade history."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_mt4_csv(
    content: str | bytes,
    *,
    broker_hint: str | None = None,
) -> list[dict[str, Any]]:
    """Parse an MT4 CSV trade history export.

    Args:
        content: Raw CSV text (str or bytes).
        broker_hint: Optional broker name for edge-case handling.

    Returns:
        List of trade dicts matching the `trades` table schema:
        {ticket, symbol, direction, lot, open_price, close_price,
         stop_loss, take_profit, profit_money, commission, swap,
         opened_at, closed_at, source}

    Raises:
        MT4ParseError: If the file cannot be parsed.
    """
    if isinstance(content, bytes):
        content = _decode(content)

    content = _strip_html_and_headers(content)
    if not content.strip():
        raise MT4ParseError("File is empty after stripping headers")

    delimiter = _detect_delimiter(content)
    rows = _read_csv(content, delimiter)
    if not rows:
        raise MT4ParseError("No data rows found")

    header = rows[0]
    col_map = _map_columns(header)
    _validate_columns(col_map)

    date_fmt = _detect_date_format(rows[1:], col_map)

    trades: list[dict[str, Any]] = []
    errors: list[str] = []

    for i, row in enumerate(rows[1:], start=2):
        if len(row) < len(header):
            row.extend([""] * (len(header) - len(row)))

        try:
            trade = _parse_row(row, col_map, date_fmt, header)
        except _SkipRow:
            continue
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")
            continue

        trades.append(trade)

    if not trades and errors:
        raise MT4ParseError(
            f"No valid trades parsed. Errors:\n" + "\n".join(errors[:10])
        )

    return trades


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _SkipRow(Exception):
    """Signal to skip a non-trade row."""


def _decode(data: bytes) -> str:
    """Decode bytes trying common encodings."""
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return data.decode("utf-8", errors="replace")


def _strip_html_and_headers(text: str) -> str:
    """Remove HTML tags and common MT4 report preamble lines."""
    # Strip HTML tags if present (detailed report saved as HTML)
    if "<" in text and ">" in text:
        text = re.sub(r"<[^>]+>", "", text)

    lines = text.splitlines()
    cleaned: list[str] = []
    header_found = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lower()

        # Skip preamble lines (account info, report title, etc.)
        if not header_found:
            if any(
                kw in low
                for kw in ("account:", "name:", "currency:", "leverage:",
                           "closed transactions", "account history",
                           "trade history", "statement")
            ):
                continue
            # Heuristic: header row contains "ticket" or "order"
            if "ticket" in low or "order" in low:
                header_found = True
                cleaned.append(stripped)
                continue
            # Also accept if the line has multiple known column names
            known_hits = sum(
                1 for kw in header_detection_keywords() if kw in low
            )
            if known_hits >= 3:
                header_found = True
                cleaned.append(stripped)
                continue
        else:
            # Skip summary/footer lines
            if low.startswith(("closed p/l", "total", "summary",
                               "floating", "balance", "equity",
                               "margin", "free margin")):
                continue
            cleaned.append(stripped)

    return "\n".join(cleaned)


def _detect_delimiter(text: str) -> str:
    """Auto-detect CSV delimiter (tab, comma, semicolon)."""
    first_lines = text.strip().splitlines()[:3]
    sample = "\n".join(first_lines)

    # Tab is the most common for MT4 copy-paste
    counts = {
        "\t": sample.count("\t"),
        ",": sample.count(","),
        ";": sample.count(";"),
    }

    # Pick the delimiter that appears most consistently
    best = max(counts, key=counts.get)  # type: ignore[arg-type]
    if counts[best] == 0:
        raise MT4ParseError("Cannot detect delimiter")
    return best


def _read_csv(text: str, delimiter: str) -> list[list[str]]:
    """Parse CSV text into rows."""
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = []
    for row in reader:
        cleaned = [cell.strip() for cell in row]
        # Skip fully empty rows
        if any(cleaned):
            rows.append(cleaned)
    return rows


def _map_columns(header: list[str]) -> dict[str, int]:
    """Map canonical field names to column indices.

    Handles duplicate Price/Rate columns (open vs close) and duplicate Time
    columns the same way as the Excel parser.
    """
    col_map: dict[str, int] = {}
    normalized = [normalize_header_label(raw) for raw in header]
    price_syn = frozenset(PRICE_NAMES)

    for i, cell in enumerate(normalized):
        if cell in price_syn:
            continue
        if cell in ALIASES:
            canonical = ALIASES[cell]
            if canonical not in col_map:
                col_map[canonical] = i

    price_indices: list[int] = []
    for i, cell in enumerate(normalized):
        if cell in PRICE_NAMES and i not in col_map.values():
            price_indices.append(i)

    if price_indices:
        if "open_price" not in col_map:
            col_map["open_price"] = price_indices[0]
        if len(price_indices) >= 2 and "close_price" not in col_map:
            col_map["close_price"] = price_indices[1]

    time_indices: list[int] = []
    for i, cell in enumerate(normalized):
        if cell == TIME_HEADER_DUPLICATE_LABEL and i not in col_map.values():
            time_indices.append(i)
    if time_indices:
        if "open_time" not in col_map:
            col_map["open_time"] = time_indices[0]
        if len(time_indices) >= 2 and "close_time" not in col_map:
            col_map["close_time"] = time_indices[1]

    return col_map


def _validate_columns(col_map: dict[str, int]) -> None:
    """Ensure minimum required columns are present."""
    missing = REQUIRED_CANONICAL_FIELDS - set(col_map.keys())
    if missing:
        raise MT4ParseError(
            f"Missing required columns: {', '.join(sorted(missing))}. "
            f"Found: {', '.join(sorted(col_map.keys()))}"
        )
    if not has_mapped_time_column(col_map):
        raise MT4ParseError(
            "Missing a recognizable date/time column. Expected at least one "
            "header such as Open Time, Close Time, Open, or Close, or two "
            "columns named Time."
        )


def _detect_date_format(
    data_rows: list[list[str]], col_map: dict[str, int]
) -> str | None:
    """Try to detect the date format from sample rows."""
    date_col = primary_date_sample_column(col_map)
    if date_col is None:
        return None

    for row in data_rows[:10]:
        if date_col >= len(row):
            continue
        val = row[date_col].strip()
        if not val:
            continue
        for fmt in DATE_FORMATS:
            try:
                datetime.strptime(val, fmt)
                return fmt
            except ValueError:
                continue

    return None


def _parse_decimal(value: str) -> Decimal | None:
    """Parse a numeric string to Decimal, handling commas as decimal sep."""
    value = value.strip()
    if not value or value == "—" or value == "-":
        return None

    # Remove spaces (thousand separators)
    value = value.replace(" ", "")

    # If comma is used as decimal separator (European), convert it
    # Heuristic: if there's a comma and no period, or comma is after period
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    elif "," in value and "." in value:
        # Both present: comma is thousands separator (e.g. 1,234.56)
        value = value.replace(",", "")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _parse_datetime(value: str, fmt: str | None) -> str | None:
    """Parse a datetime string, return ISO format or None."""
    value = value.strip()
    if not value:
        return None

    if fmt:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.isoformat()
        except ValueError:
            pass

    # Fallback: try all formats
    for f in DATE_FORMATS:
        try:
            dt = datetime.strptime(value, f)
            return dt.isoformat()
        except ValueError:
            continue

    return None


def _get(row: list[str], col_map: dict[str, int], field: str) -> str:
    """Safely get a cell value by canonical field name."""
    idx = col_map.get(field)
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


def _parse_row(
    row: list[str],
    col_map: dict[str, int],
    date_fmt: str | None,
    header: list[str],
) -> dict[str, Any]:
    """Parse a single CSV row into a standardized trade dict."""
    trade_type = _get(row, col_map, "type").lower()

    # Skip non-trade rows
    if not trade_type or any(skip in trade_type for skip in SKIP_TYPES):
        raise _SkipRow()

    # Determine direction
    if trade_type in BUY_TYPES or "buy" in trade_type:
        direction = "buy"
    elif trade_type in SELL_TYPES or "sell" in trade_type:
        direction = "sell"
    else:
        raise _SkipRow()

    # Symbol — clean up suffixes (e.g. EURUSDm, EURUSD.ecn)
    raw_symbol = _get(row, col_map, "symbol")
    if not raw_symbol:
        raise ValueError("Empty symbol")
    symbol = _clean_symbol(raw_symbol)

    # Lot size
    lot = _parse_decimal(_get(row, col_map, "lot"))
    if lot is None or lot <= 0:
        raise ValueError(f"Invalid lot: {_get(row, col_map, 'lot')}")

    # Prices
    open_price = _parse_decimal(_get(row, col_map, "open_price"))
    close_price = _parse_decimal(_get(row, col_map, "close_price"))
    stop_loss = _parse_decimal(_get(row, col_map, "stop_loss"))
    take_profit = _parse_decimal(_get(row, col_map, "take_profit"))

    # Zero SL/TP means not set
    if stop_loss is not None and stop_loss == 0:
        stop_loss = None
    if take_profit is not None and take_profit == 0:
        take_profit = None

    # Financials
    profit = _parse_decimal(_get(row, col_map, "profit"))
    commission = _parse_decimal(_get(row, col_map, "commission"))
    swap = _parse_decimal(_get(row, col_map, "swap"))

    # Dates
    opened_at = _parse_datetime(_get(row, col_map, "open_time"), date_fmt)
    closed_at = _parse_datetime(_get(row, col_map, "close_time"), date_fmt)

    # Ticket
    ticket_str = _get(row, col_map, "ticket")
    ticket = int(ticket_str) if ticket_str.isdigit() else None

    pips_from_file = _parse_decimal(_get(row, col_map, "pips"))
    profit_pips = (
        float(pips_from_file) if pips_from_file is not None
        else _calc_pips(symbol, direction, open_price, close_price)
    )

    return {
        "ticket": ticket,
        "symbol": symbol,
        "direction": direction,
        "lot": float(lot),
        "open_price": float(open_price) if open_price is not None else None,
        "close_price": float(close_price) if close_price is not None else None,
        "stop_loss": float(stop_loss) if stop_loss is not None else None,
        "take_profit": float(take_profit) if take_profit is not None else None,
        "profit_pips": float(profit_pips) if profit_pips is not None else None,
        "profit_money": float(profit) if profit is not None else None,
        "commission": float(commission) if commission is not None else None,
        "swap": float(swap) if swap is not None else None,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "source": "csv",
    }


def _clean_symbol(raw: str) -> str:
    """Normalize broker-specific symbol names.

    Strips common suffixes: trailing 'm', '.ecn', '.pro', '_SB', micro/mini
    prefixes, etc. Result is uppercase (e.g., EURUSD, GBPJPY).
    """
    s = raw.strip().upper()
    # Remove common suffixes
    s = re.sub(r"[._](ECN|PRO|SB|STD|RAW|MICRO|MINI|STP|C)$", "", s, flags=re.I)
    # Remove trailing 'm' or 'M' (micro lots suffix on some brokers)
    if len(s) > 3 and s.endswith("M") and s[-2].isalpha():
        s = s[:-1]
    # Remove leading '#' (some brokers prefix CFDs)
    s = s.lstrip("#")
    return s


def _calc_pips(
    symbol: str,
    direction: str,
    open_price: Decimal | None,
    close_price: Decimal | None,
) -> float | None:
    """Calculate profit in pips from open/close prices."""
    if open_price is None or close_price is None:
        return None

    diff = close_price - open_price
    if direction == "sell":
        diff = -diff

    # JPY pairs have 2-3 decimal places, others have 4-5
    jpy_in_symbol = "JPY" in symbol.upper()
    if jpy_in_symbol:
        pips = float(diff) * 100
    else:
        pips = float(diff) * 10_000

    return round(pips, 1)
