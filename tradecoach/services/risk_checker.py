"""
Pre-trade risk checker.

Validates a proposed trade against the trader's own rules before entry.
Called from the Telegram "Check" flow and the pre-trade checklist.

Inputs:
  - proposed trade: symbol, direction, lot, stop_loss (price), open_price
  - settings: user_settings dict (max_risk_pct, max_trades_per_day, watchlist)
  - today_trades: list of trades already taken today
  - account_balance: current balance

Output:
  - ChecklistResult with pass/fail per rule and warning messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tradecoach.services._helpers import _net_profit, _to_dt


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CheckItem:
    rule: str
    passed: bool
    message: str


@dataclass
class ChecklistResult:
    items: list[CheckItem] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(item.passed for item in self.items)

    @property
    def warnings(self) -> list[str]:
        return [item.message for item in self.items if not item.passed]

    @property
    def passed_count(self) -> int:
        return sum(1 for item in self.items if item.passed)

    @property
    def total_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "passed": self.passed_count,
            "total": self.total_count,
            "items": [
                {"rule": i.rule, "passed": i.passed, "message": i.message}
                for i in self.items
            ],
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pre_trade_check(
    *,
    symbol: str,
    direction: str,
    lot: float,
    stop_loss: float | None,
    open_price: float,
    account_balance: float,
    settings: dict,
    today_trades: list[dict] | None = None,
    all_trades: list[dict] | None = None,
) -> ChecklistResult:
    """Run all pre-trade validation checks.

    Args:
        symbol: e.g. "EURUSD"
        direction: "buy" or "sell"
        lot: position size
        stop_loss: SL price (None if not set)
        open_price: intended entry price
        account_balance: current account balance
        settings: user_settings dict
        today_trades: trades already closed/opened today
        all_trades: full trade history for contract size detection

    Returns:
        ChecklistResult with pass/fail for each rule.
    """
    today_trades = today_trades or []
    result = ChecklistResult()

    result.items.append(_check_risk_size(
        symbol, direction, lot, stop_loss, open_price,
        account_balance, settings, all_trades=all_trades,
    ))
    result.items.append(_check_stop_loss_set(stop_loss))
    result.items.append(_check_daily_trade_count(today_trades, settings))
    result.items.append(_check_watchlist(symbol, settings))
    result.items.append(_check_losing_streak(today_trades))

    return result


# ---------------------------------------------------------------------------
# Risk calculation (also exposed for standalone use)
# ---------------------------------------------------------------------------

def calculate_risk(
    *,
    symbol: str,
    lot: float,
    stop_loss: float,
    open_price: float,
    account_balance: float,
    contract_size: float,
) -> dict[str, float]:
    """Calculate risk in money and percentage.

    risk_money = abs(open_price - stop_loss) * contract_size * lot

    Returns {risk_money, risk_pct}.
    """
    risk_money = abs(open_price - stop_loss) * contract_size * lot
    risk_pct = (risk_money / account_balance * 100) if account_balance > 0 else 0.0

    return {
        "risk_money": round(risk_money, 2),
        "risk_pct": round(risk_pct, 2),
    }


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_risk_size(
    symbol: str,
    direction: str,
    lot: float,
    stop_loss: float | None,
    open_price: float,
    account_balance: float,
    settings: dict,
    *,
    all_trades: list[dict] | None = None,
) -> CheckItem:
    """Check position risk against max_risk_pct."""
    from tradecoach.services.trade_analyzer import build_contract_lookup

    max_risk = settings.get("max_risk_pct", 2.0)

    if stop_loss is None:
        return CheckItem(
            rule="risk_size",
            passed=False,
            message=f"Cannot calculate risk without stop loss. "
                    f"Max allowed: {max_risk}% of account.",
        )

    if account_balance <= 0:
        return CheckItem(
            rule="risk_size",
            passed=False,
            message="Account balance must be positive to calculate risk.",
        )

    contracts = build_contract_lookup(all_trades or [])
    sym = symbol.upper()
    if sym not in contracts:
        return CheckItem(
            rule="risk_size",
            passed=True,
            message=f"Cannot calculate risk for {symbol} — "
                    f"no trade history to detect contract size.",
        )

    risk = calculate_risk(
        symbol=symbol, lot=lot,
        stop_loss=stop_loss, open_price=open_price,
        account_balance=account_balance,
        contract_size=contracts[sym],
    )

    if risk["risk_pct"] <= max_risk:
        return CheckItem(
            rule="risk_size",
            passed=True,
            message=f"Risk: {risk['risk_pct']}% (${risk['risk_money']}) — "
                    f"within {max_risk}% limit.",
        )
    else:
        return CheckItem(
            rule="risk_size",
            passed=False,
            message=f"Risk too high: {risk['risk_pct']}% (${risk['risk_money']}) — "
                    f"exceeds {max_risk}% limit. "
                    f"Reduce lot or widen your risk rule.",
        )


def _check_stop_loss_set(stop_loss: float | None) -> CheckItem:
    """Check that a stop loss is set."""
    if stop_loss is not None:
        return CheckItem(
            rule="stop_loss",
            passed=True,
            message="Stop loss is set.",
        )
    return CheckItem(
        rule="stop_loss",
        passed=False,
        message="No stop loss set. Trading without SL violates risk discipline.",
    )


def _check_daily_trade_count(
    today_trades: list[dict], settings: dict
) -> CheckItem:
    """Check trade count against max_trades_per_day."""
    max_trades = settings.get("max_trades_per_day", 5)
    count = len(today_trades)

    if count < max_trades:
        remaining = max_trades - count
        return CheckItem(
            rule="daily_limit",
            passed=True,
            message=f"Trade {count + 1} of {max_trades} today. "
                    f"{remaining - 1} more after this.",
        )
    else:
        return CheckItem(
            rule="daily_limit",
            passed=False,
            message=f"Daily limit reached: {count}/{max_trades} trades today. "
                    f"Stop trading for today.",
        )


def _check_watchlist(symbol: str, settings: dict) -> CheckItem:
    """Check if symbol is in trader's watchlist."""
    watchlist = settings.get("watchlist") or []

    if not watchlist:
        return CheckItem(
            rule="watchlist",
            passed=True,
            message="No watchlist configured — all symbols allowed.",
        )

    normalized_watchlist = [s.upper() for s in watchlist]
    if symbol.upper() in normalized_watchlist:
        return CheckItem(
            rule="watchlist",
            passed=True,
            message=f"{symbol} is in your watchlist.",
        )
    else:
        return CheckItem(
            rule="watchlist",
            passed=False,
            message=f"{symbol} is NOT in your watchlist "
                    f"({', '.join(watchlist)}). "
                    f"Trading off-watchlist hurts consistency.",
        )


