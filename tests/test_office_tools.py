import pytest
from unittest.mock import patch, AsyncMock

from routers.office_tools import (
    get_offices,
    get_office_details,
    get_office_services,
    get_office_address,
    get_office_geolocation,
)

AUTH = "Basic abc"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool, args, path",
    [
        (get_offices, (), "/self/offices"),
        (get_office_details, (1,), "/self/offices/1/details"),
        (get_office_services, (1,), "/self/offices/1/services"),
        (get_office_address, (1,), "/self/offices/1/address"),
        (get_office_geolocation, (1,), "/self/offices/1/geolocation"),
    ],
)
@patch("routers.office_tools.make_request", new_callable=AsyncMock)
@patch("routers.office_tools.get_auth_header")
async def test_office_tools_call_the_plugin(mock_get_auth_header, mock_make_request, tool, args, path):
    mock_get_auth_header.return_value = AUTH
    mock_make_request.return_value = {"id": 1}
    assert await tool(*args) == {"id": 1}
    mock_make_request.assert_called_once_with("GET", path, auth=AUTH)


@pytest.mark.asyncio
@pytest.mark.parametrize("tool, what", [(get_office_address, "address"), (get_office_geolocation, "geolocation")])
@patch("routers.office_tools.make_request", new_callable=AsyncMock)
@patch("routers.office_tools.get_auth_header")
async def test_no_content_means_nothing_recorded(mock_get_auth_header, mock_make_request, tool, what):
    mock_get_auth_header.return_value = AUTH
    mock_make_request.return_value = {"message": "Success", "status_code": 204}
    assert await tool(1) == {"message": f"No {what} is recorded for this office."}


@pytest.mark.asyncio
@patch("routers.office_tools.make_request", new_callable=AsyncMock)
@patch("routers.office_tools.get_auth_header")
async def test_errors_are_passed_through(mock_get_auth_header, mock_make_request):
    mock_get_auth_header.return_value = AUTH
    error = {"error": True, "status_code": 404, "message": "not found"}
    mock_make_request.return_value = error
    assert await get_office_details(999) == error
    assert await get_office_geolocation(999) == error


@pytest.mark.asyncio
@patch("routers.office_tools.make_request", new_callable=AsyncMock)
@patch("routers.office_tools.get_auth_header")
async def test_list_tools_return_lists_through_mcp(mock_get_auth_header, mock_make_request):
    """The office list and services endpoints return JSON arrays; the output schema must accept them."""
    import main

    mock_get_auth_header.return_value = AUTH
    mock_make_request.return_value = [{"id": 1, "name": "CENTRAL"}, {"id": 2, "name": "NORTE"}]
    _, structured = await main.mcp.call_tool("get_offices", {})
    assert [office["id"] for office in structured["result"]] == [1, 2]
    _, structured = await main.mcp.call_tool("get_office_services", {"office_id": 1})
    assert len(structured["result"]) == 2
