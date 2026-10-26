from datetime import date
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations
from mcp_app import mcp
from utils.http import make_request

SIMULATE_PATH = "/self/loans/simulate"
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)


@mcp.tool(name="get_loan_simulation_products", annotations=READ_ONLY)
async def get_loan_simulation_products() -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Get Loan Simulation Products - Lists the loan products a user can simulate, without logging in.

    Each product has its currency, default/min/max principal, interest rate, number of repayments
    and repayment frequency. Use the product id with simulate_loan.
    """
    return await make_request("GET", f"{SIMULATE_PATH}/products")


def _summary(product: Dict[str, Any], schedule: Dict[str, Any]) -> Dict[str, Any]:
    periods = [p for p in schedule.get("periods", []) if p.get("period")]
    return {
        "productId": product.get("id"),
        "productName": product.get("name"),
        "currency": product.get("currencyCode"),
        "principal": schedule.get("totalPrincipalExpected"),
        "totalInterest": schedule.get("totalInterestCharged"),
        "totalFeesAndPenalties": (schedule.get("totalFeeChargesCharged") or 0)
        + (schedule.get("totalPenaltyChargesCharged") or 0),
        "totalRepayment": schedule.get("totalRepaymentExpected"),
        "numberOfInstallments": len(periods),
        "firstInstallmentAmount": periods[0].get("totalDueForPeriod") if periods else None,
        "loanTermInDays": schedule.get("loanTermInDays"),
        "schedule": [
            {
                "installment": p.get("period"),
                "dueDate": p.get("dueDate"),
                "principal": p.get("principalDue"),
                "interest": p.get("interestDue"),
                "fees": (p.get("feeChargesDue") or 0) + (p.get("penaltyChargesDue") or 0),
                "total": p.get("totalDueForPeriod"),
            }
            for p in periods
        ],
    }


def _outside_limits(what: str, value: float, minimum: Optional[float], maximum: Optional[float]) -> Optional[str]:
    """The simulation endpoint does not check the product limits, so check them here."""
    if minimum is not None and value < minimum:
        return f"The {what} must be at least {minimum:g}"
    if maximum is not None and value > maximum:
        return f"The {what} must be at most {maximum:g}"
    return None


@mcp.tool(name="simulate_loan", annotations=READ_ONLY)
async def simulate_loan(
    product_id: int,
    principal: float,
    number_of_repayments: Optional[int] = None,
    interest_rate_per_period: Optional[float] = None,
) -> Dict[str, Any]:
    """Simulate Loan - Estimates what a loan would cost. Does not apply for a loan; no login needed.

    Give a product id (from get_loan_simulation_products) and the amount. The number of repayments
    and the interest rate default to the product's values; the amount and the number of
    repayments must be within the product's limits. Returns the total interest, the total to
    repay, the installment amount and the repayment schedule calculated by the bank.
    """
    products = await make_request("GET", f"{SIMULATE_PATH}/products")
    if not isinstance(products, list):
        return products
    product = next((p for p in products if isinstance(p, dict) and p.get("id") == product_id), None)
    if product is None:
        return {
            "error": True,
            "status_code": 404,
            "message": f"Loan product {product_id} is not available for simulation.",
        }

    repayments = number_of_repayments or product.get("numberOfRepayments")
    problem = _outside_limits("principal", principal, product.get("minPrincipal"), product.get("maxPrincipal"))
    problem = problem or _outside_limits(
        "number of repayments", repayments, product.get("minNumberOfRepayments"), product.get("maxNumberOfRepayments")
    )
    if problem:
        return {"error": True, "status_code": 400, "message": f"{problem} for product {product.get('name')}."}
    repayment_every = product.get("repaymentEvery") or 1
    today = date.today().strftime("%d %B %Y")
    data = {
        "productId": product_id,
        "principal": principal,
        "loanTermFrequency": repayments * repayment_every,
        "loanTermFrequencyType": product.get("repaymentFrequencyType"),
        "numberOfRepayments": repayments,
        "repaymentEvery": repayment_every,
        "repaymentFrequencyType": product.get("repaymentFrequencyType"),
        "interestRatePerPeriod": (
            interest_rate_per_period if interest_rate_per_period is not None else product.get("interestRatePerPeriod")
        ),
        "amortizationType": product.get("amortizationType"),
        "interestType": product.get("interestType"),
        "interestCalculationPeriodType": product.get("interestCalculationPeriodType"),
        "transactionProcessingStrategyCode": product.get("transactionProcessingStrategyCode"),
        "expectedDisbursementDate": today,
        "submittedOnDate": today,
        "loanType": "individual",
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
    }
    schedule = await make_request("POST", f"{SIMULATE_PATH}?command=calculateLoanSchedule", data=data)
    if not isinstance(schedule, dict) or schedule.get("error"):
        return schedule
    return _summary(product, schedule)
