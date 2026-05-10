"""
Shared test fixtures.

Auto-mocks the auth dependency so that existing tests continue to pass
without needing real Supabase JWT tokens.
"""

from __future__ import annotations

import pytest

from tradecoach.api.auth import get_current_user
from tradecoach.main import app

# A fixed test user ID used across all tests
TEST_USER_ID = "test-user-1"


@pytest.fixture(autouse=True)
def _mock_auth():
    """Override the auth dependency globally so all endpoints accept requests.

    Individual tests can override this by providing their own dependency.
    """

    def _fake_current_user() -> str:
        return TEST_USER_ID

    app.dependency_overrides[get_current_user] = _fake_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
