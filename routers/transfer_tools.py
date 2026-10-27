from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from mcp_app import mcp
from utils import stepup, transfers
from utils.auth import get_auth_header
from utils.http import make_request

TRANSFER_PATH = "/self/accounttransfers"
THIRD_PARTY_TRANSFER_PATH = "/self/accounttransfers?type=tpt"

PREPARE = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False)
CONFIRM = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True)
CANCEL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)


async def _post_transfer(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """POST a transfer. If the bank asks for a verification code, confirm it with the user first."""
    auth = get_auth_header()
    result = await make_request("POST", endpoint, auth=auth, data=data)
    return await stepup.resolve_step_up(result, "POST", endpoint, auth=auth, data=data)


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


# --- two-step transfers (US-E13-07) -------------------------------------------------------------


def _find_account(options: Any, account_id: int, account_type: int) -> Optional[Dict[str, Any]]:
    for option in options or []:
        if not isinstance(option, dict):
            continue
        option_type = option.get("accountType")
        option_type_id = option_type.get("id") if isinstance(option_type, dict) else option_type
        if option.get("accountId") == account_id and option_type_id == account_type:
            return option
    return None


def _account_view(option: Dict[str, Any]) -> Dict[str, Any]:
    account_type = option.get("accountType")
    return {
        "accountId": option.get("accountId"),
        "accountNo": option.get("accountNo"),
        "accountType": account_type.get("value") if isinstance(account_type, dict) else account_type,
        "clientName": option.get("clientName"),
    }


async def _source_savings(account_id: int, auth: str) -> Dict[str, Any]:
    """Currency, balance and fee setting of a savings source account (empty if the bank does not say)."""
    account = await make_request("GET", f"/self/savingsaccounts/{account_id}", auth=auth)
    if not isinstance(account, dict) or account.get("error"):
        return {}
    currency = account.get("currency") if isinstance(account.get("currency"), dict) else {}
    summary = account.get("summary") if isinstance(account.get("summary"), dict) else {}
    balance = summary.get("availableBalance", summary.get("accountBalance"))
    return {
        "currency": currency.get("code"),
        "availableBalance": balance,
        "withdrawalFeeForTransfers": bool(account.get("withdrawalFeeForTransfers")),
    }


@mcp.tool(name="prepare_transfer", annotations=PREPARE)
async def prepare_transfer(
    from_account_id: int,
    to_account_id: int,
    amount: float,
    description: str = "Transfer",
    from_account_type: int = transfers.SAVINGS,
    to_account_type: int = transfers.SAVINGS,
    third_party: bool = False,
) -> Dict[str, Any]:
    """Prepare Transfer - Step 1 of 2. Checks a transfer and returns a summary and a confirmation_id.

    Moves no money. Use it for every transfer: between the user's own accounts (third_party false, e.g. a
    loan repayment from savings with to_account_type 1) or to a saved beneficiary (third_party true).
    Account types: 2 = savings, 1 = loan. Show the returned summary (accounts, amount, fee) to the user
    and ask them to confirm. Only after the user says yes, call confirm_transfer with the confirmation_id.
    The id works once and expires after a few minutes.
    """
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        return transfers.failure(400, "The amount must be a number.")
    if not value.is_finite() or value <= 0:
        return transfers.failure(400, "The amount must be greater than zero.")
    limit = transfers.max_amount()
    if limit is not None and value > limit:
        return transfers.failure(
            403,
            f"Transfers above {limit} cannot be made through the assistant. Use the bank's app or website.",
            limit_exceeded=True,
        )
    description = (description or "").strip()
    if not description:
        return transfers.failure(400, "A description is required.")
    if len(description) > 200:
        return transfers.failure(400, "The description can have at most 200 characters.")
    if from_account_id == to_account_id and from_account_type == to_account_type:
        return transfers.failure(400, "The source and destination accounts must be different.")

    auth = get_auth_header()
    template_path = "/self/accounttransfers/template" + ("?type=tpt" if third_party else "")
    template = await make_request("GET", template_path, auth=auth)
    if not isinstance(template, dict) or template.get("error"):
        return (
            template if isinstance(template, dict) else transfers.failure(502, "Could not read the transfer template.")
        )
    source = _find_account(template.get("fromAccountOptions"), from_account_id, from_account_type)
    if source is None:
        return transfers.failure(400, "The source account is not one of your accounts that can send transfers.")
    target = _find_account(template.get("toAccountOptions"), to_account_id, to_account_type)
    if target is None:
        where = "your saved beneficiaries" if third_party else "your own accounts"
        return transfers.failure(400, f"The destination account is not one of {where}.")

    summary: Dict[str, Any] = {
        "kind": "third-party transfer" if third_party else "transfer between your accounts",
        "from": _account_view(source),
        "to": _account_view(target),
        "amount": float(value),
        "description": description,
    }
    if from_account_type == transfers.SAVINGS:
        savings = await _source_savings(from_account_id, auth)
        if savings.get("currency"):
            summary["currency"] = savings["currency"]
        balance = savings.get("availableBalance")
        if isinstance(balance, (int, float)) and Decimal(str(balance)) < value:
            return transfers.failure(400, f"The available balance ({balance}) is lower than the amount.")
        summary["fee"] = (
            "The savings product charges its withdrawal fee on transfers; the bank adds it when the transfer runs."
            if savings.get("withdrawalFeeForTransfers")
            else "No transfer fee."
        )

    data = {
        "fromOfficeId": source.get("officeId"),
        "fromClientId": source.get("clientId"),
        "fromAccountType": from_account_type,
        "fromAccountId": from_account_id,
        "toOfficeId": target.get("officeId"),
        "toClientId": target.get("clientId"),
        "toAccountType": to_account_type,
        "toAccountId": to_account_id,
        "transferAmount": float(value),
        "transferDate": transfers.format_date(transfers.today()),
        "transferDescription": description,
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
    }
    currency = f" {summary['currency']}" if summary.get("currency") else ""
    text = (
        f"{summary['kind']} of {value}{currency} from account {source.get('accountNo')} "
        f"to account {target.get('accountNo')} ({target.get('clientName')})"
    )
    prepared = transfers.remember(THIRD_PARTY_TRANSFER_PATH if third_party else TRANSFER_PATH, data, summary, text)
    return {
        "prepared": True,
        "executed": False,
        "confirmation_id": prepared.confirmation_id,
        "expires_in_seconds": transfers.ttl_seconds(),
        "transfer": summary,
        "message": (
            f"Nothing has been sent yet. Show the user this transfer: {text}. Call confirm_transfer with the "
            "confirmation_id only after the user says yes, or cancel_transfer if they do not."
        ),
    }


async def _person_confirms(prepared: transfers.PreparedTransfer) -> Optional[bool]:
    """Ask the person in the client's form. ``None`` means the client cannot show a form.

    A client that offers forms but fails to show this one counts as "not confirmed": no money moves.
    """
    ctx = stepup._elicitation_context()
    if ctx is None:
        return None
    try:
        answer = await ctx.elicit(message=f"Send this {prepared.text}?", schema=transfers.ConfirmTransferForm)
    except Exception:
        return False
    return getattr(answer, "action", None) == "accept" and bool(getattr(answer.data, "confirm", False))


@mcp.tool(name="confirm_transfer", annotations=CONFIRM)
async def confirm_transfer(confirmation_id: str) -> Dict[str, Any]:
    """Confirm Transfer - Step 2 of 2. Sends a transfer prepared with prepare_transfer.

    Call it only after the user has seen the summary and said yes. The id works once. The client may show
    the user a confirmation form, and the bank may ask for a one-time code: the user types it, never you.
    """
    prepared = transfers.take(confirmation_id)
    if prepared is None:
        return transfers.failure(
            404,
            "There is no prepared transfer with this confirmation_id (it expired, was already used or was "
            "cancelled). Call prepare_transfer again.",
        )
    if await _person_confirms(prepared) is False:
        return transfers.failure(400, "The user did not confirm the transfer. Nothing was sent.", cancelled=True)
    result = await _post_transfer(prepared.endpoint, prepared.data)
    if isinstance(result, dict) and not result.get("error") and not result.get("step_up_required"):
        return {"executed": True, "transfer": prepared.summary, **result}
    return result


@mcp.tool(name="cancel_transfer", annotations=CANCEL)
async def cancel_transfer(confirmation_id: str) -> Dict[str, Any]:
    """Cancel Transfer - Drops a transfer prepared with prepare_transfer. Moves no money."""
    prepared = transfers.take(confirmation_id)
    if prepared is None:
        return transfers.failure(404, "There is no prepared transfer with this confirmation_id.")
    return {"cancelled": True, "executed": False, "transfer": prepared.summary}
