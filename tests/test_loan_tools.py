from unittest.mock import AsyncMock, patch

import pytest

from routers.loan_tools import (
    calculate_loan_repayment_calendar,
    get_loan_account_charges,
    get_loan_account_details,
    get_loan_product_details,
    get_loan_products,
    get_loan_template,
    get_loan_transaction_detail,
    submit_loan_application,
    update_loan_application,
    withdraw_loan_application,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_products(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 1}]

    result = await get_loan_products(1, "user1", "pwd")
    assert result == [{"id": 1}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/loanproducts?clientId=1", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_product_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 2}

    result = await get_loan_product_details(1, 2, "user1", "pwd")
    assert result == {"id": 2}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/loanproducts?clientId=1&productId=2", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_account_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 3}

    result = await get_loan_account_details(3, "user1", "pwd", associations="all")
    assert result == {"id": 3}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/loans/3?associations=all", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_transaction_detail(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 4}

    result = await get_loan_transaction_detail(3, 4, "user1", "pwd")
    assert result == {"id": 4}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/loans/3/transactions/4", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_account_charges(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 5}]

    result = await get_loan_account_charges(3, "user1", "pwd")
    assert result == [{"id": 5}]
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/loans/3/charges", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_loan_template(1, 2, "user1", "pwd")
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "GET", "/self/loans/template?clientId=1&productId=2&templateType=individual", auth=mock_auth
    )


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_calculate_loan_repayment_calendar(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"schedule": []}
    data = {"amount": 1000}

    result = await calculate_loan_repayment_calendar(data, "user1", "pwd")
    assert result == {"schedule": []}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "POST", "/self/loans?command=calculateLoanSchedule", auth=mock_auth, data=data
    )


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_submit_loan_application(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 10}
    data = {"amount": 1000}

    result = await submit_loan_application(data, "user1", "pwd")
    assert result == {"resourceId": 10}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("POST", "/self/loans", auth=mock_auth, data=data)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_update_loan_application(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 10}
    data = {"amount": 2000}

    result = await update_loan_application(10, data, "user1", "pwd")
    assert result == {"resourceId": 10}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("PUT", "/self/loans/10", auth=mock_auth, data=data)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_withdraw_loan_application(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 10}

    result = await withdraw_loan_application(10, "Changed mind", "user1", "pwd")
    assert result == {"resourceId": 10}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "POST",
        "/self/loans/10?command=withdrawnByApplicant",
        auth=mock_auth,
        data={
            "withdrawnOnDate": "30 August 2025",
            "note": "Changed mind",
            "dateFormat": "dd MMMM yyyy",
            "locale": "en",
        },
    )
