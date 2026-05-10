"""
Telegram bot handlers — thin client, all logic in services.

Flows:
  /start      — welcome + persistent reply keyboard
  /accounts   — alias for My Accounts
  /premium    — premium placeholder
  /reset      — delete all user data with confirmation
  /cancel     — abort any flow

  Reply keyboard buttons:
    Upload trades  — account-based file upload
    My Accounts    — list/create/manage accounts
    Premium        — placeholder

  Account actions (inline):
    Upload trades to account
    Show report (all time / period)
    Clear account trades
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tradecoach.bot.keyboards import (
    BTN_ACCOUNTS,
    BTN_PREMIUM,
    BTN_UPLOAD,
    account_actions_keyboard,
    account_actions_new_keyboard,
    account_list_keyboard,
    analysis_keyboard,
    confirm_clear_keyboard,
    confirm_reset_keyboard,
    direction_keyboard,
    lot_keyboard,
    main_reply_keyboard,
    pair_keyboard,
    post_report_keyboard,
    post_upload_keyboard,
    report_type_keyboard,
    upload_account_keyboard,
)
from tradecoach.config import get_settings
from tradecoach.services.coaching import generate_ai_coaching
from tradecoach.services.llm import LLMError
from tradecoach.db.models import (
    AccountCreate,
    TradeCreate,
    UserCreate,
)
from tradecoach.parsers.mt4_parser import MT4ParseError, parse_mt4_csv
from tradecoach.parsers.xlsx_parser import XlsxParseError, parse_xlsx
from tradecoach.db.queries import (
    create_account,
    create_user,
    delete_account_trades,
    delete_user_data,
    find_existing_trade_keys,
    get_account,
    get_accounts,
    get_client,
    get_trades,
    get_user_by_telegram_id,
    get_user_settings,
    insert_trades,
)
from tradecoach.services.report_generator import generate_full_report
from tradecoach.services.risk_checker import run_pre_trade_check
from tradecoach.services.trade_analyzer import (
    detect_revenge_trades,
    max_drawdown,
    pnl_by_session,
    pnl_by_symbol,
    profit_factor,
    revenge_trade_cost,
    streaks,
    total_pnl,
    win_rate,
)

# ---------------------------------------------------------------------------
# Conversation states
# ---------------------------------------------------------------------------
(
    CHK_PAIR, CHK_PAIR_TEXT, CHK_DIR, CHK_LOT, CHK_LOT_TEXT,
    CHK_SL, CHK_BAL,
) = range(7)

(CSV_ACCOUNT, CSV_NAME, CSV_BALANCE, CSV_FILE) = range(7, 11)

(REPORT_PERIOD,) = range(11, 12)

(ACCT_NAME, ACCT_BALANCE) = range(12, 14)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if "user_id" in context.user_data:
        return context.user_data["user_id"]
    tg = update.effective_user
    client = get_client()
    user = get_user_by_telegram_id(client, tg.id)
    if not user:
        uid = str(uuid.uuid4())
        user = create_user(client, UserCreate(
            id=uid, telegram_id=tg.id, username=tg.username,
        ))
    context.user_data["user_id"] = user.id
    return user.id


def _cb_val(data: str) -> str:
    return data.split(":", 1)[1] if ":" in data else data


def _fmt_pnl(value: float) -> str:
    """Format P&L with correct sign: +$100.00 or -$50.00."""
    if value >= 0:
        return f"+${value:,.2f}"
    return f"-${abs(value):,.2f}"


def _get_trade_dicts(
    user_id: str,
    since: date | None = None,
    until: date | None = None,
    account_id: str | None = None,
) -> list[dict]:
    client = get_client()
    trades = get_trades(
        client, user_id, since=since, until=until,
        account_id=account_id, limit=5000,
    )
    return [t.model_dump() for t in trades]


def _split_report(report: str, max_len: int = 4096) -> list[str]:
    """Split a report into chunks that fit Telegram's message limit."""
    if len(report) <= max_len:
        return [report]

    chunks: list[str] = []
    lines = report.split("\n")
    current: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_len and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks


def _get_account_balance(user_id: str, account_id: str | None) -> float | None:
    """Get starting balance for an account."""
    if not account_id:
        return None
    client = get_client()
    acct = get_account(client, account_id)
    return acct.starting_balance if acct else None


