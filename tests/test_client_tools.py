from unittest.mock import AsyncMock, patch

import pytest

from routers.client_tools import (
    get_client_accounts,
    get_client_charges,
    get_client_details,
    get_client_images,
    get_client_transaction_detail,
    get_client_transactions,
    get_clients_linked_to_user,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.client_tools.make_request", new_callable=AsyncMock)
@patch("routers.client_tools.get_auth_header")
async def test_get_clients_linked_to_user(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 1}]

    result = await get_clients_linked_to_user("user1", "pwd")
    assert result == [{"id": 1}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.client_tools.make_request", new_callable=AsyncMock)
@patch("routers.client_tools.get_auth_header")
async def test_get_client_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 1, "name": "John"}

    result = await get_client_details(1, "user1", "pwd")
    assert result == {"id": 1, "name": "John"}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients/1", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.client_tools.make_request", new_callable=AsyncMock)
@patch("routers.client_tools.get_auth_header")
async def test_get_client_accounts_without_fields(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"loanAccounts": []}

    result = await get_client_accounts(1, "user1", "pwd")
    assert result == {"loanAccounts": []}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients/1/accounts", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.client_tools.make_request", new_callable=AsyncMock)
@patch("routers.client_tools.get_auth_header")
async def test_get_client_accounts_with_fields(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"loanAccounts": []}

    result = await get_client_accounts(1, "user1", "pwd", fields="loanAccounts")
    assert result == {"loanAccounts": []}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients/1/accounts?fields=loanAccounts", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.client_tools.make_request", new_callable=AsyncMock)
@patch("routers.client_tools.get_auth_header")
async def test_get_client_images(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"image": "base64..."}

    result = await get_client_images(1, "user1", "pwd")
    assert result == {"image": "base64..."}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients/1/images", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.client_tools.make_request", new_callable=AsyncMock)
@patch("routers.client_tools.get_auth_header")
async def test_get_client_charges(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"chargeId": 1}]

    result = await get_client_charges(1, "user1", "pwd")
    assert result == [{"chargeId": 1}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients/1/charges", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.client_tools.make_request", new_callable=AsyncMock)
@patch("routers.client_tools.get_auth_header")
async def test_get_client_transactions(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"pageItems": []}

    result = await get_client_transactions(1, "user1", "pwd", offset=10, limit=5)
    assert result == {"pageItems": []}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients/1/transactions?offset=10&limit=5", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.client_tools.make_request", new_callable=AsyncMock)
@patch("routers.client_tools.get_auth_header")
async def test_get_client_transaction_detail(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 100}

    result = await get_client_transaction_detail(1, 100, "user1", "pwd")
    assert result == {"id": 100}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients/1/transactions/100", auth=mock_auth)
