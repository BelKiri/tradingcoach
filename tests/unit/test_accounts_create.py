"""POST /api/accounts — create account including broker_timezone passthrough."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from tradecoach.db.models import Account, AccountCreate
from tradecoach.main import app


@pytest.mark.asyncio
async def test_create_account_passes_broker_timezone():
    captured: dict = {}

    def fake_create(client, data: AccountCreate) -> Account:
        captured["data"] = data
        return Account(
            id="new-acct-id",
            user_id=data.user_id,
            name=data.name,
            broker=data.broker,
            starting_balance=data.starting_balance,
            broker_timezone=data.broker_timezone,
        )

    with (
        patch("tradecoach.api.accounts.get_client"),
        patch("tradecoach.db.queries.get_user", return_value=MagicMock()),
        patch("tradecoach.api.accounts.create_account", side_effect=fake_create),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/accounts",
                json={
                    "user_id": "test-user-1",
                    "name": "My Account",
                    "broker": "Demo",
                    "starting_balance": 10000,
                    "broker_timezone": "UTC+3",
                },
            )

    assert resp.status_code == 200
    assert captured["data"].broker_timezone == "UTC+3"


@pytest.mark.asyncio
async def test_create_account_rejects_invalid_broker_timezone():
    with (
        patch("tradecoach.api.accounts.get_client"),
        patch("tradecoach.db.queries.get_user", return_value=MagicMock()),
        patch("tradecoach.api.accounts.create_account") as m_create,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/accounts",
                json={
                    "user_id": "test-user-1",
                    "name": "Bad TZ",
                    "broker_timezone": "not-a-timezone",
                },
            )

    assert resp.status_code == 422
    m_create.assert_not_called()


@pytest.mark.asyncio
async def test_create_account_accepts_iana_timezone():
    captured: dict = {}

    def fake_create(client, data: AccountCreate) -> Account:
        captured["data"] = data
        return Account(
            id="new-acct-id",
            user_id=data.user_id,
            name=data.name,
            broker=data.broker,
            starting_balance=data.starting_balance,
            broker_timezone=data.broker_timezone,
        )

    with (
        patch("tradecoach.api.accounts.get_client"),
        patch("tradecoach.db.queries.get_user", return_value=MagicMock()),
        patch("tradecoach.api.accounts.create_account", side_effect=fake_create),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/accounts",
                json={
                    "user_id": "test-user-1",
                    "name": "IANA TZ",
                    "broker_timezone": "Europe/Warsaw",
                },
            )

    assert resp.status_code == 200
    assert captured["data"].broker_timezone == "Europe/Warsaw"