def _get_user_accounts(user_id: str) -> list[dict]:
    """Get accounts as list of dicts with id and name."""
    client = get_client()
    accounts = get_accounts(client, user_id)
    return [{"id": a.id, "name": a.name} for a in accounts]


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ensure_user_id(update, context)
    await update.message.reply_text(
        "\U0001f44b Welcome to TradeCoach!\n\n"
        "I analyze your trades and show you exactly "
        "why you lose money \u2014 and how to fix it.\n\n"
        "\U0001f4ce Upload your trade history to get started.",
        reply_markup=main_reply_keyboard(),
    )


# ---------------------------------------------------------------------------
# /cancel
# ---------------------------------------------------------------------------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("check", None)
    context.user_data.pop("csv", None)
    context.user_data.pop("new_acct", None)
    msg = update.message or update.callback_query.message
    await msg.reply_text("Cancelled.", reply_markup=main_reply_keyboard())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Reply keyboard text handlers
# ---------------------------------------------------------------------------

async def upload_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Upload trades' reply keyboard button."""
    user_id = _ensure_user_id(update, context)
    accounts = _get_user_accounts(user_id)

    if not accounts:
        await update.message.reply_text(
            "You don't have any accounts yet.\n"
            "Go to \U0001f464 My Accounts to create one first.",
            reply_markup=main_reply_keyboard(),
        )
        return

    await update.message.reply_text(
        "Select account to upload to:",
        reply_markup=upload_account_keyboard(accounts),
    )


async def accounts_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'My Accounts' reply keyboard button."""
    user_id = _ensure_user_id(update, context)
    accounts = _get_user_accounts(user_id)
    await update.message.reply_text(
        "Your accounts:",
        reply_markup=account_list_keyboard(accounts),
    )


async def premium_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Premium' reply keyboard button."""
    await update.message.reply_text(
        "\u2b50 Premium features coming soon!\n\n"
        "AI-powered trade analysis, personalized coaching, "
        "and advanced risk management tools.",
        reply_markup=main_reply_keyboard(),
    )


# ---------------------------------------------------------------------------
# /accounts and /premium commands
# ---------------------------------------------------------------------------

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await accounts_button(update, context)


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await premium_button(update, context)


# ---------------------------------------------------------------------------
# /terms — trading term definitions
# ---------------------------------------------------------------------------

TERMS_TEXT = (
    "\U0001f4d6 TRADING TERMS\n"
    "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
    "\U0001f525 Revenge trading \u2014 We flag a trade as revenge when you "
    "open it within 5 minutes of closing a loss, with the same or "
    "bigger lot size. Emotional re-entry rarely ends well.\n\n"
    "\U0001f4c8 Overtrading \u2014 We flag days where you took 5 or more "
    "trades. Quality drops with volume \u2014 we compare your win rate "
    "on busy days vs normal days.\n\n"
    "\U0001f4c9 Martingale \u2014 We detect when your lot size jumps 40%+ "
    "after a losing trade. Increasing size to recover losses is how "
    "accounts blow up.\n\n"
    "\u2935\ufe0f Averaging down \u2014 We detect when you open 2+ positions "
    "in the same pair and direction within 30 minutes. Adding to a "
    "losing position multiplies your risk.\n\n"
    "\u23f1\ufe0f Quick exits \u2014 Trades closed within 2 minutes of opening. "
    "Usually panic or fear \u2014 you're not giving your setup time to "
    "play out.\n\n"
    "\U0001f4c9 Max drawdown \u2014 The biggest peak-to-trough drop in your "
    "account balance. Calculated as (peak \u2212 trough) / peak \u00d7 100%. "
    "Shows the worst hole you dug.\n\n"
    "\u2696\ufe0f Profit factor \u2014 Total profits divided by total losses. "
    "Above 1.5 is good, above 2.0 is excellent. Below 1.0 means "
    "you're losing money overall.\n\n"
    "\U0001f3af Win rate \u2014 Percentage of trades that were profitable. "
    "A 40% win rate can still be profitable if your winners are "
    "much bigger than your losers.\n\n"
    "\U0001f4b8 Drawdown \u2014 Any drop from a peak in your account equity. "
    "Managing drawdown is about survival \u2014 you can't trade "
    "if you blow your account."
)


