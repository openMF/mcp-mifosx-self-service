from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from mcp_app import mcp
from utils import stepup, transfers
from utils.auth import get_auth_header
from utils.http import make_request

SHARE_ACCOUNTS_PATH = "/self/shareaccounts"
SHARE_APPLICATION = "share_application"

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
PREPARE = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False)
SUBMIT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
CANCEL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)


@mcp.tool(name="get_share_product_list")
async def get_shares_products(client_id: int) -> Dict[str, Any]:
    """Get List of Share Product"""
    auth = get_auth_header()
    return await make_request("GET", f"/self/products/share?clientId={client_id}", auth=auth)


@mcp.tool(name="get_share_product_details")
async def get_shares_product_details(product_id: int) -> Dict[str, Any]:
    """Get the details of one share product."""
    auth = get_auth_header()
    return await make_request("GET", f"/self/products/share/{product_id}", auth=auth)


@mcp.tool(name="get_share_account_template", annotations=READ_ONLY)
async def get_share_account_template(client_id: int, product_id: Optional[int] = None) -> Dict[str, Any]:
    """Get Share Account Template - The share products a client can apply for.

    Without product_id it lists the products (id, name). With product_id it returns that product's
    details: currency, unit price, minimum and maximum shares, lock-in period and charges.
    """
    auth = get_auth_header()
    path = f"{SHARE_ACCOUNTS_PATH}/template?clientId={client_id}"
    if product_id is not None:
        path += f"&productId={product_id}"
    return await make_request("GET", path, auth=auth)


@mcp.tool(name="get_share_account", annotations=READ_ONLY)
async def get_share_account(account_id: int) -> Dict[str, Any]:
    """Get Share Account - One share account or application of the user: status, shares, value, dividends."""
    auth = get_auth_header()
    return await make_request("GET", f"{SHARE_ACCOUNTS_PATH}/{account_id}", auth=auth)


def _code(value: Any) -> Optional[str]:
    return value.get("code") if isinstance(value, dict) else None


async def _savings_account(client_id: int, savings_account_id: int, auth: str) -> Union[Dict[str, Any], str]:
    """The client's active savings account with this id, or the reason it cannot be used."""
    accounts = await make_request("GET", f"/self/clients/{client_id}/accounts", auth=auth)
    if not isinstance(accounts, dict) or accounts.get("error"):
        return "Could not read the client's accounts."
    savings: List[Any] = accounts.get("savingsAccounts") or []
    for account in savings:
        if isinstance(account, dict) and account.get("id") == savings_account_id:
            status = account.get("status") if isinstance(account.get("status"), dict) else {}
            if not status.get("active"):
                return "The savings account is not active."
            return account
    return "The savings account is not one of the client's accounts."


