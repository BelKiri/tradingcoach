"""
AI coaching endpoint — full RAG-powered coaching analysis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from tradecoach.api.auth import get_current_user, require_self
from tradecoach.db.queries import get_client
from tradecoach.services.coaching import get_ai_coaching
from tradecoach.services.llm import LLMError

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

class CoachingPeriod(BaseModel):
    date_from: str | None = None
    date_to: str | None = None


class CoachingRequest(BaseModel):
    account_id: str
    period: CoachingPeriod | None = None


class CoachingUsage(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CoachingResponse(BaseModel):
    session_id: str
    ai_response: str
    metrics_snapshot: dict[str, Any]
    verdict: str | None
    created_at: str
    usage: CoachingUsage


class CoachingSessionOut(BaseModel):
    id: str
    user_id: str
    account_id: str
    created_at: str
    ai_response: str
    metrics_snapshot: dict[str, Any] | None
    recommendations: list[str] | None
    verdict: str | None
    main_problem: str | None
    new_trades_count: int | None
    model_used: str | None


class CoachingErrorResponse(BaseModel):
    error: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_field(val: Any) -> Any:
    """Parse a JSON string field from DB, or return as-is if already parsed."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def _session_to_dict(row: dict) -> dict:
    """Convert a DB row to a clean session dict."""
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "account_id": row["account_id"],
        "created_at": row.get("created_at", ""),
        "ai_response": row.get("ai_response", ""),
        "metrics_snapshot": _parse_json_field(row.get("metrics_snapshot")),
        "recommendations": _parse_json_field(row.get("recommendations")),
        "verdict": row.get("verdict"),
        "main_problem": row.get("main_problem"),
        "new_trades_count": row.get("new_trades_count"),
        "model_used": row.get("model_used"),
    }


# ---------------------------------------------------------------------------
# POST /api/coaching/{user_id}
# ---------------------------------------------------------------------------

@router.post(
    "/{user_id}",
    response_model=CoachingResponse,
    responses={400: {"model": CoachingErrorResponse}},
)
async def request_coaching(user_id: str, body: CoachingRequest, auth_user: str = Depends(get_current_user)):
    """Generate AI coaching analysis with full RAG context."""
    require_self(auth_user, user_id)
    period_from = body.period.date_from if body.period else None
    period_to = body.period.date_to if body.period else None

    try:
        result = await get_ai_coaching(
            user_id=user_id,
            account_id=body.account_id,
            period_from=period_from,
            period_to=period_to,
        )
    except LLMError as e:
        from fastapi.responses import JSONResponse
        logger.exception("LLMError while generating coaching for user_id=%s", user_id)
        return JSONResponse(
            status_code=400,
            content={"error": "Unable to generate coaching at this time."},
        )

    return CoachingResponse(**result)


# ---------------------------------------------------------------------------
# GET /api/coaching/session/{session_id}
# ---------------------------------------------------------------------------

@router.get(
    "/session/{session_id}",
    response_model=CoachingSessionOut,
)
def get_coaching_session(session_id: str, auth_user: str = Depends(get_current_user)):
    """Get a single coaching session by ID."""
    client = get_client()
    result = (
        client.table("coaching_sessions")
        .select("*")
        .eq("id", session_id)
        .execute()
    )
    if not result.data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    session = result.data[0]
    require_self(auth_user, session["user_id"])
    return CoachingSessionOut(**_session_to_dict(session))


# ---------------------------------------------------------------------------
# GET /api/coaching/sessions/{user_id}
# ---------------------------------------------------------------------------

@router.get(
    "/sessions/{user_id}",
    response_model=list[CoachingSessionOut],
)
def list_coaching_sessions(
    user_id: str,
    account_id: str | None = Query(None),
    auth_user: str = Depends(get_current_user),
):
    """List coaching sessions for a user, newest first."""
    require_self(auth_user, user_id)
    client = get_client()
    query = (
        client.table("coaching_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(50)
    )
    if account_id:
        query = query.eq("account_id", account_id)

    result = query.execute()
    return [CoachingSessionOut(**_session_to_dict(row)) for row in result.data]
