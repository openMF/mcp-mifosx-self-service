from unittest.mock import AsyncMock, patch

import pytest

from routers.beneficiary_tools import (
    create_beneficiary_loan,
    create_beneficiary_savings,
    delete_beneficiary,
    get_beneficiary_list,
    get_beneficiary_template,
    update_beneficiary_loan,
    update_beneficiary_savings,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.beneficiary_tools.make_request", new_callable=AsyncMock)
@patch("routers.beneficiary_tools.get_auth_header")
async def test_get_beneficiary_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_beneficiary_template("user1", "pwd")
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/beneficiaries/tpt/template", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.beneficiary_tools.make_request", new_callable=AsyncMock)
@patch("routers.beneficiary_tools.get_auth_header")
async def test_get_beneficiary_list(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 1, "name": "Ben"}]

    result = await get_beneficiary_list("user1", "pwd")
    assert result == [{"id": 1, "name": "Ben"}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/beneficiaries/tpt", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.beneficiary_tools.make_request", new_callable=AsyncMock)
@patch("routers.beneficiary_tools.get_auth_header")
async def test_create_beneficiary_savings(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 1}
    data = {"name": "Ben"}

    result = await create_beneficiary_savings(data, "user1", "pwd")
    assert result == {"resourceId": 1}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("POST", "/self/beneficiaries/tpt", auth=mock_auth, data=data)


@pytest.mark.asyncio
@patch("routers.beneficiary_tools.make_request", new_callable=AsyncMock)
@patch("routers.beneficiary_tools.get_auth_header")
async def test_create_beneficiary_loan(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 2}
    data = {"name": "Ben Loan"}

    result = await create_beneficiary_loan(data, "user1", "pwd")
    assert result == {"resourceId": 2}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("POST", "/self/beneficiaries/tpt", auth=mock_auth, data=data)


@pytest.mark.asyncio
@patch("routers.beneficiary_tools.make_request", new_callable=AsyncMock)
@patch("routers.beneficiary_tools.get_auth_header")
async def test_update_beneficiary_savings(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 1}
    data = {"name": "Ben Updated"}

    result = await update_beneficiary_savings(1, data, "user1", "pwd")
    assert result == {"resourceId": 1}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("PUT", "/self/beneficiaries/tpt/1", auth=mock_auth, data=data)


@pytest.mark.asyncio
@patch("routers.beneficiary_tools.make_request", new_callable=AsyncMock)
@patch("routers.beneficiary_tools.get_auth_header")
async def test_update_beneficiary_loan(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 2}
    data = {"name": "Ben Loan Updated"}

    result = await update_beneficiary_loan(2, data, "user1", "pwd")
    assert result == {"resourceId": 2}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("PUT", "/self/beneficiaries/tpt/2", auth=mock_auth, data=data)


@pytest.mark.asyncio
@patch("routers.beneficiary_tools.make_request", new_callable=AsyncMock)
@patch("routers.beneficiary_tools.get_auth_header")
async def test_delete_beneficiary(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 3}

    result = await delete_beneficiary(3, "user1", "pwd")
    assert result == {"resourceId": 3}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("DELETE", "/self/beneficiaries/tpt/3", auth=mock_auth)