@mcp.tool(name="prepare_share_application", annotations=PREPARE)
async def prepare_share_application(
    client_id: int, product_id: int, requested_shares: int, savings_account_id: int
) -> Dict[str, Any]:
    """Prepare Share Application - Step 1 of 2. Checks an application for shares and returns a summary.

    Submits nothing. savings_account_id is the client's active savings account in the product's currency
    (the bank uses it for share payments and dividends). Show the summary (product, shares, unit price,
    total) to the user. Only after the user says yes, call confirm_share_application with the
    confirmation_id. The id works once and expires after a few minutes.
    """
    if requested_shares <= 0:
        return transfers.failure(400, "The number of shares must be greater than zero.")
    auth = get_auth_header()
    template = await make_request(
        "GET", f"{SHARE_ACCOUNTS_PATH}/template?clientId={client_id}&productId={product_id}", auth=auth
    )
    if not isinstance(template, dict) or template.get("error"):
        return template if isinstance(template, dict) else transfers.failure(502, "Could not read the template.")
    options = template.get("productOptions") or []
    product = next((p for p in options if isinstance(p, dict) and p.get("id") == product_id), None)
    if product is None:
        return transfers.failure(404, f"Share product {product_id} is not available for this client.")

    minimum, maximum = product.get("minimumShares"), product.get("maximumShares")
    if isinstance(minimum, int) and requested_shares < minimum:
        return transfers.failure(400, f"The product needs at least {minimum} shares.")
    if isinstance(maximum, int) and requested_shares > maximum:
        return transfers.failure(400, f"The product allows at most {maximum} shares.")

    savings = await _savings_account(client_id, savings_account_id, auth)
    if isinstance(savings, str):
        return transfers.failure(400, savings)
    currency = _code(product.get("currency"))
    if currency and _code(savings.get("currency")) not in (None, currency):
        return transfers.failure(400, f"The savings account must be in {currency}, the product's currency.")

    summary: Dict[str, Any] = {
        "product": product.get("name"),
        "productId": product_id,
        "requestedShares": requested_shares,
        "currency": currency,
        "savingsAccount": savings.get("accountNo"),
    }
    unit_price = product.get("unitPrice")
    if isinstance(unit_price, (int, float)):
        summary["unitPrice"] = unit_price
        summary["total"] = float(Decimal(str(unit_price)) * requested_shares)
    today = transfers.format_date(transfers.today())
    data = {
        "clientId": client_id,
        "productId": product_id,
        "requestedShares": requested_shares,
        "savingsAccountId": savings_account_id,
        "submittedDate": today,
        "applicationDate": today,
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
    }
    total = f" ({summary['total']} {currency or ''})".rstrip() if "total" in summary else ""
    text = (
        f"application for {requested_shares} shares of {product.get('name')}{total}, "
        f"linked to savings account {savings.get('accountNo')}"
    )
    prepared = transfers.remember(SHARE_ACCOUNTS_PATH, data, summary, text, kind=SHARE_APPLICATION)
    return {
        "prepared": True,
        "executed": False,
        "confirmation_id": prepared.confirmation_id,
        "expires_in_seconds": transfers.ttl_seconds(),
        "application": summary,
        "message": (
            f"Nothing has been submitted yet. Show the user this {text}. Call confirm_share_application with the "
            "confirmation_id only after the user says yes, or cancel_share_application if they do not. The bank "
            "still has to approve the application."
        ),
    }


@mcp.tool(name="confirm_share_application", annotations=SUBMIT)
async def confirm_share_application(confirmation_id: str) -> Dict[str, Any]:
    """Confirm Share Application - Step 2 of 2. Submits an application prepared with prepare_share_application.

    Call it only after the user has seen the summary and said yes. The id works once. The client may show
    the user a confirmation form. The application then waits for the bank's approval.
    """
    prepared = transfers.take(confirmation_id, SHARE_APPLICATION)
    if prepared is None:
        return transfers.failure(
            404,
            "There is no prepared share application with this confirmation_id (it expired, was already used or "
            "was cancelled). Call prepare_share_application again.",
        )
    ctx = stepup._elicitation_context()
    if ctx is not None:
        # a client that offers forms but fails to show this one counts as "not confirmed"
        try:
            answer = await ctx.elicit(message=f"Submit this {prepared.text}?", schema=transfers.ConfirmApplicationForm)
        except Exception:
            answer = None
        if not (
            getattr(answer, "action", None) == "accept" and getattr(getattr(answer, "data", None), "confirm", False)
        ):
            return transfers.failure(
                400, "The user did not confirm the application. Nothing was submitted.", cancelled=True
            )
    result = await make_request("POST", prepared.endpoint, auth=get_auth_header(), data=prepared.data)
    if isinstance(result, dict) and not result.get("error"):
        return {"executed": True, "application": prepared.summary, **result}
    return result


@mcp.tool(name="cancel_share_application", annotations=CANCEL)
async def cancel_share_application(confirmation_id: str) -> Dict[str, Any]:
    """Cancel Share Application - Drops an application prepared with prepare_share_application."""
    prepared = transfers.take(confirmation_id, SHARE_APPLICATION)
    if prepared is None:
        return transfers.failure(404, "There is no prepared share application with this confirmation_id.")
    return {"cancelled": True, "executed": False, "application": prepared.summary}
