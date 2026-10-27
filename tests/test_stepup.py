import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.elicitation import AcceptedElicitation, CancelledElicitation, DeclinedElicitation

from routers.stepup_tools import resend_step_up, verify_step_up
from routers.transfer_tools import confirm_transfer, prepare_transfer
from routers.auth_tools import update_password_self
from utils import auth, stepup
from utils.stepup import OtpForm, resend_pending, resolve_step_up, step_up_code, verify_pending
from tests.stepup_support import (
    AUTH,
    CHALLENGE,
    CONFIG,
    TOKEN,
    TRANSFER,
    TRANSFER_PAYLOAD,
    api_error,
    bank_routes,
    required,
    standard_api,
)
from utils import transfers


async def prepare_and_confirm():
    prepared = await prepare_transfer(11, 22, 100.5, "rent", third_party=True)
    return await confirm_transfer(prepared["confirmation_id"])


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.delenv("MIFOS_STEP_UP_CHANNEL", raising=False)
    monkeypatch.delenv("MIFOS_STEP_UP_ALLOW_CHAT_OTP", raising=False)
    stepup.clear_pending()
    transfers.clear_prepared()
    yield
    stepup.clear_pending()
    transfers.clear_prepared()


@pytest.fixture
def no_form():
    """The client cannot show a form: the chat fallback is used."""
    with patch("utils.stepup._elicitation_context", return_value=None):
        yield


class FakeContext:
    def __init__(self, *answers):
        self.elicit = AsyncMock(side_effect=list(answers))


def accept(otp):
    return AcceptedElicitation[OtpForm](data=OtpForm(otp=otp))


async def start(api, ctx=None, data=None, action="TPT_TRANSFER"):
    """Run the first step as a tool does, with the given client (None = chat fallback)."""
    with patch("utils.stepup.make_request", api), patch("utils.stepup._elicitation_context", return_value=ctx):
        return await resolve_step_up(
            required(action), "POST", "/self/accounttransfers?type=tpt", auth=AUTH, data=data or TRANSFER
        )


# --- reading errors -----------------------------------------------------------------------------


def test_step_up_code_reads_the_error_code():
    assert step_up_code(required()) == "required"
    assert step_up_code(api_error("otp.invalid", 400)) == "otp.invalid"


@pytest.mark.parametrize(
    "result",
    [
        {"resourceId": 1},
        {"error": True, "status_code": 403, "message": "Forbidden"},
        {"error": True, "status_code": 403, "message": "[1, 2]"},
        {"error": True, "status_code": 400, "message": json.dumps({"userMessageGlobalisationCode": "error.msg.other"})},
        None,
        "text",
    ],
)
def test_step_up_code_ignores_everything_else(result):
    assert step_up_code(result) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result",
    [
        {"resourceId": 1},
        {"error": True, "status_code": 403, "message": "Forbidden"},
        required("SOMETHING_NEW"),
        api_error("locked", 429, retryAfterSeconds=60),
    ],
)
async def test_results_that_do_not_ask_for_step_up_pass_through_untouched(result):
    api = standard_api()
    with patch("utils.stepup.make_request", api):
        assert await resolve_step_up(result, "POST", "/x", auth=AUTH, data={}) is result
    assert api.calls == []


@pytest.mark.asyncio
async def test_a_transfer_without_a_login_session_says_to_log_in_and_sends_no_code():
    api = standard_api()
    with patch("utils.stepup.make_request", api):
        result = await resolve_step_up(
            api_error("session.required"), "POST", "/self/accounttransfers?type=tpt", auth=AUTH, data=TRANSFER
        )
    assert result["error"] is True and result["executed"] is False
    assert result["code"] == "session.required"
    assert "login tool" in result["message"]
    assert api.calls == []


# --- chat fallback ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_without_a_form_the_tool_returns_a_structured_step_up_required(no_form):
    api = standard_api()
    result = await start(api)

    assert result["step_up_required"] is True
    assert result["executed"] is False
    assert result["challengeId"] == 7
    assert result["maskedDestination"] == "a***@example.com"
    assert result["attemptsRemaining"] == 5
    assert "third-party transfer of 100.5 from account 11 to account 22" in result["summary"]
    assert "Ask the USER" in result["message"] and "verify_step_up" in result["message"]
    # nothing was sent to the transfer endpoint yet, and the challenge binds only the approved fields
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []
    (challenge_call,) = api.calls_to("POST", "/self/stepup/challenges")
    assert challenge_call["auth"] == AUTH
    assert challenge_call["data"] == {"action": "TPT_TRANSFER", "channel": "EMAIL", "payload": TRANSFER_PAYLOAD}


