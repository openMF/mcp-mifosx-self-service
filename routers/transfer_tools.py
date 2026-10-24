from mcp_app import mcp
from typing import Any, Dict, List, Optional, Union
from utils.http import make_request
from utils.auth import get_auth_header
from utils.stepup import resolve_step_up

TRANSFER_PATH = "/self/accounttransfers"
THIRD_PARTY_TRANSFER_PATH = "/self/accounttransfers?type=tpt"


async def _post_transfer(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """POST a transfer. If the bank asks for a verification code, confirm it with the user first."""
    auth = get_auth_header()
    result = await make_request("POST", endpoint, auth=auth, data=data)
    return await resolve_step_up(result, "POST", endpoint, auth=auth, data=data)


@mcp.tool(name="get_transfer_fees")
async def get_transfer_fees(
    transfer_type: Optional[str] = None,
    currency_code: Optional[str] = None,
    include_inactive: bool = False,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Get Transfer Fees - Lists the fee rules the bank has for transfers.

    Use it to show the user which fees exist (by transferType, currencyCode and transferMode).
    For the exact fee of a specific transfer, call get_transfer_quote: the bank calculates it,
    including thresholds and currency conversion. Do not calculate fees from feeValue yourself,
    its unit depends on the fee type. Optional filters: transfer_type (e.g. "PIN"),
    currency_code (e.g. "USD"). Only active fees are returned unless include_inactive is true.
    """
    auth = get_auth_header()
    result = await make_request("GET", "/self/transfer-fees", auth=auth)
    if not isinstance(result, list):
        return result
    fees = [fee for fee in result if isinstance(fee, dict)]
    if not include_inactive:
        fees = [fee for fee in fees if fee.get("isActive", True)]
    if transfer_type:
        fees = [fee for fee in fees if str(fee.get("transferType", "")).upper() == transfer_type.upper()]
    if currency_code:
        fees = [fee for fee in fees if str(fee.get("currencyCode", "")).upper() == currency_code.upper()]
    return fees


@mcp.tool(name="get_transfer_quote")
async def get_transfer_quote(
    from_account: str,
    transfer_amount: float,
    transfer_type: str,
    currency_code: str = "CRC",
    transfer_mode: str = "INSTANT",
    from_account_type: int = 2,
) -> Dict[str, Any]:
    """Get Transfer Quote - Asks the bank for the fee and total of a transfer. Does not move money.

    Call it before a transfer and show the fee and total to the user. from_account is the
    user's source account id (from_account_type 2 = savings). transfer_type is one of SAME_BANK,
    PIN, SINPE_MOVIL, LINK_PAGO; transfer_mode is INSTANT or T_PLUS_1; currency_code CRC or USD.
    """
    auth = get_auth_header()
    data = {
        "fromAccount": from_account,
        "fromAccountType": from_account_type,
        "transferAmount": transfer_amount,
        "transferType": transfer_type,
        "currencyCode": currency_code,
        "transferMode": transfer_mode,
    }
    return await make_request("POST", f"{TRANSFER_PATH}/quote", auth=auth, data=data)


@mcp.tool(name="transfer_to_third_party_template")
async def get_transfer_template() -> Dict[str, Any]:
    """Transfer to Third Party (Template) - Retrieves template for third-party transfers."""
    auth = get_auth_header()
    return await make_request("GET", "/self/accounttransfers/template?type=tpt", auth=auth)


@mcp.tool(name="transfer_between_accounts")
async def transfer_between_accounts(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transfer Between Accounts - Executes a transfer between accounts.

    May ask the user for a one-time verification code. The user types it, never you.
    """
    return await _post_transfer(TRANSFER_PATH, data)


@mcp.tool(name="transfer_to_third_party")
async def transfer_third_party(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transfer to Third Party - Executes a third-party transfer.

    May ask the user for a one-time verification code. The user types it, never you.
    """
    return await _post_transfer(THIRD_PARTY_TRANSFER_PATH, data)


@mcp.tool(name="get_account_transfer_template")
async def get_account_transfer_template(savings_id: int) -> Dict[str, Any]:
    """Get Account Transfer Template - Retrieves template for account transfers from a specific savings account."""
    auth = get_auth_header()
    return await make_request(
        "GET", f"/self/accounttransfers/template?fromAccountId={savings_id}&fromAccountType=2", auth=auth
    )


@mcp.tool(name="get_third_party_transfer_template")
async def get_third_party_transfer_template() -> Dict[str, Any]:
    """Get Third Party Transfer Template - Retrieves template for third-party transfers."""
    auth = get_auth_header()
    return await make_request("GET", "/self/accounttransfers/template?type=tpt", auth=auth)


@mcp.tool(name="make_third_party_transfer")
async def make_third_party_transfer(data: Dict[str, Any]) -> Dict[str, Any]:
    """Make Third Party Transfer - Executes a third-party transfer.

    May ask the user for a one-time verification code. The user types it, never you.
    """
    return await _post_transfer(THIRD_PARTY_TRANSFER_PATH, data)


@mcp.tool(name="make_account_transfer")
async def make_account_transfer(data: Dict[str, Any]) -> Dict[str, Any]:
    """Make Account Transfer - Executes a transfer between accounts.

    May ask the user for a one-time verification code. The user types it, never you.
    """
    return await _post_transfer(TRANSFER_PATH, data)
