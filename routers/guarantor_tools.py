"""Guarantors of a loan application (US-E13-14), on the self-service endpoints added in selfservice-plugin #213.

The plugin's rules, which the tools explain before calling:

* Guarantors can be added, changed and removed only while the loan application is waiting for approval.
  After approval they are part of the bank's security for the loan and only bank staff change them.
* A savings account given as a guarantee must be the user's own. The bank holds the guarantee amount on it,
  so adding one goes through prepare + confirm, like a transfer.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Literal, Optional, Union

from mcp.types import ToolAnnotations

from mcp_app import mcp
from utils import stepup, transfers
from utils.auth import get_auth_header
from utils.http import make_request

SAVINGS_GUARANTEE = "savings_guarantee"
GUARANTOR_TYPES = {"customer": 1, "staff": 2, "external": 3}

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
PREPARE = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False)
SUBMIT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
CANCEL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
DELETE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)


def _guarantors_path(loan_id: int) -> str:
    return f"/self/loans/{loan_id}/guarantors"


async def _pending_loan(loan_id: int, auth: str) -> Union[Dict[str, Any], str]:
    """The user's loan if its application is still waiting for approval, else what is wrong."""
    loan = await make_request("GET", f"/self/loans/{loan_id}", auth=auth)
    if not isinstance(loan, dict) or loan.get("error"):
        return f"Loan {loan_id} was not found among the user's loans."
    if not (loan.get("status") or {}).get("pendingApproval"):
        return (
            f"Loan {loan_id} is no longer waiting for approval. Its guarantors can only be changed by the bank's "
            "staff now."
        )
    return loan


def _details(
    first_name: Optional[str],
    last_name: Optional[str],
    mobile_number: Optional[str],
    address_line1: Optional[str],
    city: Optional[str],
    zip_code: Optional[str],
    relationship_type_id: Optional[int],
) -> Dict[str, Any]:
    """The guarantor fields Fineract accepts (firstname/lastname, not firstName), leaving out empty ones."""
    fields = {
        "firstname": first_name,
        "lastname": last_name,
        "mobileNumber": mobile_number,
        "addressLine1": address_line1,
        "city": city,
        "zip": zip_code,
        "clientRelationshipTypeId": relationship_type_id,
    }
    return {key: value for key, value in fields.items() if value not in (None, "")}


@mcp.tool(name="get_guarantor_template", annotations=READ_ONLY)
async def get_guarantor_template(loan_id: int) -> Dict[str, Any]:
    """Get Guarantor Template - Guarantor types and relationship options for a loan of the user.

    allowedClientRelationshipTypes are the relationship_type_id values for create_guarantor.
    """
    auth = get_auth_header()
    return await make_request("GET", f"{_guarantors_path(loan_id)}/template", auth=auth)


@mcp.tool(name="get_guarantor_list", annotations=READ_ONLY)
async def get_loan_guarantors(loan_id: int) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Get Guarantor List - The guarantors of a loan of the user, with their guarantee funds."""
    auth = get_auth_header()
    return await make_request("GET", _guarantors_path(loan_id), auth=auth)


@mcp.tool(name="create_guarantor", annotations=WRITE)
async def add_loan_guarantor(
    loan_id: int,
    guarantor_type: Literal["customer", "staff", "external"],
    client_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    mobile_number: Optional[str] = None,
    address_line1: Optional[str] = None,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    relationship_type_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Create Guarantor - Adds a guarantor to a loan application that is waiting for approval.

    guarantor_type "customer" needs the guarantor's client_id, "staff" the staff_id, "external" (a person who
    is not a customer) first_name and last_name. Optional: mobile_number, address, relationship_type_id (from
    get_guarantor_template). No money is held: to pledge the user's own savings as a guarantee use
    prepare_savings_guarantee. Guarantors can only be added while the application is waiting for approval.
    """
    data: Dict[str, Any] = {"guarantorTypeId": GUARANTOR_TYPES[guarantor_type], "locale": "en"}
    if guarantor_type == "customer":
        if client_id is None:
            return transfers.failure(400, "A customer guarantor needs the guarantor's client_id.")
        data["entityId"] = client_id
    elif guarantor_type == "staff":
        if staff_id is None:
            return transfers.failure(400, "A staff guarantor needs the staff_id.")
        data["entityId"] = staff_id
    elif not (first_name and last_name):
        return transfers.failure(400, "An external guarantor needs first_name and last_name.")
    data.update(_details(first_name, last_name, mobile_number, address_line1, city, zip_code, relationship_type_id))

    auth = get_auth_header()
    loan = await _pending_loan(loan_id, auth)
    if isinstance(loan, str):
        return transfers.failure(400, loan)
    return await make_request("POST", _guarantors_path(loan_id), auth=auth, data=data)


