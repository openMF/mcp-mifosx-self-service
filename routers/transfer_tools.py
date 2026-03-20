from typing import Any, Dict

from mcp_app import mcp
from utils.auth import get_auth_header
from utils.http import make_request


@mcp.tool(name="transfer_to_third_party_template")
async def get_transfer_template(username: str, password: str) -> Dict[str, Any]:
    """Transfer to Third Party (Template) - Retrieves template for third-party transfers."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/accounttransfers/template?type=tpt", auth=auth)


@mcp.tool(name="transfer_between_accounts")
async def transfer_between_accounts(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Transfer Between Accounts - Executes a transfer between accounts."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/accounttransfers", auth=auth, data=data)


@mcp.tool(name="transfer_to_third_party")
async def transfer_third_party(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Transfer to Third Party - Executes a third-party transfer."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/accounttransfers?type=tpt", auth=auth, data=data)


@mcp.tool(name="get_account_transfer_template")
async def get_account_transfer_template(savings_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Account Transfer Template - Retrieves template for account transfers from a specific savings account."""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET", f"/self/accounttransfers/template?fromAccountId={savings_id}&fromAccountType=2", auth=auth
    )


@mcp.tool(name="get_third_party_transfer_template")
async def get_third_party_transfer_template(username: str, password: str) -> Dict[str, Any]:
    """Get Third Party Transfer Template - Retrieves template for third-party transfers."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/accounttransfers/template?type=tpt", auth=auth)


@mcp.tool(name="make_third_party_transfer")
async def make_third_party_transfer(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Make Third Party Transfer - Executes a third-party transfer."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/accounttransfers?type=tpt", auth=auth, data=data)


@mcp.tool(name="make_account_transfer")
async def make_account_transfer(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Make Account Transfer - Executes a transfer between accounts."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/accounttransfers", auth=auth, data=data)
