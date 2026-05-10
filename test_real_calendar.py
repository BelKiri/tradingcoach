import sys
sys.path.insert(0, '.')

from tradecoach.services.calendar import load_calendar, calculate_news_impact
from tradecoach.parsers.xlsx_parser import parse_xlsx

# Parse real trades
with open('trading-journal.xlsx', 'rb') as f:
    trades = parse_xlsx(f.read())
print(f"Total trades: {len(trades)}")
print(f"Date range: {min(t['opened_at'] for t in trades)} — {max(t['opened_at'] for t in trades)}")

# Load calendar
events = load_calendar('2026-01-01', '2026-03-31')
print(f"High Impact events in period: {len(events)}")
for e in events:
    print(f"  {e['date']} {e['time_utc']} — {e['currency']} {e['event_name']}")

# Calculate news impact (Exness = UTC+2)
result = calculate_news_impact(trades, events, broker_timezone="UTC+2")

print(f"\n{'='*60}")
print(f"NEWS IMPACT ANALYSIS")
print(f"{'='*60}")
print(f"\nTrades near news: {result['news_trades_count']}")
print(f"News WR: {result['news_wr']:.1f}%")
print(f"News P&L: ${result['news_pnl']:+,.2f}")
print(f"\nNormal trades: {result['normal_trades_count']}")
print(f"Normal WR: {result['normal_wr']:.1f}%")
print(f"Normal P&L: ${result['normal_pnl']:+,.2f}")
print(f"\nMoney lost to news: ${result.get('money_lost_to_news', 0):+,.2f}")
print(f"\nPer-event breakdown:")
for e in result.get('worst_events', []):
    print(f"  {e['date']} {e['event_name']}: {e['trades_count']} trades, ${e['pnl']:+,.2f}")
