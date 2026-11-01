"""Beneficiaries (US-E13-10): typed fields, and adding or changing one in two steps (prepare, then confirm)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from routers.beneficiary_tools import (
    cancel_beneficiary,
    confirm_beneficiary,
    delete_beneficiary,
    get_beneficiary_list,
    get_beneficiary_template,
    prepare_beneficiary,
    prepare_beneficiary_change,
)
from routers.shares_tools import confirm_share_application
from tests.stepup_support import FakeApi
from utils import auth, transfers

TEMPLATE = {
    "accountTypeOptions": [
        {"id": 2, "code": "accountType.savings", "value": "Savings Account"},
        {"id": 1, "code": "accountType.loan", "value": "Loan Account"},
    ]
}
OFFICES = [{"id": 1, "name": "CENTRAL"}, {"id": 2, "name": "NORTE"}]
SAVED = {
    "id": 12,
    "name": "Maria",
    "officeName": "CENTRAL",
    "accountType": {"id": 2},
    "accountNumber": "000000042",
    "transferLimit": 100,
}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.delenv(transfers.TTL_ENV, raising=False)
    transfers.clear_prepared()
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    yield
    transfers.clear_prepared()


def bank(**overrides):
    # FakeApi treats a list as answers in turn, so a list answer is wrapped in another list
    routes = {
        "GET /self/beneficiaries/tpt/template": TEMPLATE,
        "GET /self/beneficiaries/tpt": [[SAVED]],
        "GET /self/offices": [OFFICES],
        "GET /self/clients": {"pageItems": [{"id": 5}]},
        "GET /self/clients/5/accounts": {
            "savingsAccounts": [{"id": 8, "currency": {"code": "MXN"}}],
            "loanAccounts": [{"id": 9, "currency": {"code": "MXN"}}],
        },
        "POST /self/beneficiaries/tpt": {"resourceId": 13},
        "PUT /self/beneficiaries/tpt/12": {"resourceId": 12},
    }
    routes.update(overrides)
    return FakeApi(**routes)


async def run(api, coro_factory, ctx=None):
    with (
        patch("routers.beneficiary_tools.make_request", api),
        patch("utils.stepup._elicitation_context", return_value=ctx),
    ):
        return await coro_factory()


async def prepare(api, **kwargs):
    args = {
        "name": "Maria",
        "account_number": "000000042",
        "office_name": "central",
        "account_type": "savings",
        "transfer_limit": 500,
    }
    args.update(kwargs)
    return await run(api, lambda: prepare_beneficiary(**args))


def form(action="accept", confirm=True):
    return SimpleNamespace(
        elicit=AsyncMock(return_value=SimpleNamespace(action=action, data=SimpleNamespace(confirm=confirm)))
    )


def posted(api):
    return [c["data"] for c in api.calls_to("POST", "/self/beneficiaries/tpt")]


# --- read and delete ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_and_list_are_read():
    api = bank()
    assert await run(api, get_beneficiary_template) == TEMPLATE
    assert await run(api, get_beneficiary_list) == [SAVED]


@pytest.mark.asyncio
async def test_delete_removes_the_beneficiary():
    api = FakeApi(**{"DELETE /self/beneficiaries/tpt/12": {"resourceId": 12}})
    assert await run(api, lambda: delete_beneficiary(12)) == {"resourceId": 12}


# --- prepare a new beneficiary --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_saves_nothing_and_returns_a_summary():
    api = bank()
    result = await prepare(api)

    assert result["prepared"] is True and result["executed"] is False and result["confirmation_id"]
    assert result["beneficiary"] == {
        "name": "Maria",
        "accountNumber": "000000042",
        "accountType": "savings",
        "officeName": "CENTRAL",
        "currency": "MXN",
        "transferLimit": 500,
    }
    assert "savings account 000000042 at CENTRAL, transfer limit 500 MXN" in result["message"]
    assert posted(api) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, text",
    [
        ({"name": "  "}, "name is required"),
        ({"name": "x" * 51}, "at most 50 characters"),
        ({"account_number": ""}, "account number is required"),
        ({"office_name": ""}, "office name is required"),
        ({"account_type": "checking"}, '"savings" or "loan"'),
        ({"transfer_limit": 0}, "greater than zero"),
        ({"transfer_limit": -5}, "greater than zero"),
        ({"currency": "pesos"}, "three-letter code"),
        ({"office_name": "Oeste"}, "no office called Oeste. Offices: CENTRAL, NORTE"),
    ],
)
async def test_prepare_refuses_bad_beneficiaries(kwargs, text):
    result = await prepare(bank(), **kwargs)
    assert result["error"] is True and text in result["message"]
    assert transfers._prepared == {}


@pytest.mark.asyncio
async def test_an_account_type_the_bank_does_not_offer_is_refused():
    api = bank(**{"GET /self/beneficiaries/tpt/template": {"accountTypeOptions": [{"id": 2}]}})
    result = await prepare(api, account_type="loan")
    assert result["error"] is True and "does not offer loan accounts" in result["message"]


@pytest.mark.asyncio
async def test_the_currency_is_asked_for_when_the_user_has_several():
    accounts = {
        "savingsAccounts": [{"currency": {"code": "MXN"}}],
        "loanAccounts": [{"currency": {"code": "USD"}}],
    }
    api = bank(**{"GET /self/clients/5/accounts": accounts})
    result = await prepare(api)
    assert result["error"] is True and "(the user's accounts use MXN, USD)" in result["message"]

    given = await prepare(api, currency="usd")
    assert given["beneficiary"]["currency"] == "USD"


@pytest.mark.asyncio
async def test_a_bank_error_is_passed_through():
    error = {"error": True, "status_code": 403, "message": "not allowed"}
    assert await prepare(bank(**{"GET /self/beneficiaries/tpt/template": error})) == error


# --- confirm a new beneficiary --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_saves_the_prepared_beneficiary_once():
    api = bank()
    prepared = await prepare(api, name="  Maria  ")
    done = await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]))
    again = await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]))

    assert done["executed"] is True and done["resourceId"] == 13
    assert posted(api) == [
        {
            "name": "Maria",
            "accountNumber": "000000042",
            "officeName": "CENTRAL",
            "accountType": 2,
            "paymentType": "SAME_BANK",
            "currency": "MXN",
            "locale": "en",
            "transferLimit": 500,
        }
    ]
    assert again["status_code"] == 404


@pytest.mark.asyncio
async def test_no_limit_sends_no_limit():
    api = bank()
    prepared = await prepare(api, transfer_limit=None, account_type="Loan")
    await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]))
    (data,) = posted(api)
    assert "transferLimit" not in data and data["accountType"] == 1
    assert "no transfer limit" in prepared["message"]


@pytest.mark.asyncio
async def test_with_a_form_the_person_confirms_first():
    api = bank()
    prepared = await prepare(api)
    ctx = form()
    done = await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]), ctx)

    assert done["executed"] is True
    assert "new beneficiary Maria" in ctx.elicit.call_args.kwargs["message"]
    assert ctx.elicit.call_args.kwargs["schema"] is transfers.ConfirmBeneficiaryForm


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ctx",
    [form("decline"), form("cancel"), form(confirm=False), SimpleNamespace(elicit=AsyncMock(side_effect=RuntimeError))],
)
async def test_declining_the_form_saves_nothing(ctx):
    api = bank()
    prepared = await prepare(api)
    result = await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]), ctx)

    assert result["cancelled"] is True and result["executed"] is False
    assert posted(api) == []


@pytest.mark.asyncio
async def test_cancel_drops_the_beneficiary():
    api = bank()
    prepared = await prepare(api)
    cancelled = await run(api, lambda: cancel_beneficiary(prepared["confirmation_id"]))
    after = await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]))

    assert cancelled["cancelled"] is True
    assert after["status_code"] == 404
    assert posted(api) == []


@pytest.mark.asyncio
async def test_a_beneficiary_id_does_not_confirm_a_share_application():
    api = bank()
    prepared = await prepare(api)
    with patch("routers.shares_tools.make_request", api):
        result = await confirm_share_application(prepared["confirmation_id"])
    assert result["status_code"] == 404
    done = await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]))
    assert done["executed"] is True


# --- change a beneficiary -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_change_is_shown_with_old_and_new_values_and_sent_once():
    api = bank()
    prepared = await run(api, lambda: prepare_beneficiary_change(12, name="Maria L", transfer_limit=900))

    assert prepared["prepared"] is True
    assert "name Maria -> Maria L, transfer limit 100 -> 900" in prepared["message"]
    assert api.calls_to("PUT", "/self/beneficiaries/tpt/12") == []

    done = await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]))
    assert done["executed"] is True
    # the bank refuses any other field on a change, the locale included
    assert [c["data"] for c in api.calls_to("PUT", "/self/beneficiaries/tpt/12")] == [
        {"name": "Maria L", "transferLimit": 900}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, sent",
    [
        # the bank empties a field that is not sent: a rename alone would remove the transfer limit
        ({"name": "Maria L"}, {"name": "Maria L", "transferLimit": 100}),
        # and a limit alone would empty the name
        ({"transfer_limit": 50}, {"name": "Maria", "transferLimit": 50}),
    ],
)
async def test_the_unchanged_field_is_sent_with_its_current_value(kwargs, sent):
    api = bank()
    prepared = await run(api, lambda: prepare_beneficiary_change(12, **kwargs))
    await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]))
    assert [c["data"] for c in api.calls_to("PUT", "/self/beneficiaries/tpt/12")] == [sent]


@pytest.mark.asyncio
async def test_a_rename_without_a_limit_sends_no_limit():
    api = bank(**{"GET /self/beneficiaries/tpt": [[{**SAVED, "transferLimit": None}]]})
    prepared = await run(api, lambda: prepare_beneficiary_change(12, name="Maria L"))
    await run(api, lambda: confirm_beneficiary(prepared["confirmation_id"]))
    assert [c["data"] for c in api.calls_to("PUT", "/self/beneficiaries/tpt/12")] == [{"name": "Maria L"}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, status, text",
    [
        ({}, 400, "new name, a new transfer limit, or both"),
        ({"name": " "}, 400, "name is required"),
        ({"transfer_limit": 0}, 400, "greater than zero"),
        ({"beneficiary_id": 99, "transfer_limit": 5}, 404, "not one of the user's beneficiaries"),
    ],
)
async def test_bad_changes_are_refused(kwargs, status, text):
    args = {"beneficiary_id": 12, **kwargs}
    result = await run(bank(), lambda: prepare_beneficiary_change(**args))
    assert result["status_code"] == status and text in result["message"]
    assert transfers._prepared == {}
