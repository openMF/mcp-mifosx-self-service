from mcp_app import mcp
from typing import Dict, Any, Optional
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="Get List of Savings Products")
async def get_savings_products(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List of Savings Products"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/savingsproducts?clientId={client_id}", auth=auth)


@mcp.tool(name="Get Detail of Savings Products")
async def get_savings_product_details(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Detail of Savings Products"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/savingsproducts?clientId={client_id}&productId={product_id}", auth=auth)


@mcp.tool(name="Get Detail of Savings Account")
async def get_savings_details(
    savings_id: int, username: str, password: str, associations: Optional[str] = None
) -> Dict[str, Any]:
    """Get Detail of Savings Account - Supports associations (transactions,charges)."""
    auth = get_auth_header(username, password)
    path = f"/self/savingsaccounts/{savings_id}"
    if associations:
        path += f"?associations={associations}"
    return await make_request("GET", path, auth=auth)


@mcp.tool(name="Get List Savings Account Transactions")
async def get_savings_transactions(savings_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List Savings Account Transactions"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/savingsaccounts/{savings_id}?associations=transactions", auth=auth)


@mcp.tool(name="Get Detail of Savings Account Transaction")
async def get_savings_transaction_details(
    savings_id: int, transaction_id: int, username: str, password: str
) -> Dict[str, Any]:
    """Get Detail of Savings Account Transaction"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/savingsaccounts/{savings_id}/transactions/{transaction_id}", auth=auth)


@mcp.tool(name="Get List of Savings Account Charges")
async def get_savings_charges(savings_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List of Savings Account Charges"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/savingsaccounts/{savings_id}/charges", auth=auth)


@mcp.tool(name="Get Savings Account Template (Raw)")
async def get_savings_template_raw(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Savings Account Template (Raw)"""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET", f"/self/savingsaccounts/template?clientId={client_id}&productId={product_id}", auth=auth
    )


@mcp.tool(name="Request a New Savings Account (Submit Applications)")
async def submit_savings_application(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Request a New Savings Account (Submit Applications)"""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/savingsaccounts", auth=auth, data=data)


@mcp.tool(name="Update a New Savings Account Application")
async def update_savings_application(
    savings_id: int, data: Dict[str, Any], username: str, password: str
) -> Dict[str, Any]:
    """Update a New Savings Account Application"""
    auth = get_auth_header(username, password)
    return await make_request("PUT", f"/self/savingsaccounts/{savings_id}", auth=auth, data=data)


@mcp.tool(name="Get Savings Account with Associations")
async def get_savings_with_associations_alias(
    savings_id: int, username: str, password: str, associations: str = "transactions,charges"
) -> Dict[str, Any]:
    """Get Savings Account with Associations - Retrieves details (transactions,charges)."""
    return await get_savings_details(savings_id, username, password, associations=associations)


@mcp.tool(name="Get Savings Account Template")
async def get_savings_template_alias(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Savings Account Template - Retrieves template for creating savings accounts."""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/savingsaccounts/template?clientId={client_id}", auth=auth)


@mcp.tool(name="Create Savings Account")
async def create_savings_account_alias(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Create Savings Account - Submit application."""
    return await submit_savings_application(data, username, password)


@mcp.tool(name="Update Savings Account")
async def update_savings_account_alias(
    savings_id: int, data: Dict[str, Any], username: str, password: str
) -> Dict[str, Any]:
    """Update Savings Account - Updates application."""
    return await update_savings_application(savings_id, data, username, password)


@mcp.tool(name="Withdraw Savings Account Application")
async def withdraw_savings_account_application_alias(
    savings_id: int, note: str, username: str, password: str
) -> Dict[str, Any]:
    """Withdraw Savings Account Application - Withdraws application."""
    auth = get_auth_header(username, password)
    data = {"withdrawnOnDate": "01 February 2024", "note": note, "locale": "en", "dateFormat": "dd MMMM yyyy"}
    return await make_request(
        "POST", f"/self/savingsaccounts/{savings_id}?command=withdrawnByApplicant", auth=auth, data=data
    )