async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /terms command."""
    msg = update.message or update.callback_query.message
    await msg.reply_text(TERMS_TEXT, reply_markup=main_reply_keyboard())


async def terms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline 'Terms' button."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(TERMS_TEXT, reply_markup=main_reply_keyboard())


# ---------------------------------------------------------------------------
# Account actions callbacks
# ---------------------------------------------------------------------------

async def account_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """Handle account selection from My Accounts list."""
    query = update.callback_query
    await query.answer()
    val = _cb_val(query.data)

    if val == "new":
        # Start account creation conversation
        context.user_data["new_acct"] = {}
        await query.message.reply_text(
            "Give it a name (e.g. \"Exness Main\", \"IC Markets Demo\"):"
        )
        return ACCT_NAME

    # Show account actions
    user_id = _ensure_user_id(update, context)
    client = get_client()
    acct = get_account(client, val)
    if not acct:
        await query.message.reply_text("Account not found.")
        return ConversationHandler.END

    await query.message.reply_text(
        f"\U0001f4bc Account: {acct.name}",
        reply_markup=account_actions_keyboard(val),
    )
    return ConversationHandler.END


async def acct_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture account name for new account (from My Accounts context)."""
    name = update.message.text.strip()
    if not name or len(name) > 100:
        await update.message.reply_text("Please enter a valid account name (1-100 chars):")
        return ACCT_NAME
    context.user_data["new_acct"]["name"] = name
    await update.message.reply_text(
        "What was your account balance before the first trade "
        "in your report? (e.g. 5000)\n\n"
        "Type \"skip\" if you don't know."
    )
    return ACCT_BALANCE


async def acct_balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture starting balance, create account (from My Accounts context)."""
    text = update.message.text.strip().lower()
    if text == "skip":
        balance = None
    else:
        try:
            balance = float(text.replace(",", "").replace("$", ""))
        except ValueError:
            await update.message.reply_text(
                "Invalid number. Enter your starting balance (e.g. 5000) or \"skip\":"
            )
            return ACCT_BALANCE

    user_id = context.user_data["user_id"]
    name = context.user_data.pop("new_acct")["name"]
    client = get_client()
    acct = create_account(client, AccountCreate(
        user_id=user_id,
        name=name,
        starting_balance=balance,
    ))

    await update.message.reply_text(
        f"\u2705 Account \"{name}\" created!",
        reply_markup=account_actions_new_keyboard(acct.id),
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Upload account selection callback (from Upload trades button)
# ---------------------------------------------------------------------------

async def upload_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle account selection for upload."""
    query = update.callback_query
    await query.answer()
    acct_id = _cb_val(query.data)

    client = get_client()
    acct = get_account(client, acct_id)
    name = acct.name if acct else "account"
    context.user_data["upload_account_id"] = acct_id
    await query.message.reply_text(
        f"Send your trade history file for \"{name}\" (CSV or Excel).",
    )


# ---------------------------------------------------------------------------
# Report flow (per-account)
# ---------------------------------------------------------------------------

async def report_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Show report' button — show report type chooser."""
    query = update.callback_query
    await query.answer()
    acct_id = _cb_val(query.data)
    context.user_data["report_account_id"] = acct_id

    await query.message.reply_text(
        "Choose report type:",
        reply_markup=report_type_keyboard(acct_id),
    )


async def report_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """Handle report type selection (full or period)."""
    query = update.callback_query
    await query.answer()
    acct_id = _cb_val(query.data)
    user_id = _ensure_user_id(update, context)
    context.user_data["report_account_id"] = acct_id

    await _generate_and_send_report(query.message, user_id, account_id=acct_id)
    return ConversationHandler.END


async def report_period_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Select period' — ask for date range."""
    query = update.callback_query
    await query.answer()
    acct_id = _cb_val(query.data)
    context.user_data["report_account_id"] = acct_id

    await query.message.reply_text(
        "Enter period in format: DD.MM.YYYY - DD.MM.YYYY\n"
        "(e.g. 01.01.2026 - 01.03.2026)"
    )
    return REPORT_PERIOD


