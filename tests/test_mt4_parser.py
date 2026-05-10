"""Tests for MT4 CSV parser."""

import pytest

from tradecoach.parsers.mt4_parser import MT4ParseError, parse_mt4_csv


# ---------------------------------------------------------------------------
# Sample CSV data simulating real broker exports
# ---------------------------------------------------------------------------

# Standard MT4 tab-delimited (default format from terminal copy)
MT4_STANDARD_TAB = (
    "Ticket\tOpen Time\tType\tSize\tItem\tPrice\tS/L\tT/P\t"
    "Close Time\tPrice\tCommission\tTaxes\tSwap\tProfit\n"
    "12345678\t2024.01.15 09:30:00\tbuy\t0.10\tEURUSD\t1.08750\t1.08500\t1.09000\t"
    "2024.01.15 14:20:00\t1.08950\t-0.70\t0.00\t0.00\t20.00\n"
    "12345679\t2024.01.15 10:00:00\tsell\t0.20\tGBPJPY\t188.500\t189.000\t188.000\t"
    "2024.01.15 16:45:00\t188.250\t-1.40\t0.00\t-0.32\t50.00\n"
    "12345680\t2024.01.16 08:00:00\tbuy\t0.05\tUSDJPY\t148.250\t147.800\t148.800\t"
    "2024.01.16 12:30:00\t148.100\t-0.35\t0.00\t0.00\t-7.50\n"
)

# IC Markets style: comma-delimited, "Order" instead of "Ticket", "Volume"
IC_MARKETS_CSV = (
    "Order,Open Time,Type,Volume,Symbol,Open Price,S/L,T/P,"
    "Close Time,Close Price,Commission,Swap,Profit\n"
    "90001,2024.02.10 08:15:00,buy,0.50,EURUSD.ecn,1.07800,1.07500,1.08200,"
    "2024.02.10 15:30:00,1.08100,-3.50,0.00,150.00\n"
    "90002,2024.02.10 09:00:00,sell,0.30,GBPUSD.ecn,1.26200,1.26500,1.25800,"
    "2024.02.10 11:45:00,1.25950,-2.10,-0.15,75.00\n"
)

# Exness style: semicolon-delimited (European locale), comma decimal sep
EXNESS_CSV = (
    "Ticket;Open Time;Type;Lots;Instrument;Price;S/L;T/P;"
    "Close Time;Price;Commission;Swap;Profit\n"
    "7700001;2024.03.05 11:00:00;buy;0,10;EURUSDm;1,09250;1,08900;1,09600;"
    "2024.03.05 17:30:00;1,09500;-0,80;0,00;25,00\n"
    "7700002;2024.03.06 07:45:00;sell;0,20;GBPUSDm;1,26800;1,27200;1,26400;"
    "2024.03.06 13:15:00;1,26550;-1,60;-0,25;50,00\n"
)

# FBS style: European date format dd.mm.yyyy
FBS_CSV = (
    "Ticket,Open Time,Type,Size,Symbol,Price,S/L,T/P,"
    "Close Time,Price,Commission,Swap,Profit\n"
    "55001,15.01.2024 09:30:00,buy,0.10,EURUSD,1.08750,1.08500,1.09000,"
    "15.01.2024 14:20:00,1.08950,-0.70,0.00,20.00\n"
)

# Pepperstone/XM style: dash dates, "Lots" column
PEPPERSTONE_CSV = (
    "Ticket,Open Time,Action,Lots,Symbol,Open Price,S/L,T/P,"
    "Close Time,Close Price,Commission,Swap,Profit\n"
    "330001,2024-01-20 10:15:00,buy,0.25,AUDUSD,0.65800,0.65500,0.66200,"
    "2024-01-20 16:00:00,0.66100,-1.75,0.00,75.00\n"
    "330002,2024-01-20 11:30:00,sell,0.15,NZDUSD,0.61200,0.61500,0.60800,"
    "2024-01-20 15:45:00,0.61050,-1.05,-0.10,22.50\n"
)

