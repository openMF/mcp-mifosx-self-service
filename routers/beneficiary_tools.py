from mcp_app import mcp
from typing import Dict, Any
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="Get Beneficiaries Template")
async def get_beneficiaries_template(username: str, password: str) -> Dict[str, Any]:
    """Get Beneficiaries Template - Retrieves list of third-party transfer beneficiaries."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/beneficiaries/tpt", auth=auth)


@mcp.tool(name="Add Beneficiary - Savings")
async def add_beneficiary_savings(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Add Beneficiary - Savings"""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/beneficiaries/tpt", auth=auth, data=data)


@mcp.tool(name="Add Beneficiary - Loan")
async def add_beneficiary_loan(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Add Beneficiary - Loan"""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/beneficiaries/tpt", auth=auth, data=data)


@mcp.tool(name="Update Beneficiary - Savings (Raw)")
async def update_beneficiary_savings_raw(
    beneficiary_id: int, data: Dict[str, Any], username: str, password: str
) -> Dict[str, Any]:
    """Update Beneficiary - Savings (Raw)"""
    auth = get_auth_header(username, password)
    return await make_request("PUT", f"/self/beneficiaries/tpt/{beneficiary_id}", auth=auth, data=data)


@mcp.tool(name="Update Beneficiary - Loan (Raw)")
async def update_beneficiary_loan_raw(
    beneficiary_id: int, data: Dict[str, Any], username: str, password: str
) -> Dict[str, Any]:
    """Update Beneficiary - Loan (Raw)"""
    auth = get_auth_header(username, password)
    return await make_request("PUT", f"/self/beneficiaries/tpt/{beneficiary_id}", auth=auth, data=data)


@mcp.tool(name="Delete Beneficiary (Raw)")
async def delete_beneficiary_raw(beneficiary_id: int, username: str, password: str) -> Dict[str, Any]:
    """Delete Beneficiary (Raw)"""
    auth = get_auth_header(username, password)
    return await make_request("DELETE", f"/self/beneficiaries/tpt/{beneficiary_id}", auth=auth)


# Service Copy Alises
@mcp.tool(name="Get Beneficiary Template")
async def get_beneficiary_template(username: str, password: str) -> Dict[str, Any]:
    """Get Beneficiary Template - Retrieves template data for creating beneficiaries."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/beneficiaries/tpt/template", auth=auth)


@mcp.tool(name="Get Beneficiary List")
async def get_beneficiary_list_alias(username: str, password: str) -> Dict[str, Any]:
    """Get Beneficiary List - Retrieves list of third-party transfer beneficiaries."""
    return await get_beneficiaries_template(username, password)


@mcp.tool(name="Create Beneficiary - Savings")
async def create_beneficiary_savings_alias(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Create Beneficiary - Savings - Creates a new beneficiary for savings accounts."""
    return await add_beneficiary_savings(data, username, password)


@mcp.tool(name="Create Beneficiary - Loan")
async def create_beneficiary_loan_alias(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Create Beneficiary - Loan - Creates a new beneficiary for loan accounts."""
    return await add_beneficiary_loan(data, username, password)


@mcp.tool(name="Update Beneficiary - Savings")
async def update_beneficiary_savings_alias(
    beneficiary_id: int, data: Dict[str, Any], username: str, password: str
) -> Dict[str, Any]:
    """Update Beneficiary - Savings - Updates an existing savings beneficiary."""
    return await update_beneficiary_savings_raw(beneficiary_id, data, username, password)


@mcp.tool(name="Update Beneficiary - Loan")
async def update_beneficiary_loan_alias(
    beneficiary_id: int, data: Dict[str, Any], username: str, password: str
) -> Dict[str, Any]:
    """Update Beneficiary - Loan - Updates an existing loan beneficiary."""
    return await update_beneficiary_loan_raw(beneficiary_id, data, username, password)


@mcp.tool(name="Delete Beneficiary")
async def delete_beneficiary_alias(beneficiary_id: int, username: str, password: str) -> Dict[str, Any]:
    """Delete Beneficiary - Deletes a beneficiary."""
    return await delete_beneficiary_raw(beneficiary_id, username, password)
