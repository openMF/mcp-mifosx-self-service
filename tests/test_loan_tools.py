import pytest
from datetime import date, datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch, AsyncMock
from routers.loan_tools import (
    get_loan_products,
    get_loan_product_details,
    get_loan_account_details,
    get_loan_transaction_detail,
    get_loan_account_charges,
    get_loan_template,
    withdraw_loan_application,
)
from tests.stepup_support import FakeApi
from utils import transfers


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_products(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 1}]

    result = await get_loan_products(1)
    assert result == [{"id": 1}]
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with("GET", "/self/loanproducts?clientId=1", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_product_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 2}

    result = await get_loan_product_details(2)
    assert result == {"id": 2}
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with("GET", "/self/loanproducts/2", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_account_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 3}

    result = await get_loan_account_details(3, associations="all")
    assert result == {"id": 3}
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with("GET", "/self/loans/3?associations=all", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_transaction_detail(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 4}

    result = await get_loan_transaction_detail(3, 4)
    assert result == {"id": 4}
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with("GET", "/self/loans/3/transactions/4", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_account_charges(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = [{"id": 5}]

    result = await get_loan_account_charges(3)
    assert result == [{"id": 5}]
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with("GET", "/self/loans/3/charges", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.loan_tools.make_request", new_callable=AsyncMock)
@patch("routers.loan_tools.get_auth_header")
async def test_get_loan_template(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"template": True}

    result = await get_loan_template(1, 2)
    assert result == {"template": True}
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with(
        "GET", "/self/loans/template?clientId=1&templateType=individual&productId=2", auth=mock_auth
    )


PENDING = {"id": 10, "status": {"value": "Submitted and pending approval", "pendingApproval": True}}


def withdraw_api(loan):
    return FakeApi(
        **{
            "GET /self/loans/10": loan,
            "POST /self/loans/10?command=withdrawnByApplicant": {"resourceId": 10},
        }
    )


async def withdraw(api, *args):
    with patch("routers.loan_tools.make_request", api), patch("routers.loan_tools.get_auth_header", return_value="a"):
        return await withdraw_loan_application(10, *args)


@pytest.mark.asyncio
async def test_withdraw_sends_today_and_the_note(monkeypatch):
    monkeypatch.setattr(transfers, "today", lambda: date(2026, 10, 31))
    api = withdraw_api(PENDING)

    assert await withdraw(api, "  Changed mind  ") == {"resourceId": 10}
    (sent,) = api.calls_to("POST", "/self/loans/10?command=withdrawnByApplicant")
    assert sent["data"] == {
        "withdrawnOnDate": "31 October 2026",
        "note": "Changed mind",
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
    }


@pytest.mark.asyncio
async def test_today_comes_from_the_bank_time_zone(monkeypatch):
    monkeypatch.setenv(transfers.TIMEZONE_ENV, "America/Mexico_City")
    expected = datetime.now(ZoneInfo("America/Mexico_City")).date()
    api = withdraw_api(PENDING)
    await withdraw(api)
    (sent,) = api.calls_to("POST", "/self/loans/10?command=withdrawnByApplicant")
    assert sent["data"]["withdrawnOnDate"] == transfers.format_date(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("note", [None, "", "   "])
async def test_the_note_is_optional(note):
    api = withdraw_api(PENDING)
    await withdraw(api, note)
    (sent,) = api.calls_to("POST", "/self/loans/10?command=withdrawnByApplicant")
    assert "note" not in sent["data"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "loan, status, text",
    [
        (
            {"id": 10, "status": {"value": "Active", "pendingApproval": False}},
            400,
            "Loan 10 is Active. Only an application that is still waiting for approval",
        ),
        ({"error": True, "status_code": 404, "message": "not found"}, 404, "not found among the user's loans"),
    ],
)
async def test_only_a_pending_application_of_the_user_is_withdrawn(loan, status, text):
    api = withdraw_api(loan)
    result = await withdraw(api, "x")
    assert result["status_code"] == status and text in result["message"]
    assert api.calls_to("POST", "/self/loans/10?command=withdrawnByApplicant") == []
