"""
Trading Habit Score calculator (0-100).

Pure math, no AI. The score measures process quality, not P&L.
A trader can have a high score even with negative P&L (good process,
bad luck) — this is the key differentiator from Myfxbook-style dashboards.

Inputs:
  - trades: list of trade dicts (with followed_plan, moved_stop, lot, etc.)
  - emotions: list of emotion dicts (with emotion, trade_id, context)
  - settings: user_settings dict (max_risk_pct)
  - account_balance: for risk % calculation

Output:
  - HabitScore with overall score (0-100) and 5 weighted sub-scores.
  - Matches the habit_scores table schema.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Weights for each sub-score (must sum to 1.0)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "plan_adherence": 0.25,
    "emotional_stability": 0.20,
    "risk_discipline": 0.25,
    "consistency": 0.15,
    "journal_completion": 0.15,
}

# Emotions considered "stable"
_STABLE_EMOTIONS = {"calm", "confident"}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class HabitScore:
    score: int  # 0-100, weighted composite
    plan_adherence: float  # 0-100
    emotional_stability: float  # 0-100
    risk_discipline: float  # 0-100
    consistency: float  # 0-100
    journal_completion: float  # 0-100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_habit_score(
    trades: list[dict],
    emotions: list[dict],
    settings: dict | None = None,
    *,
    account_balance: float | None = None,
) -> HabitScore:
    """Calculate the Trading Habit Score.

    Args:
        trades: Trade dicts (need: followed_plan, lot, stop_loss,
                open_price, direction, symbol).
        emotions: Emotion dicts (need: emotion, trade_id).
        settings: User settings dict (need: max_risk_pct).
        account_balance: Current account balance for risk calculation.

    Returns:
        HabitScore with overall score and 5 sub-scores.
    """
    if not trades:
        return HabitScore(
            score=0,
            plan_adherence=0.0,
            emotional_stability=0.0,
            risk_discipline=0.0,
            consistency=0.0,
            journal_completion=0.0,
        )

    pa = _plan_adherence(trades)
    es = _emotional_stability(trades, emotions)
    rd = _risk_discipline(trades, settings, account_balance)
    co = _consistency(trades)
    jc = _journal_completion(trades, emotions)

    weighted = (
        pa * WEIGHTS["plan_adherence"]
        + es * WEIGHTS["emotional_stability"]
        + rd * WEIGHTS["risk_discipline"]
        + co * WEIGHTS["consistency"]
        + jc * WEIGHTS["journal_completion"]
    )

    return HabitScore(
        score=round(weighted),
        plan_adherence=round(pa, 2),
        emotional_stability=round(es, 2),
        risk_discipline=round(rd, 2),
        consistency=round(co, 2),
        journal_completion=round(jc, 2),
    )


# ---------------------------------------------------------------------------
# Sub-score calculations
# ---------------------------------------------------------------------------

def _plan_adherence(trades: list[dict]) -> float:
    """% of trades where followed_plan is True.

    Trades with followed_plan=None (not answered) count as non-adherent.
    """
    if not trades:
        return 0.0
    followed = sum(1 for t in trades if t.get("followed_plan") is True)
    return followed / len(trades) * 100


def _emotional_stability(
    trades: list[dict], emotions: list[dict]
) -> float:
    """% of trades with a 'calm' or 'confident' emotion logged.

    Only post-trade emotions linked to a trade are counted.
    Trades without any emotion log count as unstable.
    """
    if not trades:
        return 0.0

    # Build map: trade_id -> list of emotions
    trade_ids = {t.get("id") or t.get("ticket") for t in trades}
    emotion_by_trade: dict[Any, list[str]] = {}
    for e in emotions:
        tid = e.get("trade_id")
        if tid is not None and tid in trade_ids:
            emotion_by_trade.setdefault(tid, []).append(
                e.get("emotion", "").lower()
            )

    stable_count = 0
    for t in trades:
        tid = t.get("id") or t.get("ticket")
        trade_emotions = emotion_by_trade.get(tid, [])
        if trade_emotions and any(em in _STABLE_EMOTIONS for em in trade_emotions):
            stable_count += 1

    return stable_count / len(trades) * 100


def _risk_discipline(
    trades: list[dict],
    settings: dict | None,
    account_balance: float | None,
) -> float:
    """% of trades within the user's max risk rule.

    Risk is estimated from lot size and stop distance.
    Trades without SL are considered risk violations.
    If no settings or balance provided, only checks SL presence.
    """
    if not trades:
        return 0.0

    from tradecoach.services.trade_analyzer import build_contract_lookup

    max_risk = (settings or {}).get("max_risk_pct", 2.0)
    contracts = build_contract_lookup(trades)
    compliant = 0

    for t in trades:
        sl = t.get("stop_loss")
        op = t.get("open_price")
        lot = t.get("lot")

        # No stop loss = automatic violation
        if not sl:
            continue

        # If we can calculate risk %, check against max
        symbol = (t.get("symbol") or "").upper()
        if op and lot and account_balance and account_balance > 0 and symbol in contracts:
            risk_money = abs(float(op) - float(sl)) * contracts[symbol] * float(lot)
            risk_pct = risk_money / account_balance * 100
            if risk_pct <= max_risk:
                compliant += 1
        else:
            # Has SL but can't calculate risk — count as compliant
            compliant += 1

    return compliant / len(trades) * 100


def _consistency(trades: list[dict]) -> float:
    """Score for sticking to a consistent set of symbols.

    Measures how concentrated trading is across instruments.
    Trading 1-2 pairs = 100, 3 pairs = 85, 4 = 70, 5 = 55, 6+ = max(40, decay).

    This penalizes "strategy hopping" across many instruments.
    """
    if not trades:
        return 0.0

    symbols = [t.get("symbol", "UNKNOWN") for t in trades]
    unique_count = len(set(symbols))

    # Also consider concentration (top pair should be dominant)
    counts = Counter(symbols)
    if not counts:
        return 0.0

    top_freq = counts.most_common(1)[0][1] / len(trades)

    # Base score from number of unique symbols
    if unique_count <= 2:
        base = 100.0
    elif unique_count == 3:
        base = 85.0
    elif unique_count == 4:
        base = 70.0
    elif unique_count == 5:
        base = 55.0
    else:
        base = max(40.0, 100.0 - unique_count * 10)

    # Bonus/penalty for concentration (if top pair is >50% of trades, boost)
    concentration_bonus = (top_freq - 0.5) * 20 if top_freq > 0.5 else 0

    return min(100.0, max(0.0, base + concentration_bonus))


def _journal_completion(
    trades: list[dict], emotions: list[dict]
) -> float:
    """% of trades that have a complete post-trade journal.

    A trade is "journaled" if it has:
    - followed_plan answered (not None), AND
    - at least one emotion logged for it
    """
    if not trades:
        return 0.0

    trade_ids_with_emotion = set()
    for e in emotions:
        tid = e.get("trade_id")
        if tid is not None:
            trade_ids_with_emotion.add(tid)

    journaled = 0
    for t in trades:
        tid = t.get("id") or t.get("ticket")
        has_plan_answer = t.get("followed_plan") is not None
        has_emotion = tid in trade_ids_with_emotion
        if has_plan_answer and has_emotion:
            journaled += 1

    return journaled / len(trades) * 100
