from mcp_app import mcp
from typing import Dict, Any, Optional
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="Get List of Loan Products")
async def get_loan_products(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List of Loan Products"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/loanproducts?clientId={client_id}", auth=auth)


@mcp.tool(name="Get Detail of a Loan Product")
async def get_loan_product_details(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Detail of a Loan Product"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/loanproducts?clientId={client_id}&productId={product_id}", auth=auth)


@mcp.tool(name="Get Loan Account Details (With Associations Support)")
async def get_loan_details(
    loan_id: int, username: str, password: str, associations: Optional[str] = None
) -> Dict[str, Any]:
    """Get Loan Account Details - Supports associations (repaymentSchedule,transactions)."""
    auth = get_auth_header(username, password)
    path = f"/self/loans/{loan_id}"
    if associations:
        path += f"?associations={associations}"
    return await make_request("GET", path, auth=auth)


@mcp.tool(name="Get Loan Account Transaction Detail")
async def get_loan_transaction_details(
    loan_id: int, transaction_id: int, username: str, password: str
) -> Dict[str, Any]:
    """Get Loan Account Transaction Detail"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/loans/{loan_id}/transactions/{transaction_id}", auth=auth)


@mcp.tool(name="Get Loan Account Charges")
async def get_loan_charges(loan_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Loan Account Charges"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/loans/{loan_id}/charges", auth=auth)


@mcp.tool(name="Get Loan Account Template")
async def get_loan_template(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Loan Account Template"""
    auth = get_auth_header(username, password)
    return await make_request(
        "GET", f"/self/loans/template?clientId={client_id}&productId={product_id}&templateType=individual", auth=auth
    )


@mcp.tool(name="Request a New Loan Account (Calculate Loan Repayment Calendar)")
async def calculate_loan_schedule(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Request a New Loan Account (Calculate Loan Repayment Calendar)"""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/loans?command=calculateLoanSchedule", auth=auth, data=data)


@mcp.tool(name="Request a New Loan Account (Submit an Application)")
async def submit_loan_application(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Request a New Loan Account (Submit an Application)"""
    auth = get_auth_header(username, password)
    return await make_request("POST", "/self/loans", auth=auth, data=data)


@mcp.tool(name="Update a New Loan Account (Update an Application)")
async def update_loan_application(loan_id: int, data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Update a New Loan Account (Update an Application)"""
    auth = get_auth_header(username, password)
    return await make_request("PUT", f"/self/loans/{loan_id}", auth=auth, data=data)


@mcp.tool(name="Withdrawn Loan Account Application")
async def withdraw_loan_application(loan_id: int, note: str, username: str, password: str) -> Dict[str, Any]:
    """Withdrawn Loan Account Application"""
    auth = get_auth_header(username, password)
    data = {"withdrawnOnDate": "30 August 2025", "note": note, "dateFormat": "dd MMMM yyyy", "locale": "en"}
    return await make_request("POST", f"/self/loans/{loan_id}?command=withdrawnByApplicant", auth=auth, data=data)


@mcp.tool(name="Get Loan Account Details")
async def get_loan_details_alias(loan_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Loan Account Details - Retrieves basic detailed info."""
    return await get_loan_details(loan_id, username, password)


@mcp.tool(name="Get Loan with Associations")
async def get_loan_with_associations_alias(
    loan_id: int, username: str, password: str, associations: str = "repaymentSchedule,transactions"
) -> Dict[str, Any]:
    """Get Loan with Associations - Retrieves details (repaymentSchedule,transactions)."""
    return await get_loan_details(loan_id, username, password, associations=associations)


@mcp.tool(name="Get Loan Template")
async def get_loan_template_alias(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Loan Template - Retrieves template for individual loans."""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/loans/template?templateType=individual&clientId={client_id}", auth=auth)


@mcp.tool(name="Get Loan Template by Product")
async def get_loan_template_by_product(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Loan Template by Product - Template for specific product."""
    return await get_loan_template(client_id, product_id, username, password)


@mcp.tool(name="Create Loan Account")
async def create_loan_account_alias(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Create Loan Account - Submission of application."""
    return await submit_loan_application(data, username, password)


@mcp.tool(name="Update Loan Account")
async def update_loan_account_alias(loan_id: int, data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Update Loan Account - Updates existing application."""
    return await update_loan_application(loan_id, data, username, password)


@mcp.tool(name="Withdraw Loan Application")
async def withdraw_loan_application_alias(loan_id: int, note: str, username: str, password: str) -> Dict[str, Any]:
    """Withdraw Loan Application - Withdraws an application."""
    return await withdraw_loan_application(loan_id, note, username, password)


@mcp.tool(name="Get Loan Charges")
async def get_loan_charges_alias(loan_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Loan Charges - Retrieves charges for specific loan."""
    return await get_loan_charges(loan_id, username, password)