async def report_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parse date range and generate period report."""
    text = update.message.text.strip()
    user_id = context.user_data["user_id"]
    account_id = context.user_data.get("report_account_id")

    # Parse DD.MM.YYYY - DD.MM.YYYY
    match = re.match(
        r"(\d{2})[./](\d{2})[./](\d{4})\s*[-\u2013]\s*(\d{2})[./](\d{2})[./](\d{4})",
        text,
    )
    if not match:
        await update.message.reply_text(
            "Invalid format. Please enter: DD.MM.YYYY - DD.MM.YYYY\n"
            "(e.g. 01.01.2026 - 01.03.2026)"
        )
        return REPORT_PERIOD

    try:
        d1, m1, y1, d2, m2, y2 = match.groups()
        since = date(int(y1), int(m1), int(d1))
        until = date(int(y2), int(m2), int(d2))
    except ValueError:
        await update.message.reply_text(
            "Invalid date. Please enter: DD.MM.YYYY - DD.MM.YYYY"
        )
        return REPORT_PERIOD

    if since > until:
        since, until = until, since

    await _generate_and_send_report(
        update.message, user_id, since=since, until=until, account_id=account_id,
    )
    return ConversationHandler.END


async def _generate_and_send_report(
    msg, user_id: str, *,
    since: date | None = None, until: date | None = None,
    account_id: str | None = None,
) -> None:
    """Generate and send the full analysis report."""
    trades = _get_trade_dicts(user_id, since=since, until=until, account_id=account_id)

    if not trades:
        period_str = ""
        if since and until:
            period_str = f" for {since.strftime('%d.%m.%Y')} - {until.strftime('%d.%m.%Y')}"
        reply_markup = post_upload_keyboard(account_id) if account_id else main_reply_keyboard()
        await msg.reply_text(
            f"No trades found{period_str}.",
            reply_markup=reply_markup,
        )
        return

    balance = _get_account_balance(user_id, account_id)
    report = generate_full_report(trades, None, account_balance=balance)

    chunks = _split_report(report)
    for i, chunk in enumerate(chunks):
        markup = post_report_keyboard(account_id) if (i == len(chunks) - 1 and account_id) else None
        await msg.reply_text(chunk, reply_markup=markup)


# ---------------------------------------------------------------------------
# AI Coaching
# ---------------------------------------------------------------------------

async def ai_coaching_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle AI Coaching button — generate and send AI analysis."""
    query = update.callback_query
    await query.answer()
    acct_id = _cb_val(query.data)

    user_id = _ensure_user_id(update, context)

    await query.message.reply_text("\U0001f9e0 Generating AI coaching analysis...")

    trades = _get_trade_dicts(user_id, account_id=acct_id)
    if not trades:
        await query.message.reply_text("No trades found for this account.")
        return

    balance = _get_account_balance(user_id, acct_id)

    client = get_client()
    acct = get_account(client, acct_id)
    acct_name = acct.name if acct else ""

    try:
        coaching_text, usage = await generate_ai_coaching(
            trades, account_balance=balance, account_name=acct_name,
        )
    except LLMError as e:
        await query.message.reply_text(
            f"Could not generate AI coaching: {e}\n\n"
            "Make sure API keys are configured.",
        )
        return

    chunks = _split_report(coaching_text)
    for i, chunk in enumerate(chunks):
        markup = post_report_keyboard(acct_id) if i == len(chunks) - 1 else None
        await query.message.reply_text(chunk, reply_markup=markup)


# ---------------------------------------------------------------------------
# Clear account trades
# ---------------------------------------------------------------------------

async def clear_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Clear account' button — show confirmation."""
    query = update.callback_query
    await query.answer()
    acct_id = _cb_val(query.data)

    client = get_client()
    acct = get_account(client, acct_id)
    name = acct.name if acct else "this account"
    await query.message.reply_text(
        f"\u26a0\ufe0f Delete all trades from \"{name}\"?\n"
        "This cannot be undone.",
        reply_markup=confirm_clear_keyboard(acct_id),
    )