@pytest.mark.asyncio
async def test_the_right_code_repeats_exactly_the_approved_request_with_the_token(no_form):
    api = standard_api()
    data = dict(TRANSFER)
    await start(api, data=data)
    data["transferAmount"] = 999999  # the AI cannot change what was approved afterwards

    with patch("utils.stepup.make_request", api):
        result = await verify_pending(7, " 123456 ", auth=AUTH)

    assert result == {"resourceId": 99}
    (verify_call,) = api.calls_to("POST", "/self/stepup/challenges/7/verify")
    assert verify_call["data"] == {"otp": "123456"}
    (replay,) = api.calls_to("POST", "/self/accounttransfers?type=tpt")
    assert replay["data"] == TRANSFER
    assert replay["headers"] == {"X-Step-Up-Token": TOKEN}
    assert replay["auth"] == AUTH
    # the code works once
    with patch("utils.stepup.make_request", api):
        again = await verify_pending(7, "123456", auth=AUTH)
    assert again["error"] is True and again["status_code"] == 404
    assert len(api.calls_to("POST", "/self/accounttransfers?type=tpt")) == 1


@pytest.mark.asyncio
async def test_the_token_and_the_code_never_appear_in_what_the_ai_receives(no_form):
    api = standard_api()
    started = await start(api)
    with patch("utils.stepup.make_request", api):
        wrong = await verify_pending(7, "000000", auth=AUTH)
    assert "123456" not in json.dumps(started) + json.dumps(wrong)
    assert TOKEN not in json.dumps(started) + json.dumps(wrong)


@pytest.mark.asyncio
async def test_a_wrong_code_keeps_the_operation_waiting_and_reports_attempts(no_form):
    api = standard_api(**{"POST /self/stepup/challenges/7/verify": api_error("otp.invalid", 400, attemptsRemaining=4)})
    await start(api)
    with patch("utils.stepup.make_request", api):
        result = await verify_pending(7, "000000", auth=AUTH)

    assert result["error"] is True
    assert result["step_up_required"] is True
    assert result["executed"] is False
    assert result["attemptsRemaining"] == 4
    assert "4 attempts left" in result["message"]
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []
    assert 7 in stepup._pending


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error, text",
    [
        (api_error("locked", 429, retryAfterSeconds=900), "Too many incorrect codes"),
        (api_error("otp.expired", 400), "expired"),
        (api_error("invalid", 403), "no longer valid"),
    ],
)
async def test_a_final_failure_cancels_the_waiting_operation(no_form, error, text):
    api = standard_api(**{"POST /self/stepup/challenges/7/verify": error})
    await start(api)
    with patch("utils.stepup.make_request", api):
        result = await verify_pending(7, "123456", auth=AUTH)

    assert result["error"] is True and result["executed"] is False
    assert text in result["message"]
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []
    assert 7 not in stepup._pending


@pytest.mark.asyncio
async def test_a_failed_failure_message_does_not_echo_the_server_text(no_form):
    raw = api_error("locked", 429, retryAfterSeconds=900)
    body = json.loads(raw["message"])
    body["developerMessage"] = "stack trace SELECT * FROM secrets"
    raw["message"] = json.dumps(body)
    api = standard_api(**{"POST /self/stepup/challenges/7/verify": raw})
    await start(api)
    with patch("utils.stepup.make_request", api):
        result = await verify_pending(7, "123456", auth=AUTH)
    assert "secrets" not in json.dumps(result)
    assert result["retryAfterSeconds"] == 900


@pytest.mark.asyncio
async def test_verify_for_an_unknown_challenge_does_not_call_the_server():
    api = standard_api()
    with patch("utils.stepup.make_request", api):
        result = await verify_pending(123, "123456", auth=AUTH)
    assert result["status_code"] == 404 and result["executed"] is False
    assert api.calls == []


