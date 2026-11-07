from typing import Any, Dict, Optional, Union

from mcp.types import ToolAnnotations

from mcp_app import mcp
from utils import stepup, transfers
from utils.auth import get_auth_header
from utils.http import make_request


@mcp.tool(name="get_savings_products")
async def get_savings_products(client_id: int) -> Dict[str, Any]:
    """Get List of Savings Products"""
    auth = get_auth_header()
    return await make_request("GET", f"/self/savingsproducts?clientId={client_id}", auth=auth)


@mcp.tool(name="get_savings_product_details")
async def get_savings_product_details(product_id: int) -> Dict[str, Any]:
    """Get the details of one savings product."""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/savingsproducts/{product_id}",
        auth=auth,
    )


@mcp.tool(name="get_savings_account_details")
async def get_savings_details(
    savings_id: int,
    associations: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Detail of Savings Account - Supports associations (transactions,charges)."""
    auth = get_auth_header()

    path = f"/self/savingsaccounts/{savings_id}"
    if associations:
        path += f"?associations={associations}"

    return await make_request("GET", path, auth=auth)


@mcp.tool(name="get_savings_account_transactions")
async def get_savings_transactions(
    savings_id: int,
) -> Dict[str, Any]:
    """Get List Savings Account Transactions"""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/savingsaccounts/{savings_id}?associations=transactions",
        auth=auth,
    )


@mcp.tool(name="get_savings_account_transaction_details")
async def get_savings_transaction_details(
    savings_id: int,
    transaction_id: int,
) -> Dict[str, Any]:
    """Get Detail of Savings Account Transaction"""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/savingsaccounts/{savings_id}/transactions/{transaction_id}",
        auth=auth,
    )


@mcp.tool(name="get_savings_account_charges")
async def get_savings_charges(
    savings_id: int,
) -> Dict[str, Any]:
    """Get List of Savings Account Charges"""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/savingsaccounts/{savings_id}/charges",
        auth=auth,
    )


@mcp.tool(name="get_savings_account_template_raw")
async def get_savings_template_raw(
    client_id: int,
    product_id: int,
) -> Dict[str, Any]:
    """Get Savings Account Template (Raw)"""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/savingsaccounts/template?clientId={client_id}&productId={product_id}",
        auth=auth,
    )


SAVINGS_PATH = "/self/savingsaccounts"
SAVINGS_APPLICATION = "savings_application"

PREPARE = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False)
SUBMIT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
CANCEL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)


def _failure(status_code: int, message: str, **extra: Any) -> Dict[str, Any]:
    return {"error": True, "status_code": status_code, "message": message, "executed": False, **extra}


def _option(options: Any, option_id: int) -> Optional[Dict[str, Any]]:
    return next((o for o in options or [] if isinstance(o, dict) and o.get("id") == option_id), None)


async def _product_template(client_id: int, product_id: int, auth: str) -> Union[Dict[str, Any], str]:
    """The savings template for this client and product, or the reason the product cannot be used."""
    template = await make_request("GET", f"{SAVINGS_PATH}/template?clientId={client_id}", auth=auth)
    if not isinstance(template, dict) or template.get("error"):
        return template if isinstance(template, dict) else "Could not read the savings template."
    if _option(template.get("productOptions"), product_id) is None:
        names = ", ".join(f"{o.get('id')} {o.get('name')}" for o in template.get("productOptions") or [])
        return f"Savings product {product_id} is not offered to this client. Offered: {names or 'none'}."
    detail = await make_request(
        "GET", f"{SAVINGS_PATH}/template?clientId={client_id}&productId={product_id}", auth=auth
    )
    return detail if isinstance(detail, dict) else "Could not read the savings product."


def _summary(detail: Dict[str, Any], product_id: int) -> Dict[str, Any]:
    product = _option(detail.get("productOptions"), product_id) or {}
    currency = detail.get("currency") if isinstance(detail.get("currency"), dict) else {}
    summary: Dict[str, Any] = {
        "product": product.get("name"),
        "productId": product_id,
        "client": detail.get("clientName"),
        "currency": currency.get("code"),
        "nominalAnnualInterestRate": detail.get("nominalAnnualInterestRate"),
    }
    for key in ("minRequiredOpeningBalance", "lockinPeriodFrequency"):
        if detail.get(key) is not None:
            summary[key] = detail[key]
    lockin_type = detail.get("lockinPeriodFrequencyType")
    if isinstance(lockin_type, dict) and "lockinPeriodFrequency" in summary:
        summary["lockinPeriodFrequencyType"] = lockin_type.get("value")
    charges = [c.get("name") for c in detail.get("charges") or [] if isinstance(c, dict)]
    if charges:
        summary["charges"] = charges
    return summary


@mcp.tool(name="prepare_savings_application", annotations=PREPARE)
async def prepare_savings_application(
    client_id: int,
    product_id: int,
    field_officer_id: Optional[int] = None,
    external_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare Savings Application - Step 1 of 2. Checks an application for a savings account.

    Submits nothing. The product must be one the bank offers this client (see get_savings_products).
    Show the returned summary (product, currency, interest rate, minimum opening balance, lock-in, charges)
    to the user. Only after the user says yes, call confirm_savings_application with the confirmation_id.
    The id works once and expires after a few minutes. The bank still has to approve the application.
    """
    auth = get_auth_header()
    detail = await _product_template(client_id, product_id, auth)
    if isinstance(detail, str):
        return _failure(400, detail)
    if detail.get("error"):
        return detail
    if field_officer_id is not None and _option(detail.get("fieldOfficerOptions"), field_officer_id) is None:
        return _failure(400, f"Field officer {field_officer_id} is not one of the bank's officers for this product.")
    external_id = (external_id or "").strip() or None
    if external_id and len(external_id) > 100:
        return _failure(400, "The external id can have at most 100 characters.")

    summary = _summary(detail, product_id)
    data: Dict[str, Any] = {
        "clientId": client_id,
        "productId": product_id,
        "submittedOnDate": transfers.format_date(transfers.today()),
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
    }
    if field_officer_id is not None:
        data["fieldOfficerId"] = field_officer_id
    if external_id:
        data["externalId"] = external_id
    text = f"application for a {summary['product']} savings account ({summary['currency']}) for {summary['client']}"
    prepared = transfers.remember(SAVINGS_PATH, data, summary, text, kind=SAVINGS_APPLICATION)
    return {
        "prepared": True,
        "executed": False,
        "confirmation_id": prepared.confirmation_id,
        "expires_in_seconds": transfers.ttl_seconds(),
        "application": summary,
        "message": (
            f"Nothing has been submitted yet. Show the user this {text}. Call confirm_savings_application with the "
            "confirmation_id only after the user says yes, or cancel_savings_application if they do not."
        ),
    }


async def _person_confirms(text: str) -> Optional[bool]:
    """Ask in the client's form. None: the client cannot show forms. A form that fails counts as no."""
    ctx = stepup._elicitation_context()
    if ctx is None:
        return None
    try:
        answer = await ctx.elicit(message=f"Submit this {text}?", schema=transfers.ConfirmApplicationForm)
    except Exception:
        return False
    return getattr(answer, "action", None) == "accept" and bool(getattr(answer.data, "confirm", False))


@mcp.tool(name="confirm_savings_application", annotations=SUBMIT)
async def confirm_savings_application(confirmation_id: str) -> Dict[str, Any]:
    """Confirm Savings Application - Step 2 of 2. Submits an application prepared with prepare_savings_application.

    Call it only after the user has seen the summary and said yes. The id works once.
    """
    prepared = transfers.take(confirmation_id, SAVINGS_APPLICATION)
    if prepared is None:
        return _failure(
            404,
            "There is no prepared savings application with this confirmation_id (it expired, was already used or "
            "was cancelled). Call prepare_savings_application again.",
        )
    if await _person_confirms(prepared.text) is False:
        return _failure(400, "The user did not confirm the application. Nothing was submitted.", cancelled=True)
    result = await make_request("POST", prepared.endpoint, auth=get_auth_header(), data=prepared.data)
    if isinstance(result, dict) and not result.get("error"):
        return {"executed": True, "application": prepared.summary, **result}
    return result


@mcp.tool(name="cancel_savings_application", annotations=CANCEL)
async def cancel_savings_application(confirmation_id: str) -> Dict[str, Any]:
    """Cancel Savings Application - Drops an application prepared with prepare_savings_application."""
    prepared = transfers.take(confirmation_id, SAVINGS_APPLICATION)
    if prepared is None:
        return _failure(404, "There is no prepared savings application with this confirmation_id.")
    return {"cancelled": True, "executed": False, "application": prepared.summary}


@mcp.tool(name="update_savings_account_application")
async def update_savings_application(
    savings_id: int,
    product_id: Optional[int] = None,
    field_officer_id: Optional[int] = None,
    external_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a Savings Account Application - Changes the product, field officer or external id of an application.

    Only applications that are still waiting for approval can be changed. The account always stays with its own
    client: the client id is taken from the account, never from the request.
    """
    if product_id is None and field_officer_id is None and external_id is None:
        return _failure(400, "Give at least one of product_id, field_officer_id or external_id.")
    auth = get_auth_header()
    account = await make_request("GET", f"{SAVINGS_PATH}/{savings_id}", auth=auth)
    if not isinstance(account, dict) or account.get("error"):
        return account if isinstance(account, dict) else _failure(502, "Could not read the savings account.")
    status = account.get("status") if isinstance(account.get("status"), dict) else {}
    if not status.get("submittedAndPendingApproval"):
        return _failure(400, "Only an application that is waiting for approval can be changed.")
    client_id = account.get("clientId")
    if product_id is not None:
        detail = await _product_template(client_id, product_id, auth)
        if isinstance(detail, str):
            return _failure(400, detail)
        if detail.get("error"):
            return detail
    data: Dict[str, Any] = {"clientId": client_id, "dateFormat": "dd MMMM yyyy", "locale": "en"}
    if product_id is not None:
        data["productId"] = product_id
    if field_officer_id is not None:
        data["fieldOfficerId"] = field_officer_id
    if external_id is not None:
        data["externalId"] = external_id.strip()
    return await make_request("PUT", f"{SAVINGS_PATH}/{savings_id}", auth=auth, data=data)
