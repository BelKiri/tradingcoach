"""
Tests for AI coaching service — full RAG integration.

Tests verify:
  - build_full_coaching_prompt: all sections present
  - build_full_coaching_prompt with previous session: comparison section
  - get_ai_coaching: mock LLM → session saved
  - API endpoint: mock request → response format
  - Legacy generate_ai_coaching: backward compatibility
  - Parsers: rules block, main_problem, verdict
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tradecoach.services.coaching import (
    _build_behavioral_section,
    _build_calendar_section,
    _build_context,
    _build_metrics_snapshot,
    _build_repeat_prompt,
    _build_statistics_section,
    _build_trade_log,
    _parse_main_problem,
    _parse_rules,
    _parse_verdict,
    _strip_rules_block,
    build_full_coaching_prompt,
    generate_ai_coaching,
    get_ai_coaching,
)
from tradecoach.services.llm import LLMError, LLMUsage


# ===================================================================
# Test data
# ===================================================================


def _make_trades(count: int = 10, *, winners: int = 6) -> list[dict]:
    """Generate test trades with realistic timestamps."""
    trades = []
    for i in range(count):
        is_win = i < winners
        pnl = 100.0 if is_win else -80.0
        trades.append({
            "symbol": "EURUSD" if i % 2 == 0 else "GBPUSD",
            "direction": "buy",
            "lot": 0.1,
            "open_price": 1.1000,
            "close_price": 1.1010 if is_win else 1.0990,
            "profit_money": pnl,
            "commission": -1.0,
            "swap": 0.0,
            "stop_loss": 1.0950,
            "take_profit": 1.1050,
            "opened_at": f"2025-01-{10 + i:02d}T10:00:00",
            "closed_at": f"2025-01-{10 + i:02d}T11:00:00",
        })
    return trades


def _make_revenge_trades() -> list[dict]:
    """Generate trades that trigger revenge detection."""
    return [
        {
            "symbol": "XAUUSD", "direction": "buy", "lot": 0.10,
            "open_price": 2000.0, "close_price": 1990.0,
            "profit_money": -100.0, "commission": -1.0, "swap": 0.0,
            "stop_loss": 1985.0,
            "opened_at": "2025-01-15T10:00:00",
            "closed_at": "2025-01-15T10:30:00",
        },
        {
            "symbol": "XAUUSD", "direction": "buy", "lot": 0.30,
            "open_price": 1992.0, "close_price": 1988.0,
            "profit_money": -120.0, "commission": -1.0, "swap": 0.0,
            "stop_loss": 1985.0,
            "opened_at": "2025-01-15T10:32:00",
            "closed_at": "2025-01-15T10:45:00",
        },
    ]


def _make_no_sl_trades() -> list[dict]:
    """Trades without stop loss."""
    return [
        {
            "symbol": "EURUSD", "direction": "buy", "lot": 0.1,
            "open_price": 1.1000, "close_price": 1.0950,
            "profit_money": -50.0, "commission": -1.0, "swap": 0.0,
            "stop_loss": None,
            "opened_at": "2025-01-20T14:00:00",
            "closed_at": "2025-01-20T15:00:00",
        },
    ]


def _mock_llm_usage() -> LLMUsage:
    return LLMUsage(
        model="claude-sonnet-4-20250514",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.0105,
        latency_ms=3000,
    )


_MOCK_RULES_JSON = """\
[
  {"action": "Maximum 3 trades per calm day", "rationale": "You took 59 trades on normal days with 32% WR, losing $2,338.", "savings_estimate_usd": 400},
  {"action": "No trading within 30 minutes of a loss", "rationale": "Revenge trades after losses cost $300/month in your log.", "savings_estimate_usd": 300},
  {"action": "Only trade XAUUSD and EURUSD", "rationale": "GBPUSD trades lost $200 over this period with no edge.", "savings_estimate_usd": 200}
]"""

_MOCK_AI_RESPONSE = """\
Your biggest problem is overtrading on calm days. You took 59 trades on normal days \
with 32% WR, losing $2,338. Meanwhile your 22 volatile-day trades had 36% WR and made $1,375.

**HIDDEN PATTERN**: Your revenge trades cluster on Wednesday afternoons in London session.

**STRENGTH**: You respect stop losses on 85% of trades, saving an estimated $800.

**PROJECTED SAVINGS**: Following all 3 rules saves approximately $900/month.

