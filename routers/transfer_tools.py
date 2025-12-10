from mcp_app import mcp
from typing import Dict, Any
from utils.http import make_request
from utils.auth import get_auth_header

@mcp.tool()
async def get_transfer_template(username: str, password: str) -> Dict[str, Any]:
    """
    Get transfer template for third-party transfers

    Args:
        username: Username for authentication
        password: Password for authentication

    Returns:
        Transfer template with available options
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", '/self/accounttransfers/template?type="tpt"', auth=auth)


@mcp.tool()
async def make_third_party_transfer(
    from_account_id: str,
    from_account_type: str,
    from_client_id: int,
    from_office_id: int,
    to_account_id: str,
    to_account_type: int,
    to_client_id: int,
    to_office_id: int,
    transfer_amount: float,
    transfer_date: str,
    transfer_description: str,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """
    Make a third-party transfer

    Args:
        from_account_id: Source account ID
        from_account_type: Source account type
        from_client_id: Source client ID
        from_office_id: Source office ID
        to_account_id: Destination account ID
        to_account_type: Destination account type (1=Savings, 2=Loan)
        to_client_id: Destination client ID
        to_office_id: Destination office ID
        transfer_amount: Amount to transfer
        transfer_date: Transfer date (format: "dd MMMM yyyy")
        transfer_description: Transfer description
        username: Username for authentication
        password: Password for authentication

    Returns:
        Transfer confirmation details
    """
    auth = get_auth_header(username, password)
    data = {
        "toOfficeId": to_office_id,
        "toClientId": to_client_id,
        "toAccountType": to_account_type,
        "toAccountId": to_account_id,
        "transferAmount": transfer_amount,
        "transferDate": transfer_date,
        "transferDescription": transfer_description,
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
        "fromAccountId": from_account_id,
        "fromAccountType": from_account_type,
        "fromClientId": from_client_id,
        "fromOfficeId": from_office_id,
    }

    return await make_request("POST", '/self/accounttransfers?type="tpt"', auth=auth, data=data)
