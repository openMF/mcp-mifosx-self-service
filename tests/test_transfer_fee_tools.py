import pytest
from unittest.mock import patch, AsyncMock

from routers.transfer_tools import get_transfer_fees

FEES = [
    {
        "id": 2,
        "transferType": "PIN",
        "currencyCode": "CRC",
        "feeType": "PERCENTAGE",
        "feeValue": 0.005729,
        "isActive": True,
    },
    {
        "id": 4,
        "transferType": "PIN",
        "currencyCode": "USD",
        "feeType": "PERCENTAGE",
        "feeValue": 0.005729,
        "isActive": True,
    },
    {
        "id": 5,
        "transferType": "SINPE_MOVIL",
        "currencyCode": "CRC",
        "feeType": "FIXED",
        "feeValue": 0.0,
        "isActive": True,
    },
    {"id": 9, "transferType": "PIN", "currencyCode": "CRC", "feeType": "FIXED", "feeValue": 50.0, "isActive": False},
]


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_transfer_fees_returns_active_fees(mock_get_auth_header, mock_make_request):
    mock_get_auth_header.return_value = "Basic abc"
    mock_make_request.return_value = list(FEES)
    result = await get_transfer_fees()
    assert [fee["id"] for fee in result] == [2, 4, 5]
    mock_make_request.assert_called_once_with("GET", "/self/transfer-fees", auth="Basic abc")


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_transfer_fees_filters(mock_get_auth_header, mock_make_request):
    mock_get_auth_header.return_value = "Basic abc"
    mock_make_request.return_value = list(FEES)
    result = await get_transfer_fees(transfer_type="pin", currency_code="usd")
    assert [fee["id"] for fee in result] == [4]


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_transfer_fees_include_inactive(mock_get_auth_header, mock_make_request):
    mock_get_auth_header.return_value = "Basic abc"
    mock_make_request.return_value = list(FEES)
    result = await get_transfer_fees(transfer_type="PIN", currency_code="CRC", include_inactive=True)
    assert [fee["id"] for fee in result] == [2, 9]


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_transfer_fees_passes_errors_through(mock_get_auth_header, mock_make_request):
    mock_get_auth_header.return_value = "Basic abc"
    error = {"error": True, "status_code": 403, "message": "Forbidden"}
    mock_make_request.return_value = error
    assert await get_transfer_fees() == error


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_transfer_fees_through_mcp_returns_the_list(mock_get_auth_header, mock_make_request):
    """The endpoint returns a JSON array; the tool's output schema must accept it."""
    import main

    mock_get_auth_header.return_value = "Basic abc"
    mock_make_request.return_value = list(FEES)
    _, structured = await main.mcp.call_tool("get_transfer_fees", {"currency_code": "USD"})
    assert [fee["id"] for fee in structured["result"]] == [4]


@pytest.mark.asyncio
@patch("routers.transfer_tools.make_request", new_callable=AsyncMock)
@patch("routers.transfer_tools.get_auth_header")
async def test_get_transfer_quote(mock_get_auth_header, mock_make_request):
    from routers.transfer_tools import get_transfer_quote

    mock_get_auth_header.return_value = "Basic abc"
    mock_make_request.return_value = {
        "feeAmount": 2.86,
        "totalAmount": 502.86,
        "currencyCode": "USD",
        "feeDescription": "Comisión T+1 (0.5729%)",
    }
    result = await get_transfer_quote("26", 500, "PIN", currency_code="USD", transfer_mode="T_PLUS_1")
    assert result["feeAmount"] == 2.86
    mock_make_request.assert_called_once_with(
        "POST",
        "/self/accounttransfers/quote",
        auth="Basic abc",
        data={
            "fromAccount": "26",
            "fromAccountType": 2,
            "transferAmount": 500,
            "transferType": "PIN",
            "currencyCode": "USD",
            "transferMode": "T_PLUS_1",
        },
    )
