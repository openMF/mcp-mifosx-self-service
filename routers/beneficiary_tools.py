from mcp_app import mcp
from typing import Optional, Dict, Any
from utils.http import make_request
from utils.auth import get_auth_header
@mcp.tool()
async def get_beneficiaries(username: str, password: str) -> Dict[str, Any]:
    """
    Get list of beneficiaries for third-party transfers

    Args:
        username: Username for authentication
        password: Password for authentication

    Returns:
        List of beneficiaries
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/beneficiaries/tpt", auth=auth)


@mcp.tool()
async def get_beneficiary_template(account_number: str, username: str, password: str) -> Dict[str, Any]:
    """
    Get beneficiary template for a specific account

    Args:
        account_number: Account number
        username: Username for authentication
        password: Password for authentication

    Returns:
        Beneficiary template
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/beneficiaries/tpt/{account_number}", auth=auth)


@mcp.tool()
async def add_beneficiary(
    name: str,
    office_name: str,
    account_number: str,
    account_type: int,
    transfer_limit: float,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """
    Add a new beneficiary for third-party transfers

    Args:
        name: Beneficiary name
        office_name: Office name (e.g., "Head Office")
        account_number: Beneficiary account number
        account_type: Account type (1=Savings, 2=Loan)
        transfer_limit: Maximum transfer limit
        username: Username for authentication
        password: Password for authentication

    Returns:
        Created beneficiary details
    """
    auth = get_auth_header(username, password)
    data = {
        "locale": "en",
        "name": name,
        "officeName": office_name,
        "accountNumber": account_number,
        "accountType": account_type,
        "transferLimit": transfer_limit,
    }

    return await make_request("POST", "/self/beneficiaries/tpt", auth=auth, data=data)


@mcp.tool()
async def update_beneficiary(
    beneficiary_id: int, name: Optional[str], transfer_limit: Optional[float], username: str, password: str
) -> Dict[str, Any]:
    """
    Update an existing beneficiary

    Args:
        beneficiary_id: Beneficiary ID to update
        name: New beneficiary name (optional)
        transfer_limit: New transfer limit (optional)
        username: Username for authentication
        password: Password for authentication

    Returns:
        Updated beneficiary details
    """
    auth = get_auth_header(username, password)
    data = {}

    if name:
        data["name"] = name
    if transfer_limit is not None:
        data["transferLimit"] = transfer_limit

    return await make_request("PUT", f"/self/beneficiaries/tpt/{beneficiary_id}", auth=auth, data=data)


@mcp.tool()
async def delete_beneficiary(beneficiary_id: int, username: str, password: str) -> Dict[str, Any]:
    """
    Delete a beneficiary

    Args:
        beneficiary_id: Beneficiary ID to delete
        username: Username for authentication
        password: Password for authentication

    Returns:
        Deletion confirmation
    """
    auth = get_auth_header(username, password)
    return await make_request("DELETE", f"/self/beneficiaries/tpt/{beneficiary_id}", auth=auth)
