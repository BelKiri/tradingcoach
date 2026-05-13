"""
Tests for LLM integration — GPT-4o-mini and Claude Sonnet.

All API calls are mocked. Tests verify:
  - quick_query calls OpenAI with correct params
  - deep_analysis calls Anthropic with correct params
  - Error handling for API failures
  - Token counting and cost tracking
  - Model routing logic
  - System prompt is included
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tradecoach.services.llm import (
    LLMError,
    LLMUsage,
    QueryType,
    SYSTEM_PROMPT,
    _calc_cost,
    deep_analysis,
    get_stats,
    quick_query,
    reset_stats,
    route_query,
)


# ===================================================================
# Fixtures
# ===================================================================


def _mock_openai_response(text: str = "AI response", input_tokens: int = 100, output_tokens: int = 50):
    """Build a mock OpenAI ChatCompletion response."""
    usage = MagicMock()
    usage.prompt_tokens = input_tokens
    usage.completion_tokens = output_tokens
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


def _mock_anthropic_response(text: str = "AI response", input_tokens: int = 200, output_tokens: int = 100):
    """Build a mock Anthropic Messages response."""
    content_block = MagicMock()
    content_block.text = text
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    return response


@pytest.fixture(autouse=True)
def _reset():
    reset_stats()


# ===================================================================
# Cost calculation
# ===================================================================


class TestCalcCost:
    def test_gpt4o_mini_cost(self):
        cost = _calc_cost("gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == pytest.approx(0.75)  # 0.15 + 0.60

    def test_claude_sonnet_cost(self):
        cost = _calc_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.0)  # 3.0 + 15.0

    def test_unknown_model_zero_cost(self):
        cost = _calc_cost("unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_small_call_cost(self):
        cost = _calc_cost("gpt-4o-mini", 100, 50)
        expected = (100 * 0.15 + 50 * 0.60) / 1_000_000
        assert cost == pytest.approx(expected)


# ===================================================================
# quick_query (OpenAI GPT-4o-mini)
# ===================================================================


class TestQuickQuery:
    @pytest.mark.asyncio
    async def test_basic_query(self):
        mock_response = _mock_openai_response("Hello trader!")
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.openai.AsyncOpenAI", return_value=mock_client):
            mock_settings.return_value.openai_api_key = "test-key"
            text, usage = await quick_query("How am I doing?")

        assert text == "Hello trader!"
        assert usage.model == "gpt-4o-mini"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_with_context(self):
        mock_response = _mock_openai_response("Analysis here")
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.openai.AsyncOpenAI", return_value=mock_client):
            mock_settings.return_value.openai_api_key = "test-key"
            text, usage = await quick_query("Summarize", context="Win rate: 55%")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT
        assert "Win rate: 55%" in messages[1]["content"]
        assert messages[-1]["content"] == "Summarize"

    @pytest.mark.asyncio
    async def test_no_api_key_raises(self):
        with patch("tradecoach.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = ""
            with pytest.raises(LLMError, match="OpenAI API key not configured"):
                await quick_query("test")

    @pytest.mark.asyncio
    async def test_api_error_raises(self):
        import openai as openai_mod
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai_mod.APIError(
                message="Server error",
                request=MagicMock(),
                body=None,
            )
        )

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.openai.AsyncOpenAI", return_value=mock_client):
            mock_settings.return_value.openai_api_key = "test-key"
            with pytest.raises(LLMError, match="OpenAI API error"):
                await quick_query("test")

    @pytest.mark.asyncio
    async def test_rate_limit_raises(self):
        import openai as openai_mod
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai_mod.RateLimitError(
                message="Rate limit",
                response=MagicMock(status_code=429, headers={}),
                body=None,
            )
        )

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.openai.AsyncOpenAI", return_value=mock_client):
            mock_settings.return_value.openai_api_key = "test-key"
            with pytest.raises(LLMError, match="rate limit"):
                await quick_query("test")

    @pytest.mark.asyncio
    async def test_tracks_stats(self):
        mock_response = _mock_openai_response("ok", 50, 25)
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.openai.AsyncOpenAI", return_value=mock_client):
            mock_settings.return_value.openai_api_key = "test-key"
            await quick_query("test")

        stats = get_stats()
        assert len(stats.calls) == 1
        assert stats.total_input_tokens == 50
        assert stats.total_output_tokens == 25
        assert stats.total_cost > 0


# ===================================================================
# deep_analysis (Anthropic Claude Sonnet)
# ===================================================================


class TestDeepAnalysis:
    @pytest.mark.asyncio
    async def test_basic_analysis(self):
        mock_response = _mock_anthropic_response("Deep analysis here")
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.anthropic.AsyncAnthropic", return_value=mock_client):
            mock_settings.return_value.anthropic_api_key = "test-key"
            text, usage = await deep_analysis("Analyze my trading")

        assert text == "Deep analysis here"
        assert usage.model == "claude-sonnet-4-6"
        assert usage.input_tokens == 200
        assert usage.output_tokens == 100

    @pytest.mark.asyncio
    async def test_with_context(self):
        mock_response = _mock_anthropic_response("result")
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.anthropic.AsyncAnthropic", return_value=mock_client):
            mock_settings.return_value.anthropic_api_key = "test-key"
            await deep_analysis("Analyze", context="P&L: -$500")

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["system"] == SYSTEM_PROMPT
        messages = call_args.kwargs["messages"]
        assert "P&L: -$500" in messages[0]["content"]
        assert messages[-1]["content"] == "Analyze"

    @pytest.mark.asyncio
    async def test_no_api_key_raises(self):
        with patch("tradecoach.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = ""
            with pytest.raises(LLMError, match="Anthropic API key not configured"):
                await deep_analysis("test")

    @pytest.mark.asyncio
    async def test_api_error_raises(self):
        import anthropic as anthropic_mod
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic_mod.APIError(
                message="Server error",
                request=MagicMock(),
                body=None,
            )
        )

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.anthropic.AsyncAnthropic", return_value=mock_client):
            mock_settings.return_value.anthropic_api_key = "test-key"
            with pytest.raises(LLMError, match="Anthropic API error"):
                await deep_analysis("test")

    @pytest.mark.asyncio
    async def test_tracks_stats(self):
        mock_response = _mock_anthropic_response("ok", 200, 100)
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("tradecoach.services.llm.get_settings") as mock_settings, \
             patch("tradecoach.services.llm.anthropic.AsyncAnthropic", return_value=mock_client):
            mock_settings.return_value.anthropic_api_key = "test-key"
            await deep_analysis("test")

        stats = get_stats()
        assert len(stats.calls) == 1
        assert stats.total_input_tokens == 200
        assert stats.total_output_tokens == 100


# ===================================================================
# Model routing
# ===================================================================


class TestRouteQuery:
    def test_quick_types(self):
        assert route_query("stats") == QueryType.QUICK
        assert route_query("question") == QueryType.QUICK
        assert route_query("unknown") == QueryType.QUICK

    def test_deep_types(self):
        assert route_query("coaching") == QueryType.DEEP
        assert route_query("analysis") == QueryType.DEEP
        assert route_query("review") == QueryType.DEEP
        assert route_query("weekly_review") == QueryType.DEEP


# ===================================================================
# Stats tracking
# ===================================================================


class TestStats:
    def test_empty_stats(self):
        stats = get_stats()
        assert stats.total_cost == 0
        assert stats.total_input_tokens == 0
        assert stats.total_output_tokens == 0
        assert len(stats.calls) == 0

    def test_reset_stats(self):
        stats = get_stats()
        stats.calls.append(LLMUsage(
            model="test", input_tokens=100, output_tokens=50,
            cost_usd=0.01, latency_ms=100,
        ))
        assert len(get_stats().calls) == 1
        reset_stats()
        assert len(get_stats().calls) == 0

    def test_multiple_calls_aggregate(self):
        stats = get_stats()
        stats.calls.append(LLMUsage(
            model="m1", input_tokens=100, output_tokens=50,
            cost_usd=0.01, latency_ms=100,
        ))
        stats.calls.append(LLMUsage(
            model="m2", input_tokens=200, output_tokens=100,
            cost_usd=0.02, latency_ms=200,
        ))
        assert stats.total_input_tokens == 300
        assert stats.total_output_tokens == 150
        assert stats.total_cost == pytest.approx(0.03)
