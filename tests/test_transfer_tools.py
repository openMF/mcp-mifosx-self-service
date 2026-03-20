from unittest.mock import AsyncMock, patch

import pytest

from routers.transfer_tools import (
    get_account_transfer_template,
    get_third_party_transfer_template,
    get_transfer_template,
    make_account_transfer,
    make_third_party_transfer,
    transfer_between_accounts,
    transfer_third_party,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_transfer_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_transfer_template("user1", "pwd")
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/accounttransfers/template?type=tpt", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_transfer_between_accounts(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 1}

    result = await transfer_between_accounts({"amount": 100}, "user1", "pwd")
    assert result == {"resourceId": 1}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("POST", "/self/accounttransfers", auth=mock_auth, data={"amount": 100})


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_transfer_third_party(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 2}

    result = await transfer_third_party({"amount": 200}, "user1", "pwd")
    assert result == {"resourceId": 2}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "POST", "/self/accounttransfers?type=tpt", auth=mock_auth, data={"amount": 200}
    )


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_account_transfer_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_account_transfer_template(10, "user1", "pwd")
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "GET", "/self/accounttransfers/template?fromAccountId=10&fromAccountType=2", auth=mock_auth
    )


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_third_party_transfer_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_third_party_transfer_template("user1", "pwd")
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/accounttransfers/template?type=tpt", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_make_third_party_transfer(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 3}

    result = await make_third_party_transfer({"amount": 300}, "user1", "pwd")
    assert result == {"resourceId": 3}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "POST", "/self/accounttransfers?type=tpt", auth=mock_auth, data={"amount": 300}
    )


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_make_account_transfer(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 4}

    result = await make_account_transfer({"amount": 400}, "user1", "pwd")
    assert result == {"resourceId": 4}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("POST", "/self/accounttransfers", auth=mock_auth, data={"amount": 400})