async def clear_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle clear confirmation."""
    query = update.callback_query
    await query.answer()
    acct_id = _cb_val(query.data)

    client = get_client()
    count = delete_account_trades(client, acct_id)
    await query.message.reply_text(
        f"\u2705 {count} trades deleted.",
        reply_markup=main_reply_keyboard(),
    )


async def clear_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle clear cancellation."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "Clear cancelled.",
        reply_markup=main_reply_keyboard(),
    )


# ---------------------------------------------------------------------------
# Analysis drill-down callbacks
# ---------------------------------------------------------------------------

async def analysis_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = _cb_val(query.data)
    user_id = _ensure_user_id(update, context)
    trades = _get_trade_dicts(user_id)

    if action == "revenge":
        revenge = detect_revenge_trades(trades)
        cost = revenge_trade_cost(trades)
        if not revenge:
            await query.message.reply_text("No revenge trades detected. Good discipline!")
            return
        text = (
            f"Revenge Trading\n---\n"
            f"Revenge trades: {len(revenge)}\n"
            f"Cost: ${abs(cost):,.2f}\n"
        )
        await query.message.reply_text(text)

    elif action == "risk":
        from tradecoach.services.trade_analyzer import avg_win, avg_loss, max_drawdown
        aw = avg_win(trades)
        al = avg_loss(trades)
        dd = max_drawdown(trades)
        aw_str = f"${aw:,.2f}" if aw else "N/A"
        al_str = f"${al:,.2f}" if al else "N/A"
        text = (
            f"Risk Management\n---\n"
            f"Avg win: {aw_str}\n"
            f"Avg loss: {al_str}\n"
            f"Max drawdown: ${dd['amount']:,.2f}\n"
        )
        await query.message.reply_text(text)

    elif action == "times":
        sessions = pnl_by_session(trades)
        lines = ["Best/Worst Times\n---"]
        for session, data in sessions.items():
            sign = "+" if data["pnl"] >= 0 else ""
            lines.append(
                f"{session}: {sign}${data['pnl']:,.2f} "
                f"({data['win_rate']:.0f}% WR, {data['trades']} trades)"
            )
        await query.message.reply_text("\n".join(lines))

    elif action == "ask":
        await query.message.reply_text(
            "AI chat coming soon. For now, use /stats for your numbers."
        )


# ---------------------------------------------------------------------------
# Pre-trade check flow (kept but not registered — can be re-enabled later)
# ---------------------------------------------------------------------------

async def check_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _ensure_user_id(update, context)
    context.user_data["check"] = {}
    msg = update.message or update.callback_query.message
    await msg.reply_text("Select pair:", reply_markup=pair_keyboard("cpair"))
    return CHK_PAIR


async def check_pair(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    val = _cb_val(query.data)
    if val == "OTHER":
        await query.message.reply_text("Type the pair:")
        return CHK_PAIR_TEXT
    context.user_data["check"]["symbol"] = val.upper()
    await query.message.reply_text(f"{val} — Direction?", reply_markup=direction_keyboard("cdir"))
    return CHK_DIR


async def check_pair_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["check"]["symbol"] = update.message.text.strip().upper()
    await update.message.reply_text("Direction?", reply_markup=direction_keyboard("cdir"))
    return CHK_DIR


async def check_dir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["check"]["direction"] = _cb_val(query.data)
    await query.message.reply_text("Lot size?", reply_markup=lot_keyboard("clot"))
    return CHK_LOT


async def check_lot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    val = _cb_val(query.data)
    if val == "OTHER":
        await query.message.reply_text("Type lot size:")
        return CHK_LOT_TEXT
    context.user_data["check"]["lot"] = float(val)
    await query.message.reply_text("Stop loss distance in pips? (e.g. 30)")
    return CHK_SL


async def check_lot_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["check"]["lot"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid number. Type lot size:")
        return CHK_LOT_TEXT
    await update.message.reply_text("Stop loss distance in pips? (e.g. 30)")
    return CHK_SL


async def check_sl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["check"]["sl_pips"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid number. Stop loss in pips? (e.g. 30)")
        return CHK_SL
    await update.message.reply_text("Account balance in $? (e.g. 5000)")
    return CHK_BAL


async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        balance = float(update.message.text.strip().replace(",", "").replace("$", ""))
    except ValueError:
        await update.message.reply_text("Invalid number. Balance in $? (e.g. 5000)")
        return CHK_BAL

    c = context.user_data.pop("check")
    user_id = context.user_data["user_id"]
    client = get_client()

    jpy = "JPY" in c["symbol"].upper()
    sl_price_dist = c["sl_pips"] / (100 if jpy else 10_000)
    open_price = 1.0
    if c["direction"] == "buy":
        stop_loss = open_price - sl_price_dist
    else:
        stop_loss = open_price + sl_price_dist

    settings = get_user_settings(client, user_id)
    settings_dict = settings.model_dump() if settings else {}
    today_trades = get_trades(client, user_id, since=date.today())
    today_dicts = [t.model_dump() for t in today_trades]

    result = run_pre_trade_check(
        symbol=c["symbol"],
        direction=c["direction"],
        lot=c["lot"],
        stop_loss=stop_loss,
        open_price=open_price,
        account_balance=balance,
        settings=settings_dict,
        today_trades=today_dicts,
    )

    lines = [f"Pre-trade Check: {c['symbol']} {c['direction'].upper()} {c['lot']} lot\n---"]
    for item in result.items:
        icon = "PASS" if item.passed else "FAIL"
        lines.append(f"[{icon}] {item.message}")
    lines.append(f"\n{result.passed_count}/{result.total_count} checks passed.")
    if result.all_passed:
        lines.append("All clear. Trade responsibly.")
    else:
        lines.append("Review warnings before entering.")

    await update.message.reply_text("\n".join(lines), reply_markup=main_reply_keyboard())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Upload flow — account-based (from Upload trades button or acctup: callback)
# ---------------------------------------------------------------------------

async def csv_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for guided upload flow via /upload command."""
    user_id = _ensure_user_id(update, context)
    context.user_data["csv"] = {}
    msg = update.message or update.callback_query.message

    client = get_client()
    accounts = get_accounts(client, user_id)

    if accounts:
        acct_dicts = [{"id": a.id, "name": a.name} for a in accounts]
        await msg.reply_text(
            "Select account to upload to:",
            reply_markup=upload_account_keyboard(acct_dicts),
        )
        return CSV_ACCOUNT
    else:
        await msg.reply_text(
            "Let's create your first account.\n"
            "Give it a name (e.g. \"Exness Main\", \"IC Markets Demo\"):"
        )
        return CSV_NAME


