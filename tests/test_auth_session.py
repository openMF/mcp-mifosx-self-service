import base64

import pytest

from utils import auth


def test_not_logged_in_raises():
    with pytest.raises(auth.NotLoggedInError):
        auth.get_auth_header()


def test_env_credentials_are_used(monkeypatch):
    monkeypatch.setenv("MIFOS_USERNAME", "tomas")
    monkeypatch.setenv("MIFOS_PASSWORD", "secret")
    expected = "Basic " + base64.b64encode(b"tomas:secret").decode()
    assert auth.get_auth_header() == expected


def test_saved_token_wins_over_env_credentials(monkeypatch):
    monkeypatch.setenv("MIFOS_USERNAME", "tomas")
    monkeypatch.setenv("MIFOS_PASSWORD", "secret")
    auth.save_login({"base64EncodedAuthenticationKey": "dG9rZW4="})
    assert auth.get_auth_header() == "Basic dG9rZW4="


def test_save_login_removes_secrets():
    cleaned = auth.save_login({"username": "tomas", "base64EncodedAuthenticationKey": "a", "refreshToken": "b"})
    assert cleaned == {"username": "tomas"}


def test_clear_login():
    auth.save_login({"base64EncodedAuthenticationKey": "dG9rZW4="})
    auth.clear_login()
    with pytest.raises(auth.NotLoggedInError):
        auth.get_auth_header()


@pytest.mark.asyncio
async def test_tool_without_login_tells_the_ai_to_log_in():
    from mcp.server.fastmcp.exceptions import ToolError

    import main

    with pytest.raises(ToolError, match="Not logged in"):
        await main.mcp.call_tool("get_clients_linked_to_user", {})


@pytest.mark.asyncio
async def test_no_tool_asks_for_a_password_except_login_and_registration():
    import main

    allowed = {"login", "authenticate_user_self_service", "register_self_service_existing_client"}
    for tool in await main.mcp.list_tools():
        inputs = set(tool.inputSchema.get("properties", {}))
        if tool.name not in allowed:
            assert not {"username", "password"} & inputs, tool.name
