"""Guarantor tools (US-E13-14) on the endpoints of selfservice-plugin #213: typed fields, the plugin's rules
checked first, and a savings guarantee only after prepare + confirm."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from routers.guarantor_tools import (
    add_loan_guarantor,
    cancel_savings_guarantee,
    confirm_savings_guarantee,
    delete_loan_guarantor,
    get_guarantor_template,
    get_loan_guarantors,
    prepare_savings_guarantee,
    update_loan_guarantor,
)
from routers.shares_tools import confirm_share_application
from tests.stepup_support import FakeApi
from utils import auth, transfers

PENDING = {
    "id": 7,
    "accountNo": "000000007",
    "clientId": 5,
    "currency": {"code": "MXN"},
    "status": {"pendingApproval": True},
}
ACTIVE = {**PENDING, "status": {"pendingApproval": False, "active": True}}
EXTERNAL = {"id": 11, "guarantorType": {"id": 3}, "entityId": 0, "firstname": "Maria", "status": True}
CUSTOMER = {"id": 12, "guarantorType": {"id": 1}, "entityId": 9, "status": True}
REMOVED = {"id": 13, "guarantorType": {"id": 3}, "entityId": 0, "status": False}
ACCOUNTS = {
    "savingsAccounts": [
        {
            "id": 20,
            "accountNo": "000000020",
            "accountBalance": 5000.0,
            "currency": {"code": "MXN"},
            "status": {"active": True},
        },
        {
            "id": 21,
            "accountNo": "000000021",
            "accountBalance": 5000.0,
            "currency": {"code": "USD"},
            "status": {"active": True},
        },
        {
            "id": 22,
            "accountNo": "000000022",
            "accountBalance": 5000.0,
            "currency": {"code": "MXN"},
            "status": {"active": False},
        },
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
        "GET /self/loans/7": PENDING,
        # FakeApi treats a list as answers in turn, so the one list answer is wrapped
        "GET /self/loans/7/guarantors": [[EXTERNAL, CUSTOMER, REMOVED]],
        "GET /self/loans/7/guarantors/template": {"guarantorTypeOptions": []},
        "POST /self/loans/7/guarantors": {"loanId": 7, "resourceId": 30},
        "PUT /self/loans/7/guarantors/11": {"resourceId": 11, "changes": {"city": "Morelia"}},
        "PUT /self/loans/7/guarantors/12": {"resourceId": 12, "changes": {"city": "Morelia"}},
        "DELETE /self/loans/7/guarantors/11": {"resourceId": 11},
        "DELETE /self/loans/7/guarantors/11?guarantorFundingId=4": {"resourceId": 11},
        "GET /self/clients/5/accounts": ACCOUNTS,
    }
    routes.update(overrides)
    return FakeApi(**routes)


async def run(api, coro_factory, ctx=None):
    with (
        patch("routers.guarantor_tools.make_request", api),
        patch("routers.guarantor_tools.get_auth_header", return_value="Basic c2Vzc2lvbg=="),
        patch("utils.stepup._elicitation_context", return_value=ctx),
    ):
        return await coro_factory()


def writes(api):
    return [c for c in api.calls if c["method"] != "GET"]


def form(action="accept", confirm=True):
    return SimpleNamespace(
        elicit=AsyncMock(return_value=SimpleNamespace(action=action, data=SimpleNamespace(confirm=confirm)))
    )


# --- reads ----------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_and_list_read_the_plugin_endpoints():
    api = bank()
    await run(api, lambda: get_guarantor_template(7))
    listed = await run(api, lambda: get_loan_guarantors(7))
    assert [c["endpoint"] for c in api.calls] == ["/self/loans/7/guarantors/template", "/self/loans/7/guarantors"]
    assert isinstance(listed, list) and len(listed) == 3


# --- create ---------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_external_guarantor_is_sent_with_the_field_names_fineract_accepts():
    api = bank()
    result = await run(
        api,
        lambda: add_loan_guarantor(
            7,
            "external",
            first_name="Maria",
            last_name="Lopez",
            mobile_number="5551234567",
            city="Morelia",
            relationship_type_id=6,
        ),
    )
    assert result["resourceId"] == 30
    assert writes(api)[0]["data"] == {
        "guarantorTypeId": 3,
        "firstname": "Maria",
        "lastname": "Lopez",
        "mobileNumber": "5551234567",
        "city": "Morelia",
        "clientRelationshipTypeId": 6,
        "locale": "en",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"guarantor_type": "customer", "client_id": 9}, {"guarantorTypeId": 1, "entityId": 9, "locale": "en"}),
        ({"guarantor_type": "staff", "staff_id": 2}, {"guarantorTypeId": 2, "entityId": 2, "locale": "en"}),
    ],
)
async def test_customer_and_staff_guarantors_are_given_by_id(kwargs, expected):
    api = bank()
    await run(api, lambda: add_loan_guarantor(7, **kwargs))
    assert writes(api)[0]["data"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, message",
    [
        (
            {"guarantor_type": "external", "first_name": "Maria"},
            "An external guarantor needs first_name and last_name.",
        ),
        ({"guarantor_type": "customer"}, "A customer guarantor needs the guarantor's client_id."),
        ({"guarantor_type": "staff"}, "A staff guarantor needs the staff_id."),
    ],
)
async def test_missing_details_are_refused_without_calling_the_bank(kwargs, message):
    api = bank()
    result = await run(api, lambda: add_loan_guarantor(7, **kwargs))
    assert result["status_code"] == 400 and result["message"] == message
    assert api.calls == []


@pytest.mark.asyncio
async def test_guarantors_cannot_be_added_once_the_loan_is_approved():
    api = bank(**{"GET /self/loans/7": ACTIVE})
    result = await run(api, lambda: add_loan_guarantor(7, "external", first_name="Maria", last_name="Lopez"))
    assert result["status_code"] == 400
    assert "no longer waiting for approval" in result["message"]
    assert writes(api) == []


# --- update and delete ----------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_sends_only_the_given_fields_with_the_guarantor_type():
    api = bank()
    result = await run(api, lambda: update_loan_guarantor(7, 11, city="Morelia"))
    assert result["changes"] == {"city": "Morelia"}
    assert writes(api)[0]["data"] == {"city": "Morelia", "guarantorTypeId": 3, "locale": "en"}


@pytest.mark.asyncio
async def test_update_of_a_customer_guarantor_keeps_its_client():
    api = bank()
    await run(api, lambda: update_loan_guarantor(7, 12, city="Morelia"))
    assert writes(api)[0]["data"] == {"city": "Morelia", "guarantorTypeId": 1, "entityId": 9, "locale": "en"}


@pytest.mark.asyncio
@pytest.mark.parametrize("guarantor_id", [13, 99])
async def test_update_of_a_removed_or_unknown_guarantor_is_refused(guarantor_id):
    api = bank()
    result = await run(api, lambda: update_loan_guarantor(7, guarantor_id, city="Morelia"))
    assert result["status_code"] == 404
    assert writes(api) == []


@pytest.mark.asyncio
async def test_update_without_fields_is_refused():
    api = bank()
    result = await run(api, lambda: update_loan_guarantor(7, 11))
    assert result["status_code"] == 400
    assert api.calls == []


@pytest.mark.asyncio
async def test_delete_removes_a_guarantor_or_one_of_its_funds():
    api = bank()
    await run(api, lambda: delete_loan_guarantor(7, 11))
    await run(api, lambda: delete_loan_guarantor(7, 11, guarantor_funding_id=4))
    assert [c["endpoint"] for c in writes(api)] == [
        "/self/loans/7/guarantors/11",
        "/self/loans/7/guarantors/11?guarantorFundingId=4",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool",
    [lambda: update_loan_guarantor(7, 11, city="Morelia"), lambda: delete_loan_guarantor(7, 11)],
)
async def test_update_and_delete_only_while_waiting_for_approval(tool):
    api = bank(**{"GET /self/loans/7": ACTIVE})
    result = await run(api, tool)
    assert result["status_code"] == 400
    assert writes(api) == []


# --- savings guarantee: prepare + confirm ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_checks_the_users_own_savings_and_submits_nothing():
    api = bank()
    result = await run(api, lambda: prepare_savings_guarantee(7, 20, 1500.0))
    assert result["prepared"] is True and result["executed"] is False
    assert result["guarantee"] == {
        "loanId": 7,
        "loanAccount": "000000007",
        "savingsAccount": "000000020",
        "amount": 1500.0,
        "currency": "MXN",
    }
    assert "blocked" in result["message"]
    assert writes(api) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "savings_id, amount, message",
    [
        (99, 100.0, "Savings account 99 is not one of the user's accounts."),
        (21, 100.0, "The savings account must be in MXN, the loan's currency."),
        (22, 100.0, "Savings account 000000022 is not active."),
        (20, 9000.0, "The savings account has only 5000.0 MXN."),
        (20, 0.0, "The amount must be greater than zero."),
    ],
)
async def test_guarantees_the_plugin_or_the_bank_would_refuse_are_stopped_early(savings_id, amount, message):
    api = bank()
    result = await run(api, lambda: prepare_savings_guarantee(7, savings_id, amount))
    assert result["status_code"] == 400 and result["message"] == message
    assert transfers._prepared == {}


@pytest.mark.asyncio
async def test_a_guarantee_cannot_be_prepared_for_an_approved_loan():
    api = bank(**{"GET /self/loans/7": ACTIVE})
    result = await run(api, lambda: prepare_savings_guarantee(7, 20, 100.0))
    assert result["status_code"] == 400
    assert transfers._prepared == {}


@pytest.mark.asyncio
async def test_confirm_adds_the_prepared_guarantee_once():
    api = bank()
    prepared = await run(api, lambda: prepare_savings_guarantee(7, 20, 1500.0))
    result = await run(api, lambda: confirm_savings_guarantee(prepared["confirmation_id"]))
    assert result["executed"] is True and result["resourceId"] == 30
    assert writes(api)[0]["data"] == {
        "guarantorTypeId": 1,
        "entityId": 5,
        "savingsId": 20,
        "amount": 1500.0,
        "locale": "en",
    }
    again = await run(api, lambda: confirm_savings_guarantee(prepared["confirmation_id"]))
    assert again["status_code"] == 404
    assert len(writes(api)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ctx",
    [
        form(action="decline"),
        form(confirm=False),
        SimpleNamespace(elicit=AsyncMock(side_effect=RuntimeError("client closed the form"))),
    ],
)
async def test_nothing_is_held_unless_the_person_confirms_in_the_form(ctx):
    api = bank()
    prepared = await run(api, lambda: prepare_savings_guarantee(7, 20, 1500.0))
    result = await run(api, lambda: confirm_savings_guarantee(prepared["confirmation_id"]), ctx=ctx)
    assert result["cancelled"] is True and result["executed"] is False
    assert writes(api) == []


@pytest.mark.asyncio
async def test_cancel_drops_the_prepared_guarantee():
    api = bank()
    prepared = await run(api, lambda: prepare_savings_guarantee(7, 20, 1500.0))
    assert (await run(api, lambda: cancel_savings_guarantee(prepared["confirmation_id"])))["cancelled"] is True
    result = await run(api, lambda: confirm_savings_guarantee(prepared["confirmation_id"]))
    assert result["status_code"] == 404
    assert writes(api) == []


@pytest.mark.asyncio
async def test_a_guarantee_confirmation_id_cannot_confirm_another_kind_of_operation():
    api = bank()
    prepared = await run(api, lambda: prepare_savings_guarantee(7, 20, 1500.0))
    with patch("utils.stepup._elicitation_context", return_value=None):
        other = await confirm_share_application(prepared["confirmation_id"])
    assert other["status_code"] == 404
    assert (await run(api, lambda: confirm_savings_guarantee(prepared["confirmation_id"])))["executed"] is True
