"""GET /api/analysis — emotion analysis endpoint."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.conftest import TEST_USER_ID
from tradecoach.main import app


def test_get_emotion_analysis_default_broker_timezone_fallback():
    """Regression test for the DEFAULT_BROKER_TIMEZONE fallback branch in get_emotion_analysis. Ensures the endpoint can be invoked without a broker_timezone query param without raising NameError on the fallback expression."""
    with (
        patch("tradecoach.api.analysis.get_client"),
        patch("tradecoach.api.analysis.get_trades", return_value=[]),
        patch("tradecoach.api.analysis.get_emotions", return_value=[]),
    ):
        client = TestClient(app)
        resp = client.get(f"/api/analysis/{TEST_USER_ID}/emotions")

    assert resp.status_code == 200
