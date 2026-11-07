"""Loan applications (US-E13-12): typed fields from the bank's template, the schedule first, then prepare + confirm."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from routers.loan_tools import (
    calculate_loan_repayment_calendar,
    cancel_loan_application,
    confirm_loan_application,
    get_loan_template,
    prepare_loan_application,
)
from routers.shares_tools import confirm_share_application
from tests.stepup_support import FakeApi
from utils import auth, transfers

TODAY = date(2026, 10, 31)
TEMPLATE_PATH = "/self/loans/template?clientId=5&productId=2&templateType=individual"
TEMPLATE = {
    "clientId": 5,
    "loanProductName": "Group Credit",
    "currency": {"code": "MXN"},
    "productOptions": [{"id": 2, "name": "Group Credit"}, {"id": 3, "name": "Car Loan"}],
    "product": {
        "id": 2,
        "minPrincipal": 1000.0,
        "maxPrincipal": 50000.0,
        "minNumberOfRepayments": 6,
        "maxNumberOfRepayments": 24,
    },
    "numberOfRepayments": 12,
    "repaymentEvery": 1,
    "repaymentFrequencyType": {"id": 2, "value": "Months"},
    "interestRatePerPeriod": 8.5,
    "amortizationType": {"id": 1},
    "interestType": {"id": 0},
    "interestCalculationPeriodType": {"id": 1},
    "transactionProcessingStrategyCode": "mifos-standard-strategy",
    "loanPurposeOptions": [{"id": 43, "name": "Working capital"}, {"id": 44, "name": "House"}],
    "charges": [{"chargeId": 7, "amount": 150.0, "dueDate": [2026, 11, 15]}],
}
SCHEDULE = {
    "totalPrincipalExpected": 10000.0,
    "totalInterestCharged": 470.0,
    "totalFeeChargesCharged": 150.0,
    "totalRepaymentExpected": 10620.0,
    "loanTermInDays": 365,
    "periods": [
        {"dueDate": [2026, 10, 31]},  # the disbursement row has no period number
        {
            "period": 1,
            "dueDate": [2026, 11, 30],
            "principalDue": 800.0,
            "interestDue": 70.0,
            "feeChargesDue": 150.0,
            "totalDueForPeriod": 1020.0,
        },
        {
            "period": 2,
            "dueDate": [2026, 12, 31],
            "principalDue": 810.0,
            "interestDue": 60.0,
            "totalDueForPeriod": 870.0,
        },
    ],
}
PENDING_LOAN = {"id": 61, "clientId": 5, "status": {"pendingApproval": True}}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.delenv(transfers.TTL_ENV, raising=False)
    transfers.clear_prepared()
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    with patch("utils.transfers.today", return_value=TODAY):
        yield
    transfers.clear_prepared()


def bank(**overrides):
    routes = {
        f"GET {TEMPLATE_PATH}": TEMPLATE,
        "POST /self/loans?command=calculateLoanSchedule": SCHEDULE,
        "POST /self/loans": {"loanId": 61, "resourceId": 61},
        "GET /self/loans/61": PENDING_LOAN,
        "PUT /self/loans/61": {"loanId": 61, "resourceId": 61, "changes": {"principal": 12000.0}},
    }
    routes.update(overrides)
    return FakeApi(**routes)


async def run(api, coro_factory, ctx=None):
    with (
        patch("routers.loan_tools.make_request", api),
        patch("routers.loan_tools.get_auth_header", return_value="Basic c2Vzc2lvbg=="),
        patch("utils.stepup._elicitation_context", return_value=ctx),
    ):
        return await coro_factory()


async def prepare(api, **kwargs):
    args = {"client_id": 5, "product_id": 2, "principal": 10000.0}
    args.update(kwargs)
    return await run(api, lambda: prepare_loan_application(**args))


def form(action="accept", confirm=True):
    return SimpleNamespace(
        elicit=AsyncMock(return_value=SimpleNamespace(action=action, data=SimpleNamespace(confirm=confirm)))
    )


# --- the template and the schedule ----------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_id, path",
    [
        (None, "/self/loans/template?clientId=5&templateType=individual"),
        (2, "/self/loans/template?clientId=5&templateType=individual&productId=2"),
    ],
)
async def test_the_template_lists_products_or_shows_one(product_id, path):
    api = FakeApi(**{f"GET {path}": TEMPLATE})
    await run(api, lambda: get_loan_template(5, product_id))
    assert api.calls[0]["endpoint"] == path


@pytest.mark.asyncio
async def test_the_schedule_is_calculated_from_the_template_and_the_typed_fields():
    api = bank()
    result = await run(
        api, lambda: calculate_loan_repayment_calendar(5, 2, 10000.0, number_of_repayments=6, loan_purpose_id=43)
    )

    sent = api.calls_to("POST", "/self/loans?command=calculateLoanSchedule")[0]["data"]
    assert sent == {
        "clientId": 5,
        "productId": 2,
        "principal": 10000.0,
        "loanTermFrequency": 6,
        "loanTermFrequencyType": 2,
        "numberOfRepayments": 6,
        "repaymentEvery": 1,
        "repaymentFrequencyType": 2,
        "interestRatePerPeriod": 8.5,
        "amortizationType": 1,
        "interestType": 0,
        "interestCalculationPeriodType": 1,
        "transactionProcessingStrategyCode": "mifos-standard-strategy",
        "expectedDisbursementDate": "31 October 2026",
        "submittedOnDate": "31 October 2026",
        "loanType": "individual",
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
        "loanPurposeId": 43,
        "charges": [{"chargeId": 7, "amount": 150.0, "dueDate": "15 November 2026"}],
    }
    assert result["totalRepayment"] == 10620.0
    assert result["totalFeesAndPenalties"] == 150.0
    assert result["numberOfInstallments"] == 2
    assert result["loanPurpose"] == "Working capital"
    assert result["currency"] == "MXN"
    assert not api.calls_to("POST", "/self/loans")


@pytest.mark.asyncio
async def test_the_product_number_of_repayments_is_the_default():
    api = bank()
    await run(api, lambda: calculate_loan_repayment_calendar(5, 2, 10000.0))
    sent = api.calls_to("POST", "/self/loans?command=calculateLoanSchedule")[0]["data"]
    assert sent["numberOfRepayments"] == 12
    assert sent["loanTermFrequency"] == 12
    assert "loanPurposeId" not in sent


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"principal": 500.0}, "The amount must be at least 1000 for Group Credit."),
        ({"principal": 60000.0}, "The amount must be at most 50000 for Group Credit."),
        ({"principal": 0.0}, "The amount must be greater than zero."),
        ({"number_of_repayments": 3}, "The number of repayments must be at least 6 for Group Credit."),
        ({"number_of_repayments": 36}, "The number of repayments must be at most 24 for Group Credit."),
        (
            {"loan_purpose_id": 99},
            "Loan purpose 99 is not offered. Purposes for this product: 43 (Working capital), " "44 (House).",
        ),
        (
            {"expected_disbursement_date": TODAY - timedelta(days=1)},
            "The expected disbursement date cannot be in the past.",
        ),
    ],
)
async def test_values_outside_the_product_are_refused_before_the_bank_is_asked(kwargs, message):
    api = bank()
    result = await prepare(api, **kwargs)
    assert result["error"] is True and result["status_code"] == 400
    assert result["message"] == message
    assert result["executed"] is False
    assert [c["method"] for c in api.calls] == ["GET"]


@pytest.mark.asyncio
async def test_a_product_not_offered_to_the_client_is_refused():
    api = bank(**{"GET /self/loans/template?clientId=5&productId=9&templateType=individual": TEMPLATE})
    result = await prepare(api, product_id=9)
    assert result["status_code"] == 404
    assert "not available for this client" in result["message"]


@pytest.mark.asyncio
async def test_a_bank_error_on_the_schedule_is_passed_on_and_nothing_is_prepared():
    error = {"error": True, "status_code": 400, "message": "Validation errors exist."}
    api = bank(**{"POST /self/loans?command=calculateLoanSchedule": error})
    result = await prepare(api)
    assert result == error
    assert transfers._prepared == {}


# --- prepare + confirm ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_shows_the_schedule_and_submits_nothing():
    api = bank()
    result = await prepare(api)
    assert result["prepared"] is True and result["executed"] is False
    assert result["application"]["totalRepayment"] == 10620.0
    assert len(result["application"]["schedule"]) == 2
    assert "confirm_loan_application" in result["message"]
    assert not api.calls_to("POST", "/self/loans")


@pytest.mark.asyncio
async def test_confirm_submits_the_prepared_application_once():
    api = bank()
    prepared = await prepare(api, loan_purpose_id=44)
    result = await run(api, lambda: confirm_loan_application(prepared["confirmation_id"]))

    assert result["executed"] is True and result["loanId"] == 61
    submitted = api.calls_to("POST", "/self/loans")
    assert len(submitted) == 1
    assert submitted[0]["data"]["principal"] == 10000.0
    assert submitted[0]["data"]["loanPurposeId"] == 44

    again = await run(api, lambda: confirm_loan_application(prepared["confirmation_id"]))
    assert again["status_code"] == 404
    assert len(api.calls_to("POST", "/self/loans")) == 1


@pytest.mark.asyncio
async def test_the_person_confirms_in_the_form_when_the_client_offers_one():
    api = bank()
    prepared = await prepare(api)
    ctx = form()
    result = await run(api, lambda: confirm_loan_application(prepared["confirmation_id"]), ctx=ctx)
    assert result["executed"] is True
    assert "10000 MXN" in ctx.elicit.call_args.kwargs["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", [form(action="decline"), form(confirm=False)])
async def test_nothing_is_submitted_when_the_person_says_no(answer):
    api = bank()
    prepared = await prepare(api)
    result = await run(api, lambda: confirm_loan_application(prepared["confirmation_id"]), ctx=answer)
    assert result["cancelled"] is True and result["executed"] is False
    assert not api.calls_to("POST", "/self/loans")


@pytest.mark.asyncio
async def test_a_form_that_fails_counts_as_not_confirmed():
    api = bank()
    prepared = await prepare(api)
    broken = SimpleNamespace(elicit=AsyncMock(side_effect=RuntimeError("client closed the form")))
    result = await run(api, lambda: confirm_loan_application(prepared["confirmation_id"]), ctx=broken)
    assert result["cancelled"] is True
    assert not api.calls_to("POST", "/self/loans")


@pytest.mark.asyncio
async def test_cancel_drops_the_prepared_application():
    api = bank()
    prepared = await prepare(api)
    cancelled = await run(api, lambda: cancel_loan_application(prepared["confirmation_id"]))
    assert cancelled["cancelled"] is True
    result = await run(api, lambda: confirm_loan_application(prepared["confirmation_id"]))
    assert result["status_code"] == 404
    assert not api.calls_to("POST", "/self/loans")


@pytest.mark.asyncio
async def test_a_loan_confirmation_id_cannot_confirm_another_kind_of_operation():
    api = bank()
    prepared = await prepare(api)
    with patch("utils.stepup._elicitation_context", return_value=None):
        other = await confirm_share_application(prepared["confirmation_id"])
    assert other["status_code"] == 404
    result = await run(api, lambda: confirm_loan_application(prepared["confirmation_id"]))
    assert result["executed"] is True


# --- changing an application that waits for approval ------------------------------------------------


@pytest.mark.asyncio
async def test_a_pending_application_is_changed_with_put_after_confirming():
    api = bank()
    prepared = await prepare(api, principal=12000.0, loan_id=61)
    assert "change to loan application 61" in prepared["message"]
    result = await run(api, lambda: confirm_loan_application(prepared["confirmation_id"]))

    assert result["executed"] is True
    changed = api.calls_to("PUT", "/self/loans/61")
    assert len(changed) == 1 and changed[0]["data"]["principal"] == 12000.0
    assert not api.calls_to("POST", "/self/loans")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "loan, message",
    [
        (
            {"id": 61, "clientId": 5, "status": {"pendingApproval": False, "active": True}},
            "Loan 61 is no longer waiting for approval, so it cannot be changed.",
        ),
        ({"id": 61, "clientId": 8, "status": {"pendingApproval": True}}, "Loan 61 belongs to another client."),
        ({"error": True, "status_code": 404, "message": "not found"}, "Loan 61 was not found among the user's loans."),
    ],
)
async def test_only_the_clients_pending_applications_can_be_changed(loan, message):
    api = bank(**{"GET /self/loans/61": loan})
    result = await prepare(api, loan_id=61)
    assert result["status_code"] == 400 and result["message"] == message
    assert transfers._prepared == {}
