import sys
sys.path.insert(0, '.')

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

from tradecoach.services.news import (
    fetch_all_news,
    fetch_news_finnhub,
    match_news_to_instruments,
    get_relevant_news_for_trades,
    build_news_context_for_coaching,
)
from tradecoach.parsers.xlsx_parser import parse_xlsx

# ---------------------------------------------------------------------------
# 1. Check FINNHUB_API_KEY
# ---------------------------------------------------------------------------
has_key = bool(os.environ.get("FINNHUB_API_KEY"))
print(f"FINNHUB_API_KEY in .env: {'YES' if has_key else 'NO'}")
print()

# ---------------------------------------------------------------------------
# 2. Fetch LIVE news from Finnhub (today) to prove API works
# ---------------------------------------------------------------------------
if has_key:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Fetching LIVE news from Finnhub for today ({today})...")
    for cat in ("forex", "general", "crypto"):
        items = fetch_news_finnhub(today, today, cat)
        print(f"  {cat}: {len(items)} items")
        for item in items[:3]:
            instruments = match_news_to_instruments(item)
            tag = ", ".join(instruments) if instruments else "(no match)"
            print(f"    {item['date']} | {item['headline'][:70]}")
            print(f"                  → {tag}")
    print()
    print("NOTE: Finnhub free tier only returns recent news (not historical).")
    print("      Using mock dataset for historical trade matching below.\n")

# ---------------------------------------------------------------------------
# 3. Mock news for historical period (Jan-Mar 2026)
# ---------------------------------------------------------------------------
print("Historical mock news dataset for Jan-Mar 2026:")
news = [
    {"date": "2026-01-08 14:00", "headline": "Iran launches missiles at Israeli targets, Middle East tensions escalate", "summary": "Military conflict intensifies as Iran retaliates", "source": "Reuters", "url": "", "category": "general"},
    {"date": "2026-01-09 13:45", "headline": "US Non-Farm Payrolls beat expectations at 256K, dollar surges", "summary": "Strong NFP data pushes dollar higher against major currencies. US employment remains robust.", "source": "Bloomberg", "url": "", "category": "forex"},
    {"date": "2026-01-14 14:00", "headline": "US CPI comes in hot at 3.2%, Fed rate cut hopes fade", "summary": "US inflation higher than expected, markets reprice Fed path", "source": "CNBC", "url": "", "category": "forex"},
    {"date": "2026-01-22 13:30", "headline": "ECB cuts rates by 25bps as eurozone growth stalls", "summary": "European Central Bank lowers rates, euro weakens against dollar", "source": "Reuters", "url": "", "category": "forex"},
    {"date": "2026-01-28 19:15", "headline": "FOMC holds rates steady, signals patience on cuts", "summary": "Federal Reserve keeps rates unchanged, Powell cautious on inflation", "source": "Bloomberg", "url": "", "category": "forex"},
    {"date": "2026-02-03 10:00", "headline": "Gold price hits record $2,950 on safe haven demand", "summary": "Gold surges as geopolitical risks and central bank buying drive demand", "source": "Reuters", "url": "", "category": "forex"},
    {"date": "2026-02-06 13:45", "headline": "NFP misses badly at 125K, recession fears spike", "summary": "Weak US jobs data sparks recession fears, dollar drops sharply", "source": "Bloomberg", "url": "", "category": "forex"},
    {"date": "2026-02-10 15:00", "headline": "Bitcoin surges past $110K as ETF inflows hit new record", "summary": "Bitcoin rallies on massive institutional ETF bitcoin inflows", "source": "CoinDesk", "url": "", "category": "crypto"},
    {"date": "2026-02-11 13:45", "headline": "US CPI drops to 2.8%, rate cut bets surge", "summary": "US inflation cools faster than expected, markets price in June cut", "source": "CNBC", "url": "", "category": "forex"},
    {"date": "2026-02-20 09:00", "headline": "Russia-Ukraine ceasefire collapses, troops mobilize", "summary": "Military conflict resumes as ceasefire breaks down, sanctions expected", "source": "Reuters", "url": "", "category": "general"},
    {"date": "2026-02-26 14:00", "headline": "US GDP revised down to 1.2%, slowdown deepens", "summary": "US GDP growth weaker than expected, recession fears grow", "source": "Bloomberg", "url": "", "category": "forex"},
    {"date": "2026-03-02 15:15", "headline": "OPEC announces surprise production cut, oil price jumps", "summary": "OPEC cuts output by 1M barrels, crude oil surges 5%", "source": "Reuters", "url": "", "category": "forex"},
    {"date": "2026-03-02 16:00", "headline": "Wall Street sells off on stagflation fears", "summary": "S&P 500 drops 2% as recession and inflation fears collide. US stocks under pressure.", "source": "CNBC", "url": "", "category": "general"},
]
print(f"  {len(news)} mock headlines\n")

# ---------------------------------------------------------------------------
# 4. Parse real trades
# ---------------------------------------------------------------------------
with open('trading-journal.xlsx', 'rb') as f:
    trades = parse_xlsx(f.read())
print(f"Total trades: {len(trades)}")
print(f"Date range: {min(t['opened_at'] for t in trades)} — {max(t['opened_at'] for t in trades)}")
symbols = set(t['symbol'] for t in trades)
print(f"Instruments traded: {sorted(symbols)}")
print()

# ---------------------------------------------------------------------------
# 5. Match each news item to instruments
# ---------------------------------------------------------------------------
print("=" * 70)
print("NEWS → INSTRUMENT MATCHING")
print("=" * 70)
for n in news:
    matched = match_news_to_instruments(n)
    tag = ", ".join(matched) if matched else "(no match)"
    print(f"  {n['date'][:10]} | {n['headline'][:65]}")
    print(f"           → {tag}")
    print()

# ---------------------------------------------------------------------------
# 6. Build coaching context
# ---------------------------------------------------------------------------
print("=" * 70)
print("COACHING CONTEXT STRING")
print("=" * 70)
ctx = build_news_context_for_coaching(trades, news, broker_timezone="UTC+2")
if ctx:
    print(ctx)
else:
    print("(empty — no trades matched any news)")
print()

# ---------------------------------------------------------------------------
# 7. Summary stats
# ---------------------------------------------------------------------------
matched_results = get_relevant_news_for_trades(trades, news, "UTC+2")
news_trade_ids = set()
for m in matched_results:
    news_trade_ids.add(id(m["trade"]))

news_trades = [t for t in trades if id(t) in news_trade_ids]
normal_trades = [t for t in trades if id(t) not in news_trade_ids]

def _net(t):
    return (t.get("profit_money") or 0) + (t.get("commission") or 0) + (t.get("swap") or 0)

def _wr(group):
    if not group: return "N/A"
    wins = sum(1 for t in group if _net(t) > 0)
    return f"{wins/len(group)*100:.1f}%"

def _pnl(group):
    return sum(_net(t) for t in group)

print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total trades: {len(trades)}")
print(f"Trades with relevant news nearby: {len(news_trades)}")
print(f"Trades without news: {len(normal_trades)}")
print(f"")
print(f"With news    — WR: {_wr(news_trades)}, P&L: ${_pnl(news_trades):+,.2f}")
print(f"Without news — WR: {_wr(normal_trades)}, P&L: ${_pnl(normal_trades):+,.2f}")
