import pytest
from unittest.mock import patch, AsyncMock
from routers.shares_tools import (
    get_shares_products,
    get_shares_product_details,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.shares_tools.make_request", new_callable=AsyncMock)
@patch("routers.shares_tools.get_auth_header")
async def test_get_share_product_list(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 1, "name": "Share Product A"}]

    result = await get_shares_products(1, "user1", "pwd")
    assert result == [{"id": 1, "name": "Share Product A"}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/products/share?clientId=1", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.shares_tools.make_request", new_callable=AsyncMock)
@patch("routers.shares_tools.get_auth_header")
async def test_get_share_product_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 2, "name": "Share Product B", "totalShares": 500}

    result = await get_shares_product_details(1, 2, "user1", "pwd")
    assert result == {"id": 2, "name": "Share Product B", "totalShares": 500}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/products/share?clientId=1&productId=2", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.shares_tools.make_request", new_callable=AsyncMock)
@patch("routers.shares_tools.get_auth_header")
async def test_get_share_product_list_empty(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = []

    result = await get_shares_products(1, "user1", "pwd")
    assert result == []
    mock_make_request.assert_called_once_with("GET", "/self/products/share?clientId=1", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.shares_tools.make_request", new_callable=AsyncMock)
@patch("routers.shares_tools.get_auth_header")
async def test_get_share_product_list_error(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"error": True, "status_code": 403, "message": "Forbidden"}

    result = await get_shares_products(99, "user1", "pwd")
    assert result["error"] is True
    assert result["status_code"] == 403


@pytest.mark.asyncio
@patch("routers.shares_tools.make_request", new_callable=AsyncMock)
@patch("routers.shares_tools.get_auth_header")
async def test_get_share_product_details_not_found(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"error": True, "status_code": 404, "message": "Share product not found"}

    result = await get_shares_product_details(1, 999, "user1", "pwd")
    assert result["error"] is True
    assert result["status_code"] == 404
