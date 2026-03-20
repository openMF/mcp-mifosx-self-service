from typing import Any, Dict, Optional

from mcp_app import mcp
from utils.auth import get_auth_header
from utils.http import make_request


@mcp.tool(name="get_guarantor_template")
async def get_guarantor_template(loan_id: int, username: str, password: str) -> Dict[str, Any]:
    """
    Get template for creating loan guarantors.
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/loans/{loan_id}/guarantors/template", auth=auth)


@mcp.tool(name="get_guarantor_list")
async def get_loan_guarantors(loan_id: int, username: str, password: str) -> Dict[str, Any]:
    """
    Get list of guarantors for a specific loan.
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/loans/{loan_id}/guarantors", auth=auth)


@mcp.tool(name="create_guarantor")
async def add_loan_guarantor(
    loan_id: int,
    guarantor_type: int,
    first_name: str,
    last_name: str,
    mobile_number: str,
    username: str,
    password: str,
    address_line1: Optional[str] = None,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add a new guarantor for a loan.
    - guarantor_type: 1 for Customer/Client, 3 for External.
    """
    auth = get_auth_header(username, password)
    data = {
        "guarantorType": guarantor_type,
        "firstName": first_name,
        "lastName": last_name,
        "mobileNumber": mobile_number,
        "addressLine1": address_line1,
        "city": city,
        "zip": zip_code,
        "locale": "en",
    }
    return await make_request("POST", f"/self/loans/{loan_id}/guarantors", auth=auth, data=data)


@mcp.tool(name="update_guarantor")
async def update_loan_guarantor(
    loan_id: int,
    guarantor_id: int,
    data: Dict[str, Any],
    username: str,
    password: str,
) -> Dict[str, Any]:
    """
    Update an existing loan guarantor.
    """
    auth = get_auth_header(username, password)
    return await make_request("PUT", f"/self/loans/{loan_id}/guarantors/{guarantor_id}", auth=auth, data=data)


@mcp.tool(name="delete_guarantor")
async def delete_loan_guarantor(loan_id: int, guarantor_id: int, username: str, password: str) -> Dict[str, Any]:
    """
    Delete a loan guarantor.
    """
    auth = get_auth_header(username, password)
    return await make_request("DELETE", f"/self/loans/{loan_id}/guarantors/{guarantor_id}", auth=auth)
