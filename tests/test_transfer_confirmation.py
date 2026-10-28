"""Two-step transfers (US-E13-07): prepare_transfer moves no money, confirm_transfer runs it once."""

import time
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from routers.stepup_tools import verify_step_up
from routers.transfer_tools import cancel_transfer, confirm_transfer, prepare_transfer
from tests.stepup_support import TPT_SENT, bank_routes, required
from utils import auth, stepup, transfers
from zoneinfo import ZoneInfo


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    for name in (transfers.MAX_AMOUNT_ENV, transfers.TTL_ENV, transfers.TIMEZONE_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("MIFOS_STEP_UP_ALLOW_CHAT_OTP", raising=False)
    transfers.clear_prepared()
    stepup.clear_pending()
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    yield
    transfers.clear_prepared()
    stepup.clear_pending()


def bank(**overrides):
    routes = {
        "POST /self/accounttransfers": {"resourceId": 77},
        "POST /self/accounttransfers?type=tpt": {"resourceId": 99},
    }
    routes.update(overrides)
    return bank_routes(**routes)


def patched(api, ctx=None):
    """Fake the bank, and the client's form (None = the client cannot show one)."""
    return (
        patch("routers.transfer_tools.make_request", api),
        patch("utils.stepup.make_request", api),
        patch("utils.stepup._elicitation_context", return_value=ctx),
    )


async def run(api, coro_factory, ctx=None):
    first, second, third = patched(api, ctx)
    with first, second, third:
        return await coro_factory()


def form(*answers):
    return SimpleNamespace(elicit=AsyncMock(side_effect=list(answers)))


def answer(action="accept", confirm=True):
    return SimpleNamespace(action=action, data=SimpleNamespace(confirm=confirm))


async def prepare_tpt(api, **kwargs):
    args = {"from_account_id": 11, "to_account_id": 22, "amount": 100.5, "description": "rent", "third_party": True}
    args.update(kwargs)
    return await run(api, lambda: prepare_transfer(**args))


# --- prepare --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_moves_no_money_and_returns_a_summary_and_an_id():
    api = bank()
    result = await prepare_tpt(api)

    assert result["prepared"] is True and result["executed"] is False
    assert result["confirmation_id"]
    assert result["transfer"]["from"]["accountNo"] == "000000011"
    assert result["transfer"]["to"] == {
        "accountId": 22,
        "accountNo": "000000022",
        "accountType": "Savings Account",
        "clientName": "LUIS MORA",
    }
    assert result["transfer"]["amount"] == 100.5
    assert result["transfer"]["currency"] == "USD"
    assert result["transfer"]["fee"] == "No transfer fee."
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []
    assert api.calls_to("POST", "/self/accounttransfers") == []


@pytest.mark.asyncio
async def test_prepare_reports_the_savings_withdrawal_fee_on_transfers():
    api = bank(
        **{
            "GET /self/savingsaccounts/11": {
                "currency": {"code": "USD"},
                "summary": {"availableBalance": 500.0},
                "withdrawalFeeForTransfers": True,
            }
        }
    )
    result = await prepare_tpt(api)
    assert "withdrawal fee" in result["transfer"]["fee"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, text",
    [
        ({"amount": 0}, "greater than zero"),
        ({"amount": -5}, "greater than zero"),
        ({"amount": float("nan")}, "greater than zero"),
        ({"description": "   "}, "description is required"),
        ({"description": "x" * 201}, "at most 200"),
        ({"to_account_id": 11}, "must be different"),
        ({"to_account_id": 44}, "saved beneficiaries"),
        ({"from_account_id": 44}, "source account"),
        ({"amount": 900}, "available balance"),
    ],
)
async def test_prepare_refuses_bad_requests_and_remembers_nothing(kwargs, text):
    api = bank()
    result = await prepare_tpt(api, **kwargs)
    assert result["error"] is True and result["executed"] is False
    assert text in result["message"]
    assert transfers._prepared == {}


@pytest.mark.asyncio
async def test_a_beneficiary_is_not_accepted_as_an_own_account_transfer():
    result = await prepare_tpt(bank(), third_party=False)
    assert result["error"] is True
    assert "your own accounts" in result["message"]


@pytest.mark.asyncio
async def test_amounts_above_the_operator_limit_are_refused(monkeypatch):
    monkeypatch.setenv(transfers.MAX_AMOUNT_ENV, "100")
    api = bank()
    result = await prepare_tpt(api)

    assert result["error"] is True and result["limit_exceeded"] is True
    assert "bank's app" in result["message"]
    assert api.calls == []  # refused before asking the bank anything
    assert (await prepare_tpt(bank(), amount=100))["prepared"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["lots", "NaN", "Infinity", "-Infinity"])
async def test_a_limit_that_is_not_a_number_refuses_every_transfer(monkeypatch, value):
    monkeypatch.setenv(transfers.MAX_AMOUNT_ENV, value)
    result = await prepare_tpt(bank(), amount=1)
    assert result["limit_exceeded"] is True


@pytest.mark.asyncio
async def test_a_loan_repayment_from_savings_is_an_own_account_transfer():
    api = bank()
    prepared = await prepare_tpt(api, to_account_id=33, to_account_type=1, third_party=False)
    done = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]))

    assert done["executed"] is True and done["resourceId"] == 77
    (sent,) = api.calls_to("POST", "/self/accounttransfers")
    assert sent["data"]["toAccountType"] == 1 and sent["data"]["toAccountId"] == 33


