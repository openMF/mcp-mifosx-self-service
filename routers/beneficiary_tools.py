"""Beneficiaries (US-E13-10): accounts at the same bank the user can send third-party transfers to.

A beneficiary is where money can be sent later, so adding one and changing one (its name or transfer
limit) are two steps, like transfers: ``prepare_*`` checks the request and shows it, ``confirm_beneficiary``
saves it once the user said yes. The tools take typed fields; the request sent to the bank is built here.
"""

from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from mcp_app import mcp
from utils import stepup, transfers
from utils.auth import get_auth_header
from utils.http import make_request

BENEFICIARIES_PATH = "/self/beneficiaries/tpt"
NEW_BENEFICIARY = "beneficiary"
BENEFICIARY_CHANGE = "beneficiary_change"
# The plugin's limit for the name, office name and account number
MAX_TEXT_LENGTH = 50
ACCOUNT_TYPES = {"savings": transfers.SAVINGS, "loan": transfers.LOAN}

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
PREPARE = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False)
SAVE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
CANCEL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
DELETE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True)


@mcp.tool(name="get_beneficiary_template", annotations=READ_ONLY)
async def get_beneficiary_template() -> Dict[str, Any]:
    """Get Beneficiary Template - The account types a beneficiary can have (savings, loan)."""
    auth = get_auth_header()
    return await make_request("GET", f"{BENEFICIARIES_PATH}/template", auth=auth)


@mcp.tool(name="get_beneficiary_list", annotations=READ_ONLY)
async def get_beneficiary_list() -> Any:
    """Get Beneficiary List - The user's saved beneficiaries, with their id, account and transfer limit."""
    auth = get_auth_header()
    return await make_request("GET", BENEFICIARIES_PATH, auth=auth)


def _text(label: str, value: Optional[str]) -> Union[str, Dict[str, Any]]:
    """The value without surrounding spaces, or a failure when it is empty or too long."""
    value = (value or "").strip()
    if not value:
        return transfers.failure(400, f"The {label} is required.")
    if len(value) > MAX_TEXT_LENGTH:
        return transfers.failure(400, f"The {label} can have at most {MAX_TEXT_LENGTH} characters.")
    return value


def _limit(transfer_limit: Optional[int]) -> Optional[Dict[str, Any]]:
    if transfer_limit is not None and transfer_limit <= 0:
        return transfers.failure(400, "The transfer limit must be a whole number greater than zero.")
    return None


async def _office_name(office_name: str, auth: str) -> Union[str, Dict[str, Any]]:
    """The bank's spelling of the office (it must match exactly), or a failure listing the offices."""
    offices = await make_request("GET", "/self/offices", auth=auth)
    if not isinstance(offices, list):
        return offices if isinstance(offices, dict) else transfers.failure(502, "Could not read the offices.")
    names = [o.get("name") for o in offices if isinstance(o, dict) and o.get("name")]
    match = next((n for n in names if n.casefold() == office_name.casefold()), None)
    if match is None:
        return transfers.failure(
            400, f"There is no office called {office_name}. Offices: {', '.join(names) or 'none'}."
        )
    return match


async def _own_currency(auth: str) -> Union[str, Dict[str, Any]]:
    """The currency of the user's own accounts when they all use one, else a failure asking for it."""
    clients = await make_request("GET", "/self/clients", auth=auth)
    if not isinstance(clients, dict) or clients.get("error"):
        return clients if isinstance(clients, dict) else transfers.failure(502, "Could not read the user's clients.")
    currencies = set()
    for client in clients.get("pageItems") or []:
        accounts = await make_request("GET", f"/self/clients/{client.get('id')}/accounts", auth=auth)
        if not isinstance(accounts, dict) or accounts.get("error"):
            continue
        for account in (accounts.get("savingsAccounts") or []) + (accounts.get("loanAccounts") or []):
            code = (account.get("currency") or {}).get("code") if isinstance(account, dict) else None
            if code:
                currencies.add(code)
    if len(currencies) != 1:
        found = f" (the user's accounts use {', '.join(sorted(currencies))})" if currencies else ""
        return transfers.failure(400, f"Pass the currency of the beneficiary's account{found}.")
    return currencies.pop()