@pytest.mark.asyncio
async def test_waiting_operations_expire_and_are_limited(no_form, monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(stepup.time, "monotonic", lambda: clock["now"])
    api = standard_api()
    await start(api)
    clock["now"] += stepup.PENDING_TTL_SECONDS + 1
    with patch("utils.stepup.make_request", api):
        expired = await verify_pending(7, "123456", auth=AUTH)
    assert expired["status_code"] == 404

    for number in range(stepup.MAX_PENDING + 2):
        stepup._remember_and_ask({"challengeId": number}, "POST", "/x", {}, "TPT_TRANSFER", "s")
    assert len(stepup._pending) == stepup.MAX_PENDING
    assert 0 not in stepup._pending and stepup.MAX_PENDING + 1 in stepup._pending


@pytest.mark.asyncio
async def test_resend_asks_the_server_and_reports_the_new_state(no_form):
    api = standard_api(**{"POST /self/stepup/challenges/7/resend": {**CHALLENGE, "resendsRemaining": 2}})
    await start(api)
    with patch("utils.stepup.make_request", api):
        result = await resend_pending(7, auth=AUTH)
    assert result["step_up_required"] is True
    assert result["resendsRemaining"] == 2
    assert "verify_step_up" in result["message"]

    api.routes[("POST", "/self/stepup/challenges/7/resend")] = [api_error("resend.cooldown", 429, retryAfterSeconds=12)]
    with patch("utils.stepup.make_request", api):
        slow = await resend_pending(7, auth=AUTH)
    assert slow["error"] is True and slow["retryAfterSeconds"] == 12
    assert 7 in stepup._pending

    with patch("utils.stepup.make_request", api):
        assert (await resend_pending(55, auth=AUTH))["status_code"] == 404


# --- channel and configuration ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_channel_can_be_chosen_by_the_operator(no_form, monkeypatch):
    monkeypatch.setenv("MIFOS_STEP_UP_CHANNEL", "sms")
    api = standard_api()
    await start(api)
    assert api.calls_to("POST", "/self/stepup/challenges")[0]["data"]["channel"] == "SMS"


@pytest.mark.asyncio
async def test_an_unavailable_channel_falls_back_to_one_the_user_has(no_form, monkeypatch):
    monkeypatch.setenv("MIFOS_STEP_UP_CHANNEL", "SMS")
    api = standard_api(**{"GET /self/stepup/config": {**CONFIG, "availableChannels": ["EMAIL"]}})
    await start(api)
    assert api.calls_to("POST", "/self/stepup/challenges")[0]["data"]["channel"] == "EMAIL"


@pytest.mark.asyncio
async def test_no_channel_means_no_code_is_sent(no_form):
    api = standard_api(**{"GET /self/stepup/config": {**CONFIG, "availableChannels": []}})
    result = await start(api)
    assert result["error"] is True and result["executed"] is False
    assert "Contact the bank" in result["message"]
    assert api.calls_to("POST", "/self/stepup/challenges") == []


@pytest.mark.asyncio
async def test_a_login_session_is_needed_and_the_message_says_so(no_form):
    api = standard_api(**{"POST /self/stepup/challenges": api_error("session.required")})
    result = await start(api)
    assert result["error"] is True and result["executed"] is False
    assert "login tool" in result["message"]
    assert result["code"] == "session.required"


@pytest.mark.asyncio
async def test_a_failure_to_send_the_code_is_reported_without_server_text(no_form):
    api = standard_api(**{"POST /self/stepup/challenges": api_error("rate.limited", 429, retryAfterSeconds=60)})
    result = await start(api)
    assert result["error"] is True and result["retryAfterSeconds"] == 60
    assert result["message"] == "Could not start the verification."


@pytest.mark.asyncio
async def test_config_failure_stops_before_any_code_is_sent(no_form):
    api = standard_api(**{"GET /self/stepup/config": {"error": True, "status_code": 500, "message": "boom"}})
    result = await start(api)
    assert result["error"] is True
    assert api.calls_to("POST", "/self/stepup/challenges") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["false", "0", "no", "OFF"])
async def test_the_chat_fallback_can_be_forbidden(monkeypatch, value):
    monkeypatch.setenv("MIFOS_STEP_UP_ALLOW_CHAT_OTP", value)
    api = standard_api()
    result = await start(api)
    assert result["error"] is True and result["executed"] is False
    assert "securely" in result["message"]
    assert api.calls == []  # no code was even sent


# --- password change ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_password_change_binds_only_the_action_and_never_sends_the_password_in_the_challenge(no_form):
    api = standard_api(**{"POST /self/stepup/challenges": {**CHALLENGE, "action": "CHANGE_PASSWORD"}})
    data = {"password": "n3w-secret", "repeatPassword": "n3w-secret"}
    result = await start(api, data=data, action="CHANGE_PASSWORD")

    (challenge_call,) = api.calls_to("POST", "/self/stepup/challenges")
    assert challenge_call["data"] == {"action": "CHANGE_PASSWORD", "channel": "EMAIL"}
    assert "n3w-secret" not in json.dumps(result)
    assert "change the password" in result["summary"]


