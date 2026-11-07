"""Step-up through a real MCP client and server (in memory), with only the bank's HTTP API faked.

These tests check what the unit tests cannot: that the form really reaches the client, that a client
without elicitation is detected, and that the tools are registered.
"""

import json
from unittest.mock import patch

import pytest
from mcp import types
from mcp.shared.memory import create_connected_server_and_client_session

import main  # noqa: F401  (registers every tool)
from mcp_app import mcp
from tests.stepup_support import CHALLENGE, TOKEN, bank_routes, required
from utils import auth, stepup, transfers

PREPARE_ARGUMENTS = {
    "from_account_id": 11,
    "to_account_id": 22,
    "amount": 100.5,
    "description": "rent",
    "third_party": True,
}


@pytest.fixture(autouse=True)
def logged_in():
    stepup.clear_pending()
    transfers.clear_prepared()
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    yield
    stepup.clear_pending()
    transfers.clear_prepared()


def fake_bank(**overrides):
    routes = {"POST /self/accounttransfers?type=tpt": [required(), {"resourceId": 99}]}
    routes.update(overrides)
    return bank_routes(**routes)


def patched(api):
    return (
        patch("routers.transfer_tools.make_request", api),
        patch("utils.stepup.make_request", api),
    )


def payload(result: types.CallToolResult):
    assert result.isError is False, result.content
    return json.loads(result.content[0].text)


async def transfer(client):
    """prepare_transfer, then confirm_transfer with the id it returned."""
    prepared = payload(await client.call_tool("prepare_transfer", PREPARE_ARGUMENTS))
    return await client.call_tool("confirm_transfer", {"confirmation_id": prepared["confirmation_id"]})


@pytest.mark.asyncio
async def test_the_step_up_tools_are_registered():
    async with create_connected_server_and_client_session(mcp) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
    assert {
        "verify_step_up",
        "resend_step_up",
        "prepare_transfer",
        "confirm_transfer",
        "update_account_password",
    } <= names
    # the old one-step transfer tools are gone
    assert not names & {
        "transfer_to_third_party",
        "make_third_party_transfer",
        "transfer_between_accounts",
        "make_account_transfer",
    }


@pytest.mark.asyncio
async def test_a_client_with_elicitation_shows_the_form_and_the_transfer_completes():
    asked = []

    async def form(context, params):
        asked.append(params)
        if "confirm" in params.requestedSchema["properties"]:
            return types.ElicitResult(action="accept", content={"confirm": True})
        return types.ElicitResult(action="accept", content={"otp": "123456"})

    api = fake_bank()
    first, second = patched(api)
    with first, second:
        async with create_connected_server_and_client_session(mcp, elicitation_callback=form) as client:
            result = await transfer(client)

    assert payload(result)["executed"] is True and payload(result)["resourceId"] == 99
    confirmation, params = asked
    assert "100.5 USD from account 000000011 to account 000000022 (LUIS MORA)" in confirmation.message
    assert "a***@example.com" in params.message
    assert "third-party transfer of 100.5 from account 11 to account 22" in params.message
    assert set(params.requestedSchema["properties"]) == {"otp"}
    # the AI-facing result and the form never carry the code or the token
    assert "123456" not in json.dumps(payload(result))
    assert TOKEN not in json.dumps(payload(result))
    transfers = api.calls_to("POST", "/self/accounttransfers?type=tpt")
    assert [c["headers"] for c in transfers] == [None, {"X-Step-Up-Token": TOKEN}]


@pytest.mark.asyncio
@pytest.mark.parametrize("declined_form", ["confirm", "otp"])
async def test_declining_the_form_leaves_the_money_where_it_is(declined_form):
    async def form(context, params):
        if declined_form in params.requestedSchema["properties"]:
            return types.ElicitResult(action="decline")
        return types.ElicitResult(action="accept", content={"confirm": True})

    api = fake_bank()
    first, second = patched(api)
    with first, second:
        async with create_connected_server_and_client_session(mcp, elicitation_callback=form) as client:
            result = await transfer(client)

    body = payload(result)
    assert body["cancelled"] is True and body["executed"] is False
    # declining the confirmation sends nothing; declining the code stops after the first (refused) attempt
    expected = 0 if declined_form == "confirm" else 1
    assert len(api.calls_to("POST", "/self/accounttransfers?type=tpt")) == expected


@pytest.mark.asyncio
async def test_a_client_without_elicitation_gets_the_chat_fallback():
    api = fake_bank()
    first, second = patched(api)
    with first, second:
        async with create_connected_server_and_client_session(mcp) as client:
            waiting = payload(await transfer(client))
            done = payload(
                await client.call_tool("verify_step_up", {"challengeId": waiting["challengeId"], "otp": "123456"})
            )

    assert waiting["step_up_required"] is True and waiting["challengeId"] == CHALLENGE["challengeId"]
    assert done == {"resourceId": 99}


@pytest.mark.asyncio
async def test_an_operator_can_forbid_the_chat_fallback(monkeypatch):
    monkeypatch.setenv("MIFOS_STEP_UP_ALLOW_CHAT_OTP", "false")
    api = fake_bank()
    first, second = patched(api)
    with first, second:
        async with create_connected_server_and_client_session(mcp) as client:
            body = payload(await transfer(client))

    assert body["error"] is True and body["executed"] is False
    assert api.calls_to("POST", "/self/stepup/challenges") == []  # no code was sent