def _check_losing_streak(
    today_trades: list[dict], *, threshold: int = 3
) -> CheckItem:
    """Detect if the trader is on a losing streak (3+ consecutive losses)."""
    if not today_trades:
        return CheckItem(
            rule="losing_streak",
            passed=True,
            message="No trades today yet. Fresh start.",
        )

    # Sort by close time, count consecutive losses from the end
    sorted_trades = sorted(
        today_trades,
        key=lambda t: _to_dt(t.get("closed_at")) or datetime.min,
    )

    consecutive_losses = 0
    for t in reversed(sorted_trades):
        if _net_profit(t) < 0:
            consecutive_losses += 1
        else:
            break

    if consecutive_losses >= threshold:
        total_lost = sum(
            _net_profit(t) for t in sorted_trades[-consecutive_losses:]
        )
        return CheckItem(
            rule="losing_streak",
            passed=False,
            message=f"You're on a {consecutive_losses}-trade losing streak "
                    f"(${round(total_lost, 2)} lost). "
                    f"Consider taking a break.",
        )
    elif consecutive_losses > 0:
        return CheckItem(
            rule="losing_streak",
            passed=True,
            message=f"{consecutive_losses} consecutive loss(es). "
                    f"Not yet a streak, but stay disciplined.",
        )
    else:
        return CheckItem(
            rule="losing_streak",
            passed=True,
            message="No losing streak. Last trade was a winner.",
        )
