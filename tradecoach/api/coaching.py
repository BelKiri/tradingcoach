"""
AI coaching endpoint — full RAG-powered coaching analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from tradecoach.api.auth import get_current_user, require_self
from tradecoach.db.queries import get_client
from tradecoach.services.beta_quota import BetaQuotaError
from tradecoach.services.coaching import get_ai_coaching
from tradecoach.services.llm import LLMError
from tradecoach.utils.json_helpers import parse_json_field

router = APIRouter()
logger = logging.getLogger(__name__)

FEEDBACK_COMMENT_MAX_LEN = 2000


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


class RuleItem(BaseModel):
    action: str
    rationale: str
    savings_estimate_usd: int


class CoachingResponse(BaseModel):
    session_id: str
    ai_response: str
    metrics_snapshot: dict[str, Any]
    verdict: str | None
    rules: list[RuleItem] | None
    created_at: str
    usage: CoachingUsage


class CoachingSessionOut(BaseModel):
    id: str
    user_id: str
    account_id: str
    created_at: str
    ai_response: str
    metrics_snapshot: dict[str, Any] | None
    rules: list[RuleItem] | None
    recommendations: list[str] | None
    verdict: str | None
    main_problem: str | None
    new_trades_count: int | None
    model_used: str | None
    feedback_rating: int | None = None
    feedback_comment: str | None = None
    feedback_learned_new: bool | None = None
    feedback_submitted_at: str | None = None


class CoachingFeedbackRequest(BaseModel):
    feedback_rating: int | None = Field(default=None, ge=1, le=5)
    feedback_learned_new: bool | None = None
    feedback_comment: str | None = Field(default=None, max_length=FEEDBACK_COMMENT_MAX_LEN)

    @model_validator(mode="after")
    def at_least_one_field(self) -> CoachingFeedbackRequest:
        has_rating = self.feedback_rating is not None
        has_learned = self.feedback_learned_new is not None
        has_comment = bool(self.feedback_comment and self.feedback_comment.strip())
        if not (has_rating or has_learned or has_comment):
            raise ValueError("At least one feedback field is required")
        return self


class CoachingErrorResponse(BaseModel):
    error: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_to_dict(row: dict) -> dict:
    """Convert a DB row to a clean session dict."""
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "account_id": row["account_id"],
        "created_at": row.get("created_at", ""),
        "ai_response": row.get("ai_response", ""),
        "metrics_snapshot": parse_json_field(row.get("metrics_snapshot")),
        "rules": parse_json_field(row.get("rules")),
        "recommendations": parse_json_field(row.get("recommendations")),
        "verdict": row.get("verdict"),
        "main_problem": row.get("main_problem"),
        "new_trades_count": row.get("new_trades_count"),
        "model_used": row.get("model_used"),
        "feedback_rating": row.get("feedback_rating"),
        "feedback_comment": row.get("feedback_comment"),
        "feedback_learned_new": row.get("feedback_learned_new"),
        "feedback_submitted_at": row.get("feedback_submitted_at"),
    }


def _fetch_session_row(client: Any, session_id: str) -> dict | None:
    result = (
        client.table("coaching_sessions")
        .select("*")
        .eq("id", session_id)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]


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
    except BetaQuotaError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=str(e)) from e
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
    session = _fetch_session_row(client, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    require_self(auth_user, session["user_id"])
    return CoachingSessionOut(**_session_to_dict(session))


# ---------------------------------------------------------------------------
# POST /api/coaching/session/{session_id}/feedback
# ---------------------------------------------------------------------------

@router.post(
    "/session/{session_id}/feedback",
    response_model=CoachingSessionOut,
)
def submit_coaching_feedback(
    session_id: str,
    body: CoachingFeedbackRequest,
    auth_user: str = Depends(get_current_user),
):
    """Submit one-time feedback for a coaching session."""
    client = get_client()
    session = _fetch_session_row(client, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    require_self(auth_user, session["user_id"])

    if session.get("feedback_submitted_at"):
        raise HTTPException(status_code=409, detail="Feedback already submitted")

    submitted_at = datetime.now(timezone.utc).isoformat()
    update: dict[str, Any] = {"feedback_submitted_at": submitted_at}

    if body.feedback_rating is not None:
        update["feedback_rating"] = body.feedback_rating
    if body.feedback_learned_new is not None:
        update["feedback_learned_new"] = body.feedback_learned_new
    if body.feedback_comment is not None:
        comment = body.feedback_comment.strip()
        if comment:
            update["feedback_comment"] = comment

    result = (
        client.table("coaching_sessions")
        .update(update)
        .eq("id", session_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save feedback")

    return CoachingSessionOut(**_session_to_dict(result.data[0]))


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
