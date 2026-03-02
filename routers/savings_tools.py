from mcp_app import mcp
from typing import Dict, Any, Optional
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="get_savings_products")
async def get_savings_products(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List of Savings Products"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/savingsproducts?clientId={client_id}", auth=auth)


@mcp.tool(name="get_savings_product_details")
async def get_savings_product_details(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Detail of Savings Products"""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/savingsproducts?clientId={client_id}&productId={product_id}",
        auth=auth,
    )


@mcp.tool(name="get_savings_account_details")
async def get_savings_details(
    savings_id: int,
    username: str,
    password: str,
    associations: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Detail of Savings Account - Supports associations (transactions,charges)."""
    auth = get_auth_header(username, password)

    path = f"/self/savingsaccounts/{savings_id}"
    if associations:
        path += f"?associations={associations}"

    return await make_request("GET", path, auth=auth)


@mcp.tool(name="get_savings_account_transactions")
async def get_savings_transactions(
    savings_id: int,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Get List Savings Account Transactions"""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/savingsaccounts/{savings_id}?associations=transactions",
        auth=auth,
    )


@mcp.tool(name="get_savings_account_transaction_details")
async def get_savings_transaction_details(
    savings_id: int,
    transaction_id: int,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Get Detail of Savings Account Transaction"""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/savingsaccounts/{savings_id}/transactions/{transaction_id}",
        auth=auth,
    )


@mcp.tool(name="get_savings_account_charges")
async def get_savings_charges(
    savings_id: int,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Get List of Savings Account Charges"""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/savingsaccounts/{savings_id}/charges",
        auth=auth,
    )


@mcp.tool(name="get_savings_account_template_raw")
async def get_savings_template_raw(
    client_id: int,
    product_id: int,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Get Savings Account Template (Raw)"""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/savingsaccounts/template?clientId={client_id}&productId={product_id}",
        auth=auth,
    )


@mcp.tool(name="submit_savings_application")
async def submit_savings_application(
    data: Dict[str, Any],
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Request a New Savings Account (Submit Application)"""
    auth = get_auth_header(username, password)
    return await make_request(
        "POST",
        "/self/savingsaccounts",
        auth=auth,
        data=data,
    )


@mcp.tool(name="update_savings_account_application")
async def update_savings_application(
    savings_id: int,
    data: Dict[str, Any],
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Update a Savings Account Application"""
    auth = get_auth_header(username, password)
    return await make_request(
        "PUT",
        f"/self/savingsaccounts/{savings_id}",
        auth=auth,
        data=data,
    )
