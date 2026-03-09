import pytest
from unittest.mock import patch, AsyncMock
from routers.guarantor_tools import (
    get_guarantor_template,
    get_loan_guarantors,
    add_loan_guarantor,
    update_loan_guarantor,
    delete_loan_guarantor,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.guarantor_tools.make_request", new_callable=AsyncMock)
@patch("routers.guarantor_tools.get_auth_header")
async def test_get_guarantor_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_guarantor_template(1, "user1", "pwd")
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/loans/1/guarantors/template", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.guarantor_tools.make_request", new_callable=AsyncMock)
@patch("routers.guarantor_tools.get_auth_header")
async def test_get_loan_guarantors(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 1}]

    result = await get_loan_guarantors(1, "user1", "pwd")
    assert result == [{"id": 1}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/loans/1/guarantors", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.guarantor_tools.make_request", new_callable=AsyncMock)
@patch("routers.guarantor_tools.get_auth_header")
async def test_add_loan_guarantor(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 2}

    result = await add_loan_guarantor(
        1, 1, "Guarantor", "Last", "123456", "user1", "pwd", address_line1="123 Street", city="City", zip_code="00000"
    )
    assert result == {"resourceId": 2}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "POST",
        "/self/loans/1/guarantors",
        auth=mock_auth,
        data={
            "guarantorType": 1,
            "firstName": "Guarantor",
            "lastName": "Last",
            "mobileNumber": "123456",
            "addressLine1": "123 Street",
            "city": "City",
            "zip": "00000",
            "locale": "en",
        },
    )


@pytest.mark.asyncio
@patch("routers.guarantor_tools.make_request", new_callable=AsyncMock)
@patch("routers.guarantor_tools.get_auth_header")
async def test_update_loan_guarantor(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 1}
    data = {"firstName": "Updated"}

    result = await update_loan_guarantor(1, 1, data, "user1", "pwd")
    assert result == {"resourceId": 1}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("PUT", "/self/loans/1/guarantors/1", auth=mock_auth, data=data)


@pytest.mark.asyncio
@patch("routers.guarantor_tools.make_request", new_callable=AsyncMock)
@patch("routers.guarantor_tools.get_auth_header")
async def test_delete_loan_guarantor(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 3}

    result = await delete_loan_guarantor(1, 3, "user1", "pwd")
    assert result == {"resourceId": 3}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("DELETE", "/self/loans/1/guarantors/3", auth=mock_auth)
