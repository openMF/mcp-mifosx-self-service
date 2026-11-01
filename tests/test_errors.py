"""Bank errors reach the assistant as a short message plus field errors, never as raw response text."""

import json
from unittest.mock import patch

import httpx
import pytest

from utils import stepup
from utils.errors import MAX_MESSAGE_LENGTH, api_error
from utils.http import make_request

VALIDATION = {
    "developerMessage": (
        "The request was invalid. This typically will happen due to validation errors which are provided."
    ),
    "httpStatusCode": "400",
    "defaultUserMessage": "Validation errors exist.",
    "userMessageGlobalisationCode": "validation.msg.validation.errors.exist",
    "errors": [
        {
            "developerMessage": "The parameter `principal` must be greater than or equal to 50000.",
            "defaultUserMessage": "The parameter `principal` must be greater than or equal to 50000.",
            "userMessageGlobalisationCode": "validation.msg.loan.principal.is.less.than.min",
            "parameterName": "principal",
            "value": None,
            "args": [{"value": 10}],
        },
        {
            "developerMessage": "The parameter `numberOfRepayments` is mandatory.",
            "defaultUserMessage": "The parameter `numberOfRepayments` is mandatory.",
            "userMessageGlobalisationCode": "validation.msg.loan.numberOfRepayments.cannot.be.blank",
            "parameterName": "numberOfRepayments",
            "value": None,
            "args": [],
        },
    ],
}
PLATFORM = {
    "developerMessage": "Loan with identifier 999 does not exist",
    "httpStatusCode": "404",
    "defaultUserMessage": "Loan with identifier 999 does not exist",
    "userMessageGlobalisationCode": "error.msg.loan.id.invalid",
    "errors": [
        {
            "developerMessage": "Loan with identifier 999 does not exist",
            "defaultUserMessage": "Loan with identifier 999 does not exist",
            "userMessageGlobalisationCode": "error.msg.loan.id.invalid",
            "parameterName": "id",
            "value": None,
            "args": [{"value": 999}],
        }
    ],
}
SPRING_404 = {
    "timestamp": "2026-10-28T02:28:45.338Z",
    "status": 404,
    "error": "Not Found",
    "path": "/fineract-provider/api/v1/self/userdetails",
}
HTML = "<html><body><h1>502 Bad Gateway</h1><hr><center>nginx/1.25.3</center></body></html>"


def test_validation_errors_become_one_message_per_field():
    result = api_error(400, json.dumps(VALIDATION))

    assert result["error"] is True and result["status_code"] == 400
    assert result["message"] == (
        "The parameter `principal` must be greater than or equal to 50000.; "
        "The parameter `numberOfRepayments` is mandatory."
    )
    assert result["errors"] == [
        {"message": "The parameter `principal` must be greater than or equal to 50000.", "parameter": "principal"},
        {"message": "The parameter `numberOfRepayments` is mandatory.", "parameter": "numberOfRepayments"},
    ]
    assert result["code"] == "validation.msg.validation.errors.exist"


def test_a_platform_error_keeps_the_bank_message():
    result = api_error(404, json.dumps(PLATFORM))

    assert result["message"] == "Loan with identifier 999 does not exist"
    assert result["code"] == "error.msg.loan.id.invalid"
    assert result["errors"] == [{"message": "Loan with identifier 999 does not exist", "parameter": "id"}]


def test_developer_details_never_reach_the_assistant():
    raw = json.dumps(VALIDATION) + json.dumps(SPRING_404)
    for result in (api_error(400, json.dumps(VALIDATION)), api_error(404, json.dumps(SPRING_404))):
        text = json.dumps(result)
        assert "developerMessage" not in text
        assert "This typically will happen" not in text
        assert "/fineract-provider/api" not in text
    assert raw  # the raw text had all of it


@pytest.mark.parametrize(
    "status, expected",
    [
        (404, "The bank could not find what was asked for."),
        (502, "The bank had an internal error. Try again later."),
        (418, "The bank answered with an error (HTTP 418)."),
    ],
)
def test_a_spring_error_or_an_html_page_gets_a_plain_message(status, expected):
    assert api_error(status, json.dumps({**SPRING_404, "status": status}))["message"] == expected
    html = api_error(status, HTML)
    assert html == {"error": True, "status_code": status, "message": expected}


def test_an_empty_body_gets_a_plain_message():
    assert api_error(401, "") == {
        "error": True,
        "status_code": 401,
        "message": "The bank did not accept the login. Log in again.",
    }


def test_long_messages_are_cut():
    body = {"defaultUserMessage": "x " * 2000, "userMessageGlobalisationCode": "error.msg.long"}
    message = api_error(400, json.dumps(body))["message"]
    assert len(message) == MAX_MESSAGE_LENGTH and message.endswith("...")


def test_step_up_details_are_kept_and_still_understood():
    body = {
        "userMessageGlobalisationCode": "error.msg.selfservice.stepup.otp.invalid",
        "defaultUserMessage": "The verification code is not valid.",
        "attemptsRemaining": 3,
        "action": "TPT_TRANSFER",
        "developerMessage": "otp mismatch for challenge 7",
    }
    result = api_error(400, json.dumps(body))

    assert result["attemptsRemaining"] == 3 and result["action"] == "TPT_TRANSFER"
    assert "developerMessage" not in result
    assert stepup.step_up_code(result) == "otp.invalid"


# --- through make_request -------------------------------------------------------------------------


def _client_answering(status, text, content_type="application/json"):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status, text=text, headers={"content-type": content_type})
    )
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real_client(*args, transport=transport, **kwargs)

    return patch("utils.http.httpx.AsyncClient", factory)


@pytest.mark.asyncio
async def test_make_request_returns_the_readable_error():
    with _client_answering(400, json.dumps(VALIDATION)):
        result = await make_request("POST", "/self/loans", auth="Basic x", data={})

    assert result["status_code"] == 400
    assert result["errors"][0]["parameter"] == "principal"
    assert "developerMessage" not in json.dumps(result)


@pytest.mark.asyncio
async def test_make_request_hides_an_html_error_page():
    with _client_answering(502, HTML, "text/html"):
        result = await make_request("GET", "/self/clients", auth="Basic x")

    assert result == {"error": True, "status_code": 502, "message": "The bank had an internal error. Try again later."}


@pytest.mark.asyncio
async def test_make_request_still_returns_successful_answers_unchanged():
    with _client_answering(200, json.dumps({"resourceId": 5})):
        assert await make_request("GET", "/self/clients/5", auth="Basic x") == {"resourceId": 5}