# With non-trade rows (balance, deposit) that should be skipped
WITH_BALANCE_ROWS = (
    "Ticket\tOpen Time\tType\tSize\tItem\tPrice\tS/L\tT/P\t"
    "Close Time\tPrice\tCommission\tTaxes\tSwap\tProfit\n"
    "0\t2024.01.01 00:00:00\tbalance\t0.00\t\t0.00000\t0.00000\t0.00000\t"
    "2024.01.01 00:00:00\t0.00000\t0.00\t0.00\t0.00\t5000.00\n"
    "12345678\t2024.01.15 09:30:00\tbuy\t0.10\tEURUSD\t1.08750\t1.08500\t1.09000\t"
    "2024.01.15 14:20:00\t1.08950\t-0.70\t0.00\t0.00\t20.00\n"
    "0\t2024.01.20 00:00:00\tdeposit\t0.00\t\t0.00000\t0.00000\t0.00000\t"
    "2024.01.20 00:00:00\t0.00000\t0.00\t0.00\t0.00\t1000.00\n"
)

# With preamble/header lines (account info before actual data)
WITH_PREAMBLE = (
    "Account: 12345678\n"
    "Name: John Doe\n"
    "Currency: USD\n"
    "Leverage: 1:500\n"
    "Closed Transactions:\n"
    "\n"
    "Ticket\tOpen Time\tType\tSize\tItem\tPrice\tS/L\tT/P\t"
    "Close Time\tPrice\tCommission\tTaxes\tSwap\tProfit\n"
    "12345678\t2024.01.15 09:30:00\tbuy\t0.10\tEURUSD\t1.08750\t1.08500\t1.09000\t"
    "2024.01.15 14:20:00\t1.08950\t-0.70\t0.00\t0.00\t20.00\n"
)

# With footer/summary lines
WITH_FOOTER = (
    "Ticket\tOpen Time\tType\tSize\tItem\tPrice\tS/L\tT/P\t"
    "Close Time\tPrice\tCommission\tTaxes\tSwap\tProfit\n"
    "12345678\t2024.01.15 09:30:00\tbuy\t0.10\tEURUSD\t1.08750\t1.08500\t1.09000\t"
    "2024.01.15 14:20:00\t1.08950\t-0.70\t0.00\t0.00\t20.00\n"
    "Total\t\t\t\t\t\t\t\t\t\t-0.70\t0.00\t0.00\t20.00\n"
    "Closed P/L:\t\t\t\t\t\t\t\t\t\t\t\t\t20.00\n"
)

