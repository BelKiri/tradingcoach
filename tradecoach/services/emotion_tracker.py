"""
Emotion correlation analysis — pure math, no AI.

Correlates trader emotions with performance metrics.
"When you tag 'boredom' your win rate is 23%. When 'calm' it's 61%."

Inputs:
  - trades: list of trade dicts (standard schema)
  - emotions: list of emotion dicts ({trade_id, emotion, context, logged_at})

Emotions: calm, confident, fear, boredom, revenge
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from tradecoach.services._helpers import (
    _is_winner,
    _net_profit,
)
from tradecoach.services.tz_utils import (
    DEFAULT_BROKER_TIMEZONE,
    broker_local_hour,
    broker_local_weekday,
    session_label_for_utc,
    trade_instant_utc,
)

_EPOCH_EM = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_EMOTIONS = ("calm", "confident", "fear", "boredom", "revenge")
POSITIVE_EMOTIONS = {"calm", "confident"}
NEGATIVE_EMOTIONS = {"fear", "boredom", "revenge"}


# ---------------------------------------------------------------------------
# Trade-emotion joining
# ---------------------------------------------------------------------------

def _build_trade_map(trades: list[dict]) -> dict[Any, dict]:
    """Map trade ID → trade dict."""
    m: dict[Any, dict] = {}
    for t in trades:
        tid = t.get("id") or t.get("ticket")
        if tid is not None:
            m[tid] = t
    return m


def _join_trades_emotions(
    trades: list[dict], emotions: list[dict]
) -> list[tuple[dict, str]]:
    """Return list of (trade, emotion_str) pairs.

    Each trade appears once with its primary emotion (first post_trade,
    or first emotion if no post_trade context).
    """
    trade_map = _build_trade_map(trades)

    # Group emotions by trade_id, prefer post_trade context
    best_emotion: dict[Any, str] = {}
    for e in emotions:
        tid = e.get("trade_id")
        if tid is None or tid not in trade_map:
            continue
        emotion = (e.get("emotion") or "").lower()
        if not emotion:
            continue
        ctx = (e.get("context") or "").lower()
        # Prefer post_trade; only overwrite if current is not post_trade
        if tid not in best_emotion or ctx == "post_trade":
            best_emotion[tid] = emotion

    pairs = []
    for tid, emotion in best_emotion.items():
        pairs.append((trade_map[tid], emotion))
    return pairs


# ---------------------------------------------------------------------------
# Core: stats per emotion
# ---------------------------------------------------------------------------

def stats_by_emotion(
    trades: list[dict], emotions: list[dict]
) -> dict[str, dict[str, Any]]:
    """Win rate and avg P&L per emotion.

    Returns {emotion: {trades, wins, losses, win_rate, avg_pnl, total_pnl}}.
    """
    pairs = _join_trades_emotions(trades, emotions)
    groups: dict[str, list[dict]] = defaultdict(list)
    for trade, emotion in pairs:
        groups[emotion].append(trade)

    result = {}
    for emotion in ALL_EMOTIONS:
        group = groups.get(emotion, [])
        if not group:
            result[emotion] = {
                "trades": 0, "wins": 0, "losses": 0,
                "win_rate": None, "avg_pnl": None, "total_pnl": 0.0,
            }
            continue

        wins = sum(1 for t in group if _is_winner(t))
        losses = sum(1 for t in group if _net_profit(t) < 0)
        pnls = [_net_profit(t) for t in group]

        result[emotion] = {
            "trades": len(group),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(group) * 100, 2),
            "avg_pnl": round(sum(pnls) / len(pnls), 2),
            "total_pnl": round(sum(pnls), 2),
        }
    return result


# ---------------------------------------------------------------------------
# Best / worst emotion
# ---------------------------------------------------------------------------

def best_emotion(
    trades: list[dict], emotions: list[dict]
) -> dict[str, Any] | None:
    """Emotion with the highest win rate (min 1 trade)."""
    stats = stats_by_emotion(trades, emotions)
    candidates = [
        (em, data) for em, data in stats.items()
        if data["trades"] > 0 and data["win_rate"] is not None
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda x: x[1]["win_rate"])
    return {"emotion": best[0], **best[1]}


def worst_emotion(
    trades: list[dict], emotions: list[dict]
) -> dict[str, Any] | None:
    """Emotion with the lowest win rate (min 1 trade)."""
    stats = stats_by_emotion(trades, emotions)
    candidates = [
        (em, data) for em, data in stats.items()
        if data["trades"] > 0 and data["win_rate"] is not None
    ]
    if not candidates:
        return None
    worst = min(candidates, key=lambda x: x[1]["win_rate"])
    return {"emotion": worst[0], **worst[1]}


# ---------------------------------------------------------------------------
# Emotional streaks
# ---------------------------------------------------------------------------

def detect_emotional_streaks(
    trades: list[dict],
    emotions: list[dict],
    *,
    min_streak: int = 3,
) -> list[dict[str, Any]]:
    """Detect streaks of 3+ consecutive trades with the same negative emotion.

    Trades sorted by open time. Returns list of
    {emotion, length, trades, total_pnl}.
    """
    pairs = _join_trades_emotions(trades, emotions)
    # Sort by open time
    pairs.sort(
        key=lambda p: trade_instant_utc(p[0].get("opened_at")) or _EPOCH_EM,
    )

    streaks: list[dict[str, Any]] = []
    if not pairs:
        return streaks

    current_emotion: str | None = None
    current_trades: list[dict] = []

    def _flush() -> None:
        if (
            current_emotion
            and current_emotion in NEGATIVE_EMOTIONS
            and len(current_trades) >= min_streak
        ):
            streaks.append({
                "emotion": current_emotion,
                "length": len(current_trades),
                "trades": list(current_trades),
                "total_pnl": round(
                    sum(_net_profit(t) for t in current_trades), 2
                ),
            })

    for trade, emotion in pairs:
        if emotion == current_emotion:
            current_trades.append(trade)
        else:
            _flush()
            current_emotion = emotion
            current_trades = [trade]

    _flush()
    return streaks


# ---------------------------------------------------------------------------
# Correlations: emotion × symbol, session, hour, day of week
# ---------------------------------------------------------------------------

def emotion_by_symbol(
    trades: list[dict], emotions: list[dict]
) -> dict[str, dict[str, dict[str, Any]]]:
    """Emotion distribution and win rate per symbol.

    Returns {symbol: {emotion: {trades, win_rate, avg_pnl}}}.
    """
    pairs = _join_trades_emotions(trades, emotions)
    groups: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for trade, emotion in pairs:
        symbol = trade.get("symbol", "UNKNOWN")
        groups[symbol][emotion].append(trade)

    return _build_correlation_result(groups)


def emotion_by_session(
    trades: list[dict], emotions: list[dict],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Emotion distribution per trading session (UTC IANA buckets)."""
    pairs = _join_trades_emotions(trades, emotions)
    groups: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for trade, emotion in pairs:
        dt_utc = trade_instant_utc(trade.get("opened_at"))
        session = session_label_for_utc(dt_utc) if dt_utc else "Unknown"
        groups[session][emotion].append(trade)

    return _build_correlation_result(groups)


