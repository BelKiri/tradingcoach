import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from tradecoach.services.coaching import build_full_coaching_prompt
from tradecoach.parsers.xlsx_parser import parse_xlsx

with open('trading-journal.xlsx', 'rb') as f:
    trades = parse_xlsx(f.read())

print(f"Parsed {len(trades)} trades\n")

# Build the full prompt that would go to Claude Sonnet
prompt, context = build_full_coaching_prompt(
    trades=trades,
    account={'id': 'test', 'name': 'Demo', 'starting_balance': 25000, 'broker_timezone': 'UTC+2'},
    previous_session=None
)

print("SYSTEM PROMPT FOR AI:")
print("=" * 80)
print(prompt)
print("=" * 80)

print("\n\nCONTEXT DATA FOR AI:")
print("=" * 80)
print(context)
print("=" * 80)

print(f"\nPrompt length: {len(prompt)} chars, ~{len(prompt)//4} tokens")
print(f"Context length: {len(context)} chars, ~{len(context)//4} tokens")
print(f"Total: {len(prompt) + len(context)} chars, ~{(len(prompt) + len(context))//4} tokens")
