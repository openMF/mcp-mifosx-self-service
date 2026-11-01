"""Savings applications (US-E13-11): checked against the bank's template, then submitted once after confirmation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from routers.savings_tools import (
    cancel_savings_application,
    confirm_savings_application,
    prepare_savings_application,
    update_savings_application,
)
from routers.transfer_tools import confirm_transfer
from tests.stepup_support import FakeApi
from utils import auth, transfers

TEMPLATE = {
    "clientId": 5,
    "clientName": "ANA MORA",
    "productOptions": [{"id": 1, "name": "MONEDERO"}, {"id": 3, "name": "WALLET"}],
}
DETAIL = {
    **TEMPLATE,
    "currency": {"code": "MXN"},
    "nominalAnnualInterestRate": 4.5,
    "minRequiredOpeningBalance": 100.0,
    "lockinPeriodFrequency": 1,
    "lockinPeriodFrequencyType": {"id": 2, "value": "Months"},
    "charges": [{"name": "Account fee"}],
    "fieldOfficerOptions": [{"id": 9, "displayName": "Officer"}],
}
PENDING = {"id": 40, "clientId": 5, "status": {"submittedAndPendingApproval": True}}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.delenv(transfers.TTL_ENV, raising=False)
    transfers.clear_prepared()
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    yield
    transfers.clear_prepared()


def bank(**overrides):
    routes = {
        "GET /self/savingsaccounts/template?clientId=5": TEMPLATE,
        "GET /self/savingsaccounts/template?clientId=5&productId=1": DETAIL,
        "GET /self/savingsaccounts/template?clientId=5&productId=3": {**DETAIL, "currency": {"code": "USD"}},
        "POST /self/savingsaccounts": {"resourceId": 40, "savingsId": 40},
        "GET /self/savingsaccounts/40": PENDING,
        "PUT /self/savingsaccounts/40": {"resourceId": 40, "changes": {}},
    }
    routes.update(overrides)
    return FakeApi(**routes)


async def run(api, coro_factory, ctx=None):
    with (
        patch("routers.savings_tools.make_request", api),
        patch("utils.stepup._elicitation_context", return_value=ctx),
    ):
        return await coro_factory()


async def prepare(api, **kwargs):
    args = {"client_id": 5, "product_id": 1}
    args.update(kwargs)
    return await run(api, lambda: prepare_savings_application(**args))


def form(action="accept", confirm=True):
    answer = SimpleNamespace(action=action, data=SimpleNamespace(confirm=confirm))
    return SimpleNamespace(elicit=AsyncMock(return_value=answer))


# --- prepare --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_submits_nothing_and_shows_the_product_terms():
    api = bank()
    result = await prepare(api)

    assert result["prepared"] is True and result["executed"] is False and result["confirmation_id"]
    assert result["application"] == {
        "product": "MONEDERO",
        "productId": 1,
        "client": "ANA MORA",
        "currency": "MXN",
        "nominalAnnualInterestRate": 4.5,
        "minRequiredOpeningBalance": 100.0,
        "lockinPeriodFrequency": 1,
        "lockinPeriodFrequencyType": "Months",
        "charges": ["Account fee"],
    }
    assert api.calls_to("POST", "/self/savingsaccounts") == []


@pytest.mark.asyncio
async def test_a_product_the_bank_does_not_offer_is_refused_with_the_offered_ones():
    result = await prepare(bank(), product_id=2)
    assert result["error"] is True
    assert "1 MONEDERO, 3 WALLET" in result["message"]
    assert transfers._prepared == {}


@pytest.mark.asyncio
async def test_an_unknown_field_officer_is_refused():
    result = await prepare(bank(), field_officer_id=77)
    assert result["error"] is True and "Field officer 77" in result["message"]


@pytest.mark.asyncio
async def test_a_bank_error_on_the_template_is_passed_through():
    error = {"error": True, "status_code": 404, "message": "Client with identifier 5 does not exist"}
    assert await prepare(bank(**{"GET /self/savingsaccounts/template?clientId=5": error})) == error


# --- confirm --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_submits_the_prepared_application_once():
    api = bank()
    prepared = await prepare(api, field_officer_id=9, external_id=" my-ref ")
    done = await run(api, lambda: confirm_savings_application(prepared["confirmation_id"]))
    again = await run(api, lambda: confirm_savings_application(prepared["confirmation_id"]))

    assert done["executed"] is True and done["savingsId"] == 40
    (sent,) = api.calls_to("POST", "/self/savingsaccounts")
    data = sent["data"]
    assert {k: data[k] for k in ("clientId", "productId", "fieldOfficerId", "externalId")} == {
        "clientId": 5,
        "productId": 1,
        "fieldOfficerId": 9,
        "externalId": "my-ref",
    }
    assert (data["dateFormat"], data["locale"]) == ("dd MMMM yyyy", "en") and data["submittedOnDate"]
    assert again["status_code"] == 404


@pytest.mark.asyncio
async def test_a_savings_id_does_not_confirm_a_transfer():
    api = bank()
    prepared = await prepare(api)
    with patch("routers.transfer_tools.make_request", api):
        assert (await confirm_transfer(prepared["confirmation_id"]))["status_code"] == 404


@pytest.mark.asyncio
async def test_with_a_form_the_person_confirms_first():
    api = bank()
    prepared = await prepare(api)
    ctx = form()
    done = await run(api, lambda: confirm_savings_application(prepared["confirmation_id"]), ctx)

    assert done["executed"] is True
    assert "MONEDERO savings account (MXN) for ANA MORA" in ctx.elicit.call_args.kwargs["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ctx",
    [form("decline"), form("cancel"), form(confirm=False), SimpleNamespace(elicit=AsyncMock(side_effect=RuntimeError))],
)
async def test_declining_or_a_failing_form_submits_nothing(ctx):
    api = bank()
    prepared = await prepare(api)
    result = await run(api, lambda: confirm_savings_application(prepared["confirmation_id"]), ctx)

    assert result["cancelled"] is True and result["executed"] is False
    assert api.calls_to("POST", "/self/savingsaccounts") == []


@pytest.mark.asyncio
async def test_cancel_drops_the_application():
    api = bank()
    prepared = await prepare(api)
    assert (await run(api, lambda: cancel_savings_application(prepared["confirmation_id"])))["cancelled"] is True
    assert (await run(api, lambda: confirm_savings_application(prepared["confirmation_id"])))["status_code"] == 404


# --- update ---------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_keeps_the_account_with_its_own_client():
    api = bank()
    result = await run(api, lambda: update_savings_application(40, product_id=3, external_id="new-ref"))

    assert result["resourceId"] == 40
    (sent,) = api.calls_to("PUT", "/self/savingsaccounts/40")
    assert sent["data"]["clientId"] == 5  # taken from the account, not from the caller
    assert sent["data"]["productId"] == 3 and sent["data"]["externalId"] == "new-ref"


@pytest.mark.asyncio
async def test_update_refuses_an_approved_account():
    api = bank(**{"GET /self/savingsaccounts/40": {**PENDING, "status": {"submittedAndPendingApproval": False}}})
    result = await run(api, lambda: update_savings_application(40, external_id="x"))
    assert result["error"] is True and "waiting for approval" in result["message"]
    assert api.calls_to("PUT", "/self/savingsaccounts/40") == []


@pytest.mark.asyncio
async def test_update_refuses_a_product_the_bank_does_not_offer():
    api = bank()
    result = await run(api, lambda: update_savings_application(40, product_id=2))
    assert result["error"] is True and api.calls_to("PUT", "/self/savingsaccounts/40") == []


@pytest.mark.asyncio
async def test_update_needs_something_to_change():
    api = bank()
    result = await run(api, lambda: update_savings_application(40))
    assert result["error"] is True and api.calls == []
