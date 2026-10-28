from typing import Any, Dict, List, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_app import mcp
from utils.auth import SECRET_LOGIN_FIELDS, get_auth_header
from utils.http import make_request

POCKETS_PATH = "/self/pockets"
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
POCKET_CHANGE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)

# Fields of /self/userdetails that are credentials and must not reach the AI.
SECRET_USER_FIELDS = (*SECRET_LOGIN_FIELDS, "accessToken")


class PocketAccount(BaseModel):
    account_id: int = Field(description="The account id")
    account_type: Literal["loan", "savings", "shares"] = Field(description="loan, savings or shares")


@mcp.tool(name="get_user_details", annotations=READ_ONLY)
async def get_user_details() -> Dict[str, Any]:
    """Get User Details - The logged-in self-service user: username, roles, permissions and linked clients.

    Only banks that log in with OAuth offer this. For the client's own profile (name, contact, office,
    status) use get_clients_linked_to_user and get_client_details.
    """
    result = await make_request("GET", "/self/userdetails", auth=get_auth_header())
    if isinstance(result, dict) and result.get("error") and result.get("status_code") == 404:
        return {
            "error": True,
            "status_code": 404,
            "message": (
                "This bank does not offer user details (it is only available with OAuth login). Use "
                "get_clients_linked_to_user and get_client_details for the client's profile."
            ),
        }
    if isinstance(result, dict):
        return {k: v for k, v in result.items() if k not in SECRET_USER_FIELDS}
    return result


@mcp.tool(name="get_pockets", annotations=READ_ONLY)
async def get_pockets() -> Dict[str, Any]:
    """Get Pockets - The accounts the user saved as favourites (pockets), by type.

    Each entry has the mapping id (needed to remove it), the account id and the account number.
    """
    result = await make_request("GET", POCKETS_PATH, auth=get_auth_header())
    if isinstance(result, dict) and result.get("status_code") == 204:
        # the bank answers 204 No Content when nothing is saved yet
        return {"loanAccounts": [], "savingsAccounts": [], "shareAccounts": []}
    return result


@mcp.tool(name="add_accounts_to_pocket", annotations=POCKET_CHANGE)
async def add_accounts_to_pocket(accounts: List[PocketAccount]) -> Dict[str, Any]:
    """Add Accounts to Pocket - Saves the user's own loan, savings or share accounts as favourites.

    Moves no money. Only the user's own accounts can be added.
    """
    if not accounts:
        return {"error": True, "status_code": 400, "message": "Give at least one account."}
    data = {"accountsDetail": [{"accountId": a.account_id, "accountType": a.account_type} for a in accounts]}
    return await make_request("POST", f"{POCKETS_PATH}?command=linkAccounts", auth=get_auth_header(), data=data)


@mcp.tool(name="remove_accounts_from_pocket", annotations=POCKET_CHANGE)
async def remove_accounts_from_pocket(mapping_ids: List[int]) -> Dict[str, Any]:
    """Remove Accounts from Pocket - Removes favourites by their mapping id (the "id" from get_pockets).

    Moves no money and does not close the accounts.
    """
    if not mapping_ids:
        return {"error": True, "status_code": 400, "message": "Give at least one mapping id from get_pockets."}
    return await make_request(
        "POST",
        f"{POCKETS_PATH}?command=delinkAccounts",
        auth=get_auth_header(),
        data={"pocketAccountMappingIds": list(mapping_ids)},
    )
