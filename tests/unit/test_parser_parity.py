"""
Parity between CSV and Excel import parsers on logically identical tabular data.

Fails if column mapping or normalization diverges between paths again.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

import openpyxl

from tradecoach.parsers.mt4_parser import parse_mt4_csv
from tradecoach.parsers.xlsx_parser import parse_xlsx

# Exact first line from broker terminal export (last field quoted).
BROKER_CSV_HEADER_LINE = (
    "Ticket,Open,Type,Volume,Symbol,Price,SL,TP,Close,Price,"
    'Swap,Commissions,Profit,Pips,"Trade duration in seconds"'
)


def _make_xlsx(rows: list[list[Any]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _broker_direct_table() -> list[list[Any]]:
    """Same columns as production broker CSV (order and names)."""
    header = [
        "Ticket",
        "Open",
        "Type",
        "Volume",
        "Symbol",
        "Price",
        "SL",
        "TP",
        "Close",
        "Price",
        "Swap",
        "Commissions",
        "Profit",
        "Pips",
        "Trade duration in seconds",
    ]
    row1 = [
        12345,
        "2024.01.15 09:30:00",
        "buy",
        0.1,
        "EURUSD",
        1.08750,
        1.08500,
        1.09000,
        "2024.01.15 14:20:00",
        1.08950,
        0.00,
        -0.70,
        20.00,
        -9.1,
        179,
    ]
    row2 = [
        12346,
        "2024.01.15 10:00:00",
        "sell",
        0.2,
        "GBPJPY",
        188.500,
        189.000,
        188.000,
        "2024.01.15 16:45:00",
        188.250,
        -0.32,
        -1.40,
        50.00,
        2.9,
        58,
    ]
    row3 = [
        12347,
        "2024.01.16 08:00:00",
        "buy",
        0.05,
        "USDJPY",
        148.250,
        147.800,
        148.800,
        "2024.01.16 12:30:00",
        148.100,
        0.00,
        -0.35,
        -7.50,
        -12.4,
        270,
    ]
    return [header, row1, row2, row3]


def _normalize_timestamp(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val.replace(microsecond=0)
        return dt.isoformat()
    s = str(val).strip().replace("Z", "")
    dt = datetime.fromisoformat(s)
    return dt.replace(microsecond=0).isoformat()


def _normalize_trade(t: dict[str, Any]) -> dict[str, Any]:
    """Canonical dict for equality (timestamps naive ISO, floats rounded)."""
    out: dict[str, Any] = {}
    for k in sorted(t.keys()):
        v = t[k]
        if k in ("opened_at", "closed_at"):
            out[k] = _normalize_timestamp(v)
        elif isinstance(v, float):
            out[k] = round(v, 6)
        else:
            out[k] = v
    return out


class TestParserParity:
    def test_csv_matches_xlsx_on_broker_direct_layout(self):
        table = _broker_direct_table()
        _, *data_rows = table

        csv_buf = io.StringIO()
        csv_buf.write(BROKER_CSV_HEADER_LINE + "\n")
        writer = csv.writer(csv_buf, lineterminator="\n")
        writer.writerows(data_rows)
        csv_text = csv_buf.getvalue()
        assert csv_text.splitlines()[0] == BROKER_CSV_HEADER_LINE
        xlsx_bytes = _make_xlsx(table)

        csv_trades = parse_mt4_csv(csv_text)
        xlsx_trades = parse_xlsx(xlsx_bytes)

        assert len(csv_trades) == len(xlsx_trades) == len(data_rows)

        for csv_t, xlsx_t in zip(csv_trades, xlsx_trades, strict=True):
            assert _normalize_trade(csv_t) == _normalize_trade(xlsx_t)
