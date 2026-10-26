import pytest
from unittest.mock import patch, AsyncMock

from routers.loan_simulation_tools import get_loan_simulation_products, simulate_loan

PRODUCT = {
    "id": 2,
    "name": "CREDITO SOLIDARIO",
    "currencyCode": "MXN",
    "principal": 50000.0,
    "minPrincipal": 10000.0,
    "maxPrincipal": 100000.0,
    "minNumberOfRepayments": 6,
    "maxNumberOfRepayments": 24,
    "interestRatePerPeriod": 8.5,
    "numberOfRepayments": 23,
    "repaymentEvery": 1,
    "repaymentFrequencyType": 2,
    "amortizationType": 1,
    "interestType": 0,
    "interestCalculationPeriodType": 1,
    "transactionProcessingStrategyCode": "creocore-strategy",
}
SCHEDULE = {
    "totalPrincipalExpected": 50000.0,
    "totalInterestCharged": 4359.94,
    "totalFeeChargesCharged": 0,
    "totalPenaltyChargesCharged": 0,
    "totalRepaymentExpected": 54359.94,
    "loanTermInDays": 701,
    "periods": [
        {"dueDate": [2026, 10, 26], "principalDisbursed": 50000.0},
        {
            "period": 1,
            "dueDate": [2026, 11, 26],
            "principalDue": 2009.31,
            "interestDue": 354.17,
            "totalDueForPeriod": 2363.48,
        },
        {
            "period": 2,
            "dueDate": [2026, 12, 26],
            "principalDue": 2023.54,
            "interestDue": 339.94,
            "totalDueForPeriod": 2363.48,
        },
    ],
}


def responses(*values):
    return AsyncMock(side_effect=list(values))


@pytest.mark.asyncio
async def test_get_loan_simulation_products_needs_no_login():
    with patch("routers.loan_simulation_tools.make_request", new=responses([PRODUCT])) as mock:
        assert await get_loan_simulation_products() == [PRODUCT]
    mock.assert_called_once_with("GET", "/self/loans/simulate/products")


@pytest.mark.asyncio
async def test_simulate_loan_uses_product_defaults_and_summarises():
    with patch("routers.loan_simulation_tools.make_request", new=responses([PRODUCT], SCHEDULE)) as mock:
        result = await simulate_loan(2, 50000)

    method, path = mock.call_args_list[1].args
    body = mock.call_args_list[1].kwargs["data"]
    assert (method, path) == ("POST", "/self/loans/simulate?command=calculateLoanSchedule")
    assert "clientId" not in body
    assert body["numberOfRepayments"] == 23 and body["loanTermFrequency"] == 23 and body["loanTermFrequencyType"] == 2
    assert body["interestRatePerPeriod"] == 8.5
    assert body["transactionProcessingStrategyCode"] == "creocore-strategy"
    assert result["totalInterest"] == 4359.94
    assert result["totalRepayment"] == 54359.94
    assert result["firstInstallmentAmount"] == 2363.48
    assert result["numberOfInstallments"] == 2
    assert result["schedule"][0] == {
        "installment": 1,
        "dueDate": [2026, 11, 26],
        "principal": 2009.31,
        "interest": 354.17,
        "fees": 0,
        "total": 2363.48,
    }


@pytest.mark.asyncio
async def test_simulate_loan_overrides_repayments_and_rate():
    with patch("routers.loan_simulation_tools.make_request", new=responses([PRODUCT], SCHEDULE)) as mock:
        await simulate_loan(2, 20000, number_of_repayments=12, interest_rate_per_period=6)
    body = mock.call_args_list[1].kwargs["data"]
    assert body["principal"] == 20000
    assert body["numberOfRepayments"] == 12 and body["loanTermFrequency"] == 12
    assert body["interestRatePerPeriod"] == 6


@pytest.mark.asyncio
async def test_simulate_loan_unknown_product():
    with patch("routers.loan_simulation_tools.make_request", new=responses([PRODUCT])) as mock:
        result = await simulate_loan(99, 1000)
    assert result["error"] is True and result["status_code"] == 404
    mock.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "principal, repayments, message",
    [
        (10, None, "The principal must be at least 10000"),
        (200000, None, "The principal must be at most 100000"),
        (50000, 3, "The number of repayments must be at least 6"),
        (50000, 36, "The number of repayments must be at most 24"),
    ],
)
async def test_simulate_loan_checks_product_limits(principal, repayments, message):
    with patch("routers.loan_simulation_tools.make_request", new=responses([PRODUCT])) as mock:
        result = await simulate_loan(2, principal, number_of_repayments=repayments)
    assert result["status_code"] == 400
    assert result["message"] == f"{message} for product CREDITO SOLIDARIO."
    mock.assert_called_once()


@pytest.mark.asyncio
async def test_simulate_loan_passes_bank_errors_through():
    error = {"error": True, "status_code": 400, "message": "Validation errors exist."}
    with patch("routers.loan_simulation_tools.make_request", new=responses([PRODUCT], error)):
        assert await simulate_loan(2, 50000) == error


@pytest.mark.asyncio
async def test_simulation_tools_through_mcp():
    import main

    tools = {tool.name: tool for tool in await main.mcp.list_tools()}
    assert tools["simulate_loan"].annotations.readOnlyHint is True
    with patch("routers.loan_simulation_tools.make_request", new=responses([PRODUCT, PRODUCT])):
        _, structured = await main.mcp.call_tool("get_loan_simulation_products", {})
    assert len(structured["result"]) == 2


@pytest.mark.asyncio
async def test_simulate_loan_rejects_zero_repayments():
    product = {**PRODUCT, "minNumberOfRepayments": None}
    with patch("routers.loan_simulation_tools.make_request", new=responses([product])) as mock:
        result = await simulate_loan(2, 50000, number_of_repayments=0)
    assert result == {"error": True, "status_code": 400, "message": "The number of repayments must be at least 1."}
    mock.assert_called_once()
