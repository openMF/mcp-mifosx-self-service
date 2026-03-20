from unittest.mock import AsyncMock, patch

import pytest

from routers.savings_tools import (
    get_savings_charges,
    get_savings_details,
    get_savings_product_details,
    get_savings_products,
    get_savings_template_raw,
    get_savings_transaction_details,
    get_savings_transactions,
    submit_savings_application,
    update_savings_application,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_get_savings_products(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 1}]

    result = await get_savings_products(1, "user1", "pwd")
    assert result == [{"id": 1}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/savingsproducts?clientId=1", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_get_savings_product_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 2}

    result = await get_savings_product_details(1, 2, "user1", "pwd")
    assert result == {"id": 2}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/savingsproducts?clientId=1&productId=2", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_get_savings_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 3}

    result = await get_savings_details(3, "user1", "pwd", associations="all")
    assert result == {"id": 3}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/savingsaccounts/3?associations=all", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_get_savings_transactions(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"transactions": []}

    result = await get_savings_transactions(3, "user1", "pwd")
    assert result == {"transactions": []}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "GET", "/self/savingsaccounts/3?associations=transactions", auth=mock_auth
    )


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_get_savings_transaction_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 4}

    result = await get_savings_transaction_details(3, 4, "user1", "pwd")
    assert result == {"id": 4}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/savingsaccounts/3/transactions/4", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_get_savings_charges(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 5}]

    result = await get_savings_charges(3, "user1", "pwd")
    assert result == [{"id": 5}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/savingsaccounts/3/charges", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_get_savings_template_raw(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_savings_template_raw(1, 2, "user1", "pwd")
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "GET", "/self/savingsaccounts/template?clientId=1&productId=2", auth=mock_auth
    )


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_submit_savings_application(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 10}
    data = {"amount": 1000}

    result = await submit_savings_application(data, "user1", "pwd")
    assert result == {"resourceId": 10}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("POST", "/self/savingsaccounts", auth=mock_auth, data=data)


@pytest.mark.asyncio
@patch("routers.savings_tools.make_request", new_callable=AsyncMock)
@patch("routers.savings_tools.get_auth_header")
async def test_update_savings_application(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 10}
    data = {"amount": 2000}

    result = await update_savings_application(10, data, "user1", "pwd")
    assert result == {"resourceId": 10}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("PUT", "/self/savingsaccounts/10", auth=mock_auth, data=data)