def emotion_by_hour(
    trades: list[dict], emotions: list[dict], broker_timezone: str | None = None,
) -> dict[int, dict[str, dict[str, Any]]]:
    """Emotion distribution per broker-local hour."""
    bt = broker_timezone or DEFAULT_BROKER_TIMEZONE
    pairs = _join_trades_emotions(trades, emotions)
    groups: dict[int, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for trade, emotion in pairs:
        dt_utc = trade_instant_utc(trade.get("opened_at"))
        if dt_utc:
            groups[broker_local_hour(dt_utc, bt)][emotion].append(trade)

    result = {}
    for hour in sorted(groups.keys()):
        result[hour] = _summarize_emotion_group(groups[hour])
    return result


def emotion_by_day_of_week(
    trades: list[dict], emotions: list[dict], broker_timezone: str | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Emotion distribution per broker-local weekday."""
    bt = broker_timezone or DEFAULT_BROKER_TIMEZONE
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
    pairs = _join_trades_emotions(trades, emotions)
    groups: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for trade, emotion in pairs:
        dt_utc = trade_instant_utc(trade.get("opened_at"))
        if dt_utc:
            wd = broker_local_weekday(dt_utc, bt)
            groups[day_names[wd]][emotion].append(trade)

    return _build_correlation_result(groups)


def _build_correlation_result(
    groups: dict[str, dict[str, list[dict]]]
) -> dict[str, dict[str, dict[str, Any]]]:
    result = {}
    for key in sorted(groups.keys()):
        result[key] = _summarize_emotion_group(groups[key])
    return result


def _summarize_emotion_group(
    emotion_trades: dict[str, list[dict]]
) -> dict[str, dict[str, Any]]:
    summary = {}
    for emotion, group in sorted(emotion_trades.items()):
        wins = sum(1 for t in group if _is_winner(t))
        pnls = [_net_profit(t) for t in group]
        summary[emotion] = {
            "trades": len(group),
            "win_rate": round(wins / len(group) * 100, 2),
            "avg_pnl": round(sum(pnls) / len(pnls), 2),
        }
    return summary


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def emotion_summary(
    trades: list[dict], emotions: list[dict], broker_timezone: str | None = None,
) -> dict[str, Any]:
    """Full emotion analysis in one call."""
    bt = broker_timezone or DEFAULT_BROKER_TIMEZONE
    return {
        "stats_by_emotion": stats_by_emotion(trades, emotions),
        "best_emotion": best_emotion(trades, emotions),
        "worst_emotion": worst_emotion(trades, emotions),
        "emotional_streaks": detect_emotional_streaks(trades, emotions),
        "by_symbol": emotion_by_symbol(trades, emotions),
        "by_session": emotion_by_session(trades, emotions),
        "by_hour": emotion_by_hour(trades, emotions, broker_timezone=bt),
        "by_day_of_week": emotion_by_day_of_week(trades, emotions, broker_timezone=bt),
    }
