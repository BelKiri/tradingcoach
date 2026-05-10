import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from tradecoach.services.market_data import analyze_trader_volatility, build_volatility_context_for_coaching
from tradecoach.parsers.xlsx_parser import parse_xlsx

# Parse real trades
with open('trading-journal.xlsx', 'rb') as f:
    trades = parse_xlsx(f.read())
print(f"Total trades: {len(trades)}")

# Get unique instruments
instruments = set(t['symbol'] for t in trades)
print(f"Instruments: {instruments}")

# Run volatility analysis (Exness = UTC+2)
print("\nFetching price data from TwelveData (may take a minute due to rate limits)...")
result = analyze_trader_volatility(trades, broker_timezone="UTC+2")

print(f"\n{'='*60}")
print(f"VOLATILITY ANALYSIS RESULTS")
print(f"{'='*60}")

hv = result['high_vol']
nv = result['normal']

if hv['count'] > 0:
    print(f"\nHigh-volatility trades: {hv['count']} trades, WR {hv['wr']:.1f}%, P&L ${hv['pnl']:+,.2f}")
else:
    print(f"\nHigh-volatility trades: 0 trades")

if nv['count'] > 0:
    print(f"Normal trades: {nv['count']} trades, WR {nv['wr']:.1f}%, P&L ${nv['pnl']:+,.2f}")
else:
    print(f"Normal trades: 0 trades")

print(f"Money lost to volatility: ${result['money_lost_to_volatility']:+,.2f}")

print(f"\nVolatile day details:")
for day in hv.get('days', []):
    print(f"  {day['date']} {day['symbol']}: ATR ratio {day['atr_ratio']:.1f}x, day range ratio {day['day_ratio']:.1f}x")
    print(f"    Trades: {day['trades_count']}, P&L: ${day['day_pnl']:+,.2f}")

if not hv.get('days'):
    print("  (none)")

# Now build full coaching context (without news for now)
print(f"\n{'='*60}")
print(f"COACHING CONTEXT (what AI will see):")
print(f"{'='*60}")
context = build_volatility_context_for_coaching(trades, broker_timezone="UTC+2")
if context:
    print(context)
else:
    print("(empty — no trades on volatile days)")
