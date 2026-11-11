from datetime import date
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from mcp_app import mcp
from routers.loan_simulation_tools import _outside_limits, _summary
from utils import stepup, transfers
from utils.auth import get_auth_header
from utils.http import make_request

LOANS_PATH = "/self/loans"
# A new application is POSTed, a change to a pending one is PUT; the kind tells confirm which it is.
LOAN_APPLICATION = "loan_application"
LOAN_APPLICATION_CHANGE = "loan_application_change"

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
PREPARE = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False)
SUBMIT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
CANCEL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)


@mcp.tool(name="get_loan_products")
async def get_loan_products(client_id: int) -> Any:
    """Retrieve available loan products."""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/loanproducts?clientId={client_id}",
        auth=auth,
    )


@mcp.tool(name="get_loan_product_details")
async def get_loan_product_details(product_id: int) -> Any:
    """Retrieve the details of one loan product."""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/loanproducts/{product_id}",
        auth=auth,
    )


@mcp.tool(name="get_loan_account_details")
async def get_loan_account_details(
    loan_id: int,
    associations: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve loan account details (optional associations)."""
    auth = get_auth_header()

    path = f"/self/loans/{loan_id}"
    if associations:
        path += f"?associations={associations}"

    return await make_request("GET", path, auth=auth)


@mcp.tool(name="get_loan_transaction_detail")
async def get_loan_transaction_detail(loan_id: int, transaction_id: int) -> Dict[str, Any]:
    """Retrieve loan transaction detail."""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/loans/{loan_id}/transactions/{transaction_id}",
        auth=auth,
    )


@mcp.tool(name="get_loan_account_charges")
async def get_loan_account_charges(loan_id: int) -> Dict[str, Any]:
    """Retrieve loan charges."""
    auth = get_auth_header()
    return await make_request(
        "GET",
        f"/self/loans/{loan_id}/charges",
        auth=auth,
    )


@mcp.tool(name="get_loan_template", annotations=READ_ONLY)
async def get_loan_template(client_id: int, product_id: Optional[int] = None) -> Dict[str, Any]:
    """Get Loan Template - The loan products a client can apply for, and one product's terms.

    Without product_id it lists the products (productOptions). With product_id it also returns that
    product's amount limits, number of repayments, interest, loan purposes (loanPurposeOptions) and charges.
    """
    auth = get_auth_header()
    path = f"{LOANS_PATH}/template?clientId={client_id}&templateType=individual"
    if product_id is not None:
        path += f"&productId={product_id}"
    return await make_request("GET", path, auth=auth)


def _id(value: Any) -> Any:
    """Template enums come as {"id": 2, "value": "Months"}; the application takes the id."""
    return value.get("id") if isinstance(value, dict) else value


def _date_text(value: Any) -> Optional[str]:
    """Fineract dates come as [2026, 10, 31]."""
    if isinstance(value, list) and len(value) == 3:
        return transfers.format_date(date(*value))
    return None


async def _loan_template(client_id: int, product_id: int, auth: str) -> Dict[str, Any]:
    """The loan template for this client and product, or a failure. Only the client's own products are offered."""
    template = await make_request(
        "GET", f"{LOANS_PATH}/template?clientId={client_id}&productId={product_id}&templateType=individual", auth=auth
    )
    if not isinstance(template, dict) or template.get("error"):
        return template if isinstance(template, dict) else transfers.failure(502, "Could not read the loan template.")
    if not any(_id(p) == product_id for p in template.get("productOptions") or []):
        return transfers.failure(404, f"Loan product {product_id} is not available for this client.")
    return template


def _application(
    template: Dict[str, Any],
    client_id: int,
    product_id: int,
    principal: float,
    number_of_repayments: Optional[int],
    loan_purpose_id: Optional[int],
    expected_disbursement_date: Optional[date],
) -> Union[Dict[str, Any], str]:
    """The full application the bank expects, from the template; a string says what is wrong."""
    product = template.get("product") or {}
    repayments = number_of_repayments if number_of_repayments is not None else template.get("numberOfRepayments")
    if not isinstance(repayments, int) or repayments < 1:
        return "The number of repayments must be at least 1."
    if principal <= 0:
        return "The amount must be greater than zero."
    problem = _outside_limits("amount", principal, product.get("minPrincipal"), product.get("maxPrincipal"))
    problem = problem or _outside_limits(
        "number of repayments", repayments, product.get("minNumberOfRepayments"), product.get("maxNumberOfRepayments")
    )
    if problem:
        return f"{problem} for {template.get('loanProductName') or 'this product'}."
    purposes = template.get("loanPurposeOptions") or []
    if loan_purpose_id is not None and not any(_id(p) == loan_purpose_id for p in purposes):
        names = ", ".join(f"{p.get('id')} ({p.get('name')})" for p in purposes if isinstance(p, dict)) or "none"
        return f"Loan purpose {loan_purpose_id} is not offered. Purposes for this product: {names}."
    today = transfers.today()
    disbursement = expected_disbursement_date or today
    if disbursement < today:
        return "The expected disbursement date cannot be in the past."

    every = template.get("repaymentEvery") or 1
    frequency = _id(template.get("repaymentFrequencyType"))
    data: Dict[str, Any] = {
        "clientId": client_id,
        "productId": product_id,
        "principal": principal,
        "loanTermFrequency": repayments * every,
        "loanTermFrequencyType": frequency,
        "numberOfRepayments": repayments,
        "repaymentEvery": every,
        "repaymentFrequencyType": frequency,
        "interestRatePerPeriod": template.get("interestRatePerPeriod"),
        "amortizationType": _id(template.get("amortizationType")),
        "interestType": _id(template.get("interestType")),
        "interestCalculationPeriodType": _id(template.get("interestCalculationPeriodType")),
        "transactionProcessingStrategyCode": template.get("transactionProcessingStrategyCode"),
        "expectedDisbursementDate": transfers.format_date(disbursement),
        "submittedOnDate": transfers.format_date(today),
        "loanType": "individual",
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
    }
    if loan_purpose_id is not None:
        data["loanPurposeId"] = loan_purpose_id
    # The product's own charges are part of the application, as in the bank's web app
    charges: List[Dict[str, Any]] = []
    for charge in template.get("charges") or []:
        if isinstance(charge, dict) and charge.get("chargeId") is not None:
            item = {"chargeId": charge["chargeId"], "amount": charge.get("amount")}
            if _date_text(charge.get("dueDate")):
                item["dueDate"] = _date_text(charge.get("dueDate"))
            charges.append(item)
    if charges:
        data["charges"] = charges
    return data


async def _schedule(template: Dict[str, Any], data: Dict[str, Any], auth: str) -> Dict[str, Any]:
    """The repayment schedule the bank calculates for this application (nothing is submitted)."""
    schedule = await make_request("POST", f"{LOANS_PATH}?command=calculateLoanSchedule", auth=auth, data=data)
    if not isinstance(schedule, dict) or schedule.get("error"):
        return schedule if isinstance(schedule, dict) else transfers.failure(502, "Could not calculate the schedule.")
    product = {
        "id": data["productId"],
        "name": template.get("loanProductName"),
        "currencyCode": (template.get("currency") or {}).get("code"),
    }
    summary = _summary(product, schedule)
    purpose = next(
        (p.get("name") for p in template.get("loanPurposeOptions") or [] if _id(p) == data.get("loanPurposeId")), None
    )
    if purpose:
        summary["loanPurpose"] = purpose
    summary["expectedDisbursementDate"] = data["expectedDisbursementDate"]
    return summary


@mcp.tool(name="calculate_loan_repayment_calendar", annotations=READ_ONLY)
async def calculate_loan_repayment_calendar(
    client_id: int,
    product_id: int,
    principal: float,
    number_of_repayments: Optional[int] = None,
    loan_purpose_id: Optional[int] = None,
    expected_disbursement_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Calculate Loan Repayment Calendar - The schedule a loan application would have. Submits nothing.

    Use a product id from get_loan_template (without product_id it lists the client's products). The
    number of repayments defaults to the product's; the amount and the number of repayments must be within
    the product's limits. Everything else (interest, frequency, charges) comes from the bank's template.
    Returns the total interest, the total to repay and each installment.
    """
    auth = get_auth_header()
    template = await _loan_template(client_id, product_id, auth)
    if template.get("error"):
        return template
    data = _application(
        template, client_id, product_id, principal, number_of_repayments, loan_purpose_id, expected_disbursement_date
    )
    if isinstance(data, str):
        return transfers.failure(400, data)
    return await _schedule(template, data, auth)


async def _pending_application(loan_id: int, client_id: int, auth: str) -> Optional[str]:
    """None when the loan is this client's application still waiting for approval, else what is wrong."""
    loan = await make_request("GET", f"{LOANS_PATH}/{loan_id}", auth=auth)
    if not isinstance(loan, dict) or loan.get("error"):
        return f"Loan {loan_id} was not found among the user's loans."
    if loan.get("clientId") not in (None, client_id):
        return f"Loan {loan_id} belongs to another client."
    if not (loan.get("status") or {}).get("pendingApproval"):
        return f"Loan {loan_id} is no longer waiting for approval, so it cannot be changed."
    return None


@mcp.tool(name="prepare_loan_application", annotations=PREPARE)
async def prepare_loan_application(
    client_id: int,
    product_id: int,
    principal: float,
    number_of_repayments: Optional[int] = None,
    loan_purpose_id: Optional[int] = None,
    expected_disbursement_date: Optional[date] = None,
    loan_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Prepare Loan Application - Step 1 of 2. Checks a loan application and shows its repayment schedule.

    Submits nothing. A loan creates a debt, so show the user the amount, number of installments, total
    interest, total to repay and the schedule. Only after the user says yes, call confirm_loan_application
    with the confirmation_id (cancel_loan_application if not). The id works once and expires after a few
    minutes. To change an application that is still waiting for approval, pass its loan_id.
    """
    auth = get_auth_header()
    template = await _loan_template(client_id, product_id, auth)
    if template.get("error"):
        return template
    data = _application(
        template, client_id, product_id, principal, number_of_repayments, loan_purpose_id, expected_disbursement_date
    )
    if isinstance(data, str):
        return transfers.failure(400, data)
    if loan_id is not None:
        problem = await _pending_application(loan_id, client_id, auth)
        if problem:
            return transfers.failure(400, problem)
    summary = await _schedule(template, data, auth)
    if summary.get("error"):
        return summary

    currency = summary.get("currency") or ""
    what = f"change to loan application {loan_id}" if loan_id is not None else "loan application"
    text = (
        f"{what}: {summary.get('productName')}, {principal:g} {currency}, {summary.get('numberOfInstallments')} "
        f"installments, total to repay {summary.get('totalRepayment')} {currency}"
    ).replace("  ", " ")
    if loan_id is None:
        prepared = transfers.remember(LOANS_PATH, data, summary, text, kind=LOAN_APPLICATION)
    else:
        prepared = transfers.remember(f"{LOANS_PATH}/{loan_id}", data, summary, text, kind=LOAN_APPLICATION_CHANGE)
    return {
        "prepared": True,
        "executed": False,
        "confirmation_id": prepared.confirmation_id,
        "expires_in_seconds": transfers.ttl_seconds(),
        "application": summary,
        "message": (
            f"Nothing has been submitted yet. Show the user this {text} and the schedule. Call "
            "confirm_loan_application with the confirmation_id only after the user says yes, or "
            "cancel_loan_application if they do not. The bank still has to approve the loan."
        ),
    }


def _take_application(confirmation_id: str):
    return transfers.take(confirmation_id, LOAN_APPLICATION) or transfers.take(confirmation_id, LOAN_APPLICATION_CHANGE)


@mcp.tool(name="confirm_loan_application", annotations=SUBMIT)
async def confirm_loan_application(confirmation_id: str) -> Dict[str, Any]:
    """Confirm Loan Application - Step 2 of 2. Submits an application prepared with prepare_loan_application.

    Call it only after the user has seen the schedule and said yes. The id works once. The client may show
    the user a confirmation form. The application then waits for the bank's approval.
    """
    prepared = _take_application(confirmation_id)
    if prepared is None:
        return transfers.failure(
            404,
            "There is no prepared loan application with this confirmation_id (it expired, was already used or "
            "was cancelled). Call prepare_loan_application again.",
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
                400, "The user did not confirm the loan application. Nothing was submitted.", cancelled=True
            )
    method = "PUT" if prepared.kind == LOAN_APPLICATION_CHANGE else "POST"
    result = await make_request(method, prepared.endpoint, auth=get_auth_header(), data=prepared.data)
    if isinstance(result, dict) and not result.get("error"):
        return {"executed": True, "application": prepared.summary, **result}
    return result


@mcp.tool(name="cancel_loan_application", annotations=CANCEL)
async def cancel_loan_application(confirmation_id: str) -> Dict[str, Any]:
    """Cancel Loan Application - Drops an application prepared with prepare_loan_application."""
    prepared = _take_application(confirmation_id)
    if prepared is None:
        return transfers.failure(404, "There is no prepared loan application with this confirmation_id.")
    return {"cancelled": True, "executed": False, "application": prepared.summary}


@mcp.tool(name="withdraw_loan_application")
async def withdraw_loan_application(loan_id: int, note: Optional[str] = None) -> Dict[str, Any]:
    """Withdraw Loan Application - Withdraws one of the user's loan applications that is still waiting for approval.

    After approval only the bank's staff can stop the loan. The date is today in the bank's time zone.
    """
    auth = get_auth_header()
    loan = await make_request("GET", f"/self/loans/{loan_id}", auth=auth)
    if not isinstance(loan, dict) or loan.get("error"):
        return transfers.failure(404, f"Loan {loan_id} was not found among the user's loans.")
    status = loan.get("status") or {}
    if not status.get("pendingApproval"):
        return transfers.failure(
            400,
            f"Loan {loan_id} is {status.get('value') or 'not waiting for approval'}. Only an application that is "
            "still waiting for approval can be withdrawn.",
        )

    data = {
        "withdrawnOnDate": transfers.format_date(transfers.today()),
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
    }
    if note and note.strip():
        data["note"] = note.strip()
    return await make_request(
        "POST",
        f"/self/loans/{loan_id}?command=withdrawnByApplicant",
        auth=auth,
        data=data,
    )