@mcp.tool(name="update_guarantor", annotations=WRITE)
async def update_loan_guarantor(
    loan_id: int,
    guarantor_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    mobile_number: Optional[str] = None,
    address_line1: Optional[str] = None,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    relationship_type_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Update Guarantor - Changes the name, contact, address or relationship of a guarantor.

    Only the fields given are changed. Only while the loan application is waiting for approval; the
    guarantee amount cannot be changed here (remove the guarantee and prepare a new one).
    """
    data = _details(first_name, last_name, mobile_number, address_line1, city, zip_code, relationship_type_id)
    if not data:
        return transfers.failure(400, "Nothing to change: give at least one field.")
    auth = get_auth_header()
    loan = await _pending_loan(loan_id, auth)
    if isinstance(loan, str):
        return transfers.failure(400, loan)
    guarantors = await make_request("GET", _guarantors_path(loan_id), auth=auth)
    if isinstance(guarantors, dict) and guarantors.get("error"):
        return guarantors
    current = next(
        (g for g in guarantors or [] if isinstance(g, dict) and g.get("id") == guarantor_id and g.get("status")), None
    )
    if current is None:
        return transfers.failure(404, f"Loan {loan_id} has no active guarantor {guarantor_id}.")
    # Fineract needs the guarantor's type on every update (without it the request fails with a server error)
    type_id = (current.get("guarantorType") or {}).get("id")
    data["guarantorTypeId"] = type_id
    if type_id != GUARANTOR_TYPES["external"] and current.get("entityId"):
        data["entityId"] = current["entityId"]
    data["locale"] = "en"
    return await make_request("PUT", f"{_guarantors_path(loan_id)}/{guarantor_id}", auth=auth, data=data)


@mcp.tool(name="delete_guarantor", annotations=DELETE)
async def delete_loan_guarantor(
    loan_id: int, guarantor_id: int, guarantor_funding_id: Optional[int] = None
) -> Dict[str, Any]:
    """Delete Guarantor - Removes a guarantor, or only one of its guarantee funds (guarantor_funding_id).

    Only while the loan application is waiting for approval. Removing a savings guarantee releases the amount
    held on that savings account. Ask the user before removing a guarantor.
    """
    auth = get_auth_header()
    loan = await _pending_loan(loan_id, auth)
    if isinstance(loan, str):
        return transfers.failure(400, loan)
    path = f"{_guarantors_path(loan_id)}/{guarantor_id}"
    if guarantor_funding_id is not None:
        path += f"?guarantorFundingId={guarantor_funding_id}"
    return await make_request("DELETE", path, auth=auth)


# --- a savings guarantee holds money: prepare + confirm --------------------------------------------


@mcp.tool(name="prepare_savings_guarantee", annotations=PREPARE)
async def prepare_savings_guarantee(loan_id: int, savings_account_id: int, amount: float) -> Dict[str, Any]:
    """Prepare Savings Guarantee - Step 1 of 2. Checks a guarantee from the user's own savings account.

    Submits nothing. The bank holds the amount on that savings account while the loan is guaranteed, so the
    user cannot withdraw it. The account must be the user's own, active and in the loan's currency, and the
    loan application must be waiting for approval. Show the user the summary; only after they say yes call
    confirm_savings_guarantee with the confirmation_id (cancel_savings_guarantee if not).
    """
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        return transfers.failure(400, "The amount must be a number.")
    if not value.is_finite() or value <= 0:
        return transfers.failure(400, "The amount must be greater than zero.")
    auth = get_auth_header()
    loan = await _pending_loan(loan_id, auth)
    if isinstance(loan, str):
        return transfers.failure(400, loan)
    client_id = loan.get("clientId")
    accounts = await make_request("GET", f"/self/clients/{client_id}/accounts", auth=auth)
    if not isinstance(accounts, dict) or accounts.get("error"):
        return accounts if isinstance(accounts, dict) else transfers.failure(502, "Could not read the accounts.")
    savings = next(
        (s for s in accounts.get("savingsAccounts") or [] if isinstance(s, dict) and s.get("id") == savings_account_id),
        None,
    )
    if savings is None:
        return transfers.failure(400, f"Savings account {savings_account_id} is not one of the user's accounts.")
    if not (savings.get("status") or {}).get("active"):
        return transfers.failure(400, f"Savings account {savings.get('accountNo')} is not active.")
    loan_currency = (loan.get("currency") or {}).get("code")
    savings_currency = (savings.get("currency") or {}).get("code")
    if loan_currency and savings_currency and loan_currency != savings_currency:
        return transfers.failure(400, f"The savings account must be in {loan_currency}, the loan's currency.")
    balance = savings.get("accountBalance")
    if isinstance(balance, (int, float)) and value > Decimal(str(balance)):
        return transfers.failure(400, f"The savings account has only {balance} {savings_currency or ''}".rstrip() + ".")

    data = {
        "guarantorTypeId": GUARANTOR_TYPES["customer"],
        "entityId": client_id,
        "savingsId": savings_account_id,
        "amount": float(value),
        "locale": "en",
    }
    summary = {
        "loanId": loan_id,
        "loanAccount": loan.get("accountNo"),
        "savingsAccount": savings.get("accountNo"),
        "amount": float(value),
        "currency": savings_currency,
    }
    text = (
        f"guarantee of {value:f} {savings_currency or ''} held on savings account {savings.get('accountNo')} "
        f"for loan {loan.get('accountNo') or loan_id}"
    ).replace("  ", " ")
    prepared = transfers.remember(_guarantors_path(loan_id), data, summary, text, kind=SAVINGS_GUARANTEE)
    return {
        "prepared": True,
        "executed": False,
        "confirmation_id": prepared.confirmation_id,
        "expires_in_seconds": transfers.ttl_seconds(),
        "guarantee": summary,
        "message": (
            f"Nothing has been submitted yet. Show the user this {text}: the amount stays blocked on the account "
            "while it guarantees the loan. Call confirm_savings_guarantee with the confirmation_id only after the "
            "user says yes, or cancel_savings_guarantee if they do not."
        ),
    }


@mcp.tool(name="confirm_savings_guarantee", annotations=SUBMIT)
async def confirm_savings_guarantee(confirmation_id: str) -> Dict[str, Any]:
    """Confirm Savings Guarantee - Step 2 of 2. Adds a guarantee prepared with prepare_savings_guarantee.

    Call it only after the user has seen the summary and said yes. The id works once. The client may show
    the user a confirmation form.
    """
    prepared = transfers.take(confirmation_id, SAVINGS_GUARANTEE)
    if prepared is None:
        return transfers.failure(
            404,
            "There is no prepared savings guarantee with this confirmation_id (it expired, was already used or was "
            "cancelled). Call prepare_savings_guarantee again.",
        )
    ctx = stepup._elicitation_context()
    if ctx is not None:
        # a client that offers forms but fails to show this one counts as "not confirmed"
        try:
            answer = await ctx.elicit(message=f"Add this {prepared.text}?", schema=transfers.ConfirmApplicationForm)
        except Exception:
            answer = None
        if not (
            getattr(answer, "action", None) == "accept" and getattr(getattr(answer, "data", None), "confirm", False)
        ):
            return transfers.failure(400, "The user did not confirm the guarantee. Nothing was added.", cancelled=True)
    result = await make_request("POST", prepared.endpoint, auth=get_auth_header(), data=prepared.data)
    if isinstance(result, dict) and not result.get("error"):
        return {"executed": True, "guarantee": prepared.summary, **result}
    return result


@mcp.tool(name="cancel_savings_guarantee", annotations=CANCEL)
async def cancel_savings_guarantee(confirmation_id: str) -> Dict[str, Any]:
    """Cancel Savings Guarantee - Drops a guarantee prepared with prepare_savings_guarantee."""
    prepared = transfers.take(confirmation_id, SAVINGS_GUARANTEE)
    if prepared is None:
        return transfers.failure(404, "There is no prepared savings guarantee with this confirmation_id.")
    return {"cancelled": True, "executed": False, "guarantee": prepared.summary}
