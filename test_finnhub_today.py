import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from tradecoach.services.news import fetch_all_news, match_news_to_instruments
from datetime import datetime, timedelta

today = datetime.now().strftime('%Y-%m-%d')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

news = fetch_all_news(yesterday, today)
print(f"Total news items: {len(news)}")
print(f"Categories: forex={sum(1 for n in news if n.get('category')=='forex')}, general={sum(1 for n in news if n.get('category')=='general')}, crypto={sum(1 for n in news if n.get('category')=='crypto')}")

print(f"\n{'='*80}")
print("ALL NEWS WITH INSTRUMENT MATCHING:")
print(f"{'='*80}")

matched_count = 0
unmatched_count = 0

for n in sorted(news, key=lambda x: x.get('date', '')):
    instruments = match_news_to_instruments(n)
    headline = n.get('headline', 'no headline')[:100]
    source = n.get('source', '?')
    category = n.get('category', '?')

    if instruments:
        matched_count += 1
        print(f"\n✅ [{category}] {headline}")
        print(f"   Source: {source}")
        print(f"   Matched: {', '.join(instruments)}")
    else:
        unmatched_count += 1
        print(f"\n❌ [{category}] {headline}")
        print(f"   Source: {source}")
        print(f"   No instrument match")

print(f"\n{'='*80}")
print(f"SUMMARY: {matched_count} matched, {unmatched_count} unmatched out of {len(news)} total")
print(f"Match rate: {matched_count/len(news)*100:.0f}%" if news else "No news")

# Show instrument coverage
print(f"\nINSTRUMENT COVERAGE:")
instrument_counts = {}
for n in news:
    for inst in match_news_to_instruments(n):
        instrument_counts[inst] = instrument_counts.get(inst, 0) + 1
for inst, count in sorted(instrument_counts.items(), key=lambda x: -x[1]):
    print(f"  {inst}: {count} news items")