async def csv_upload_to_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for upload via acctup: callback (account already chosen)."""
    query = update.callback_query
    await query.answer()
    acct_id = _cb_val(query.data)

    _ensure_user_id(update, context)
    context.user_data["csv"] = {"account_id": acct_id}

    client = get_client()
    acct = get_account(client, acct_id)
    name = acct.name if acct else "account"
    await query.message.reply_text(
        f"Send your trade history file for \"{name}\" (CSV or Excel)."
    )
    return CSV_FILE


async def csv_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle account selection in upload flow."""
    query = update.callback_query
    await query.answer()
    val = _cb_val(query.data)

    if val == "new":
        await query.message.reply_text(
            "Give it a name (e.g. \"Exness Main\", \"IC Markets Demo\"):"
        )
        return CSV_NAME

    context.user_data["csv"]["account_id"] = val
    client = get_client()
    acct = get_account(client, val)
    name = acct.name if acct else "account"
    await query.message.reply_text(
        f"Uploading to \"{name}\".\n"
        f"Send your trade history file (CSV or Excel)."
    )
    return CSV_FILE


async def csv_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture account name for new account."""
    name = update.message.text.strip()
    if not name or len(name) > 100:
        await update.message.reply_text("Please enter a valid account name (1-100 chars):")
        return CSV_NAME
    context.user_data["csv"]["name"] = name
    await update.message.reply_text(
        "What was your account balance before the first trade "
        "in your report? (e.g. 5000)\n\n"
        "Type \"skip\" if you don't know."
    )
    return CSV_BALANCE


async def csv_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture starting balance, create account, then ask for file."""
    text = update.message.text.strip().lower()
    if text == "skip":
        balance = None
    else:
        try:
            balance = float(text.replace(",", "").replace("$", ""))
        except ValueError:
            await update.message.reply_text(
                "Invalid number. Enter your starting balance (e.g. 5000) or \"skip\":"
            )
            return CSV_BALANCE

    user_id = context.user_data["user_id"]
    name = context.user_data["csv"]["name"]
    client = get_client()
    acct = create_account(client, AccountCreate(
        user_id=user_id,
        name=name,
        starting_balance=balance,
    ))
    context.user_data["csv"]["account_id"] = acct.id
    context.user_data["csv"]["balance"] = balance

    await update.message.reply_text(
        f"Account \"{name}\" created!\n"
        f"Now send your trade history file.\n"
        f"Export Account History from your broker as CSV or Excel."
    )
    return CSV_FILE


def _validate_trades(
    parsed: list[dict], user_id: str, account_id: str | None,
) -> tuple[list[TradeCreate], list[str]]:
    """Convert parsed dicts to TradeCreate models, collecting errors."""
    trade_creates: list[TradeCreate] = []
    errors: list[str] = []
    for i, t in enumerate(parsed):
        try:
            trade_creates.append(TradeCreate(
                user_id=user_id,
                account_id=account_id,
                source="csv",
                ticket=t.get("ticket"),
                symbol=t["symbol"],
                direction=t["direction"],
                lot=t["lot"],
                open_price=t.get("open_price"),
                close_price=t.get("close_price"),
                stop_loss=t.get("stop_loss"),
                take_profit=t.get("take_profit"),
                profit_pips=t.get("profit_pips"),
                profit_money=t.get("profit_money"),
                commission=t.get("commission") or 0.0,
                swap=t.get("swap") or 0.0,
                opened_at=t.get("opened_at"),
                closed_at=t.get("closed_at"),
            ))
        except Exception as exc:
            errors.append(f"Row {i + 1}: {exc}")
    return trade_creates, errors


