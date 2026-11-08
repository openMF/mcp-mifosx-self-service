from mcp.types import ToolAnnotations
from mcp_app import mcp
from typing import Any, Dict, List, Union
from utils.http import make_request
from utils.auth import get_auth_header

OFFICES_PATH = "/self/offices"
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)


def _nothing_recorded(result: Any, what: str) -> Any:
    """The plugin answers 204 No Content when an office has no geolocation or address."""
    if isinstance(result, dict) and result.get("status_code") == 204:
        return {"message": f"No {what} is recorded for this office."}
    return result


@mcp.tool(name="get_offices", annotations=READ_ONLY)
async def get_offices() -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Get Offices - Lists the bank's offices (branches) with id, name and opening date.

    Use the office id with get_office_details, get_office_services, get_office_address and
    get_office_geolocation to answer "where is my branch" or "what does this branch offer".
    """
    auth = get_auth_header()
    return await make_request("GET", OFFICES_PATH, auth=auth)


@mcp.tool(name="get_office_details", annotations=READ_ONLY)
async def get_office_details(office_id: int) -> Dict[str, Any]:
    """Get Office Details - Retrieves the details of one office (branch)."""
    auth = get_auth_header()
    return await make_request("GET", f"{OFFICES_PATH}/{office_id}/details", auth=auth)


@mcp.tool(name="get_office_services", annotations=READ_ONLY)
async def get_office_services(office_id: int) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Get Office Services - Lists the services an office offers, with their working hours."""
    auth = get_auth_header()
    return await make_request("GET", f"{OFFICES_PATH}/{office_id}/services", auth=auth)


@mcp.tool(name="get_office_address", annotations=READ_ONLY)
async def get_office_address(office_id: int) -> Dict[str, Any]:
    """Get Office Address - Retrieves the street address of an office."""
    auth = get_auth_header()
    result = await make_request("GET", f"{OFFICES_PATH}/{office_id}/address", auth=auth)
    return _nothing_recorded(result, "address")


@mcp.tool(name="get_office_geolocation", annotations=READ_ONLY)
async def get_office_geolocation(office_id: int) -> Dict[str, Any]:
    """Get Office Geolocation - Retrieves the map location (latitude and longitude) of an office."""
    auth = get_auth_header()
    result = await make_request("GET", f"{OFFICES_PATH}/{office_id}/geolocation", auth=auth)
    return _nothing_recorded(result, "geolocation")
