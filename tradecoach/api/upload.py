"""
File upload endpoint — CSV/Excel → parse → dedup → save to Supabase.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel

from tradecoach.api.auth import get_current_user, require_self

from tradecoach.db.models import TradeCreate
from tradecoach.db.queries import (
    find_existing_trade_keys,
    get_account,
    get_client,
    get_trades,
    insert_trades,
    trade_dedup_key,
)
from tradecoach.parsers.mt4_parser import MT4ParseError, parse_mt4_csv
from tradecoach.parsers.xlsx_parser import XlsxParseError, parse_xlsx
from tradecoach.services import trade_analyzer as ta
from tradecoach.services.beta_quota import BetaQuotaError, assert_can_upload_file
from tradecoach.services.tz_utils import DEFAULT_BROKER_TIMEZONE, naive_broker_wall_to_utc

router = APIRouter()


class UploadResponse(BaseModel):
    trades_parsed: int
    trades_new: int
    trades_duplicate: int
    trades_saved: int
    errors: list[str]
    summary: dict | None = None


def _broker_tz_for_upload(client, account_id: str) -> str:
    if not (account_id or "").strip():
        return DEFAULT_BROKER_TIMEZONE
    acct = get_account(client, account_id)
    if acct and (acct.broker_timezone or "").strip():
        return acct.broker_timezone
    return DEFAULT_BROKER_TIMEZONE


def _parsed_row_times_to_utc(row: dict, broker_tz: str) -> dict:
    """Journal times are broker-local wall; store true UTC on trade dict."""
    out = dict(row)
    for key in ("opened_at", "closed_at"):
        v = out.get(key)
        if v is None:
            continue
        if isinstance(v, str):
            s = v.strip().replace("Z", "")
            dt_naive = datetime.fromisoformat(s)
        elif isinstance(v, datetime):
            dt_naive = v.replace(tzinfo=None) if v.tzinfo else v
        else:
            continue
        out[key] = naive_broker_wall_to_utc(dt_naive, broker_tz).replace(microsecond=0)
    return out


@router.post("/{user_id}", response_model=UploadResponse)
def upload_file(
    user_id: str,
    file: UploadFile,
    account_id: str = Form(""),
    auth_user: str = Depends(get_current_user),
):
    """Upload CSV or Excel trade history."""
    require_self(auth_user, user_id)
    if not file.filename:
        raise HTTPException(400, "No file provided")

    fname = file.filename.lower()
    content = file.file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    # Parse based on file type
    if fname.endswith((".xlsx", ".xls")):
        try:
            parsed = parse_xlsx(content)
        except XlsxParseError as e:
            raise HTTPException(422, f"Excel parse error: {e}")
    elif fname.endswith((".csv", ".txt")):
        try:
            parsed = parse_mt4_csv(content)
        except MT4ParseError as e:
            raise HTTPException(422, f"CSV parse error: {e}")
    else:
        raise HTTPException(400, "File must be .csv, .txt, .xlsx, or .xls")

    if not parsed:
        raise HTTPException(422, "No trades found in file")

    client = get_client()
    try:
        assert_can_upload_file(client, user_id, account_id)
    except BetaQuotaError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    broker_tz = _broker_tz_for_upload(client, account_id)

    # Build TradeCreate objects
    errors: list[str] = []
    trade_creates: list[TradeCreate] = []

    for i, t in enumerate(parsed):
        try:
            t = _parsed_row_times_to_utc(t, broker_tz)
            tc = TradeCreate(
                user_id=user_id,
                account_id=account_id or None,
                source="excel" if fname.endswith((".xlsx", ".xls")) else "csv",
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
            )
            trade_creates.append(tc)
        except Exception as exc:
            errors.append(f"Trade {i + 1}: {exc}")

    # Dedup against existing trades
    existing_keys = find_existing_trade_keys(
        client, user_id, account_id=account_id or None,
    )

    new_trades: list[TradeCreate] = []
    duplicates = 0
    for tc in trade_creates:
        key = trade_dedup_key(tc.model_dump())
        if key in existing_keys:
            duplicates += 1
        else:
            new_trades.append(tc)

    # Insert new trades
    saved = []
    if new_trades:
        try:
            saved = insert_trades(client, new_trades)
        except Exception as exc:
            raise HTTPException(500, f"Database error: {exc}")

    # Summary stats from all trades in this account
    summary = None
    if saved and account_id:
        all_trades = get_trades(client, user_id, account_id=account_id)
        trade_dicts = [t.model_dump() for t in all_trades]
        summary = {
            "total_trades": len(trade_dicts),
            "win_rate": ta.win_rate(trade_dicts),
            "total_pnl": ta.total_pnl(trade_dicts),
        }

    return UploadResponse(
        trades_parsed=len(parsed),
        trades_new=len(new_trades),
        trades_duplicate=duplicates,
        trades_saved=len(saved),
        errors=errors,
        summary=summary,
    )
