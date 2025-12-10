from mcp_app import mcp
from typing import Optional, Dict, Any
from utils.http import make_request
from utils.auth import get_auth_header



@mcp.tool()
async def get_client_info(username: str, password: str) -> Dict[str, Any]:
    """
    Get client information for authenticated user

    Args:
        username: Username for authentication
        password: Password for authentication

    Returns:
        Client information
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/clients", auth=auth)


@mcp.tool()
async def get_client_accounts(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """
    Get list of accounts for a client

    Args:
        client_id: Client ID
        username: Username for authentication
        password: Password for authentication

    Returns:
        List of client accounts
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/accounts", auth=auth)


@mcp.tool()
async def get_client_charges(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """
    Get list of charges for a client

    Args:
        client_id: Client ID
        username: Username for authentication
        password: Password for authentication

    Returns:
        List of client charges
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/charges", auth=auth)


@mcp.tool()
async def get_client_transactions(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """
    Get list of transactions for a client

    Args:
        client_id: Client ID
        username: Username for authentication
        password: Password for authentication

    Returns:
        List of client transactions
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/transactions", auth=auth)