@pytest.mark.asyncio
async def test_the_transfer_date_uses_the_bank_time_zone(monkeypatch):
    monkeypatch.setenv(transfers.TIMEZONE_ENV, "America/Mexico_City")
    assert transfers.today() == datetime.now(ZoneInfo("America/Mexico_City")).date()
    assert transfers.format_date(date(2026, 3, 5)) == "05 March 2026"


# --- confirm --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_sends_exactly_the_prepared_request_once():
    api = bank()
    prepared = await prepare_tpt(api)
    done = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]))
    again = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]))

    assert done["executed"] is True and done["resourceId"] == 99
    assert done["transfer"] == prepared["transfer"]
    (sent,) = api.calls_to("POST", "/self/accounttransfers?type=tpt")
    assert {k: v for k, v in sent["data"].items() if k != "transferDate"} == TPT_SENT
    assert again["error"] is True and again["status_code"] == 404


@pytest.mark.asyncio
async def test_an_unknown_id_sends_nothing():
    api = bank()
    result = await run(api, lambda: confirm_transfer("made-up"))
    assert result["status_code"] == 404 and result["executed"] is False
    assert api.calls == []


@pytest.mark.asyncio
async def test_an_expired_id_sends_nothing(monkeypatch):
    api = bank()
    prepared = await prepare_tpt(api)
    clock = time.monotonic() + transfers.DEFAULT_TTL_SECONDS + 1
    monkeypatch.setattr(transfers.time, "monotonic", lambda: clock)

    result = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]))
    assert result["status_code"] == 404
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []


@pytest.mark.asyncio
async def test_only_the_last_few_prepared_transfers_are_kept():
    api = bank()
    ids = [(await prepare_tpt(api))["confirmation_id"] for _ in range(transfers.MAX_PREPARED + 1)]
    oldest = await run(api, lambda: confirm_transfer(ids[0]))
    newest = await run(api, lambda: confirm_transfer(ids[-1]))
    assert oldest["status_code"] == 404
    assert newest["executed"] is True


@pytest.mark.asyncio
async def test_cancel_drops_the_prepared_transfer():
    api = bank()
    prepared = await prepare_tpt(api)
    cancelled = await run(api, lambda: cancel_transfer(prepared["confirmation_id"]))
    after = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]))

    assert cancelled["cancelled"] is True and cancelled["executed"] is False
    assert after["status_code"] == 404
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []


# --- the person confirms in the client's form ----------------------------------------------------


@pytest.mark.asyncio
async def test_with_a_form_the_person_confirms_before_anything_is_sent():
    api = bank()
    prepared = await prepare_tpt(api)
    ctx = form(answer())
    done = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]), ctx)

    assert done["executed"] is True
    message = ctx.elicit.call_args.kwargs["message"]
    assert "100.5 USD from account 000000011 to account 000000022 (LUIS MORA)" in message


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", [answer("decline"), answer("cancel"), answer(confirm=False)])
async def test_declining_the_form_sends_nothing_and_uses_up_the_id(reply):
    api = bank()
    prepared = await prepare_tpt(api)
    result = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]), form(reply))
    again = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]))

    assert result["cancelled"] is True and result["executed"] is False
    assert again["status_code"] == 404
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []


@pytest.mark.asyncio
async def test_a_client_whose_form_fails_sends_nothing():
    api = bank()
    prepared = await prepare_tpt(api)
    broken = SimpleNamespace(elicit=AsyncMock(side_effect=RuntimeError("no form")))
    result = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]), broken)
    assert result["cancelled"] is True and result["executed"] is False
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []


# --- with the bank's one-time code (step-up) -----------------------------------------------------


@pytest.mark.asyncio
async def test_when_the_bank_asks_for_a_code_confirm_waits_for_it():
    api = bank(**{"POST /self/accounttransfers?type=tpt": [required(), {"resourceId": 99}]})
    prepared = await prepare_tpt(api)
    waiting = await run(api, lambda: confirm_transfer(prepared["confirmation_id"]))

    assert waiting["step_up_required"] is True and waiting["executed"] is False
    assert "third-party transfer of 100.5 from account 11 to account 22" in waiting["summary"]
    done = await run(api, lambda: verify_step_up(waiting["challengeId"], "123456"))
    assert done == {"resourceId": 99}
    first, second = api.calls_to("POST", "/self/accounttransfers?type=tpt")
    assert first["data"] == second["data"]
    assert second["headers"] == {"X-Step-Up-Token": "SECRET-ONE-TIME-TOKEN"}
