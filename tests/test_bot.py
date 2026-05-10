"""
Tests for Telegram bot handlers and keyboards.

Tests verify:
  - Keyboard layout and callback data patterns
  - Handler logic with mocked DB and Telegram objects
  - Conversation flow state transitions
  - Account-centric upload flow
  - Per-account report flow (full and period)
  - Account clearing flow
  - Reset data flow
  - Reply keyboard text matching
  - Menu command registration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tradecoach.parsers.mt4_parser import MT4ParseError
from tradecoach.parsers.xlsx_parser import XlsxParseError
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


# ===================================================================
# Keyboard tests
# ===================================================================


class TestPairKeyboard:
    def test_contains_major_pairs(self):
        kb = pair_keyboard()
        all_cb = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "pair:EURUSD" in all_cb
        assert "pair:GBPUSD" in all_cb
        assert "pair:USDJPY" in all_cb
        assert "pair:XAUUSD" in all_cb

    def test_has_other_option(self):
        kb = pair_keyboard()
        last_row = kb.inline_keyboard[-1]
        assert last_row[0].callback_data == "pair:OTHER"

    def test_custom_prefix(self):
        kb = pair_keyboard("cpair")
        all_cb = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "cpair:EURUSD" in all_cb
        assert "cpair:OTHER" in all_cb

    def test_grid_layout(self):
        kb = pair_keyboard()
        for row in kb.inline_keyboard[:-1]:
            assert len(row) <= 3


class TestDirectionKeyboard:
    def test_buy_sell(self):
        kb = direction_keyboard()
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "dir:buy" in cbs
        assert "dir:sell" in cbs

    def test_custom_prefix(self):
        kb = direction_keyboard("cdir")
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "cdir:buy" in cbs
        assert "cdir:sell" in cbs


class TestLotKeyboard:
    def test_preset_lots(self):
        kb = lot_keyboard()
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "lot:0.01" in cbs
        assert "lot:0.1" in cbs
        assert "lot:1.0" in cbs

    def test_has_other(self):
        kb = lot_keyboard()
        last_row = kb.inline_keyboard[-1]
        assert last_row[0].callback_data == "lot:OTHER"


class TestAnalysisKeyboard:
    def test_drill_down_options(self):
        kb = analysis_keyboard()
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "analysis:revenge" in cbs
        assert "analysis:risk" in cbs
        assert "analysis:times" in cbs
        assert "analysis:ask" in cbs


class TestMainReplyKeyboard:
    def test_has_three_buttons(self):
        kb = main_reply_keyboard()
        all_labels = [btn.text for row in kb.keyboard for btn in row]
        assert BTN_UPLOAD in all_labels
        assert BTN_ACCOUNTS in all_labels
        assert BTN_PREMIUM in all_labels

    def test_layout(self):
        kb = main_reply_keyboard()
        assert len(kb.keyboard) == 2
        assert len(kb.keyboard[0]) == 2  # Upload + Accounts
        assert len(kb.keyboard[1]) == 1  # Premium

    def test_resize_keyboard(self):
        kb = main_reply_keyboard()
        assert kb.resize_keyboard is True


class TestAccountListKeyboard:
    def test_empty_accounts(self):
        kb = account_list_keyboard([])
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acct:new" in cbs
        assert len(cbs) == 1

    def test_with_accounts(self):
        accounts = [
            {"id": "a1", "name": "Exness"},
            {"id": "a2", "name": "IC Markets"},
        ]
        kb = account_list_keyboard(accounts)
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acct:a1" in cbs
        assert "acct:a2" in cbs
        assert "acct:new" in cbs


class TestAccountActionsKeyboard:
    def test_has_upload_report_clear(self):
        kb = account_actions_keyboard("a1")
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctup:a1" in cbs
        assert "acctrpt:a1" in cbs
        assert "acctclr:a1" in cbs

    def test_new_account_no_report(self):
        kb = account_actions_new_keyboard("a1")
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctup:a1" in cbs
        assert "acctclr:a1" in cbs
        assert "acctrpt:a1" not in cbs


class TestUploadAccountKeyboard:
    def test_upload_accounts(self):
        accounts = [{"id": "a1", "name": "Exness"}]
        kb = upload_account_keyboard(accounts)
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctup:a1" in cbs
        assert "acct:new" in cbs


class TestPostUploadKeyboard:
    def test_has_report_and_upload_more(self):
        kb = post_upload_keyboard("a1")
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctrpt:a1" in cbs
        assert "acctup:a1" in cbs


class TestReportTypeKeyboard:
    def test_full_and_period(self):
        kb = report_type_keyboard("a1")
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "rptfull:a1" in cbs
        assert "rptperiod:a1" in cbs


class TestPostReportKeyboard:
    def test_has_ai_coaching_terms_and_upload(self):
        kb = post_report_keyboard("a1")
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "aicoach:a1" in cbs
        assert "terms" in cbs
        assert "acctup:a1" in cbs

    def test_no_show_report(self):
        kb = post_report_keyboard("a1")
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctrpt:a1" not in cbs

    def test_ai_coaching_label(self):
        kb = post_report_keyboard("a1")
        labels = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("AI Coaching" in label for label in labels)


class TestConfirmClearKeyboard:
    def test_confirm_and_cancel(self):
        kb = confirm_clear_keyboard("a1")
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "clryes:a1" in cbs
        assert "clrno" in cbs


class TestConfirmResetKeyboard:
    def test_confirm_and_cancel(self):
        kb = confirm_reset_keyboard()
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "reset:confirm" in cbs
        assert "reset:cancel" in cbs
        labels = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "Yes, delete everything" in labels
        assert "Cancel" in labels


# ===================================================================
# Handler helper tests
# ===================================================================


class TestCbVal:
    def test_extracts_value(self):
        from tradecoach.bot.handlers import _cb_val
        assert _cb_val("pair:EURUSD") == "EURUSD"
        assert _cb_val("dir:buy") == "buy"
        assert _cb_val("result:-10") == "-10"

    def test_no_prefix(self):
        from tradecoach.bot.handlers import _cb_val
        assert _cb_val("nocolon") == "nocolon"


# ===================================================================
# Handler tests (with mocked Telegram + DB)
# ===================================================================


def _make_update(message_text=None, callback_data=None, user_id=123, username="testuser"):
    """Create a mock Update object."""
    update = MagicMock(spec=["effective_user", "message", "callback_query"])
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = username

    if message_text:
        update.message = AsyncMock()
        update.message.text = message_text
        update.message.reply_text = AsyncMock()
        update.callback_query = None
    elif callback_data:
        update.message = None
        update.callback_query = AsyncMock()
        update.callback_query.data = callback_data
        update.callback_query.answer = AsyncMock()
        update.callback_query.message = AsyncMock()
        update.callback_query.message.reply_text = AsyncMock()
    else:
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        update.callback_query = None

    return update


def _make_context(user_data=None):
    """Create a mock context."""
    context = MagicMock()
    context.user_data = user_data or {}
    return context


@pytest.fixture
def mock_db():
    """Mock all DB calls."""
    with patch("tradecoach.bot.handlers.get_client") as mock_client, \
         patch("tradecoach.bot.handlers.get_user_by_telegram_id") as mock_get_user, \
         patch("tradecoach.bot.handlers.create_user") as mock_create, \
         patch("tradecoach.bot.handlers.get_trades") as mock_trades, \
         patch("tradecoach.bot.handlers.get_user_settings") as mock_settings, \
         patch("tradecoach.bot.handlers.insert_trades") as mock_insert, \
         patch("tradecoach.bot.handlers.find_existing_trade_keys") as mock_find_keys, \
         patch("tradecoach.bot.handlers.get_accounts") as mock_get_accounts, \
         patch("tradecoach.bot.handlers.get_account") as mock_get_account, \
         patch("tradecoach.bot.handlers.create_account") as mock_create_account, \
         patch("tradecoach.bot.handlers.delete_user_data") as mock_delete, \
         patch("tradecoach.bot.handlers.delete_account_trades") as mock_delete_acct:

        mock_user = MagicMock()
        mock_user.id = "user-uuid-123"
        mock_get_user.return_value = mock_user
        mock_find_keys.return_value = set()
        mock_get_accounts.return_value = []
        mock_delete.return_value = {"trades": 0, "emotions": 0, "habit_scores": 0, "accounts": 0}
        mock_delete_acct.return_value = 0

        yield {
            "client": mock_client,
            "get_user": mock_get_user,
            "create_user": mock_create,
            "get_trades": mock_trades,
            "get_settings": mock_settings,
            "insert_trades": mock_insert,
            "find_existing_trade_keys": mock_find_keys,
            "get_accounts": mock_get_accounts,
            "get_account": mock_get_account,
            "create_account": mock_create_account,
            "delete_user_data": mock_delete,
            "delete_account_trades": mock_delete_acct,
            "user": mock_user,
        }


# ===================================================================
# /start tests
# ===================================================================


class TestStartCommand:
    @pytest.mark.asyncio
    async def test_start_sends_welcome(self, mock_db):
        update = _make_update(message_text="/start")
        context = _make_context()
        from tradecoach.bot.handlers import start_command
        await start_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "TradeCoach" in text
        assert "trade history" in text.lower()

    @pytest.mark.asyncio
    async def test_start_sends_reply_keyboard(self, mock_db):
        update = _make_update(message_text="/start")
        context = _make_context()
        from tradecoach.bot.handlers import start_command
        await start_command(update, context)
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        all_labels = [btn.text for row in kb.keyboard for btn in row]
        assert BTN_UPLOAD in all_labels
        assert BTN_ACCOUNTS in all_labels
        assert BTN_PREMIUM in all_labels

    @pytest.mark.asyncio
    async def test_start_sets_user_id(self, mock_db):
        update = _make_update(message_text="/start")
        context = _make_context()
        from tradecoach.bot.handlers import start_command
        await start_command(update, context)
        assert context.user_data["user_id"] == "user-uuid-123"

    @pytest.mark.asyncio
    async def test_start_no_check_in_text(self, mock_db):
        update = _make_update(message_text="/start")
        context = _make_context()
        from tradecoach.bot.handlers import start_command
        await start_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "/check" not in text


# ===================================================================
# Reply keyboard button tests
# ===================================================================


class TestUploadButton:
    @pytest.mark.asyncio
    async def test_no_accounts_prompts_create(self, mock_db):
        from tradecoach.bot.handlers import upload_button
        mock_db["get_accounts"].return_value = []
        update = _make_update(message_text=BTN_UPLOAD)
        context = _make_context()
        await upload_button(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "My Accounts" in text

    @pytest.mark.asyncio
    async def test_single_account_shows_list(self, mock_db):
        """Even with 1 account, always show account list (no auto-select)."""
        from tradecoach.bot.handlers import upload_button
        acct = MagicMock(id="a1", name="Exness")
        mock_db["get_accounts"].return_value = [acct]
        update = _make_update(message_text=BTN_UPLOAD)
        context = _make_context()
        await upload_button(update, context)
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctup:a1" in cbs
        assert "acct:new" in cbs

    @pytest.mark.asyncio
    async def test_multiple_accounts_shows_selector(self, mock_db):
        from tradecoach.bot.handlers import upload_button
        a1 = MagicMock(id="a1", name="Exness")
        a2 = MagicMock(id="a2", name="IC Markets")
        mock_db["get_accounts"].return_value = [a1, a2]
        update = _make_update(message_text=BTN_UPLOAD)
        context = _make_context()
        await upload_button(update, context)
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctup:a1" in cbs
        assert "acctup:a2" in cbs


class TestAccountsButton:
    @pytest.mark.asyncio
    async def test_shows_account_list(self, mock_db):
        from tradecoach.bot.handlers import accounts_button
        acct = MagicMock(id="a1", name="Exness")
        mock_db["get_accounts"].return_value = [acct]
        update = _make_update(message_text=BTN_ACCOUNTS)
        context = _make_context()
        await accounts_button(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "accounts" in text.lower()
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acct:a1" in cbs
        assert "acct:new" in cbs

    @pytest.mark.asyncio
    async def test_empty_accounts_shows_create(self, mock_db):
        from tradecoach.bot.handlers import accounts_button
        mock_db["get_accounts"].return_value = []
        update = _make_update(message_text=BTN_ACCOUNTS)
        context = _make_context()
        await accounts_button(update, context)
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acct:new" in cbs


class TestPremiumButton:
    @pytest.mark.asyncio
    async def test_shows_premium_message(self, mock_db):
        from tradecoach.bot.handlers import premium_button
        update = _make_update(message_text=BTN_PREMIUM)
        context = _make_context()
        await premium_button(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Premium" in text
        assert "coming soon" in text.lower()


class TestTermsCommand:
    @pytest.mark.asyncio
    async def test_terms_command(self, mock_db):
        from tradecoach.bot.handlers import terms_command
        update = _make_update(message_text="/terms")
        context = _make_context()
        await terms_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        # Terms match code logic exactly
        assert "5 minutes" in text  # revenge: max_gap_minutes=5
        assert "5 or more" in text  # overtrading: threshold=5
        assert "40%" in text  # martingale: > prev_lot * 1.4
        assert "30 minutes" in text  # averaging down: max_gap_minutes=30
        assert "2 minutes" in text  # quick exits: max_minutes=2
        assert "peak" in text.lower()  # max drawdown from peak
        assert "Profit factor" in text
        assert "Win rate" in text

    @pytest.mark.asyncio
    async def test_terms_callback(self, mock_db):
        from tradecoach.bot.handlers import terms_callback
        update = _make_update(callback_data="terms")
        context = _make_context()
        await terms_callback(update, context)
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Revenge trading" in text


# ===================================================================
# Account actions tests
# ===================================================================


class TestAccountSelectCallback:
    @pytest.mark.asyncio
    async def test_select_existing_account(self, mock_db):
        from tradecoach.bot.handlers import account_select_callback
        from telegram.ext import ConversationHandler
        acct = MagicMock(id="a1", name="Exness")
        mock_db["get_account"].return_value = acct
        update = _make_update(callback_data="acct:a1")
        context = _make_context({"user_id": "user-uuid-123"})
        result = await account_select_callback(update, context)
        assert result == ConversationHandler.END
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Exness" in text
        kb = update.callback_query.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctup:a1" in cbs
        assert "acctrpt:a1" in cbs
        assert "acctclr:a1" in cbs

    @pytest.mark.asyncio
    async def test_select_new_account(self, mock_db):
        from tradecoach.bot.handlers import account_select_callback, ACCT_NAME
        update = _make_update(callback_data="acct:new")
        context = _make_context({"user_id": "user-uuid-123"})
        result = await account_select_callback(update, context)
        assert result == ACCT_NAME
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "name" in text.lower()

    @pytest.mark.asyncio
    async def test_account_not_found(self, mock_db):
        from tradecoach.bot.handlers import account_select_callback
        from telegram.ext import ConversationHandler
        mock_db["get_account"].return_value = None
        update = _make_update(callback_data="acct:nonexistent")
        context = _make_context({"user_id": "user-uuid-123"})
        result = await account_select_callback(update, context)
        assert result == ConversationHandler.END
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "not found" in text.lower()


class TestAccountCreation:
    @pytest.mark.asyncio
    async def test_acct_name_handler(self, mock_db):
        from tradecoach.bot.handlers import acct_name_handler, ACCT_BALANCE
        update = _make_update(message_text="Exness Main")
        context = _make_context({"user_id": "user-uuid-123", "new_acct": {}})
        result = await acct_name_handler(update, context)
        assert result == ACCT_BALANCE
        assert context.user_data["new_acct"]["name"] == "Exness Main"

    @pytest.mark.asyncio
    async def test_acct_name_too_long(self, mock_db):
        from tradecoach.bot.handlers import acct_name_handler, ACCT_NAME
        update = _make_update(message_text="x" * 101)
        context = _make_context({"user_id": "user-uuid-123", "new_acct": {}})
        result = await acct_name_handler(update, context)
        assert result == ACCT_NAME

    @pytest.mark.asyncio
    async def test_acct_balance_handler(self, mock_db):
        from tradecoach.bot.handlers import acct_balance_handler
        from telegram.ext import ConversationHandler
        acct = MagicMock(id="a1")
        mock_db["create_account"].return_value = acct
        update = _make_update(message_text="5000")
        context = _make_context({
            "user_id": "user-uuid-123",
            "new_acct": {"name": "Test"},
        })
        result = await acct_balance_handler(update, context)
        assert result == ConversationHandler.END
        mock_db["create_account"].assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "created" in text.lower()

    @pytest.mark.asyncio
    async def test_acct_balance_skip(self, mock_db):
        from tradecoach.bot.handlers import acct_balance_handler
        from telegram.ext import ConversationHandler
        acct = MagicMock(id="a1")
        mock_db["create_account"].return_value = acct
        update = _make_update(message_text="skip")
        context = _make_context({
            "user_id": "user-uuid-123",
            "new_acct": {"name": "Test"},
        })
        result = await acct_balance_handler(update, context)
        assert result == ConversationHandler.END
        args = mock_db["create_account"].call_args[0][1]
        assert args.starting_balance is None

    @pytest.mark.asyncio
    async def test_acct_balance_invalid(self, mock_db):
        from tradecoach.bot.handlers import acct_balance_handler, ACCT_BALANCE
        update = _make_update(message_text="not a number")
        context = _make_context({
            "user_id": "user-uuid-123",
            "new_acct": {"name": "Test"},
        })
        result = await acct_balance_handler(update, context)
        assert result == ACCT_BALANCE


# ===================================================================
# Clear account tests
# ===================================================================


class TestClearAccount:
    @pytest.mark.asyncio
    async def test_clear_shows_confirmation(self, mock_db):
        from tradecoach.bot.handlers import clear_account_callback
        acct = MagicMock(id="a1", name="Exness")
        mock_db["get_account"].return_value = acct
        update = _make_update(callback_data="acctclr:a1")
        context = _make_context({"user_id": "user-uuid-123"})
        await clear_account_callback(update, context)
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Exness" in text
        assert "Delete" in text or "delete" in text
        kb = update.callback_query.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "clryes:a1" in cbs
        assert "clrno" in cbs

    @pytest.mark.asyncio
    async def test_clear_confirm_deletes(self, mock_db):
        from tradecoach.bot.handlers import clear_confirm_callback
        mock_db["delete_account_trades"].return_value = 5
        update = _make_update(callback_data="clryes:a1")
        context = _make_context({"user_id": "user-uuid-123"})
        await clear_confirm_callback(update, context)
        mock_db["delete_account_trades"].assert_called_once()
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "5 trades deleted" in text

    @pytest.mark.asyncio
    async def test_clear_cancel(self, mock_db):
        from tradecoach.bot.handlers import clear_cancel_callback
        update = _make_update(callback_data="clrno")
        context = _make_context({"user_id": "user-uuid-123"})
        await clear_cancel_callback(update, context)
        mock_db["delete_account_trades"].assert_not_called()
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "cancelled" in text.lower()


# ===================================================================
# Report flow tests (per-account)
# ===================================================================


def _make_trade_mock(symbol, profit_money, direction="buy", opened_at="2024-01-01T10:00:00",
                     closed_at="2024-01-01T11:00:00", lot=0.1, followed_plan=True,
                     moved_stop=False, stop_loss=1.09, open_price=1.095,
                     commission=-2, swap=0, trade_id="t1"):
    """Create a mock trade object with model_dump."""
    data = {
        "id": trade_id, "symbol": symbol, "direction": direction,
        "profit_money": profit_money, "commission": commission, "swap": swap,
        "opened_at": opened_at, "closed_at": closed_at,
        "lot": lot, "followed_plan": followed_plan, "moved_stop": moved_stop,
        "stop_loss": stop_loss, "open_price": open_price,
    }
    m = MagicMock()
    m.model_dump = lambda: dict(data)
    return m


class TestReportFlow:
    @pytest.mark.asyncio
    async def test_report_select_shows_type_chooser(self, mock_db):
        from tradecoach.bot.handlers import report_select_callback
        update = _make_update(callback_data="acctrpt:a1")
        context = _make_context({"user_id": "user-uuid-123"})
        await report_select_callback(update, context)
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "report type" in text.lower() or "Choose" in text
        kb = update.callback_query.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "rptfull:a1" in cbs
        assert "rptperiod:a1" in cbs

    @pytest.mark.asyncio
    async def test_full_report(self, mock_db):
        from tradecoach.bot.handlers import report_type_callback
        from telegram.ext import ConversationHandler

        update = _make_update(callback_data="rptfull:a1")
        context = _make_context({"user_id": "user-uuid-123"})

        trades = [_make_trade_mock("EURUSD", 100, trade_id="t1")]
        mock_db["get_trades"].return_value = trades

        with patch("tradecoach.bot.handlers.generate_full_report",
                   return_value="FULL REPORT"):
            result = await report_type_callback(update, context)
            assert result == ConversationHandler.END

        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "FULL REPORT" in text

    @pytest.mark.asyncio
    async def test_period_report_prompt(self, mock_db):
        from tradecoach.bot.handlers import report_period_select_callback, REPORT_PERIOD

        update = _make_update(callback_data="rptperiod:a1")
        context = _make_context({"user_id": "user-uuid-123"})
        result = await report_period_select_callback(update, context)
        assert result == REPORT_PERIOD
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "DD.MM.YYYY" in text

    @pytest.mark.asyncio
    async def test_period_report_valid_dates(self, mock_db):
        from tradecoach.bot.handlers import report_period
        from telegram.ext import ConversationHandler

        update = _make_update(message_text="01.01.2026 - 01.03.2026")
        context = _make_context({
            "user_id": "user-uuid-123",
            "report_account_id": "a1",
        })

        trades = [_make_trade_mock("EURUSD", 100, trade_id="t1")]
        mock_db["get_trades"].return_value = trades

        with patch("tradecoach.bot.handlers.generate_full_report",
                   return_value="PERIOD REPORT"):
            result = await report_period(update, context)
            assert result == ConversationHandler.END

        text = update.message.reply_text.call_args[0][0]
        assert "PERIOD REPORT" in text

    @pytest.mark.asyncio
    async def test_period_report_invalid_format(self, mock_db):
        from tradecoach.bot.handlers import report_period, REPORT_PERIOD

        update = _make_update(message_text="not a date")
        context = _make_context({
            "user_id": "user-uuid-123",
            "report_account_id": "a1",
        })
        result = await report_period(update, context)
        assert result == REPORT_PERIOD
        text = update.message.reply_text.call_args[0][0]
        assert "Invalid" in text

    @pytest.mark.asyncio
    async def test_period_report_no_trades_in_range(self, mock_db):
        from tradecoach.bot.handlers import report_period
        from telegram.ext import ConversationHandler

        update = _make_update(message_text="01.01.2020 - 01.02.2020")
        context = _make_context({
            "user_id": "user-uuid-123",
            "report_account_id": "a1",
        })
        mock_db["get_trades"].return_value = []

        result = await report_period(update, context)
        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "No trades found" in text

    @pytest.mark.asyncio
    async def test_period_report_swapped_dates(self, mock_db):
        from tradecoach.bot.handlers import report_period
        from telegram.ext import ConversationHandler

        update = _make_update(message_text="01.03.2026 - 01.01.2026")
        context = _make_context({
            "user_id": "user-uuid-123",
            "report_account_id": "a1",
        })

        trades = [_make_trade_mock("EURUSD", 100, trade_id="t1")]
        mock_db["get_trades"].return_value = trades

        with patch("tradecoach.bot.handlers.generate_full_report",
                   return_value="REPORT") as mock_report:
            result = await report_period(update, context)
            assert result == ConversationHandler.END
            mock_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_report_has_post_report_keyboard(self, mock_db):
        from tradecoach.bot.handlers import report_type_callback
        from telegram.ext import ConversationHandler

        update = _make_update(callback_data="rptfull:a1")
        context = _make_context({"user_id": "user-uuid-123"})
        trades = [_make_trade_mock("EURUSD", 100, trade_id="t1")]
        mock_db["get_trades"].return_value = trades

        with patch("tradecoach.bot.handlers.generate_full_report",
                   return_value="REPORT"):
            await report_type_callback(update, context)

        kb = update.callback_query.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "terms" in cbs
        assert "acctup:a1" in cbs
        # No "Show report" after a report
        assert "acctrpt:a1" not in cbs


# ===================================================================
# /stats tests
# ===================================================================


class TestStatsCommand:
    @pytest.mark.asyncio
    async def test_no_accounts_shows_create_prompt(self, mock_db):
        mock_db["get_accounts"].return_value = []
        update = _make_update(message_text="/stats")
        context = _make_context()
        from tradecoach.bot.handlers import stats_command
        await stats_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Create an account" in text

    @pytest.mark.asyncio
    async def test_single_account_shows_list(self, mock_db):
        """Even with 1 account, always show account list."""
        acct = MagicMock(id="a1", name="Exness")
        mock_db["get_accounts"].return_value = [acct]
        update = _make_update(message_text="/stats")
        context = _make_context()
        from tradecoach.bot.handlers import stats_command
        await stats_command(update, context)
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acct:a1" in cbs
        assert "acct:new" in cbs

    @pytest.mark.asyncio
    async def test_multiple_accounts_shows_list(self, mock_db):
        a1 = MagicMock(id="a1", name="Exness")
        a2 = MagicMock(id="a2", name="IC Markets")
        mock_db["get_accounts"].return_value = [a1, a2]
        update = _make_update(message_text="/stats")
        context = _make_context()
        from tradecoach.bot.handlers import stats_command
        await stats_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "account" in text.lower() or "Select" in text
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acct:a1" in cbs
        assert "acct:a2" in cbs


# ===================================================================
# Cancel tests
# ===================================================================


class TestCancel:
    @pytest.mark.asyncio
    async def test_cancel_clears_state(self, mock_db):
        from telegram.ext import ConversationHandler
        from tradecoach.bot.handlers import cancel
        update = _make_update(message_text="/cancel")
        context = _make_context({"check": {}, "csv": {}, "new_acct": {}})
        state = await cancel(update, context)
        assert state == ConversationHandler.END
        assert "check" not in context.user_data
        assert "csv" not in context.user_data
        assert "new_acct" not in context.user_data


# ===================================================================
# Analysis callback tests
# ===================================================================


class TestAnalysisCallback:
    @pytest.mark.asyncio
    async def test_revenge_no_trades(self, mock_db):
        from tradecoach.bot.handlers import analysis_callback
        mock_db["get_trades"].return_value = []
        update = _make_update(callback_data="analysis:revenge")
        context = _make_context({"user_id": "user-uuid-123"})
        await analysis_callback(update, context)
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "No revenge" in text

    @pytest.mark.asyncio
    async def test_times(self, mock_db):
        from tradecoach.bot.handlers import analysis_callback
        trades = [
            MagicMock(model_dump=lambda: {
                "profit_money": 100, "commission": 0, "swap": 0,
                "symbol": "EURUSD",
                "opened_at": "2024-01-01T10:00:00",
                "closed_at": "2024-01-01T11:00:00",
            }),
        ]
        mock_db["get_trades"].return_value = trades
        update = _make_update(callback_data="analysis:times")
        context = _make_context({"user_id": "user-uuid-123"})
        await analysis_callback(update, context)
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Best/Worst Times" in text
        assert "London" in text

    @pytest.mark.asyncio
    async def test_ask_placeholder(self, mock_db):
        from tradecoach.bot.handlers import analysis_callback
        mock_db["get_trades"].return_value = []
        update = _make_update(callback_data="analysis:ask")
        context = _make_context({"user_id": "user-uuid-123"})
        await analysis_callback(update, context)
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "coming soon" in text.lower()


# ===================================================================
# Ensure user tests
# ===================================================================


class TestEnsureUser:
    def test_existing_user(self, mock_db):
        from tradecoach.bot.handlers import _ensure_user_id
        update = _make_update(message_text="hi")
        context = _make_context()
        uid = _ensure_user_id(update, context)
        assert uid == "user-uuid-123"
        mock_db["get_user"].assert_called_once()

    def test_cached_user(self, mock_db):
        from tradecoach.bot.handlers import _ensure_user_id
        update = _make_update(message_text="hi")
        context = _make_context({"user_id": "cached-123"})
        uid = _ensure_user_id(update, context)
        assert uid == "cached-123"
        mock_db["get_user"].assert_not_called()

    def test_new_user_created(self, mock_db):
        from tradecoach.bot.handlers import _ensure_user_id
        mock_db["get_user"].return_value = None
        new_user = MagicMock()
        new_user.id = "new-uuid"
        mock_db["create_user"].return_value = new_user

        update = _make_update(message_text="hi")
        context = _make_context()
        uid = _ensure_user_id(update, context)
        assert uid == "new-uuid"
        mock_db["create_user"].assert_called_once()


# ===================================================================
# Setup handlers tests
# ===================================================================


class TestSetupHandlers:
    def test_setup_registers_handlers(self):
        from telegram.ext import Application as TgApp
        from tradecoach.bot.handlers import setup_handlers
        app = MagicMock(spec=TgApp)
        app.add_handler = MagicMock()
        setup_handlers(app)
        # start, accounts, stats, terms, premium, reset (6 commands)
        # + reset_cb, acct_conv, csv_conv, report_conv,
        #   rptfull_cb, acctrpt_cb, acctclr_cb, clryes_cb, clrno_cb,
        #   acctup_cb, terms_cb, upload_btn, accounts_btn, premium_btn,
        #   csv_standalone, analysis_cb
        assert app.add_handler.call_count == 23

    def test_no_check_handler_registered(self):
        from telegram.ext import Application as TgApp
        from tradecoach.bot.handlers import setup_handlers
        app = MagicMock(spec=TgApp)
        app.add_handler = MagicMock()
        setup_handlers(app)
        for call in app.add_handler.call_args_list:
            handler = call[0][0]
            if hasattr(handler, "entry_points"):
                for ep in handler.entry_points:
                    if hasattr(ep, "commands"):
                        assert "check" not in ep.commands


class TestBuildApplication:
    def test_post_init_set(self):
        from tradecoach.bot.handlers import _post_init, build_application
        with patch("tradecoach.bot.handlers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(telegram_bot_token="test-token")
            with patch("telegram.ext.Application.builder") as mock_builder:
                mock_app = MagicMock()
                mock_builder.return_value.token.return_value.build.return_value = mock_app
                from tradecoach.bot.handlers import build_application
                app = build_application()
                assert app.post_init == _post_init


# ===================================================================
# CSV upload tests
# ===================================================================


def _make_document_update(file_name, file_bytes, user_id=123, username="testuser"):
    """Create a mock Update with a document attachment."""
    update = MagicMock(spec=["effective_user", "message", "callback_query"])
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.callback_query = None

    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()

    doc = MagicMock()
    doc.file_name = file_name
    tg_file = AsyncMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(file_bytes))
    doc.get_file = AsyncMock(return_value=tg_file)
    update.message.document = doc

    return update


SAMPLE_MT4_CSV = (
    "Ticket\tOpen Time\tClose Time\tType\tSize\tItem\tPrice\tS / L\tT / P\t"
    "Close Price\tCommission\tSwap\tProfit\n"
    "12345\t2024.01.15 10:30:00\t2024.01.15 14:00:00\tbuy\t0.10\tEURUSD\t"
    "1.09500\t1.09000\t1.10000\t1.09800\t-2.00\t0.00\t30.00\n"
    "12346\t2024.01.16 09:00:00\t2024.01.16 12:00:00\tsell\t0.20\tGBPUSD\t"
    "1.27000\t1.27500\t1.26500\t1.26700\t-3.00\t-0.50\t60.00\n"
)


class TestCsvGuidedFlow:
    """Tests for the account-based upload flow."""

    @pytest.mark.asyncio
    async def test_csv_start_no_accounts(self, mock_db):
        from tradecoach.bot.handlers import csv_start, CSV_NAME
        mock_db["get_accounts"].return_value = []
        update = _make_update(message_text="/upload")
        context = _make_context({"user_id": "user-uuid-123"})
        result = await csv_start(update, context)
        assert result == CSV_NAME
        text = update.message.reply_text.call_args[0][0]
        assert "name" in text.lower()

    @pytest.mark.asyncio
    async def test_csv_start_with_accounts(self, mock_db):
        from tradecoach.bot.handlers import csv_start, CSV_ACCOUNT
        acct = MagicMock(id="acct-1", name="Exness Main")
        mock_db["get_accounts"].return_value = [acct]
        update = _make_update(message_text="/upload")
        context = _make_context({"user_id": "user-uuid-123"})
        result = await csv_start(update, context)
        assert result == CSV_ACCOUNT
        text = update.message.reply_text.call_args[0][0]
        assert "account" in text.lower() or "select" in text.lower()

    @pytest.mark.asyncio
    async def test_csv_upload_to_account(self, mock_db):
        from tradecoach.bot.handlers import csv_upload_to_account, CSV_FILE
        acct = MagicMock(id="a1", name="Exness")
        mock_db["get_account"].return_value = acct
        update = _make_update(callback_data="acctup:a1")
        context = _make_context({"user_id": "user-uuid-123"})
        result = await csv_upload_to_account(update, context)
        assert result == CSV_FILE
        assert context.user_data["csv"]["account_id"] == "a1"
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Exness" in text

    @pytest.mark.asyncio
    async def test_csv_account_existing(self, mock_db):
        from tradecoach.bot.handlers import csv_account, CSV_FILE
        acct = MagicMock(id="acct-1", name="Exness Main")
        mock_db["get_account"].return_value = acct
        update = _make_update(callback_data="acctup:acct-1")
        context = _make_context({"user_id": "user-uuid-123", "csv": {}})
        result = await csv_account(update, context)
        assert result == CSV_FILE
        assert context.user_data["csv"]["account_id"] == "acct-1"

    @pytest.mark.asyncio
    async def test_csv_account_new(self, mock_db):
        from tradecoach.bot.handlers import csv_account, CSV_NAME
        update = _make_update(callback_data="acctup:new")
        context = _make_context({"user_id": "user-uuid-123", "csv": {}})
        result = await csv_account(update, context)
        assert result == CSV_NAME

    @pytest.mark.asyncio
    async def test_csv_name(self, mock_db):
        from tradecoach.bot.handlers import csv_name, CSV_BALANCE
        update = _make_update(message_text="Exness Main")
        context = _make_context({"user_id": "user-uuid-123", "csv": {}})
        result = await csv_name(update, context)
        assert result == CSV_BALANCE
        assert context.user_data["csv"]["name"] == "Exness Main"

    @pytest.mark.asyncio
    async def test_csv_balance(self, mock_db):
        from tradecoach.bot.handlers import csv_balance, CSV_FILE
        acct = MagicMock(id="acct-new")
        mock_db["create_account"].return_value = acct
        update = _make_update(message_text="5000")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"name": "Test Account"},
        })
        result = await csv_balance(update, context)
        assert result == CSV_FILE
        assert context.user_data["csv"]["account_id"] == "acct-new"
        mock_db["create_account"].assert_called_once()

    @pytest.mark.asyncio
    async def test_csv_balance_skip(self, mock_db):
        from tradecoach.bot.handlers import csv_balance, CSV_FILE
        acct = MagicMock(id="acct-new")
        mock_db["create_account"].return_value = acct
        update = _make_update(message_text="skip")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"name": "Test Account"},
        })
        result = await csv_balance(update, context)
        assert result == CSV_FILE
        args = mock_db["create_account"].call_args[0][1]
        assert args.starting_balance is None

    @pytest.mark.asyncio
    async def test_csv_balance_invalid(self, mock_db):
        from tradecoach.bot.handlers import csv_balance, CSV_BALANCE
        update = _make_update(message_text="not a number")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"name": "Test"},
        })
        result = await csv_balance(update, context)
        assert result == CSV_BALANCE

    @pytest.mark.asyncio
    async def test_csv_file_successful_import(self, mock_db):
        from tradecoach.bot.handlers import csv_file
        from telegram.ext import ConversationHandler

        saved = [MagicMock(id="t1"), MagicMock(id="t2")]
        mock_db["insert_trades"].return_value = saved

        update = _make_document_update("history.csv", SAMPLE_MT4_CSV.encode())
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1", "balance": 5000.0},
        })

        with patch("tradecoach.bot.handlers.parse_mt4_csv") as mock_parse:
            mock_parse.return_value = [
                {
                    "ticket": 12345, "symbol": "EURUSD", "direction": "buy",
                    "lot": 0.1, "profit_money": 30.0,
                    "opened_at": "2024-01-15T10:30:00",
                    "closed_at": "2024-01-15T14:00:00",
                },
                {
                    "ticket": 12346, "symbol": "GBPUSD", "direction": "sell",
                    "lot": 0.2, "profit_money": 60.0,
                    "opened_at": "2024-01-16T09:00:00",
                    "closed_at": "2024-01-16T12:00:00",
                },
            ]
            result = await csv_file(update, context)
            assert result == ConversationHandler.END

        assert update.message.reply_text.call_count == 1
        text = update.message.reply_text.call_args[0][0]
        assert "2 new trades imported" in text
        # Post-upload keyboard with account-specific buttons
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "acctrpt:acct-1" in cbs
        assert "acctup:acct-1" in cbs

    @pytest.mark.asyncio
    async def test_csv_file_non_csv_rejected(self, mock_db):
        from tradecoach.bot.handlers import csv_file, CSV_FILE
        update = _make_document_update("photo.jpg", b"not csv")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1"},
        })
        result = await csv_file(update, context)
        assert result == CSV_FILE

    @pytest.mark.asyncio
    async def test_csv_file_accepts_xlsx(self, mock_db):
        from tradecoach.bot.handlers import csv_file
        from telegram.ext import ConversationHandler

        saved = [MagicMock(id="t1")]
        mock_db["insert_trades"].return_value = saved

        update = _make_document_update("history.xlsx", b"fake")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1"},
        })

        with patch("tradecoach.bot.handlers.parse_xlsx") as mock_parse:
            mock_parse.return_value = [
                {"ticket": 1, "symbol": "EURUSD", "direction": "buy",
                 "lot": 0.1, "profit_money": 30.0},
            ]
            result = await csv_file(update, context)
            assert result == ConversationHandler.END
            mock_parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_csv_file_xlsx_parse_error(self, mock_db):
        from tradecoach.bot.handlers import csv_file
        from telegram.ext import ConversationHandler

        update = _make_document_update("bad.xlsx", b"garbage")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1"},
        })

        with patch("tradecoach.bot.handlers.parse_xlsx") as mock_parse:
            mock_parse.side_effect = XlsxParseError("Cannot open")
            result = await csv_file(update, context)

        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "Could not parse" in text

    @pytest.mark.asyncio
    async def test_csv_file_empty(self, mock_db):
        from tradecoach.bot.handlers import csv_file
        from telegram.ext import ConversationHandler

        update = _make_document_update("empty.csv", b"")
        update.message.document.get_file.return_value.download_as_bytearray = (
            AsyncMock(return_value=bytearray(b""))
        )
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1"},
        })
        result = await csv_file(update, context)
        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "empty" in text.lower()

    @pytest.mark.asyncio
    async def test_csv_file_parse_error(self, mock_db):
        from tradecoach.bot.handlers import csv_file
        from telegram.ext import ConversationHandler

        update = _make_document_update("bad.csv", b"garbage")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1"},
        })

        with patch("tradecoach.bot.handlers.parse_mt4_csv") as mock_parse:
            mock_parse.side_effect = MT4ParseError("No valid columns")
            result = await csv_file(update, context)

        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "Could not parse" in text

    @pytest.mark.asyncio
    async def test_csv_file_deduplication(self, mock_db):
        from tradecoach.bot.handlers import csv_file
        from telegram.ext import ConversationHandler

        mock_db["find_existing_trade_keys"].return_value = {
            ("EURUSD", "2024-01-15T10:30:00", "buy", 0.1),
        }
        mock_db["insert_trades"].return_value = [MagicMock(id="t2")]

        update = _make_document_update("trades.csv", b"data")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1"},
        })

        with patch("tradecoach.bot.handlers.parse_mt4_csv") as mock_parse:
            mock_parse.return_value = [
                {"ticket": 12345, "symbol": "EURUSD", "direction": "buy",
                 "lot": 0.1, "profit_money": 30.0,
                 "opened_at": "2024-01-15T10:30:00",
                 "closed_at": "2024-01-15T14:00:00"},
                {"ticket": 12346, "symbol": "GBPUSD", "direction": "sell",
                 "lot": 0.2, "profit_money": 60.0,
                 "opened_at": "2024-01-16T09:00:00",
                 "closed_at": "2024-01-16T12:00:00"},
            ]
            result = await csv_file(update, context)
            assert result == ConversationHandler.END

        trades_arg = mock_db["insert_trades"].call_args[0][1]
        assert len(trades_arg) == 1
        assert trades_arg[0].symbol == "GBPUSD"

        text = update.message.reply_text.call_args[0][0]
        assert "1 new trades imported" in text
        assert "1 duplicates skipped" in text

    @pytest.mark.asyncio
    async def test_csv_file_all_duplicates(self, mock_db):
        from tradecoach.bot.handlers import csv_file
        from telegram.ext import ConversationHandler

        mock_db["find_existing_trade_keys"].return_value = {
            ("EURUSD", "2024-01-15T10:30:00", "buy", 0.1),
        }

        update = _make_document_update("trades.csv", b"data")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1"},
        })

        with patch("tradecoach.bot.handlers.parse_mt4_csv") as mock_parse:
            mock_parse.return_value = [
                {"ticket": 12345, "symbol": "EURUSD", "direction": "buy",
                 "lot": 0.1, "profit_money": 30.0,
                 "opened_at": "2024-01-15T10:30:00",
                 "closed_at": "2024-01-15T14:00:00"},
            ]
            result = await csv_file(update, context)
            assert result == ConversationHandler.END

        mock_db["insert_trades"].assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "already exist" in text

    @pytest.mark.asyncio
    async def test_csv_file_db_error(self, mock_db):
        from tradecoach.bot.handlers import csv_file
        from telegram.ext import ConversationHandler

        mock_db["insert_trades"].side_effect = Exception("connection lost")
        update = _make_document_update("trades.csv", b"data")
        context = _make_context({
            "user_id": "user-uuid-123",
            "csv": {"account_id": "acct-1"},
        })

        with patch("tradecoach.bot.handlers.parse_mt4_csv") as mock_parse:
            mock_parse.return_value = [
                {"ticket": 1, "symbol": "EURUSD", "direction": "buy",
                 "lot": 0.1, "profit_money": 10.0},
            ]
            result = await csv_file(update, context)

        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "Database error" in text


class TestCsvStandaloneUpload:
    """Test that standalone uploads redirect or process."""

    @pytest.mark.asyncio
    async def test_standalone_csv_redirects_no_account(self, mock_db):
        from tradecoach.bot.handlers import handle_csv_upload
        update = _make_document_update("trades.csv", b"data")
        context = _make_context({"user_id": "user-uuid-123"})
        await handle_csv_upload(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Upload trades" in text

    @pytest.mark.asyncio
    async def test_standalone_with_account_processes(self, mock_db):
        """If upload_account_id is set from reply keyboard flow, file is processed."""
        from tradecoach.bot.handlers import handle_csv_upload

        saved = [MagicMock(id="t1")]
        mock_db["insert_trades"].return_value = saved

        update = _make_document_update("trades.csv", b"data")
        context = _make_context({
            "user_id": "user-uuid-123",
            "upload_account_id": "a1",
        })

        with patch("tradecoach.bot.handlers.parse_mt4_csv") as mock_parse:
            mock_parse.return_value = [
                {"ticket": 1, "symbol": "EURUSD", "direction": "buy",
                 "lot": 0.1, "profit_money": 10.0},
            ]
            await handle_csv_upload(update, context)

        text = update.message.reply_text.call_args[0][0]
        assert "1 new trades imported" in text

    @pytest.mark.asyncio
    async def test_standalone_ignores_non_csv(self, mock_db):
        from tradecoach.bot.handlers import handle_csv_upload
        update = _make_document_update("photo.jpg", b"not csv")
        context = _make_context()
        await handle_csv_upload(update, context)
        update.message.reply_text.assert_not_called()


# ===================================================================
# Reset data tests
# ===================================================================


class TestResetCommand:
    @pytest.mark.asyncio
    async def test_reset_shows_confirmation(self, mock_db):
        from tradecoach.bot.handlers import reset_command
        update = _make_update(message_text="/reset")
        context = _make_context()
        await reset_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Are you sure" in text
        assert "delete ALL" in text
        assert "cannot be undone" in text
        kb = update.message.reply_text.call_args[1]["reply_markup"]
        cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "reset:confirm" in cbs
        assert "reset:cancel" in cbs

    @pytest.mark.asyncio
    async def test_reset_confirm_deletes_data(self, mock_db):
        from tradecoach.bot.handlers import reset_callback
        update = _make_update(callback_data="reset:confirm")
        context = _make_context({"user_id": "user-uuid-123"})
        await reset_callback(update, context)
        mock_db["delete_user_data"].assert_called_once_with(
            mock_db["client"].return_value, "user-uuid-123",
        )
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "All data cleared" in text
        assert "start fresh" in text

    @pytest.mark.asyncio
    async def test_reset_confirm_shows_reply_keyboard(self, mock_db):
        from tradecoach.bot.handlers import reset_callback
        update = _make_update(callback_data="reset:confirm")
        context = _make_context({"user_id": "user-uuid-123"})
        await reset_callback(update, context)
        kb = update.callback_query.message.reply_text.call_args[1]["reply_markup"]
        all_labels = [btn.text for row in kb.keyboard for btn in row]
        assert BTN_UPLOAD in all_labels

    @pytest.mark.asyncio
    async def test_reset_cancel(self, mock_db):
        from tradecoach.bot.handlers import reset_callback
        update = _make_update(callback_data="reset:cancel")
        context = _make_context({"user_id": "user-uuid-123"})
        await reset_callback(update, context)
        mock_db["delete_user_data"].assert_not_called()
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "cancelled" in text.lower()


# ===================================================================
# AI Coaching handler tests
# ===================================================================


class TestAiCoachingCallback:
    @pytest.mark.asyncio
    async def test_coaching_success(self, mock_db):
        from tradecoach.bot.handlers import ai_coaching_callback
        from tradecoach.services.llm import LLMUsage

        update = _make_update(callback_data="aicoach:acct-123")
        context = _make_context({"user_id": "user-uuid-123"})

        acct = MagicMock()
        acct.name = "Exness Main"
        acct.starting_balance = 10000.0
        mock_db["get_account"].return_value = acct

        trades = [MagicMock()]
        trades[0].model_dump.return_value = {
            "symbol": "EURUSD", "pnl": 100, "direction": "buy",
            "lot": 0.1, "opened_at": "2025-01-10T10:00:00",
            "closed_at": "2025-01-10T11:00:00",
        }
        mock_db["get_trades"].return_value = trades

        mock_usage = LLMUsage(
            model="claude-sonnet-4-20250514",
            input_tokens=500, output_tokens=300,
            cost_usd=0.006, latency_ms=2000,
        )

        with patch("tradecoach.bot.handlers.generate_ai_coaching", new_callable=AsyncMock) as mock_coaching:
            mock_coaching.return_value = ("AI coaching text here", mock_usage)
            await ai_coaching_callback(update, context)

        # Should have sent "Generating..." + coaching text
        calls = update.callback_query.message.reply_text.call_args_list
        assert len(calls) >= 2
        assert "Generating" in calls[0][0][0]
        assert "AI coaching text" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_coaching_no_trades(self, mock_db):
        from tradecoach.bot.handlers import ai_coaching_callback

        update = _make_update(callback_data="aicoach:acct-123")
        context = _make_context({"user_id": "user-uuid-123"})

        mock_db["get_trades"].return_value = []
        mock_db["get_account"].return_value = MagicMock(starting_balance=None)

        await ai_coaching_callback(update, context)

        calls = update.callback_query.message.reply_text.call_args_list
        texts = [c[0][0] for c in calls]
        assert any("No trades" in t for t in texts)

    @pytest.mark.asyncio
    async def test_coaching_llm_error(self, mock_db):
        from tradecoach.bot.handlers import ai_coaching_callback
        from tradecoach.services.llm import LLMError

        update = _make_update(callback_data="aicoach:acct-123")
        context = _make_context({"user_id": "user-uuid-123"})

        acct = MagicMock()
        acct.name = "Test"
        acct.starting_balance = 5000.0
        mock_db["get_account"].return_value = acct

        trades = [MagicMock()]
        trades[0].model_dump.return_value = {
            "symbol": "EURUSD", "pnl": -50, "direction": "sell",
            "lot": 0.1, "opened_at": "2025-01-10T10:00:00",
            "closed_at": "2025-01-10T11:00:00",
        }
        mock_db["get_trades"].return_value = trades

        with patch("tradecoach.bot.handlers.generate_ai_coaching", new_callable=AsyncMock) as mock_coaching:
            mock_coaching.side_effect = LLMError("Anthropic API key not configured")
            await ai_coaching_callback(update, context)

        calls = update.callback_query.message.reply_text.call_args_list
        texts = [c[0][0] for c in calls]
        assert any("Could not generate" in t for t in texts)
        assert any("API key" in t for t in texts)
