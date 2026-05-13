import sys
sys.path.insert(0, '.')
import asyncio
from dotenv import load_dotenv
load_dotenv()

from tradecoach.services.coaching import build_full_coaching_prompt
from tradecoach.services.llm import deep_analysis
from tradecoach.parsers.xlsx_parser import parse_xlsx

with open('trading-journal.xlsx', 'rb') as f:
    trades = parse_xlsx(f.read())

prompt, context = build_full_coaching_prompt(
    trades=trades,
    account={'id': 'test', 'name': 'Demo', 'starting_balance': 25000, 'broker_timezone': 'UTC+2'},
    previous_session=None
)

print("Sending to Claude Sonnet...")

async def main():
    text, usage = await deep_analysis(prompt, context)
    print("\n" + "=" * 80)
    print("AI COACHING RESPONSE:")
    print("=" * 80)
    print(text)
    print("=" * 80)
    print(f"\nResponse length: {len(text)} chars")
    print(f"Model: {usage.model}")
    print(f"Tokens: {usage.input_tokens} in / {usage.output_tokens} out")
    print(f"Cost: ${usage.cost_usd:.4f}")
    print(f"Latency: {usage.latency_ms:.0f}ms")

asyncio.run(main())
