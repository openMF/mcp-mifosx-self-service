from mcp_app import mcp
from typing import Dict, Any, Optional
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="get_loan_products")
async def get_loan_products(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Retrieve available loan products."""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/loanproducts?clientId={client_id}",
        auth=auth,
    )


@mcp.tool(name="get_loan_product_details")
async def get_loan_product_details(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Retrieve loan product details."""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/loanproducts?clientId={client_id}&productId={product_id}",
        auth=auth,
    )


@mcp.tool(name="get_loan_account_details")
async def get_loan_account_details(
    loan_id: int,
    username: str,
    password: str,
    associations: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve loan account details (optional associations)."""
    auth = get_auth_header(username, password)

    path = f"/self/loans/{loan_id}"
    if associations:
        path += f"?associations={associations}"

    return await make_request("GET", path, auth=auth)


@mcp.tool(name="get_loan_transaction_detail")
async def get_loan_transaction_detail(
    loan_id: int, transaction_id: int, username: str, password: str
) -> Dict[str, Any]:
    """Retrieve loan transaction detail."""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/loans/{loan_id}/transactions/{transaction_id}",
        auth=auth,
    )


@mcp.tool(name="get_loan_account_charges")
async def get_loan_account_charges(loan_id: int, username: str, password: str) -> Dict[str, Any]:
    """Retrieve loan charges."""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/loans/{loan_id}/charges",
        auth=auth,
    )


@mcp.tool(name="get_loan_template")
async def get_loan_template(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Retrieve loan application template."""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET",
        f"/self/loans/template?clientId={client_id}&productId={product_id}&templateType=individual",
        auth=auth,
    )


@mcp.tool(name="calculate_loan_repayment_calendar")
async def calculate_loan_repayment_calendar(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Calculate loan repayment schedule."""
    auth = get_auth_header(username, password)
    return await make_request(
        "POST",
        "/self/loans?command=calculateLoanSchedule",
        auth=auth,
        data=data,
    )


@mcp.tool(name="submit_loan_application")
async def submit_loan_application(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Submit loan application."""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/loans", auth=auth, data=data)


@mcp.tool(name="update_loan_application")
async def update_loan_application(loan_id: int, data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Update loan application."""
    auth = get_auth_header(username, password)
    return await make_request(
        "PUT",
        f"/self/loans/{loan_id}",
        auth=auth,
        data=data,
    )


@mcp.tool(name="withdraw_loan_application")
async def withdraw_loan_application(loan_id: int, note: str, username: str, password: str) -> Dict[str, Any]:
    """Withdraw loan application."""
    auth = get_auth_header(username, password)

    data = {
        "withdrawnOnDate": "30 August 2025",
        "note": note,
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
    }

    return await make_request(
        "POST",
        f"/self/loans/{loan_id}?command=withdrawnByApplicant",
        auth=auth,
        data=data,
    )