# Zero S/L and T/P (should become None)
ZERO_SL_TP = (
    "Ticket,Open Time,Type,Size,Symbol,Price,S/L,T/P,"
    "Close Time,Price,Commission,Swap,Profit\n"
    "99001,2024.01.15 09:30:00,buy,0.10,EURUSD,1.08750,0.00000,0.00000,"
    "2024.01.15 14:20:00,1.08950,-0.70,0.00,20.00\n"
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestStandardMT4:
    """Standard tab-delimited MT4 export."""

    def test_parses_all_trades(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        assert len(trades) == 3

    def test_first_trade_fields(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        t = trades[0]
        assert t["ticket"] == 12345678
        assert t["symbol"] == "EURUSD"
        assert t["direction"] == "buy"
        assert t["lot"] == 0.10
        assert t["open_price"] == 1.08750
        assert t["close_price"] == 1.08950
        assert t["stop_loss"] == 1.08500
        assert t["take_profit"] == 1.09000
        assert t["profit_money"] == 20.00
        assert t["commission"] == -0.70
        assert t["swap"] == 0.00
        assert t["source"] == "csv"

    def test_dates_parsed(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        t = trades[0]
        assert t["opened_at"] == "2024-01-15T09:30:00"
        assert t["closed_at"] == "2024-01-15T14:20:00"

    def test_sell_direction(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        assert trades[1]["direction"] == "sell"
        assert trades[1]["symbol"] == "GBPJPY"

    def test_losing_trade(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        t = trades[2]
        assert t["profit_money"] == -7.50
        assert t["direction"] == "buy"

    def test_pips_calculation_standard_pair(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        # EURUSD buy: (1.08950 - 1.08750) * 10000 = 20.0 pips
        assert trades[0]["profit_pips"] == 20.0

    def test_pips_calculation_jpy_pair(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        # GBPJPY sell: -(188.250 - 188.500) * 100 = 25.0 pips
        assert trades[1]["profit_pips"] == 25.0

    def test_pips_calculation_losing(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        # USDJPY buy: (148.100 - 148.250) * 100 = -15.0 pips
        assert trades[2]["profit_pips"] == -15.0


class TestICMarkets:
    """IC Markets: comma-delimited, 'Order'/'Volume'/'Symbol' naming, .ecn suffix."""

    def test_parses_correctly(self):
        trades = parse_mt4_csv(IC_MARKETS_CSV)
        assert len(trades) == 2

    def test_symbol_cleaned(self):
        trades = parse_mt4_csv(IC_MARKETS_CSV)
        assert trades[0]["symbol"] == "EURUSD"
        assert trades[1]["symbol"] == "GBPUSD"

    def test_order_mapped_to_ticket(self):
        trades = parse_mt4_csv(IC_MARKETS_CSV)
        assert trades[0]["ticket"] == 90001

    def test_volume_mapped_to_lot(self):
        trades = parse_mt4_csv(IC_MARKETS_CSV)
        assert trades[0]["lot"] == 0.50


class TestExness:
    """Exness: semicolon-delimited, comma decimal separator, 'm' suffix."""

    def test_parses_semicolon_delimiter(self):
        trades = parse_mt4_csv(EXNESS_CSV)
        assert len(trades) == 2

    def test_comma_decimal_handling(self):
        trades = parse_mt4_csv(EXNESS_CSV)
        assert trades[0]["lot"] == 0.10
        assert trades[0]["profit_money"] == 25.00
        assert trades[0]["open_price"] == 1.09250

    def test_symbol_m_suffix_stripped(self):
        trades = parse_mt4_csv(EXNESS_CSV)
        assert trades[0]["symbol"] == "EURUSD"
        assert trades[1]["symbol"] == "GBPUSD"


class TestFBS:
    """FBS: European date format dd.mm.yyyy."""

    def test_european_dates(self):
        trades = parse_mt4_csv(FBS_CSV)
        assert len(trades) == 1
        t = trades[0]
        assert t["opened_at"] == "2024-01-15T09:30:00"
        assert t["closed_at"] == "2024-01-15T14:20:00"


class TestPepperstone:
    """Pepperstone/XM: 'Action'/'Lots' naming, ISO-ish dates."""

    def test_action_mapped_to_type(self):
        trades = parse_mt4_csv(PEPPERSTONE_CSV)
        assert len(trades) == 2
        assert trades[0]["direction"] == "buy"
        assert trades[1]["direction"] == "sell"

    def test_lots_mapped(self):
        trades = parse_mt4_csv(PEPPERSTONE_CSV)
        assert trades[0]["lot"] == 0.25


class TestNonTradeRowFiltering:
    """Balance, deposit, and other non-trade rows should be skipped."""

    def test_skips_balance_and_deposit(self):
        trades = parse_mt4_csv(WITH_BALANCE_ROWS)
        assert len(trades) == 1
        assert trades[0]["ticket"] == 12345678

    def test_skips_preamble(self):
        trades = parse_mt4_csv(WITH_PREAMBLE)
        assert len(trades) == 1

    def test_skips_footer(self):
        trades = parse_mt4_csv(WITH_FOOTER)
        assert len(trades) == 1


class TestEdgeCases:
    """Edge cases and validation."""

    def test_zero_sl_tp_becomes_none(self):
        trades = parse_mt4_csv(ZERO_SL_TP)
        assert trades[0]["stop_loss"] is None
        assert trades[0]["take_profit"] is None

    def test_bytes_input(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB.encode("utf-8"))
        assert len(trades) == 3

    def test_utf8_bom(self):
        content = b"\xef\xbb\xbf" + MT4_STANDARD_TAB.encode("utf-8")
        trades = parse_mt4_csv(content)
        assert len(trades) == 3

    def test_empty_content_raises(self):
        with pytest.raises(MT4ParseError, match="empty"):
            parse_mt4_csv("")

    def test_no_header_raises(self):
        with pytest.raises(MT4ParseError):
            parse_mt4_csv("just,some,random,data\n1,2,3,4\n")

    def test_all_output_fields_present(self):
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        expected_keys = {
            "ticket", "symbol", "direction", "lot",
            "open_price", "close_price", "stop_loss", "take_profit",
            "profit_pips", "profit_money", "commission", "swap",
            "opened_at", "closed_at", "source",
        }
        for t in trades:
            assert set(t.keys()) == expected_keys

    def test_source_always_csv(self):
        trades = parse_mt4_csv(IC_MARKETS_CSV)
        for t in trades:
            assert t["source"] == "csv"

    def test_direction_values(self):
        """Direction should only be 'buy' or 'sell'."""
        trades = parse_mt4_csv(MT4_STANDARD_TAB)
        for t in trades:
            assert t["direction"] in ("buy", "sell")
