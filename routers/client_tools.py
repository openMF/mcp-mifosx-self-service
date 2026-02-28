from mcp_app import mcp
from typing import Dict, Any, Optional
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="Get List of Clients Linked to the User")
async def get_my_clients(username: str, password: str) -> Dict[str, Any]:
    """Get List of Clients Linked to the User"""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/clients", auth=auth)


@mcp.tool(name="Get List of Client Details")
async def get_client_details(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List of Client Details"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}", auth=auth)


@mcp.tool(name="Get List of Accounts")
async def get_client_accounts(
    client_id: int, username: str, password: str, fields: Optional[str] = None
) -> Dict[str, Any]:
    """Get List of Accounts - Supports filtering by fields (e.g. savingsAccounts)."""
    auth = get_auth_header(username, password)
    path = f"/self/clients/{client_id}/accounts"
    if fields:
        path += f"?fields={fields}"
    return await make_request("GET", path, auth=auth)


@mcp.tool(name="Get List of Images")
async def get_client_images(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List of Images"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/images", auth=auth)


@mcp.tool(name="Get List of Charges")
async def get_client_charges(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List of Charges"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/charges", auth=auth)


@mcp.tool(name="Get List of Client Transactions")
async def get_client_transactions(
    client_id: int, username: str, password: str, offset: int = 0, limit: int = 20
) -> Dict[str, Any]:
    """Get List of Client Transactions - Supports pagination via offset and limit."""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/transactions?offset={offset}&limit={limit}", auth=auth)


@mcp.tool(name="Get List of Client Transaction Detail")
async def get_client_transaction_detail(
    client_id: int, transaction_id: int, username: str, password: str
) -> Dict[str, Any]:
    """Get List of Client Transaction Detail"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/transactions/{transaction_id}", auth=auth)


@mcp.tool(name="Get Client Accounts")
async def get_client_accounts_alias(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Client Accounts - Retrieves all accounts associated with authenticated client."""
    return await get_client_accounts(client_id, username, password)


@mcp.tool(name="Get Client Accounts by Type")
async def get_client_accounts_by_type(
    client_id: int, username: str, password: str, fields: str = "savingsAccounts"
) -> Dict[str, Any]:
    """Get Client Accounts by Type - Retrieves specific account types (savingsAccounts, loanAccounts)."""
    return await get_client_accounts(client_id, username, password, fields=fields)


@mcp.tool(name="Get Client Charges")
async def get_client_charges_alias(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Client Charges - Retrieves all charges for authenticated client."""
    return await get_client_charges(client_id, username, password)


@mcp.tool(name="Get Recent Transactions")
async def get_recent_transactions(
    client_id: int, username: str, password: str, offset: int = 0, limit: int = 20
) -> Dict[str, Any]:
    """Get Recent Transactions - Retrieves recent transactions for authenticated client."""
    return await get_client_transactions(client_id, username, password, offset=offset, limit=limit)