def _dedup_trades(
    trade_creates: list[TradeCreate],
    existing_keys: set,
) -> tuple[list[TradeCreate], int]:
    """Filter out trades that already exist in the DB."""
    new_trades: list[TradeCreate] = []
    duplicates = 0
    for tc in trade_creates:
        opened_minute = None
        if tc.opened_at:
            opened_minute = tc.opened_at.replace(second=0, microsecond=0).isoformat()
        key = (tc.symbol, opened_minute, tc.direction, float(tc.lot))
        if key in existing_keys:
            duplicates += 1
        else:
            new_trades.append(tc)
    return new_trades, duplicates


async def csv_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle file upload with deduplication."""
    doc = update.message.document
    if not doc:
        await update.message.reply_text("Please send a trade history file (CSV or Excel).")
        return CSV_FILE

    filename = (doc.file_name or "").lower()
    is_excel = filename.endswith((".xlsx", ".xls"))
    is_csv = filename.endswith((".csv", ".txt"))
    if not is_excel and not is_csv:
        await update.message.reply_text(
            "Please send a .csv, .xlsx, or .xls file."
        )
        return CSV_FILE

    user_id = context.user_data["user_id"]
    csv_data = context.user_data.pop("csv")
    account_id = csv_data.get("account_id")

    tg_file = await doc.get_file()
    data = await tg_file.download_as_bytearray()
    if not data:
        await update.message.reply_text(
            "File is empty.", reply_markup=main_reply_keyboard(),
        )
        return ConversationHandler.END

    try:
        if is_excel:
            parsed = parse_xlsx(bytes(data))
        else:
            parsed = parse_mt4_csv(bytes(data))
    except (MT4ParseError, XlsxParseError) as e:
        await update.message.reply_text(
            f"Could not parse file: {e}\n\n"
            "Supported formats: MT4/MT5 CSV, Excel trade history (.xlsx).\n"
            "Export your Account History from the terminal.",
            reply_markup=main_reply_keyboard(),
        )
        return ConversationHandler.END

    if not parsed:
        await update.message.reply_text(
            "No trades found in the file.", reply_markup=main_reply_keyboard(),
        )
        return ConversationHandler.END

    trade_creates, errors = _validate_trades(parsed, user_id, account_id)
    if not trade_creates:
        await update.message.reply_text(
            f"All {len(parsed)} trades failed validation:\n"
            + "\n".join(errors[:5]),
            reply_markup=main_reply_keyboard(),
        )
        return ConversationHandler.END

    client = get_client()
    existing_keys = find_existing_trade_keys(
        client, user_id, account_id=account_id,
    )
    new_trades, duplicates = _dedup_trades(trade_creates, existing_keys)

    if not new_trades:
        await update.message.reply_text(
            f"All {len(trade_creates)} trades already exist (duplicates skipped).\n"
            "Send a different file or export a wider date range.",
            reply_markup=post_upload_keyboard(account_id) if account_id else main_reply_keyboard(),
        )
        return ConversationHandler.END

    try:
        saved = insert_trades(client, new_trades)
    except Exception as exc:
        await update.message.reply_text(
            f"Database error: {exc}", reply_markup=main_reply_keyboard(),
        )
        return ConversationHandler.END

    parts = [f"\u2705 {len(saved)} new trades imported"]
    if duplicates:
        parts.append(f" ({duplicates} duplicates skipped)")
    if errors:
        parts.append(f" ({len(errors)} rows skipped)")
    await update.message.reply_text(
        "".join(parts),
        reply_markup=post_upload_keyboard(account_id) if account_id else main_reply_keyboard(),
    )

    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Standalone file upload — uses upload_account_id from reply keyboard flow
# ---------------------------------------------------------------------------

async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle trade files sent outside the guided flow."""
    doc = update.message.document
    filename = (doc.file_name or "").lower()
    if not filename.endswith((".csv", ".txt", ".xlsx", ".xls")):
        return

    # If user selected an account via reply keyboard upload flow
    account_id = context.user_data.pop("upload_account_id", None)
    if account_id:
        # Process the file directly
        user_id = _ensure_user_id(update, context)
        context.user_data["csv"] = {"account_id": account_id}
        # Reuse csv_file logic
        await csv_file(update, context)
        return

    _ensure_user_id(update, context)
    await update.message.reply_text(
        "To import your trades, use the \U0001f4ce Upload trades button.\n"
        "I need to know which account to import to.",
        reply_markup=main_reply_keyboard(),
    )


# ---------------------------------------------------------------------------
# /stats — redirect to accounts
# ---------------------------------------------------------------------------

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _ensure_user_id(update, context)
    accounts = _get_user_accounts(user_id)

    if not accounts:
        await update.message.reply_text(
            "Create an account first to view reports.",
            reply_markup=main_reply_keyboard(),
        )
        return

    await update.message.reply_text(
        "Select account to view report:",
        reply_markup=account_list_keyboard(accounts),
    )