# --- with a form (elicitation) ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_a_form_the_person_types_the_code_and_the_operation_finishes_in_one_call():
    api = standard_api()
    ctx = FakeContext(accept("123456"))
    result = await start(api, ctx=ctx)

    assert result == {"resourceId": 99}
    ctx.elicit.assert_awaited_once()
    kwargs = ctx.elicit.await_args.kwargs
    assert kwargs["schema"] is OtpForm
    assert "a***@example.com" in kwargs["message"]
    assert "third-party transfer of 100.5" in kwargs["message"]
    (replay,) = api.calls_to("POST", "/self/accounttransfers?type=tpt")
    assert replay["data"] == TRANSFER and replay["headers"] == {"X-Step-Up-Token": TOKEN}
    assert stepup._pending == {}
    assert TOKEN not in json.dumps(result)


@pytest.mark.asyncio
async def test_a_wrong_code_in_the_form_asks_again_and_shows_the_attempts_left():
    api = standard_api(
        **{
            "POST /self/stepup/challenges/7/verify": [
                api_error("otp.invalid", 400, attemptsRemaining=4),
                {"stepUpToken": TOKEN, "action": "TPT_TRANSFER"},
            ]
        }
    )
    ctx = FakeContext(accept("000000"), accept("123456"))
    result = await start(api, ctx=ctx)

    assert result == {"resourceId": 99}
    assert ctx.elicit.await_count == 2
    assert "4 attempts left" in ctx.elicit.await_args_list[1].kwargs["message"]
    assert len(api.calls_to("POST", "/self/stepup/challenges/7/verify")) == 2


@pytest.mark.asyncio
async def test_the_form_stops_after_the_server_locks_the_challenge():
    api = standard_api(
        **{
            "POST /self/stepup/challenges/7/verify": [
                api_error("otp.invalid", 400, attemptsRemaining=1),
                api_error("locked", 429, retryAfterSeconds=900),
            ]
        }
    )
    ctx = FakeContext(accept("000000"), accept("111111"))
    result = await start(api, ctx=ctx)

    assert result["error"] is True and result["executed"] is False
    assert "Too many incorrect codes" in result["message"]
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", [DeclinedElicitation(), CancelledElicitation()])
async def test_declining_the_form_cancels_without_executing(answer):
    api = standard_api()
    result = await start(api, ctx=FakeContext(answer))

    assert result["error"] is True and result["cancelled"] is True and result["executed"] is False
    assert api.calls_to("POST", "/self/stepup/challenges/7/verify") == []
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []


@pytest.mark.asyncio
async def test_a_client_that_cannot_show_the_form_falls_back_to_the_chat():
    api = standard_api()
    ctx = SimpleNamespace(elicit=AsyncMock(side_effect=RuntimeError("method not found")))
    result = await start(api, ctx=ctx)

    assert result["step_up_required"] is True and result["challengeId"] == 7
    assert 7 in stepup._pending
    assert len(api.calls_to("POST", "/self/stepup/challenges")) == 1  # one code, not two


@pytest.mark.asyncio
async def test_a_form_that_fails_is_not_replaced_by_the_chat_when_the_chat_is_forbidden(monkeypatch):
    monkeypatch.setenv("MIFOS_STEP_UP_ALLOW_CHAT_OTP", "false")
    ctx = SimpleNamespace(elicit=AsyncMock(side_effect=RuntimeError("boom")))
    result = await start(standard_api(), ctx=ctx)
    assert result["error"] is True and "disabled" in result["message"]
    assert stepup._pending == {}


@pytest.mark.asyncio
async def test_the_form_gives_up_after_too_many_rounds(monkeypatch):
    monkeypatch.setattr(stepup, "MAX_ELICITATION_ROUNDS", 3)
    api = standard_api(**{"POST /self/stepup/challenges/7/verify": api_error("otp.invalid", 400, attemptsRemaining=2)})
    ctx = FakeContext(*[accept("000000")] * 3)
    result = await start(api, ctx=ctx)
    assert result["error"] is True and result["executed"] is False
    assert ctx.elicit.await_count == 3


# --- detecting a client that can show a form ----------------------------------------------------


