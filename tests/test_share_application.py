"""Share accounts (US-E13-01): read tools, and applying for shares in two steps (prepare, then confirm)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from routers.shares_tools import (
    cancel_share_application,
    confirm_share_application,
    get_share_account,
    get_share_account_template,
    prepare_share_application,
)
from routers.transfer_tools import confirm_transfer
from tests.stepup_support import FakeApi
from utils import auth, transfers

PRODUCT = {
    "id": 3,
    "name": "Member Shares",
    "currency": {"code": "USD"},
    "unitPrice": 10.0,
    "minimumShares": 2,
    "maximumShares": 100,
}
ACCOUNTS = {
    "savingsAccounts": [
        {"id": 8, "accountNo": "000000008", "currency": {"code": "USD"}, "status": {"active": True}},
        {"id": 9, "accountNo": "000000009", "currency": {"code": "CRC"}, "status": {"active": True}},
        {"id": 10, "accountNo": "000000010", "currency": {"code": "USD"}, "status": {"active": False}},
    ]
}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.delenv(transfers.TTL_ENV, raising=False)
    transfers.clear_prepared()
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    yield
    transfers.clear_prepared()


def bank(**overrides):
    routes = {
        "GET /self/shareaccounts/template?clientId=5&productId=3": {"clientId": 5, "productOptions": [PRODUCT]},
        "GET /self/clients/5/accounts": ACCOUNTS,
        "POST /self/shareaccounts": {"resourceId": 41},
    }
    routes.update(overrides)
    return FakeApi(**routes)


async def run(api, coro_factory, ctx=None):
    with (
        patch("routers.shares_tools.make_request", api),
        patch("utils.stepup._elicitation_context", return_value=ctx),
    ):
        return await coro_factory()


async def prepare(api, **kwargs):
    args = {"client_id": 5, "product_id": 3, "requested_shares": 4, "savings_account_id": 8}
    args.update(kwargs)
    return await run(api, lambda: prepare_share_application(**args))


def form(action="accept", confirm=True):
    return SimpleNamespace(
        elicit=AsyncMock(return_value=SimpleNamespace(action=action, data=SimpleNamespace(confirm=confirm)))
    )


# --- read tools -----------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_id, path",
    [(None, "/self/shareaccounts/template?clientId=5"), (3, "/self/shareaccounts/template?clientId=5&productId=3")],
)
async def test_the_template_asks_for_the_client_and_optionally_the_product(product_id, path):
    api = FakeApi(**{f"GET {path}": {"productOptions": []}})
    assert await run(api, lambda: get_share_account_template(5, product_id)) == {"productOptions": []}
    assert [c["endpoint"] for c in api.calls] == [path]


@pytest.mark.asyncio
async def test_a_share_account_is_read_by_id():
    api = FakeApi(**{"GET /self/shareaccounts/41": {"id": 41}})
    assert await run(api, lambda: get_share_account(41)) == {"id": 41}


# --- prepare --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_submits_nothing_and_returns_a_summary():
    api = bank()
    result = await prepare(api)

    assert result["prepared"] is True and result["executed"] is False and result["confirmation_id"]
    assert result["application"] == {
        "product": "Member Shares",
        "productId": 3,
        "requestedShares": 4,
        "currency": "USD",
        "savingsAccount": "000000008",
        "unitPrice": 10.0,
        "total": 40.0,
    }
    assert api.calls_to("POST", "/self/shareaccounts") == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, text",
    [
        ({"requested_shares": 0}, "greater than zero"),
        ({"requested_shares": 1}, "at least 2"),
        ({"requested_shares": 101}, "at most 100"),
        ({"savings_account_id": 77}, "not one of the client's accounts"),
        ({"savings_account_id": 10}, "not active"),
        ({"savings_account_id": 9}, "must be in USD"),
    ],
)
async def test_prepare_refuses_bad_applications(kwargs, text):
    result = await prepare(bank(), **kwargs)
    assert result["error"] is True and text in result["message"]
    assert transfers._prepared == {}


@pytest.mark.asyncio
async def test_an_unknown_product_is_refused():
    api = bank(**{"GET /self/shareaccounts/template?clientId=5&productId=3": {"productOptions": []}})
    result = await prepare(api)
    assert result["status_code"] == 404


@pytest.mark.asyncio
async def test_a_bank_error_is_passed_through():
    error = {"error": True, "status_code": 403, "message": "not your client"}
    api = bank(**{"GET /self/shareaccounts/template?clientId=5&productId=3": error})
    assert await prepare(api) == error


# --- confirm --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_submits_the_prepared_application_once():
    api = bank()
    prepared = await prepare(api)
    done = await run(api, lambda: confirm_share_application(prepared["confirmation_id"]))
    again = await run(api, lambda: confirm_share_application(prepared["confirmation_id"]))

    assert done["executed"] is True and done["resourceId"] == 41
    (sent,) = api.calls_to("POST", "/self/shareaccounts")
    data = sent["data"]
    assert {k: data[k] for k in ("clientId", "productId", "requestedShares", "savingsAccountId")} == {
        "clientId": 5,
        "productId": 3,
        "requestedShares": 4,
        "savingsAccountId": 8,
    }
    assert data["submittedDate"] == data["applicationDate"]
    assert (data["dateFormat"], data["locale"]) == ("dd MMMM yyyy", "en")
    assert again["status_code"] == 404


@pytest.mark.asyncio
async def test_a_share_application_id_does_not_confirm_a_transfer():
    api = bank()
    prepared = await prepare(api)
    with patch("routers.transfer_tools.make_request", api):
        result = await confirm_transfer(prepared["confirmation_id"])
    assert result["status_code"] == 404
    # and it is still there for the right tool
    done = await run(api, lambda: confirm_share_application(prepared["confirmation_id"]))
    assert done["executed"] is True


@pytest.mark.asyncio
async def test_with_a_form_the_person_confirms_first():
    api = bank()
    prepared = await prepare(api)
    ctx = form()
    done = await run(api, lambda: confirm_share_application(prepared["confirmation_id"]), ctx)

    assert done["executed"] is True
    assert "4 shares of Member Shares (40.0 USD)" in ctx.elicit.call_args.kwargs["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ctx",
    [form("decline"), form("cancel"), form(confirm=False), SimpleNamespace(elicit=AsyncMock(side_effect=RuntimeError))],
)
async def test_declining_the_form_submits_nothing(ctx):
    api = bank()
    prepared = await prepare(api)
    result = await run(api, lambda: confirm_share_application(prepared["confirmation_id"]), ctx)

    assert result["cancelled"] is True and result["executed"] is False
    assert api.calls_to("POST", "/self/shareaccounts") == []


@pytest.mark.asyncio
async def test_cancel_drops_the_application():
    api = bank()
    prepared = await prepare(api)
    cancelled = await run(api, lambda: cancel_share_application(prepared["confirmation_id"]))
    after = await run(api, lambda: confirm_share_application(prepared["confirmation_id"]))

    assert cancelled["cancelled"] is True
    assert after["status_code"] == 404
    assert api.calls_to("POST", "/self/shareaccounts") == []