# ---------------------------------------------------------------------------
# /reset — delete all user data
# ---------------------------------------------------------------------------

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ensure_user_id(update, context)
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        "\u26a0\ufe0f Are you sure? This will delete ALL your trades "
        "and accounts. This cannot be undone.",
        reply_markup=confirm_reset_keyboard(),
    )


async def reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = _cb_val(query.data)

    if action == "cancel":
        await query.message.reply_text(
            "Reset cancelled.", reply_markup=main_reply_keyboard(),
        )
        return

    user_id = _ensure_user_id(update, context)
    client = get_client()
    delete_user_data(client, user_id)
    await query.message.reply_text(
        "\u2705 All data cleared. Send a new trade history file to start fresh.",
        reply_markup=main_reply_keyboard(),
    )


# ---------------------------------------------------------------------------
# Wire everything together
# ---------------------------------------------------------------------------

async def _post_init(app: Application) -> None:
    """Register BotFather menu commands after bot is initialized."""
    await app.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("accounts", "My accounts"),
        BotCommand("stats", "View reports"),
        BotCommand("terms", "Trading terms explained"),
        BotCommand("premium", "Premium features"),
        BotCommand("reset", "Delete all data"),
    ])


def setup_handlers(app: Application) -> None:
    """Register all handlers on the application."""

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("accounts", accounts_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(CommandHandler("premium", premium_command))
    app.add_handler(CommandHandler("reset", reset_command))

    # Reset confirmation
    app.add_handler(CallbackQueryHandler(reset_callback, pattern=r"^reset:"))

    # Account creation conversation (from My Accounts > Create new)
    acct_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(account_select_callback, pattern=r"^acct:"),
        ],
        per_message=False,
        states={
            ACCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, acct_name_handler)],
            ACCT_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, acct_balance_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(acct_conv)

    # Upload conversation (guided flow via /upload or acctup: callback)
    csv_conv = ConversationHandler(
        entry_points=[
            CommandHandler("upload", csv_start),
            CallbackQueryHandler(csv_upload_to_account, pattern=r"^acctup:"),
        ],
        per_message=False,
        states={
            CSV_ACCOUNT: [CallbackQueryHandler(csv_account, pattern=r"^acctup:")],
            CSV_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, csv_name)],
            CSV_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, csv_balance)],
            CSV_FILE: [MessageHandler(filters.Document.ALL, csv_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(csv_conv)

    # Report conversation (period date entry)
    report_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(report_period_select_callback, pattern=r"^rptperiod:"),
        ],
        per_message=False,
        states={
            REPORT_PERIOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, report_period),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(report_conv)

    # Account report (full)
    app.add_handler(CallbackQueryHandler(report_type_callback, pattern=r"^rptfull:"))

    # Account report selection
    app.add_handler(CallbackQueryHandler(report_select_callback, pattern=r"^acctrpt:"))

    # Clear account
    app.add_handler(CallbackQueryHandler(clear_account_callback, pattern=r"^acctclr:"))
    app.add_handler(CallbackQueryHandler(clear_confirm_callback, pattern=r"^clryes:"))
    app.add_handler(CallbackQueryHandler(clear_cancel_callback, pattern=r"^clrno"))

    # Upload account selection (from reply keyboard)
    app.add_handler(CallbackQueryHandler(upload_account_callback, pattern=r"^acctup:"))

    # Reply keyboard text handlers
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(f"^{re.escape(BTN_UPLOAD)}$"),
        upload_button,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(f"^{re.escape(BTN_ACCOUNTS)}$"),
        accounts_button,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(f"^{re.escape(BTN_PREMIUM)}$"),
        premium_button,
    ))

    # Standalone file upload
    app.add_handler(MessageHandler(filters.Document.ALL, handle_csv_upload))

    # Terms callback (from post-report inline button)
    app.add_handler(CallbackQueryHandler(terms_callback, pattern=r"^terms$"))

    # AI Coaching callback
    app.add_handler(CallbackQueryHandler(ai_coaching_callback, pattern=r"^aicoach:"))

    # Analysis drill-down
    app.add_handler(CallbackQueryHandler(analysis_callback, pattern=r"^analysis:"))


def build_application() -> Application:
    """Create and configure the Telegram bot application."""
    settings = get_settings()
    app = Application.builder().token(settings.telegram_bot_token).build()
    setup_handlers(app)
    app.post_init = _post_init
    return app