def context_with(elicitation):
    capabilities = SimpleNamespace(elicitation=elicitation)
    session = SimpleNamespace(client_params=SimpleNamespace(capabilities=capabilities))
    return SimpleNamespace(request_context=SimpleNamespace(session=session))


def test_outside_a_request_there_is_no_form():
    assert stepup._elicitation_context() is None


@pytest.mark.parametrize(
    "elicitation, supported",
    [
        (None, False),
        (SimpleNamespace(form=None, url=None), True),  # empty capability = the original form mode
        (SimpleNamespace(form={}, url=None), True),
        (SimpleNamespace(form={}, url={}), True),
        (SimpleNamespace(form=None, url={}), False),  # URL mode only
    ],
)
def test_only_a_client_with_form_elicitation_gets_the_form(elicitation, supported):
    ctx = context_with(elicitation)
    with patch.object(stepup.mcp, "get_context", return_value=ctx):
        assert (stepup._elicitation_context() is ctx) is supported


# --- through the real tools ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_transfer_tool_runs_the_whole_flow_with_a_form():
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    api = bank_routes(**{"POST /self/accounttransfers?type=tpt": [required(), {"resourceId": 99}]})
    # first the person confirms the transfer, then types the bank's code
    ctx = FakeContext(
        SimpleNamespace(action="accept", data=transfers.ConfirmTransferForm(confirm=True)), accept("123456")
    )
    with (
        patch("routers.transfer_tools.make_request", api),
        patch("utils.stepup.make_request", api),
        patch("utils.stepup._elicitation_context", return_value=ctx),
    ):
        result = await prepare_and_confirm()

    assert result["executed"] is True and result["resourceId"] == 99
    sent = api.calls_to("POST", "/self/accounttransfers?type=tpt")
    assert [c["headers"] for c in sent] == [None, {"X-Step-Up-Token": TOKEN}]
    assert sent[0]["data"] == sent[1]["data"]
    assert {k: sent[0]["data"][k] for k in TRANSFER_PAYLOAD} == TRANSFER_PAYLOAD


@pytest.mark.asyncio
async def test_the_transfer_tool_and_verify_tool_work_together_without_a_form():
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    api = bank_routes(**{"POST /self/accounttransfers?type=tpt": [required(), {"resourceId": 99}]})
    with (
        patch("routers.transfer_tools.make_request", api),
        patch("utils.stepup.make_request", api),
        patch("utils.stepup._elicitation_context", return_value=None),
    ):
        waiting = await prepare_and_confirm()
        assert waiting["step_up_required"] is True
        done = await verify_step_up(waiting["challengeId"], "123456")

    assert done == {"resourceId": 99}


@pytest.mark.asyncio
async def test_a_password_change_waits_for_the_code_and_keeps_the_session_until_it_succeeds(no_form):
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    api = standard_api(
        **{
            "PUT /self/user": [required("CHANGE_PASSWORD"), {"resourceId": 5}],
            "POST /self/stepup/challenges": {**CHALLENGE, "action": "CHANGE_PASSWORD"},
        }
    )
    with patch("routers.auth_tools.make_request", api), patch("utils.stepup.make_request", api):
        waiting = await update_password_self("old", "n3w-secret")
        assert waiting["step_up_required"] is True
        assert auth.get_auth_header() == AUTH  # still logged in
        done = await verify_step_up(7, "123456")

    assert done == {"resourceId": 5}
    assert api.calls_to("PUT", "/self/user")[1]["data"] == {"password": "n3w-secret", "repeatPassword": "n3w-secret"}
    # the server ended every session of the user, so the saved login is dropped too
    with pytest.raises(auth.NotLoggedInError):
        auth.get_auth_header()


@pytest.mark.asyncio
async def test_the_step_up_tools_need_a_login():
    with pytest.raises(auth.NotLoggedInError):
        await verify_step_up(7, "123456")
    with pytest.raises(auth.NotLoggedInError):
        await resend_step_up(7)


@pytest.mark.asyncio
async def test_the_resend_tool_uses_the_saved_session(no_form):
    auth.save_login({"base64EncodedAuthenticationKey": "c2Vzc2lvbg==", "username": "ana"})
    api = standard_api(**{"POST /self/stepup/challenges/7/resend": CHALLENGE})
    await start(api)
    with patch("utils.stepup.make_request", api):
        result = await resend_step_up(7)
    assert result["step_up_required"] is True
    assert api.calls_to("POST", "/self/stepup/challenges/7/resend")[0]["auth"] == AUTH
