"""
Shared import format specification for CSV and Excel trade-history parsers.

Single source of truth for header aliases, duplicate-column tokens, date formats,
trade-type literals, skip-row keywords, and structural validation rules.
No parser business logic beyond trivial accessors.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Column aliases: normalized header (lowercase stripped) → canonical field name
# ---------------------------------------------------------------------------
ALIASES: dict[str, str] = {
    # ticket
    "ticket": "ticket",
    "order": "ticket",
    "order #": "ticket",
    "deal": "ticket",
    "position": "ticket",
    # open time (bare "time" / duplicate Time → TIME_HEADER_DUPLICATE_LABEL in parsers)
    "open time": "open_time",
    "opentime": "open_time",
    "open date": "open_time",
    "open": "open_time",
    # close time
    "close time": "close_time",
    "closetime": "close_time",
    "close date": "close_time",
    "close": "close_time",
    # type / direction column (buy/sell)
    "type": "type",
    "action": "type",
    "direction": "type",
    "side": "type",
    # lot / volume
    "size": "lot",
    "lots": "lot",
    "lot": "lot",
    "volume": "lot",
    "quantity": "lot",
    # symbol
    "item": "symbol",
    "symbol": "symbol",
    "instrument": "symbol",
    "pair": "symbol",
    "asset": "symbol",
    # open price (explicit headers; generic price/rate → dual-column logic)
    "price": "open_price",
    "open price": "open_price",
    "openprice": "open_price",
    # stop loss
    "s/l": "stop_loss",
    "s / l": "stop_loss",
    "sl": "stop_loss",
    "stop loss": "stop_loss",
    "stoploss": "stop_loss",
    # take profit
    "t/p": "take_profit",
    "t / p": "take_profit",
    "tp": "take_profit",
    "take profit": "take_profit",
    "takeprofit": "take_profit",
    # close price
    "close price": "close_price",
    "closeprice": "close_price",
    # commission
    "commission": "commission",
    "commissions": "commission",
    "comm": "commission",
    # taxes (CSV brokers)
    "taxes": "taxes",
    # swap
    "swap": "swap",
    # profit / P&L
    "profit": "profit",
    "net profit": "profit",
    "p/l": "profit",
    "p&l": "profit",
    "net p/l": "profit",
    "result": "profit",
    # optional
    "comment": "comment",
    # pips / duration (xlsx-style exports)
    "pips": "pips",
    "pip": "pips",
    "points": "pips",
    "duration": "duration",
    "trade duration": "duration",
    "trade duration in seconds": "duration",
}

# Headers that may repeat: first occurrence → open price, second → close price.
# "rate" appears on some broker sheets instead of "Price".
PRICE_NAMES: tuple[str, ...] = ("price", "rate")

# Normalized header label for duplicate time columns (MT4-style two "Time" cols).
TIME_HEADER_DUPLICATE_LABEL: str = "time"

# Sentinel returned by date-format probes when cells are native Excel datetimes.
EXCEL_NATIVE_DATETIME_SENTINEL: str = "__datetime__"

# ---------------------------------------------------------------------------
# Date string formats (probe order: datetime variants first, then date-only)
# ---------------------------------------------------------------------------
DATE_FORMATS: tuple[str, ...] = (
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%Y.%m.%d",
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
)

# ---------------------------------------------------------------------------
# Direction literals and non-trade row filters
# ---------------------------------------------------------------------------
BUY_TYPES: frozenset[str] = frozenset({"buy", "long"})
SELL_TYPES: frozenset[str] = frozenset({"sell", "short"})

SKIP_TYPES: frozenset[str] = frozenset({
    "balance",
    "credit",
    "deposit",
    "withdrawal",
    "rebate",
    "bonus",
    "adjustment",
    "cancel",
})

# ---------------------------------------------------------------------------
# Structural validation: minimum canonical columns after header mapping
# ---------------------------------------------------------------------------
REQUIRED_CANONICAL_FIELDS: frozenset[str] = frozenset({"symbol", "type", "lot"})


def normalize_header_label(raw: str) -> str:
    return raw.strip().lower()


def price_header_synonyms() -> frozenset[str]:
    return frozenset(PRICE_NAMES)


def primary_date_sample_column(col_map: dict[str, int]) -> int | None:
    """Prefer open_time for format probing; fall back to close_time."""
    idx = col_map.get("open_time")
    if idx is not None:
        return idx
    return col_map.get("close_time")


def has_mapped_time_column(col_map: dict[str, int]) -> bool:
    return ("open_time" in col_map) or ("close_time" in col_map)


def header_detection_keywords() -> frozenset[str]:
    """Tokens used to spot header rows (Excel scoring, CSV preamble heuristics)."""
    return frozenset(ALIASES.keys()) | frozenset(PRICE_NAMES) | frozenset(
        {TIME_HEADER_DUPLICATE_LABEL}
    )
