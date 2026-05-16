"""Regression: broker-direct CSV layout preserves open/close timestamps on import."""

from __future__ import annotations

from datetime import datetime

from tradecoach.parsers.mt4_parser import parse_mt4_csv

# Production broker export layout (column order and names match terminal CSV).
BROKER_DIRECT_CSV = (
    "Ticket,Open,Type,Volume,Symbol,Price,SL,TP,Close,Price,"
    "Swap,Commissions,Profit,Pips,\"Trade duration in seconds\"\n"
    "12345,2024.01.15 09:30:00,buy,0.1,EURUSD,1.08750,1.08500,1.09000,"
    "2024.01.15 14:20:00,1.08950,0.00,-0.70,20.00,-9.1,179\n"
    "12346,2024.01.15 10:00:00,sell,0.2,GBPJPY,188.500,189.000,188.000,"
    "2024.01.15 16:45:00,188.250,-0.32,-1.40,50.00,2.9,58\n"
)


def test_broker_direct_csv_populates_open_and_close_timestamps() -> None:
    trades = parse_mt4_csv(BROKER_DIRECT_CSV)
    assert len(trades) == 2

    for t in trades:
        opened = t.get("opened_at")
        closed = t.get("closed_at")
        assert opened is not None and str(opened).strip() != ""
        assert closed is not None and str(closed).strip() != ""
        datetime.fromisoformat(str(opened).replace("Z", "+00:00"))
        datetime.fromisoformat(str(closed).replace("Z", "+00:00"))
