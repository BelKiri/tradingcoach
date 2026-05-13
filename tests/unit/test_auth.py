"""
Tests for API authentication and authorization.

Verifies:
  - 401 when no token provided
  - 403 when user_id doesn't match authenticated user
  - 200 when properly authenticated
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from tradecoach.api.auth import get_current_user
from tradecoach.main import app


@pytest.fixture()
def _no_auth_override():
    """Remove the autouse mock so we can test real auth rejection."""
    app.dependency_overrides.pop(get_current_user, None)
    yield
    # conftest autouse will re-apply on next test


# ===================================================================
# 401 — No token
# ===================================================================


class TestNoToken:
    """Requests without Authorization header should get 401."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_no_auth_override")
    async def test_dashboard_401(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/dashboard/user-1?account_id=acc-1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_no_auth_override")
    async def test_accounts_401(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/accounts/user-1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_no_auth_override")
    async def test_coaching_401(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/coaching/user-1",
                json={"account_id": "acc-1"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_no_auth_override")
    async def test_trades_401(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/trades/user-1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_no_auth_override")
    async def test_users_ensure_401(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/users/ensure",
                json={"user_id": "user-1"},
            )
        assert resp.status_code == 401


# ===================================================================
# 403 — Wrong user
# ===================================================================


class TestWrongUser:
    """Authenticated as user-A but requesting user-B's data → 403."""

    @pytest.mark.asyncio
    async def test_dashboard_wrong_user_403(self):
        # conftest mock returns "test-user-1", but URL says "other-user"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/dashboard/other-user?account_id=acc-1")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_accounts_wrong_user_403(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/accounts/other-user")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_coaching_wrong_user_403(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/coaching/other-user",
                json={"account_id": "acc-1"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_trades_wrong_user_403(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/trades/other-user")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_users_ensure_wrong_user_403(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/users/ensure",
                json={"user_id": "other-user"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_all_wrong_user_403(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.delete("/api/accounts/user/other-user/all")
        assert resp.status_code == 403


# ===================================================================
# 200 — Correct user
# ===================================================================


class TestCorrectUser:
    """Authenticated user accessing their own resources → 200."""

    @pytest.mark.asyncio
    async def test_dashboard_correct_user(self):
        mock_trades = []
        with (
            patch("tradecoach.api.dashboard.get_client"),
            patch("tradecoach.api.dashboard.get_trades", return_value=mock_trades),
            patch("tradecoach.api.dashboard.get_account", return_value=None),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/dashboard/test-user-1?account_id=acc-1")
        assert resp.status_code == 200
        assert resp.json()["total_trades"] == 0

    @pytest.mark.asyncio
    async def test_accounts_correct_user(self):
        with (
            patch("tradecoach.api.accounts.get_client"),
            patch("tradecoach.api.accounts.get_accounts", return_value=[]),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/accounts/test-user-1")
        assert resp.status_code == 200
        assert resp.json()["accounts"] == []

    @pytest.mark.asyncio
    async def test_trades_correct_user(self):
        with (
            patch("tradecoach.api.trades.get_client"),
            patch("tradecoach.api.trades.get_trades", return_value=[]),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/trades/test-user-1")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_users_ensure_correct_user(self):
        mock_user = MagicMock()
        mock_user.id = "test-user-1"
        with (
            patch("tradecoach.api.users.get_client"),
            patch("tradecoach.api.users.get_user", return_value=mock_user),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/api/users/ensure",
                    json={"user_id": "test-user-1"},
                )
        assert resp.status_code == 200


# ===================================================================
# Account ownership check
# ===================================================================


class TestAccountOwnership:
    """PATCH/DELETE on account requires ownership."""

    @pytest.mark.asyncio
    async def test_account_detail_wrong_owner_403(self):
        mock_acct = MagicMock()
        mock_acct.user_id = "other-user"
        with (
            patch("tradecoach.db.queries.get_client"),
            patch("tradecoach.db.queries.get_account", return_value=mock_acct),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/accounts/detail/acct-999")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_account_rename_wrong_owner_403(self):
        mock_acct = MagicMock()
        mock_acct.user_id = "other-user"
        with (
            patch("tradecoach.db.queries.get_client"),
            patch("tradecoach.db.queries.get_account", return_value=mock_acct),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.patch(
                    "/api/accounts/acct-999",
                    json={"name": "Hacked"},
                )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_account_delete_wrong_owner_403(self):
        mock_acct = MagicMock()
        mock_acct.user_id = "other-user"
        with (
            patch("tradecoach.db.queries.get_client"),
            patch("tradecoach.db.queries.get_account", return_value=mock_acct),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.delete("/api/accounts/acct-999")
        assert resp.status_code == 403
