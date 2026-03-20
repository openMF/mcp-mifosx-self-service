from typing import Any, Dict

from mcp_app import mcp
from utils.auth import get_auth_header
from utils.http import make_request


@mcp.tool(name="get_beneficiary_template")
async def get_beneficiary_template(username: str, password: str) -> Dict[str, Any]:
    """Retrieve template data for creating beneficiaries."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/beneficiaries/tpt/template", auth=auth)


@mcp.tool(name="get_beneficiary_list")
async def get_beneficiary_list(username: str, password: str) -> Dict[str, Any]:
    """Retrieve list of third-party transfer beneficiaries."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/beneficiaries/tpt", auth=auth)


@mcp.tool(name="create_beneficiary_savings")
async def create_beneficiary_savings(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Create a new savings beneficiary."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/beneficiaries/tpt", auth=auth, data=data)


@mcp.tool(name="create_beneficiary_loan")
async def create_beneficiary_loan(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Create a new loan beneficiary."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/beneficiaries/tpt", auth=auth, data=data)


@mcp.tool(name="update_beneficiary_savings")
async def update_beneficiary_savings(
    beneficiary_id: int,
    data: Dict[str, Any],
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Update an existing savings beneficiary."""
    auth = get_auth_header(username, password)
    return await make_request(
        "PUT",
        f"/self/beneficiaries/tpt/{beneficiary_id}",
        auth=auth,
        data=data,
    )


@mcp.tool(name="update_beneficiary_loan")
async def update_beneficiary_loan(
    beneficiary_id: int,
    data: Dict[str, Any],
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Update an existing loan beneficiary."""
    auth = get_auth_header(username, password)
    return await make_request(
        "PUT",
        f"/self/beneficiaries/tpt/{beneficiary_id}",
        auth=auth,
        data=data,
    )


@mcp.tool(name="delete_beneficiary")
async def delete_beneficiary(beneficiary_id: int, username: str, password: str) -> Dict[str, Any]:
    """Delete a beneficiary."""
    auth = get_auth_header(username, password)
    return await make_request(
        "DELETE",
        f"/self/beneficiaries/tpt/{beneficiary_id}",
        auth=auth,
    )