def _prepared_reply(prepared: transfers.PreparedTransfer, what: str) -> Dict[str, Any]:
    return {
        "prepared": True,
        "executed": False,
        "confirmation_id": prepared.confirmation_id,
        "expires_in_seconds": transfers.ttl_seconds(),
        "beneficiary": prepared.summary,
        "message": (
            f"Nothing has been saved yet. Show the user {what}: {prepared.text}. Call confirm_beneficiary with "
            "the confirmation_id only after the user says yes, or cancel_beneficiary if they do not."
        ),
    }


@mcp.tool(name="prepare_beneficiary", annotations=PREPARE)
async def prepare_beneficiary(
    name: str,
    account_number: str,
    office_name: str,
    account_type: str,
    transfer_limit: Optional[int] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare Beneficiary - Step 1 of 2. Checks a new beneficiary (an account at the same bank). Saves nothing.

    account_type is "savings" or "loan" (the beneficiary's account), office_name is the office of the
    account holder (see get_offices), transfer_limit is the most that can be sent to it in one transfer (a
    whole number; none means no limit of its own). The currency defaults to the one the user's own accounts
    use. Money can be sent to a beneficiary later, so show the user the name, account, office and limit, and
    only after the user says yes call confirm_beneficiary with the confirmation_id (cancel_beneficiary if
    not). The id works once and expires after a few minutes.
    """
    name_value = _text("name", name)
    if isinstance(name_value, dict):
        return name_value
    number = _text("account number", account_number)
    if isinstance(number, dict):
        return number
    office = _text("office name", office_name)
    if isinstance(office, dict):
        return office
    type_id = ACCOUNT_TYPES.get((account_type or "").strip().lower())
    if type_id is None:
        return transfers.failure(400, 'The account type must be "savings" or "loan".')
    problem = _limit(transfer_limit)
    if problem:
        return problem
    if currency is not None and (len(currency.strip()) != 3 or not currency.strip().isalpha()):
        return transfers.failure(400, "The currency must be a three-letter code such as USD.")

    auth = get_auth_header()
    template = await make_request("GET", f"{BENEFICIARIES_PATH}/template", auth=auth)
    if not isinstance(template, dict) or template.get("error"):
        return template if isinstance(template, dict) else transfers.failure(502, "Could not read the template.")
    offered: List[Any] = [o.get("id") for o in template.get("accountTypeOptions") or [] if isinstance(o, dict)]
    if type_id not in offered:
        return transfers.failure(400, f"The bank does not offer {account_type} accounts as beneficiaries.")
    office = await _office_name(office, auth)
    if isinstance(office, dict):
        return office
    code = currency.strip().upper() if currency else await _own_currency(auth)
    if isinstance(code, dict):
        return code

    data: Dict[str, Any] = {
        "name": name_value,
        "accountNumber": number,
        "officeName": office,
        "accountType": type_id,
        "paymentType": "SAME_BANK",
        "currency": code,
        "locale": "en",
    }
    if transfer_limit is not None:
        data["transferLimit"] = transfer_limit
    summary = {
        "name": name_value,
        "accountNumber": number,
        "accountType": account_type.strip().lower(),
        "officeName": office,
        "currency": code,
        "transferLimit": transfer_limit,
    }
    limit_text = f"transfer limit {transfer_limit} {code}" if transfer_limit is not None else "no transfer limit"
    text = f"new beneficiary {name_value}, {summary['accountType']} account {number} at {office}, {limit_text}"
    prepared = transfers.remember(BENEFICIARIES_PATH, data, summary, text, kind=NEW_BENEFICIARY)
    return _prepared_reply(prepared, "this new beneficiary")


@mcp.tool(name="prepare_beneficiary_change", annotations=PREPARE)
async def prepare_beneficiary_change(
    beneficiary_id: int, name: Optional[str] = None, transfer_limit: Optional[int] = None
) -> Dict[str, Any]:
    """Prepare Beneficiary Change - Step 1 of 2. Checks a new name or transfer limit for a beneficiary.

    Saves nothing. The bank only lets the name and the transfer limit change; to point to another account,
    delete the beneficiary and add a new one. Show the user the change (old and new values) and only after
    the user says yes call confirm_beneficiary with the confirmation_id (cancel_beneficiary if not).
    """
    if name is None and transfer_limit is None:
        return transfers.failure(400, "Pass a new name, a new transfer limit, or both.")
    changes: Dict[str, Any] = {}
    if name is not None:
        new_name = _text("name", name)
        if isinstance(new_name, dict):
            return new_name
        changes["name"] = new_name
    problem = _limit(transfer_limit)
    if problem:
        return problem
    if transfer_limit is not None:
        changes["transferLimit"] = transfer_limit

    auth = get_auth_header()
    beneficiaries = await make_request("GET", BENEFICIARIES_PATH, auth=auth)
    if not isinstance(beneficiaries, list):
        if isinstance(beneficiaries, dict):
            return beneficiaries
        return transfers.failure(502, "Could not read the beneficiaries.")
    current = next((b for b in beneficiaries if isinstance(b, dict) and b.get("id") == beneficiary_id), None)
    if current is None:
        return transfers.failure(404, f"Beneficiary {beneficiary_id} is not one of the user's beneficiaries.")

    parts = []
    if "name" in changes:
        parts.append(f"name {current.get('name')} -> {changes['name']}")
    if "transferLimit" in changes:
        parts.append(f"transfer limit {current.get('transferLimit') or 'none'} -> {changes['transferLimit']}")
    summary = {
        "id": beneficiary_id,
        "name": current.get("name"),
        "accountNumber": current.get("accountNumber"),
        "officeName": current.get("officeName"),
        "changes": changes,
    }
    text = f"change to beneficiary {current.get('name')} (account {current.get('accountNumber')}): {', '.join(parts)}"
    # The bank sets a field that is not sent to empty: a rename alone would drop the transfer limit (no limit
    # at all) and a limit alone fails. So both are always sent, the unchanged one with its current value. The
    # bank refuses any other field on a change, the locale included.
    data: Dict[str, Any] = {"name": changes.get("name", current.get("name"))}
    limit = changes.get("transferLimit", current.get("transferLimit"))
    if limit:
        data["transferLimit"] = limit
    prepared = transfers.remember(
        f"{BENEFICIARIES_PATH}/{beneficiary_id}", data, summary, text, kind=BENEFICIARY_CHANGE
    )
    return _prepared_reply(prepared, "this change")


def _take(confirmation_id: str) -> Optional[transfers.PreparedTransfer]:
    return transfers.take(confirmation_id, NEW_BENEFICIARY) or transfers.take(confirmation_id, BENEFICIARY_CHANGE)


@mcp.tool(name="confirm_beneficiary", annotations=SAVE)
async def confirm_beneficiary(confirmation_id: str) -> Dict[str, Any]:
    """Confirm Beneficiary - Step 2 of 2. Saves a beneficiary or a change prepared with prepare_beneficiary
    or prepare_beneficiary_change.

    Call it only after the user has seen it and said yes. The id works once. The client may show the user a
    confirmation form.
    """
    prepared = _take(confirmation_id)
    if prepared is None:
        return transfers.failure(
            404,
            "There is nothing prepared with this confirmation_id (it expired, was already used or was cancelled). "
            "Call prepare_beneficiary or prepare_beneficiary_change again.",
        )
    ctx = stepup._elicitation_context()
    if ctx is not None:
        # a client that offers forms but fails to show this one counts as "not confirmed"
        try:
            answer = await ctx.elicit(message=f"Save this {prepared.text}?", schema=transfers.ConfirmBeneficiaryForm)
        except Exception:
            answer = None
        if not (
            getattr(answer, "action", None) == "accept" and getattr(getattr(answer, "data", None), "confirm", False)
        ):
            return transfers.failure(400, "The user did not confirm. Nothing was saved.", cancelled=True)
    method = "PUT" if prepared.kind == BENEFICIARY_CHANGE else "POST"
    result = await make_request(method, prepared.endpoint, auth=get_auth_header(), data=prepared.data)
    if isinstance(result, dict) and not result.get("error"):
        return {"executed": True, "beneficiary": prepared.summary, **result}
    return result


@mcp.tool(name="cancel_beneficiary", annotations=CANCEL)
async def cancel_beneficiary(confirmation_id: str) -> Dict[str, Any]:
    """Cancel Beneficiary - Drops a beneficiary or change prepared with prepare_beneficiary(_change)."""
    prepared = _take(confirmation_id)
    if prepared is None:
        return transfers.failure(404, "There is nothing prepared with this confirmation_id.")
    return {"cancelled": True, "executed": False, "beneficiary": prepared.summary}


@mcp.tool(name="delete_beneficiary", annotations=DELETE)
async def delete_beneficiary(beneficiary_id: int) -> Dict[str, Any]:
    """Delete Beneficiary - Removes a saved beneficiary, so no more transfers can be sent to it."""
    auth = get_auth_header()
    return await make_request("DELETE", f"{BENEFICIARIES_PATH}/{beneficiary_id}", auth=auth)