<rules>
""" + _MOCK_RULES_JSON + """
</rules>"""


_MOCK_REPEAT_RESPONSE = """\
👍 Progress on two out of three rules.

**RULE CHECK**:
1. Max 3 trades/day: YES — average dropped from 5 to 2.8. Saved ~$350.
2. No trading after loss: NO — 4 revenge trades found. Cost $180.
3. XAUUSD/EURUSD only: YES — no GBPUSD trades. Saved ~$200.

**NEW INSIGHT**: Your Wednesday performance improved 40% since reducing trade count.

**PROGRESS SCORE**: 7/10 — good improvement on volume, need work on emotional control.

<rules>
[
  {"action": "Keep max 3 trades per day", "rationale": "Average dropped from 5 to 2.8; saved ~$350.", "savings_estimate_usd": 350},
  {"action": "Close terminal for 1 hour after any loss", "rationale": "4 revenge trades cost $180 this period.", "savings_estimate_usd": 300},
  {"action": "Only trade London session", "rationale": "Asian session trades lost $150 vs London.", "savings_estimate_usd": 150}
]
</rules>"""


# ===================================================================
# Statistics section
# ===================================================================


class TestBuildStatisticsSection:
    def test_includes_overview(self):
        trades = _make_trades(10, winners=6)
        section = _build_statistics_section(trades, 10000.0)
        assert "TRADE STATISTICS" in section
        assert "Trades: 10" in section
        assert "Win rate:" in section
        assert "P&L:" in section
        assert "Account balance: $10,000.00" in section

    def test_includes_best_worst_pairs(self):
        trades = _make_trades(10, winners=6)
        section = _build_statistics_section(trades, None)
        assert "Best pair:" in section
        assert "Worst pair:" in section

    def test_includes_sessions(self):
        trades = _make_trades(10, winners=6)
        section = _build_statistics_section(trades, None)
        assert "session:" in section.lower()

    def test_includes_days(self):
        trades = _make_trades(10, winners=6)
        section = _build_statistics_section(trades, None)
        assert "day:" in section.lower()

    def test_includes_streaks(self):
        trades = _make_trades(10, winners=6)
        section = _build_statistics_section(trades, None)
        assert "Streaks:" in section


# ===================================================================
# Behavioral section
# ===================================================================


class TestBuildBehavioralSection:
    def test_includes_all_categories(self):
        trades = _make_trades(10, winners=6)
        section = _build_behavioral_section(trades)
        assert "BEHAVIORAL PATTERNS" in section
        assert "Revenge" in section
        assert "Martingale" in section
        assert "Overtrading" in section
        assert "Averaging down" in section
        assert "Quick exits" in section
        assert "SL usage" in section

    def test_revenge_detected(self):
        trades = _make_revenge_trades()
        section = _build_behavioral_section(trades)
        assert "Revenge trading:" in section
        assert "none detected" not in section.split("Revenge")[1].split("\n")[0]

    def test_sl_cost(self):
        trades = _make_no_sl_trades()
        section = _build_behavioral_section(trades)
        assert "without" in section
        assert "Cost" in section


# ===================================================================
# Calendar section
# ===================================================================


class TestBuildCalendarSection:
    def test_with_events(self):
        trades = _make_trades(10, winners=6)
        with patch("tradecoach.services.coaching.load_calendar") as mock_cal:
            mock_cal.return_value = [
                {"date": "2025-01-13", "time_utc": "13:30",
                 "currency": "USD", "event_name": "CPI", "impact": "high"},
            ]
            section, _ = _build_calendar_section(trades)
        assert "ECONOMIC CALENDAR" in section

    def test_no_events(self):
        trades = _make_trades(10, winners=6)
        with patch("tradecoach.services.coaching.load_calendar") as mock_cal:
            mock_cal.return_value = []
            section, matches = _build_calendar_section(trades)
        assert "No high-impact events" in section
        assert matches == []

    def test_empty_trades(self):
        section, matches = _build_calendar_section([])
        assert section == ""
        assert matches == []


# ===================================================================
# Full coaching prompt
# ===================================================================


class TestBuildFullCoachingPrompt:
    def test_first_analysis_has_all_sections(self):
        trades = _make_trades(10, winners=6)
        account = {"broker_timezone": "UTC+2", "starting_balance": 10000.0, "name": "Test"}

        with patch("tradecoach.services.coaching.load_calendar", return_value=[]):
            with patch("tradecoach.services.coaching.build_volatility_context_for_coaching", return_value=""):
                prompt, context = build_full_coaching_prompt(trades, account)

        assert "TRADE STATISTICS" in context
        assert "BEHAVIORAL PATTERNS" in context
        assert "ECONOMIC CALENDAR" in context
        assert "VOLATILITY ANALYSIS" in context
        assert "TRADE LOG" in context

        # Prompt should be first analysis
        assert "MAIN PROBLEM" in prompt
        assert "HIDDEN PATTERN" in prompt
        assert "<rules>" in prompt
        assert "PROJECTED SAVINGS" in prompt
        assert "ACTION PLAN" not in prompt
        assert "Test" in prompt  # account name

    def test_repeat_analysis_has_comparison(self):
        trades = _make_trades(10, winners=6)
        account = {"broker_timezone": "UTC+2", "starting_balance": 10000.0}
        prev = {
            "created_at": "2025-01-01T00:00:00",
            "main_problem": "Overtrading on calm days",
            "recommendations": ["Max 3 trades", "No revenge", "Skip GBPUSD"],
            "metrics_snapshot": {"win_rate": 55.0, "total_pnl": -500.0},
        }

        with patch("tradecoach.services.coaching.load_calendar", return_value=[]):
            with patch("tradecoach.services.coaching.build_volatility_context_for_coaching", return_value=""):
                prompt, context = build_full_coaching_prompt(trades, account, prev)

        assert "PREVIOUS SESSION" in prompt
        assert "Overtrading on calm days" in prompt
        assert "Max 3 trades" in prompt
        assert "VERDICT" in prompt
        assert "RULE CHECK" in prompt
        assert "PROGRESS SCORE" in prompt

    def test_build_repeat_prompt_handles_json_string_metrics(self):
        metrics_json = (
            '{"trades_count": 81, "win_rate": 33.33, "total_pnl": -963.8, '
            '"profit_factor": 0.88, "revenge_count": 21, "revenge_cost": 3259.73, '
            '"martingale_count": 5, "quick_exits_count": 9}'
        )
        recommendations_json = (
            '["Max 3 trades per day", "No revenge trades", "Skip EURUSD"]'
        )
        prev = {
            "created_at": "2026-04-26T04:28:27+00:00",
            "main_problem": "Overtrading on calm days",
            "recommendations": recommendations_json,
            "metrics_snapshot": metrics_json,
        }

        prompt = _build_repeat_prompt(prev)

        assert isinstance(prompt, str)
        assert "PREVIOUS SESSION" in prompt
        assert "win_rate: 33.33" in prompt
        assert "Max 3 trades per day" in prompt

    def test_no_trades_raises(self):
        with pytest.raises(LLMError, match="No trades"):
            build_full_coaching_prompt([], None)

# ===================================================================
# Trade log
# ===================================================================


class TestBuildTradeLog:
    def test_renders_all_trades(self):
        trades = _make_trades(60, winners=30)
        log = _build_trade_log(trades)
        assert "TRADE LOG (60 trades)" in log
        assert "last 50 of" not in log
        assert log.count("| EURUSD") + log.count("| GBPUSD") == 60

    def test_tags_revenge(self):
        trades = _make_revenge_trades()
        log = _build_trade_log(trades)
        assert "REVENGE" in log

    def test_near_event_tag_single(self):
        trades = [
            {
                "symbol": "EURUSD", "direction": "buy", "lot": 0.1,
                "profit_money": 50.0, "commission": 0.0, "swap": 0.0,
                "stop_loss": 1.0950,
                "opened_at": "2025-01-10T13:25:00",
                "closed_at": "2025-01-10T14:00:00",
            },
        ]
        event_matches = [
            {
                "trade": trades[0],
                "matched_events": [
                    {
                        "event": {
                            "date": "2025-01-10",
                            "time_utc": "13:30",
                            "event_name": "CPI",
                            "impact": "high",
                        },
                        "minutes_offset": -5,
                    },
                ],
            },
        ]
        log = _build_trade_log(trades, event_matches)
        assert "[NEAR-CPI]" in log

    def test_near_event_tags_chronological_order(self):
        trades = [
            {
                "symbol": "EURUSD", "direction": "buy", "lot": 0.1,
                "profit_money": 0.0, "commission": 0.0, "swap": 0.0,
                "stop_loss": 1.0950,
                "opened_at": "2025-01-10T13:45:00",
                "closed_at": "2025-01-10T14:00:00",
            },
        ]
        event_matches = [
            {
                "trade": trades[0],
                "matched_events": [
                    {
                        "event": {
                            "date": "2025-01-10",
                            "time_utc": "14:00",
                            "event_name": "CPI",
                            "impact": "high",
                        },
                        "minutes_offset": -15,
                    },
                    {
                        "event": {
                            "date": "2025-01-10",
                            "time_utc": "13:30",
                            "event_name": "Non-Farm Payrolls",
                            "impact": "high",
                        },
                        "minutes_offset": 15,
                    },
                ],
            },
        ]
        log = _build_trade_log(trades, event_matches)
        assert "[NEAR-Non-Farm Payrolls,NEAR-CPI]" in log

    def test_no_near_tag_without_match(self):
        trades = _make_trades(3, winners=2)
        log = _build_trade_log(trades, [])
        assert "NEAR-" not in log
        assert "]" not in log.split("TRADE LOG")[1].split("\n")[1]


# ===================================================================
# Metrics snapshot
# ===================================================================


class TestMetricsSnapshot:
    def test_has_all_fields(self):
        trades = _make_trades(10, winners=6)
        snap = _build_metrics_snapshot(trades)
        assert "trades_count" in snap
        assert "win_rate" in snap
        assert "total_pnl" in snap
        assert "profit_factor" in snap
        assert "revenge_count" in snap
        assert "revenge_cost" in snap
        assert snap["trades_count"] == 10


# ===================================================================
# Parsers
# ===================================================================


class TestParsers:
    def test_parse_rules_valid(self):
        rules = _parse_rules(_MOCK_AI_RESPONSE)
        assert rules is not None
        assert len(rules) == 3
        assert rules[0]["action"] == "Maximum 3 trades per calm day"
        assert rules[0]["savings_estimate_usd"] == 400

    def test_parse_rules_missing_block(self):
        assert _parse_rules("No rules here.") is None

    def test_parse_rules_invalid_json(self):
        text = "Analysis.\n<rules>not json</rules>"
        assert _parse_rules(text) is None

    def test_parse_rules_wrong_count(self):
        text = 'Analysis.\n<rules>[{"action":"a","rationale":"b","savings_estimate_usd":1}]</rules>'
        assert _parse_rules(text) is None

    def test_parse_rules_with_markdown_fence(self):
        text = (
            "Analysis.\n<rules>\n```json\n"
            + _MOCK_RULES_JSON
            + "\n```\n</rules>"
        )
        rules = _parse_rules(text)
        assert rules is not None
        assert len(rules) == 3

    def test_strip_rules_block(self):
        stripped = _strip_rules_block(_MOCK_AI_RESPONSE)
        assert "<rules>" not in stripped
        assert "PROJECTED SAVINGS" in stripped

    def test_parse_main_problem(self):
        problem = _parse_main_problem(_strip_rules_block(_MOCK_AI_RESPONSE))
        assert problem is not None
        assert "overtrading" in problem.lower()

    def test_parse_verdict_progress(self):
        assert _parse_verdict("👍 Good progress!") == "progress"

    def test_parse_verdict_setback(self):
        assert _parse_verdict("👎 Setback this week.") == "setback"

    def test_parse_verdict_no_change(self):
        assert _parse_verdict("➡️ No significant change.") == "no_change"

    def test_parse_verdict_none(self):
        assert _parse_verdict("Some other text") is None


# ===================================================================
# get_ai_coaching (mocked DB + LLM)
# ===================================================================


class TestGetAiCoaching:
    @pytest.mark.asyncio
    async def test_first_session(self):
        trades = _make_trades(10, winners=6)
        trade_models = [MagicMock(model_dump=MagicMock(return_value=t)) for t in trades]
        account_model = MagicMock()
        account_model.model_dump.return_value = {
            "broker_timezone": "UTC+2",
            "starting_balance": 10000.0,
            "name": "Test Account",
        }

        mock_client = MagicMock()
        # get_account
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            account_model.model_dump()
        ]

        with patch("tradecoach.services.coaching.get_ai_coaching.__module__"):
            pass

        with (
            patch("tradecoach.services.coaching.deep_analysis", new_callable=AsyncMock) as mock_llm,
            patch("tradecoach.db.queries.get_client", return_value=mock_client),
            patch("tradecoach.db.queries.get_account", return_value=account_model),
            patch("tradecoach.db.queries.get_trades", return_value=trade_models),
            patch("tradecoach.services.coaching._get_latest_coaching_session", return_value=None),
            patch("tradecoach.services.coaching._save_coaching_session", return_value="session-123") as mock_save,
            patch("tradecoach.services.beta_quota.assert_can_generate_coaching"),
            patch("tradecoach.services.beta_quota.increment_coaching_sessions_used", return_value=True),
            patch("tradecoach.services.coaching.load_calendar", return_value=[]),
            patch("tradecoach.services.coaching.build_volatility_context_for_coaching", return_value=""),
        ):
            mock_llm.return_value = (_MOCK_AI_RESPONSE, _mock_llm_usage())

            result = await get_ai_coaching("user-1", "account-1")

        assert result["session_id"] == "session-123"
        assert "<rules>" not in result["ai_response"]
        assert result["rules"] is not None
        assert len(result["rules"]) == 3
        assert "metrics_snapshot" in result
        assert result["verdict"] is None  # first session
        assert result["usage"]["model"] == "claude-sonnet-4-20250514"
        save_kwargs = mock_save.call_args.kwargs
        assert save_kwargs["recommendations"] is None
        assert save_kwargs["rules"] is not None
        assert save_kwargs["input_tokens"] == 1000
        assert save_kwargs["output_tokens"] == 500
        assert save_kwargs["cost_usd"] == 0.0105

    @pytest.mark.asyncio
    async def test_repeat_session(self):
        trades = _make_trades(10, winners=6)
        trade_models = [MagicMock(model_dump=MagicMock(return_value=t)) for t in trades]
        account_model = MagicMock()
        account_model.model_dump.return_value = {
            "broker_timezone": "UTC+2",
            "starting_balance": 10000.0,
            "name": "Test",
        }

        prev_session = {
            "created_at": "2025-01-01T00:00:00",
            "main_problem": "Overtrading",
            "recommendations": ["Max 3 trades", "No revenge", "Skip GBPUSD"],
            "metrics_snapshot": {"win_rate": 55.0, "total_pnl": -500.0},
        }

        with (
            patch("tradecoach.services.coaching.deep_analysis", new_callable=AsyncMock) as mock_llm,
            patch("tradecoach.db.queries.get_client"),
            patch("tradecoach.db.queries.get_account", return_value=account_model),
            patch("tradecoach.db.queries.get_trades", return_value=trade_models),
            patch("tradecoach.services.coaching._get_latest_coaching_session", return_value=prev_session),
            patch("tradecoach.services.coaching._save_coaching_session", return_value="session-456"),
            patch("tradecoach.services.beta_quota.assert_can_generate_coaching"),
            patch("tradecoach.services.beta_quota.increment_coaching_sessions_used", return_value=True),
            patch("tradecoach.services.coaching.load_calendar", return_value=[]),
            patch("tradecoach.services.coaching.build_volatility_context_for_coaching", return_value=""),
        ):
            mock_llm.return_value = (_MOCK_REPEAT_RESPONSE, _mock_llm_usage())

            result = await get_ai_coaching("user-1", "account-1")

        assert result["session_id"] == "session-456"
        assert result["verdict"] == "progress"

    @pytest.mark.asyncio
    async def test_no_trades_raises(self):
        account_model = MagicMock()
        account_model.model_dump.return_value = {"broker_timezone": "UTC+2"}

        with (
            patch("tradecoach.db.queries.get_client"),
            patch("tradecoach.db.queries.get_account", return_value=account_model),
            patch("tradecoach.db.queries.get_trades", return_value=[]),
        ):
            with pytest.raises(LLMError, match="No trades"):
                await get_ai_coaching("user-1", "account-1")

    @pytest.mark.asyncio
    async def test_account_not_found_raises(self):
        with (
            patch("tradecoach.db.queries.get_client"),
            patch("tradecoach.db.queries.get_account", return_value=None),
        ):
            with pytest.raises(LLMError, match="not found"):
                await get_ai_coaching("user-1", "bad-account")


# ===================================================================
# API endpoint
# ===================================================================


class TestCoachingAPI:
    @pytest.mark.asyncio
    async def test_endpoint_returns_response(self):
        from httpx import ASGITransport, AsyncClient

        from tradecoach.main import app

        mock_result = {
            "session_id": "sess-1",
            "ai_response": "Your trading...",
            "metrics_snapshot": {"trades_count": 10, "win_rate": 60.0},
            "verdict": None,
            "rules": None,
            "created_at": "2025-01-20T12:00:00",
            "usage": {
                "model": "claude-sonnet-4-20250514",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cost_usd": 0.0105,
            },
        }

        with patch("tradecoach.api.coaching.get_ai_coaching", new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = mock_result

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/api/coaching/test-user-1",
                    json={"account_id": "acc-1"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-1"
        assert data["ai_response"] == "Your trading..."
        assert data["metrics_snapshot"]["trades_count"] == 10

    @pytest.mark.asyncio
    async def test_endpoint_with_period(self):
        from httpx import ASGITransport, AsyncClient

        from tradecoach.main import app

        mock_result = {
            "session_id": "sess-2",
            "ai_response": "Analysis...",
            "metrics_snapshot": {},
            "verdict": "progress",
            "rules": None,
            "created_at": "2025-01-20T12:00:00",
            "usage": {"model": "test", "input_tokens": 0, "output_tokens": 0, "cost_usd": 0},
        }

        with patch("tradecoach.api.coaching.get_ai_coaching", new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = mock_result

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/api/coaching/test-user-1",
                    json={
                        "account_id": "acc-1",
                        "period": {"date_from": "2025-01-01", "date_to": "2025-01-31"},
                    },
                )

        assert resp.status_code == 200
        # Verify period was passed through
        call_kwargs = mock_coach.call_args.kwargs
        assert call_kwargs["period_from"] == "2025-01-01"
        assert call_kwargs["period_to"] == "2025-01-31"

    @pytest.mark.asyncio
    async def test_endpoint_error(self):
        from httpx import ASGITransport, AsyncClient

        from tradecoach.main import app

        with patch("tradecoach.api.coaching.get_ai_coaching", new_callable=AsyncMock) as mock_coach:
            mock_coach.side_effect = LLMError("No trades found")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/api/coaching/test-user-1",
                    json={"account_id": "acc-1"},
                )

        assert resp.status_code == 400
        assert "Unable to generate coaching" in resp.json()["error"]


# ===================================================================
# Legacy compatibility
# ===================================================================


class TestLegacyCoaching:
    def test_legacy_context_empty(self):
        ctx = _build_context([], None)
        assert "No trades" in ctx

    def test_legacy_context_includes_log(self):
        trades = _make_trades(10, winners=6)
        ctx = _build_context(trades, None)
        assert "TRADE LOG" in ctx
        assert "EURUSD" in ctx

    def test_legacy_context_with_balance(self):
        trades = _make_trades(10, winners=6)
        ctx = _build_context(trades, 10000.0)
        assert "Balance: $10,000.00" in ctx

    def test_legacy_context_revenge_tags(self):
        trades = _make_revenge_trades()
        ctx = _build_context(trades, None)
        assert "REVENGE" in ctx

    def test_legacy_context_limits_50(self):
        trades = _make_trades(60, winners=30)
        ctx = _build_context(trades, None)
        assert "last 50 of 60" in ctx

    @pytest.mark.asyncio
    async def test_legacy_generates_coaching(self):
        trades = _make_trades(10, winners=6)

        with patch("tradecoach.services.coaching.deep_analysis", new_callable=AsyncMock) as mock_deep:
            mock_deep.return_value = ("Your trading shows...", _mock_llm_usage())
            text, usage = await generate_ai_coaching(trades, account_balance=10000.0)

        assert "AI COACHING" in text
        assert "Your trading shows..." in text
        assert usage.model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_legacy_with_account_name(self):
        trades = _make_trades(5)

        with patch("tradecoach.services.coaching.deep_analysis", new_callable=AsyncMock) as mock_deep:
            mock_deep.return_value = ("Analysis text", _mock_llm_usage())
            text, _ = await generate_ai_coaching(trades, account_name="Exness Main")

        assert "Exness Main" in text

    @pytest.mark.asyncio
    async def test_legacy_empty_raises(self):
        with pytest.raises(LLMError, match="No trades"):
            await generate_ai_coaching([])

    @pytest.mark.asyncio
    async def test_legacy_llm_error_propagates(self):
        trades = _make_trades(5)
        with patch("tradecoach.services.coaching.deep_analysis", new_callable=AsyncMock) as mock_deep:
            mock_deep.side_effect = LLMError("API key missing")
            with pytest.raises(LLMError, match="API key missing"):
                await generate_ai_coaching(trades)
