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
from tests.stepup_support import CHALLENGE, TOKEN, TRANSFER, required, standard_api
from utils import auth, stepup

TOOL_ARGUMENTS = {"data": TRANSFER}


@pytest.fixture(autouse=True)
def logged_in():
    stepup.clear_pending()
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    yield
    stepup.clear_pending()


def fake_bank(**overrides):
    routes = {"POST /self/accounttransfers?type=tpt": [required(), {"resourceId": 99}]}
    routes.update(overrides)
    return standard_api(**routes)


def patched(api):
    return (
        patch("routers.transfer_tools.make_request", api),
        patch("utils.stepup.make_request", api),
    )


def payload(result: types.CallToolResult):
    assert result.isError is False, result.content
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_the_step_up_tools_are_registered():
    async with create_connected_server_and_client_session(mcp) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
    assert {"verify_step_up", "resend_step_up", "transfer_to_third_party", "update_account_password"} <= names


@pytest.mark.asyncio
async def test_a_client_with_elicitation_shows_the_form_and_the_transfer_completes():
    asked = []

    async def form(context, params):
        asked.append(params)
        return types.ElicitResult(action="accept", content={"otp": "123456"})

    api = fake_bank()
    first, second = patched(api)
    with first, second:
        async with create_connected_server_and_client_session(mcp, elicitation_callback=form) as client:
            result = await client.call_tool("transfer_to_third_party", TOOL_ARGUMENTS)

    assert payload(result) == {"resourceId": 99}
    (params,) = asked
    assert "a***@example.com" in params.message
    assert "third-party transfer of 100.5 from account 11 to account 22" in params.message
    assert set(params.requestedSchema["properties"]) == {"otp"}
    # the AI-facing result and the form never carry the code or the token
    assert "123456" not in json.dumps(payload(result))
    assert TOKEN not in json.dumps(payload(result))
    transfers = api.calls_to("POST", "/self/accounttransfers?type=tpt")
    assert [c["headers"] for c in transfers] == [None, {"X-Step-Up-Token": TOKEN}]


@pytest.mark.asyncio
async def test_declining_the_form_leaves_the_money_where_it_is():
    async def form(context, params):
        return types.ElicitResult(action="decline")

    api = fake_bank()
    first, second = patched(api)
    with first, second:
        async with create_connected_server_and_client_session(mcp, elicitation_callback=form) as client:
            result = await client.call_tool("transfer_to_third_party", TOOL_ARGUMENTS)

    body = payload(result)
    assert body["cancelled"] is True and body["executed"] is False
    assert len(api.calls_to("POST", "/self/accounttransfers?type=tpt")) == 1  # only the first attempt


@pytest.mark.asyncio
async def test_a_client_without_elicitation_gets_the_chat_fallback():
    api = fake_bank()
    first, second = patched(api)
    with first, second:
        async with create_connected_server_and_client_session(mcp) as client:
            waiting = payload(await client.call_tool("transfer_to_third_party", TOOL_ARGUMENTS))
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
            body = payload(await client.call_tool("transfer_to_third_party", TOOL_ARGUMENTS))

    assert body["error"] is True and body["executed"] is False
    assert api.calls_to("POST", "/self/stepup/challenges") == []  # no code was sent
