"""Profile and pockets (US-E13-05)."""

from unittest.mock import AsyncMock, patch

import pytest

import main  # noqa: F401  (registers every tool)
from mcp_app import mcp
from routers.profile_tools import (
    PocketAccount,
    add_accounts_to_pocket,
    get_pockets,
    get_user_details,
    remove_accounts_from_pocket,
)
from utils import auth

AUTH = "Basic c2Vzc2lvbg=="


@pytest.fixture(autouse=True)
def logged_in():
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})


def bank(answer):
    return patch("routers.profile_tools.make_request", AsyncMock(return_value=answer))


@pytest.mark.asyncio
async def test_user_details_never_return_credentials():
    answer = {"username": "ana", "accessToken": "T", "base64EncodedAuthenticationKey": "K", "refreshToken": "R"}
    with bank(answer) as api:
        result = await get_user_details()
    assert result == {"username": "ana"}
    api.assert_called_once_with("GET", "/self/userdetails", auth=AUTH)


@pytest.mark.asyncio
async def test_without_oauth_user_details_point_to_the_client_tools():
    with bank({"error": True, "status_code": 404, "message": "Not Found"}):
        result = await get_user_details()
    assert result["status_code"] == 404
    assert "get_client_details" in result["message"]


@pytest.mark.asyncio
async def test_other_errors_are_passed_through():
    error = {"error": True, "status_code": 401, "message": "Unauthorized"}
    with bank(error):
        assert await get_user_details() == error


@pytest.mark.asyncio
async def test_pockets_are_listed():
    answer = {"loanAccounts": [{"id": 29, "accountId": 1475}], "savingsAccounts": [], "shareAccounts": []}
    with bank(answer) as api:
        assert await get_pockets() == answer
    api.assert_called_once_with("GET", "/self/pockets", auth=AUTH)


@pytest.mark.asyncio
async def test_no_pockets_is_an_empty_list_not_a_204():
    with bank({"message": "Success", "status_code": 204}):
        assert await get_pockets() == {"loanAccounts": [], "savingsAccounts": [], "shareAccounts": []}


@pytest.mark.asyncio
async def test_adding_accounts_sends_the_bank_format():
    with bank({"resourceId": 2}) as api:
        result = await add_accounts_to_pocket(
            [PocketAccount(account_id=1475, account_type="loan"), PocketAccount(account_id=8, account_type="savings")]
        )
    assert result == {"resourceId": 2}
    api.assert_called_once_with(
        "POST",
        "/self/pockets?command=linkAccounts",
        auth=AUTH,
        data={
            "accountsDetail": [{"accountId": 1475, "accountType": "loan"}, {"accountId": 8, "accountType": "savings"}]
        },
    )


@pytest.mark.asyncio
async def test_removing_uses_the_mapping_ids():
    with bank({"resourceId": 2}) as api:
        await remove_accounts_from_pocket([29, 30])
    api.assert_called_once_with(
        "POST", "/self/pockets?command=delinkAccounts", auth=AUTH, data={"pocketAccountMappingIds": [29, 30]}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("call", [lambda: add_accounts_to_pocket([]), lambda: remove_accounts_from_pocket([])])
async def test_empty_lists_send_nothing(call):
    with bank({}) as api:
        result = await call()
    assert result["status_code"] == 400
    api.assert_not_called()


@pytest.mark.asyncio
async def test_through_mcp_the_account_list_is_validated_and_sent():
    with bank({"resourceId": 2}) as api:
        _, structured = await mcp.call_tool(
            "add_accounts_to_pocket", {"accounts": [{"account_id": 1475, "account_type": "loan"}]}
        )
    assert structured["result"] == {"resourceId": 2}
    assert api.call_args.kwargs["data"] == {"accountsDetail": [{"accountId": 1475, "accountType": "loan"}]}
    with pytest.raises(Exception):
        await mcp.call_tool("add_accounts_to_pocket", {"accounts": [{"account_id": 1, "account_type": "car"}]})
