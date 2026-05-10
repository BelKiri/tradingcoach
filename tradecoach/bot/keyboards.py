"""
Keyboards for Telegram bot flows.

Reply keyboard: always visible after /start (Upload trades, My Accounts, Premium).
Inline keyboards: context-specific buttons within conversations.
Callback data uses 'prefix:value' pattern for routing.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "USDCAD", "NZDUSD", "EURJPY",
    "GBPJPY", "EURGBP", "XAUUSD",
]

LOTS = ["0.01", "0.05", "0.1", "0.2", "0.5", "1.0"]

# Reply keyboard button labels (used for text matching in handlers)
BTN_UPLOAD = "\U0001f4ce Upload trades"
BTN_ACCOUNTS = "\U0001f464 My Accounts"
BTN_PREMIUM = "\u2b50 Premium"


def _grid(items: list[tuple[str, str]], cols: int = 3) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for label, cb_data in items:
        row.append(InlineKeyboardButton(label, callback_data=cb_data))
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Reply keyboard (persistent, always visible)
# ---------------------------------------------------------------------------

def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Always-visible reply keyboard."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_UPLOAD), KeyboardButton(BTN_ACCOUNTS)],
            [KeyboardButton(BTN_PREMIUM)],
        ],
        resize_keyboard=True,
    )


# ---------------------------------------------------------------------------
# Inline keyboards
# ---------------------------------------------------------------------------

def pair_keyboard(prefix: str = "pair") -> InlineKeyboardMarkup:
    items = [(p, f"{prefix}:{p}") for p in PAIRS]
    rows = _grid(items, cols=3)
    rows.append([InlineKeyboardButton("Other (type it)", callback_data=f"{prefix}:OTHER")])
    return InlineKeyboardMarkup(rows)


def direction_keyboard(prefix: str = "dir") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Buy", callback_data=f"{prefix}:buy"),
        InlineKeyboardButton("Sell", callback_data=f"{prefix}:sell"),
    ]])


def lot_keyboard(prefix: str = "lot") -> InlineKeyboardMarkup:
    items = [(l, f"{prefix}:{l}") for l in LOTS]
    rows = _grid(items, cols=3)
    rows.append([InlineKeyboardButton("Other (type it)", callback_data=f"{prefix}:OTHER")])
    return InlineKeyboardMarkup(rows)


def account_list_keyboard(
    accounts: list[dict],
) -> InlineKeyboardMarkup:
    """My Accounts list — existing accounts + create new."""
    rows = [
        [InlineKeyboardButton(a["name"], callback_data=f"acct:{a['id']}")]
        for a in accounts
    ]
    rows.append([InlineKeyboardButton("\u2795 Create new account", callback_data="acct:new")])
    return InlineKeyboardMarkup(rows)


def account_actions_keyboard(account_id: str) -> InlineKeyboardMarkup:
    """Actions for a specific account."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f4ce Upload trades", callback_data=f"acctup:{account_id}")],
        [InlineKeyboardButton("\U0001f4ca Show report", callback_data=f"acctrpt:{account_id}")],
        [InlineKeyboardButton("\U0001f5d1 Clear account", callback_data=f"acctclr:{account_id}")],
    ])


def account_actions_new_keyboard(account_id: str) -> InlineKeyboardMarkup:
    """Actions for a newly created account (no report yet)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f4ce Upload trades", callback_data=f"acctup:{account_id}")],
        [InlineKeyboardButton("\U0001f5d1 Clear account", callback_data=f"acctclr:{account_id}")],
    ])


def upload_account_keyboard(
    accounts: list[dict],
) -> InlineKeyboardMarkup:
    """Account selector for upload — includes create new."""
    rows = [
        [InlineKeyboardButton(a["name"], callback_data=f"acctup:{a['id']}")]
        for a in accounts
    ]
    rows.append([InlineKeyboardButton("\u2795 Create new account", callback_data="acct:new")])
    return InlineKeyboardMarkup(rows)


def post_upload_keyboard(account_id: str) -> InlineKeyboardMarkup:
    """After successful import — report or upload more."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f4ca Show report", callback_data=f"acctrpt:{account_id}")],
        [InlineKeyboardButton("\U0001f4ce Upload more", callback_data=f"acctup:{account_id}")],
    ])


def post_report_keyboard(account_id: str) -> InlineKeyboardMarkup:
    """After showing a report — AI coaching, terms, or upload more."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f9e0 AI Coaching", callback_data=f"aicoach:{account_id}")],
        [
            InlineKeyboardButton("\U0001f4d6 Terms", callback_data="terms"),
            InlineKeyboardButton("\U0001f4ce Upload more", callback_data=f"acctup:{account_id}"),
        ],
    ])


def report_type_keyboard(account_id: str) -> InlineKeyboardMarkup:
    """Choose between full report and period report."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "\U0001f4ca All time", callback_data=f"rptfull:{account_id}")],
        [InlineKeyboardButton(
            "\U0001f4c5 Select period", callback_data=f"rptperiod:{account_id}")],
    ])


def confirm_clear_keyboard(account_id: str) -> InlineKeyboardMarkup:
    """Confirm clearing trades for a specific account."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Yes, delete all trades", callback_data=f"clryes:{account_id}")],
        [InlineKeyboardButton("Cancel", callback_data="clrno")],
    ])


def confirm_reset_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes, delete everything", callback_data="reset:confirm")],
        [InlineKeyboardButton("Cancel", callback_data="reset:cancel")],
    ])


def analysis_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Revenge trading details", callback_data="analysis:revenge")],
        [InlineKeyboardButton("Risk management", callback_data="analysis:risk")],
        [InlineKeyboardButton("Best/worst times", callback_data="analysis:times")],
        [InlineKeyboardButton("Ask a question", callback_data="analysis:ask")],
    ])
