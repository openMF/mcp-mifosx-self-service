from mcp_app import mcp
from typing import Dict, Any
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="Transfer to Third Party (Template)")
async def get_transfer_template(username: str, password: str) -> Dict[str, Any]:
    """Transfer to Third Party (Template) - Retrieves template for third-party transfers."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/accounttransfers/template?type=tpt", auth=auth)


@mcp.tool(name="Transfer Between Accounts")
async def transfer_between_accounts(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Transfer Between Accounts - Executes a transfer between accounts."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/accounttransfers", auth=auth, data=data)


@mcp.tool(name="Transfer to Third Party")
async def transfer_third_party(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Transfer to Third Party - Executes a third-party transfer."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/accounttransfers?type=tpt", auth=auth, data=data)


@mcp.tool(name="Get Account Transfer Template")
async def get_account_transfer_template(savings_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Account Transfer Template - Retrieves template for account transfers from a specific savings account."""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET", f"/self/accounttransfers/template?fromAccountId={savings_id}&fromAccountType=2", auth=auth
    )


@mcp.tool(name="Get Third Party Transfer Template")
async def get_third_party_transfer_template(username: str, password: str) -> Dict[str, Any]:
    """Get Third Party Transfer Template - Retrieves template for third-party transfers."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/accounttransfers/template?type=tpt", auth=auth)


@mcp.tool(name="Make Third Party Transfer")
async def make_third_party_transfer(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Make Third Party Transfer - Executes a third-party transfer."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/accounttransfers?type=tpt", auth=auth, data=data)


@mcp.tool(name="Make Account Transfer")
async def make_account_transfer(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Make Account Transfer - Executes a transfer between accounts."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/accounttransfers", auth=auth, data=data)
