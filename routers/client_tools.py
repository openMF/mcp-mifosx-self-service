from typing import Any, Dict, Optional

from mcp_app import mcp
from utils.auth import get_auth_header
from utils.http import make_request


@mcp.tool(name="get_clients_linked_to_user")
async def get_clients_linked_to_user(username: str, password: str) -> Dict[str, Any]:
    """Get list of clients linked to the authenticated user."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/clients", auth=auth)


@mcp.tool(name="get_client_details")
async def get_client_details(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Retrieve client details."""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}", auth=auth)


@mcp.tool(name="get_client_accounts")
async def get_client_accounts(
    client_id: int,
    username: str,
    password: str,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve client accounts (optional filtering by account type)."""
    auth = get_auth_header(username, password)
    path = f"/self/clients/{client_id}/accounts"

    if fields:
        path += f"?fields={fields}"

    return await make_request("GET", path, auth=auth)


@mcp.tool(name="get_client_images")
async def get_client_images(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Retrieve client images."""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/images", auth=auth)


@mcp.tool(name="get_client_charges")
async def get_client_charges(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Retrieve client charges."""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/charges", auth=auth)


@mcp.tool(name="get_client_transactions")
async def get_client_transactions(
    client_id: int,
    username: str,
    password: str,
    offset: int = 0,
    limit: int = 20,
) -> Dict[str, Any]:
    """Retrieve client transactions with pagination."""
    auth = get_auth_header(username, password)
    path = f"/self/clients/{client_id}/transactions?offset={offset}&limit={limit}"
    return await make_request("GET", path, auth=auth)


@mcp.tool(name="get_client_transaction_detail")
async def get_client_transaction_detail(
    client_id: int,
    transaction_id: int,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Retrieve specific client transaction detail."""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/clients/{client_id}/transactions/{transaction_id}",
        auth=auth,
    )
