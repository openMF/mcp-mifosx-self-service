import pytest
from unittest.mock import patch, AsyncMock
from routers.transfer_tools import (
    get_account_transfer_template,
    get_third_party_transfer_template,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_account_transfer_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_account_transfer_template(10)
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with(
        "GET", "/self/accounttransfers/template?fromAccountId=10&fromAccountType=2", auth=mock_auth
    )


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_third_party_transfer_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_third_party_transfer_template()
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with("GET", "/self/accounttransfers/template?type=tpt", auth=mock_auth)
