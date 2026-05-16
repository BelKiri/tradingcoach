"""Beta quota enforcement and quota read endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from tradecoach.main import app
from tradecoach.services.beta_quota import (
    ACCOUNT_LIMIT_DETAIL,
    COACHING_LIMIT_DETAIL,
    UPLOAD_LIMIT_DETAIL,
    BetaQuotaError,
    assert_can_create_account,
    assert_can_generate_coaching,
    assert_can_upload_file,
    build_user_quota,
    increment_coaching_sessions_used,
)


def _user_row(*, exempt: bool = False, used: int = 0) -> dict:
    return {"is_beta_exempt": exempt, "coaching_sessions_used": used}


def test_assert_can_create_account_blocks_at_three():
    client = MagicMock()
    with (
        patch(
            "tradecoach.services.beta_quota.get_user_beta_fields",
            return_value=(False, 0),
        ),
        patch(
            "tradecoach.services.beta_quota.get_accounts",
            return_value=[MagicMock(), MagicMock(), MagicMock()],
        ),
    ):
        with pytest.raises(BetaQuotaError, match="Account limit"):
            assert_can_create_account(client, "user-1")


def test_assert_can_create_account_exempt_bypass():
    client = MagicMock()
    with (
        patch(
            "tradecoach.services.beta_quota.get_user_beta_fields",
            return_value=(True, 0),
        ),
        patch(
            "tradecoach.services.beta_quota.get_accounts",
            return_value=[MagicMock()] * 5,
        ),
    ):
        assert_can_create_account(client, "user-1")


def test_assert_can_upload_file_blocks_when_trades_exist():
    client = MagicMock()
    with (
        patch(
            "tradecoach.services.beta_quota.get_user_beta_fields",
            return_value=(False, 0),
        ),
        patch(
            "tradecoach.services.beta_quota.account_has_any_trades",
            return_value=True,
        ),
    ):
        with pytest.raises(BetaQuotaError, match="File upload per account"):
            assert_can_upload_file(client, "user-1", "acct-1")


def test_assert_can_upload_file_exempt_bypass():
    client = MagicMock()
    with patch(
        "tradecoach.services.beta_quota.get_user_beta_fields",
        return_value=(True, 0),
    ):
        assert_can_upload_file(client, "user-1", "acct-1")


def test_assert_can_generate_coaching_lifetime_cap():
    client = MagicMock()
    with patch(
        "tradecoach.services.beta_quota.get_user_beta_fields",
        return_value=(False, 3),
    ):
        with pytest.raises(BetaQuotaError, match="All AI Coach sessions"):
            assert_can_generate_coaching(client, "user-1", "acct-1")


def test_assert_can_generate_coaching_per_account():
    client = MagicMock()
    with (
        patch(
            "tradecoach.services.beta_quota.get_user_beta_fields",
            return_value=(False, 1),
        ),
        patch(
            "tradecoach.services.beta_quota.account_has_coaching_session",
            return_value=True,
        ),
    ):
        with pytest.raises(BetaQuotaError, match=COACHING_LIMIT_DETAIL[:20]):
            assert_can_generate_coaching(client, "user-1", "acct-1")


def test_increment_coaching_sessions_used_cas_success():
    client = MagicMock()
    select_chain = MagicMock()
    select_chain.select.return_value = select_chain
    select_chain.eq.return_value = select_chain
    select_chain.execute.return_value = MagicMock(data=[{"coaching_sessions_used": 1}])

    update_chain = MagicMock()
    update_chain.update.return_value = update_chain
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = MagicMock(data=[{"coaching_sessions_used": 2}])

    client.table.return_value = select_chain
    # Second table() call for update — side_effect
    client.table.side_effect = [select_chain, update_chain]

    with patch(
        "tradecoach.services.beta_quota.get_user_beta_fields",
        return_value=(False, 1),
    ):
        assert increment_coaching_sessions_used(client, "user-1") is True


def test_build_user_quota_shape():
    client = MagicMock()
    acct = MagicMock(id="acct-1")
    with (
        patch(
            "tradecoach.services.beta_quota.get_user_beta_fields",
            return_value=(False, 2),
        ),
        patch("tradecoach.services.beta_quota.get_accounts", return_value=[acct]),
        patch(
            "tradecoach.services.beta_quota.account_has_any_trades",
            return_value=True,
        ),
        patch(
            "tradecoach.services.beta_quota.account_has_coaching_session",
            return_value=False,
        ),
    ):
        payload = build_user_quota(client, "user-1")

    assert payload["is_beta_exempt"] is False
    assert payload["coaching_sessions_used"] == 2
    assert payload["accounts"] == [
        {"id": "acct-1", "upload_used": True, "coaching_used": False},
    ]


@pytest.mark.asyncio
async def test_create_account_returns_403_at_limit():
    with (
        patch("tradecoach.api.accounts.get_client"),
        patch("tradecoach.db.queries.get_user", return_value=MagicMock()),
        patch(
            "tradecoach.api.accounts.assert_can_create_account",
            side_effect=BetaQuotaError(ACCOUNT_LIMIT_DETAIL),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/accounts",
                json={"user_id": "test-user-1", "name": "Fourth"},
            )

    assert resp.status_code == 403
    assert ACCOUNT_LIMIT_DETAIL in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_returns_403_when_account_has_trades():
    sample_trade = {
        "symbol": "EURUSD",
        "direction": "buy",
        "lot": 0.1,
        "opened_at": "2024-01-01T10:00:00",
        "closed_at": "2024-01-01T11:00:00",
    }
    with (
        patch("tradecoach.api.upload.get_client"),
        patch(
            "tradecoach.api.upload.assert_can_upload_file",
            side_effect=BetaQuotaError(UPLOAD_LIMIT_DETAIL),
        ),
        patch("tradecoach.api.upload.parse_mt4_csv", return_value=[sample_trade]),
        patch("tradecoach.api.upload.find_existing_trade_keys", return_value=set()),
        patch("tradecoach.api.upload.insert_trades", return_value=[]),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/upload/test-user-1",
                data={"account_id": "acct-1"},
                files={"file": ("t.csv", b"ticket,symbol,direction,lot\n", "text/csv")},
            )

    assert resp.status_code == 403
    assert "File upload per account" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_quota_endpoint_returns_payload():
    mock_payload = {
        "is_beta_exempt": False,
        "coaching_sessions_used": 1,
        "accounts": [{"id": "a1", "upload_used": False, "coaching_used": True}],
    }
    with (
        patch("tradecoach.api.users.get_client"),
        patch(
            "tradecoach.api.users.build_user_quota",
            return_value=mock_payload,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/users/test-user-1/quota")

    assert resp.status_code == 200
    assert resp.json() == mock_payload
