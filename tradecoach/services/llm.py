"""
LLM integration — GPT-4o-mini (fast) + Claude Sonnet (deep analysis).

All numbers are computed programmatically in trade_analyzer.py.
The LLM only wraps pre-calculated data in natural language.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import anthropic
import openai

from tradecoach.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are TradeCoach, an AI trading coach. You analyze trading data and give "
    "personalized coaching. You NEVER give financial advice or say buy/sell. You "
    "show facts, patterns, and behavioral insights. You speak directly to the "
    "trader, using their data. Be specific with numbers. Be supportive but honest."
)


class QueryType(Enum):
    QUICK = "quick"
    DEEP = "deep"


@dataclass
class LLMUsage:
    """Token usage and cost for a single LLM call."""
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


# Cost per 1M tokens (input / output) — March 2026 pricing
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet-4-6": (3.00, 15.00),
}


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a call."""
    prices = _PRICING.get(model, (0.0, 0.0))
    return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000


@dataclass
class LLMStats:
    """Aggregated stats across calls within a session."""
    calls: list[LLMUsage] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)


# Module-level stats tracker
_stats = LLMStats()


def get_stats() -> LLMStats:
    """Get current session stats."""
    return _stats


def reset_stats() -> None:
    """Reset session stats."""
    global _stats
    _stats = LLMStats()


async def quick_query(prompt: str, context: str = "") -> tuple[str, LLMUsage]:
    """Fast query using GPT-4o-mini.

    Args:
        prompt: User-facing prompt or question.
        context: Pre-calculated data/stats to include.

    Returns:
        Tuple of (response text, usage stats).

    Raises:
        LLMError: On API failure.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError("OpenAI API key not configured")

    model = "gpt-4o-mini"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({"role": "user", "content": f"Context data:\n{context}"})
        messages.append({
            "role": "assistant",
            "content": "I have the trading data. What would you like me to analyze?",
        })
    messages.append({"role": "user", "content": prompt})

    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    start = time.monotonic()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
        )
    except openai.APIConnectionError as e:
        raise LLMError(f"OpenAI connection error: {e}") from e
    except openai.RateLimitError as e:
        raise LLMError(f"OpenAI rate limit: {e}") from e
    except openai.APIError as e:
        raise LLMError(f"OpenAI API error: {e}") from e

    latency = (time.monotonic() - start) * 1000

    text = response.choices[0].message.content or ""
    usage = LLMUsage(
        model=model,
        input_tokens=response.usage.prompt_tokens if response.usage else 0,
        output_tokens=response.usage.completion_tokens if response.usage else 0,
        cost_usd=_calc_cost(
            model,
            response.usage.prompt_tokens if response.usage else 0,
            response.usage.completion_tokens if response.usage else 0,
        ),
        latency_ms=latency,
    )
    _stats.calls.append(usage)
    logger.info(
        "quick_query: %d in / %d out tokens, $%.4f, %.0fms",
        usage.input_tokens, usage.output_tokens, usage.cost_usd, usage.latency_ms,
    )
    return text, usage


async def deep_analysis(prompt: str, context: str = "") -> tuple[str, LLMUsage]:
    """Deep analysis using Claude Sonnet.

    Args:
        prompt: Analysis prompt with instructions.
        context: Pre-calculated data/stats to include.

    Returns:
        Tuple of (response text, usage stats).

    Raises:
        LLMError: On API failure.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise LLMError("Anthropic API key not configured")

    model = "claude-sonnet-4-6"
    messages = []
    if context:
        messages.append({"role": "user", "content": f"Context data:\n{context}"})
        messages.append({
            "role": "assistant",
            "content": "I have the trading data. What would you like me to analyze?",
        })
    messages.append({"role": "user", "content": prompt})

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    start = time.monotonic()
    try:
        response = await client.messages.create(
            model=model,
            system=SYSTEM_PROMPT,
            messages=messages,
            max_tokens=4096,
            temperature=0.7,
        )
    except anthropic.APIConnectionError as e:
        raise LLMError(f"Anthropic connection error: {e}") from e
    except anthropic.RateLimitError as e:
        raise LLMError(f"Anthropic rate limit: {e}") from e
    except anthropic.APIError as e:
        raise LLMError(f"Anthropic API error: {e}") from e

    latency = (time.monotonic() - start) * 1000

    text = response.content[0].text if response.content else ""
    usage = LLMUsage(
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cost_usd=_calc_cost(model, response.usage.input_tokens, response.usage.output_tokens),
        latency_ms=latency,
    )
    _stats.calls.append(usage)
    logger.info(
        "deep_analysis: %d in / %d out tokens, $%.4f, %.0fms",
        usage.input_tokens, usage.output_tokens, usage.cost_usd, usage.latency_ms,
    )
    return text, usage


def route_query(query_type: str) -> QueryType:
    """Route a query to the appropriate model based on type.

    Args:
        query_type: One of 'stats', 'question', 'coaching', 'analysis', 'review'.

    Returns:
        QueryType indicating which model to use.
    """
    deep_types = {"coaching", "analysis", "review", "weekly_review"}
    if query_type in deep_types:
        return QueryType.DEEP
    return QueryType.QUICK


class LLMError(Exception):
    """Raised when an LLM API call fails."""
