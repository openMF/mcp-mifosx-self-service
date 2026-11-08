"""Step-up with an authenticator app (channel TOTP): channel choice, the form, the chat fallback."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.elicitation import AcceptedElicitation, CancelledElicitation

from utils import stepup
from utils.stepup import AppCodeForm, OtpForm, resend_pending, resolve_step_up, verify_pending
from tests.stepup_support import (
    AUTH,
    CHALLENGE,
    CONFIG,
    TOKEN,
    TRANSFER,
    TRANSFER_PAYLOAD,
    api_error,
    required,
    standard_api,
)

APP_CONFIG = {"enabled": True, "availableChannels": ["TOTP"], "otpLength": 6}
APP_CHALLENGE = {**CHALLENGE, "channel": "TOTP", "maskedDestination": None, "resendsRemaining": 0}
RECOVERY = "ABCDE-FGHJK"


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.delenv("MIFOS_STEP_UP_CHANNEL", raising=False)
    monkeypatch.delenv("MIFOS_STEP_UP_ALLOW_CHAT_OTP", raising=False)
    stepup.clear_pending()
    yield
    stepup.clear_pending()


def app_api(**overrides):
    routes = {
        "GET /self/stepup/config": APP_CONFIG,
        "POST /self/stepup/challenges": APP_CHALLENGE,
    }
    routes.update(overrides)
    return standard_api(**routes)


class FakeContext:
    def __init__(self, *answers):
        self.elicit = AsyncMock(side_effect=list(answers))


def accept(otp="", recovery_code=""):
    return AcceptedElicitation[AppCodeForm](data=AppCodeForm(otp=otp, recovery_code=recovery_code))


async def start(api, ctx=None, action="TPT_TRANSFER"):
    with patch("utils.stepup.make_request", api), patch("utils.stepup._elicitation_context", return_value=ctx):
        return await resolve_step_up(
            required(action), "POST", "/self/accounttransfers?type=tpt", auth=AUTH, data=TRANSFER
        )


def verify_bodies(api):
    return [call["data"] for call in api.calls_to("POST", "/self/stepup/challenges/7/verify")]


# --- which channel ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_authenticator_is_used_when_the_bank_offers_it():
    api = app_api()
    await start(api, FakeContext(accept(otp="123456")))
    (challenge_call,) = api.calls_to("POST", "/self/stepup/challenges")
    assert challenge_call["data"] == {"action": "TPT_TRANSFER", "channel": "TOTP", "payload": TRANSFER_PAYLOAD}


@pytest.mark.asyncio
async def test_the_authenticator_wins_over_the_other_channels_unless_the_operator_chose_one(monkeypatch):
    both = {"enabled": True, "availableChannels": ["EMAIL", "SMS", "TOTP"], "otpLength": 6}
    api = app_api(**{"GET /self/stepup/config": both})
    await start(api, FakeContext(accept(otp="123456")))
    assert api.calls_to("POST", "/self/stepup/challenges")[0]["data"]["channel"] == "TOTP"

    monkeypatch.setenv("MIFOS_STEP_UP_CHANNEL", "SMS")
    api = app_api(**{"GET /self/stepup/config": both, "POST /self/stepup/challenges": CHALLENGE})
    await start(api, None)
    assert api.calls_to("POST", "/self/stepup/challenges")[0]["data"]["channel"] == "SMS"


@pytest.mark.asyncio
async def test_a_channel_the_user_cannot_use_is_ignored(monkeypatch):
    monkeypatch.setenv("MIFOS_STEP_UP_CHANNEL", "SMS")
    api = app_api()  # only the authenticator is offered
    await start(api, FakeContext(accept(otp="123456")))
    assert api.calls_to("POST", "/self/stepup/challenges")[0]["data"]["channel"] == "TOTP"


@pytest.mark.asyncio
async def test_without_an_authenticator_nothing_changes():
    api = standard_api()
    with patch("utils.stepup._elicitation_context", return_value=None), patch("utils.stepup.make_request", api):
        result = await resolve_step_up(required(), "POST", "/self/accounttransfers?type=tpt", auth=AUTH, data=TRANSFER)
    assert api.calls_to("POST", "/self/stepup/challenges")[0]["data"]["channel"] == "EMAIL"
    assert "was sent to a***@example.com" in result["message"]
    assert CONFIG["availableChannels"][0] == "EMAIL"


# --- the form -----------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_form_asks_for_the_code_of_the_app_and_repeats_the_approved_request():
    api = app_api()
    ctx = FakeContext(accept(otp=" 654321 "))

    result = await start(api, ctx)

    assert result == {"resourceId": 99}
    ctx.elicit.assert_awaited_once()
    kwargs = ctx.elicit.await_args.kwargs
    assert kwargs["schema"] is AppCodeForm
    assert "authenticator app" in kwargs["message"] and "6-digit" in kwargs["message"]
    assert "was sent" not in kwargs["message"]
    assert "third-party transfer of 100.5" in kwargs["message"]
    assert verify_bodies(api) == [{"otp": "654321"}]
    (replay,) = api.calls_to("POST", "/self/accounttransfers?type=tpt")
    assert replay["headers"] == {"X-Step-Up-Token": TOKEN}
    assert replay["data"] == TRANSFER


@pytest.mark.asyncio
async def test_a_recovery_code_goes_to_the_bank_as_such():
    api = app_api()

    result = await start(api, FakeContext(accept(recovery_code=f" {RECOVERY} ")))

    assert result == {"resourceId": 99}
    assert verify_bodies(api) == [{"recoveryCode": RECOVERY}]


@pytest.mark.asyncio
@pytest.mark.parametrize("first", [accept(), accept(otp="123456", recovery_code=RECOVERY)])
async def test_an_empty_form_or_both_codes_ask_again_without_using_an_attempt(first):
    api = app_api()
    ctx = FakeContext(first, accept(otp="123456"))

    result = await start(api, ctx)

    assert result == {"resourceId": 99}
    assert ctx.elicit.await_count == 2
    assert "but not both" in ctx.elicit.await_args_list[1].kwargs["message"]
    assert verify_bodies(api) == [{"otp": "123456"}]  # the bank saw only the valid attempt


@pytest.mark.asyncio
async def test_a_wrong_code_asks_again_with_the_attempts_left():
    api = app_api(
        **{
            "POST /self/stepup/challenges/7/verify": [
                api_error("otp.invalid", 400, attemptsRemaining=4),
                {"stepUpToken": TOKEN, "action": "TPT_TRANSFER"},
            ]
        }
    )
    ctx = FakeContext(accept(otp="000000"), accept(otp="123456"))

    result = await start(api, ctx)

    assert result == {"resourceId": 99}
    assert "4 attempts left" in ctx.elicit.await_args_list[1].kwargs["message"]
    assert verify_bodies(api) == [{"otp": "000000"}, {"otp": "123456"}]


@pytest.mark.asyncio
async def test_cancelling_the_form_executes_nothing():
    api = app_api()

    result = await start(api, FakeContext(CancelledElicitation()))

    assert result["cancelled"] is True and result["executed"] is False
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []
    assert verify_bodies(api) == []


@pytest.mark.asyncio
async def test_a_lock_out_of_the_app_stops_the_operation():
    api = app_api(**{"POST /self/stepup/challenges/7/verify": api_error("locked", 429, retryAfterSeconds=900)})

    result = await start(api, FakeContext(accept(otp="123456")))

    assert result["error"] is True and result["executed"] is False
    assert "Too many incorrect codes" in result["message"]
    assert result["retryAfterSeconds"] == 900
    assert api.calls_to("POST", "/self/accounttransfers?type=tpt") == []


@pytest.mark.asyncio
async def test_an_app_that_is_no_longer_active_says_so():
    api = app_api(**{"POST /self/stepup/challenges/7/verify": api_error("totp.not.enrolled", 400)})

    result = await start(api, FakeContext(accept(otp="123456")))

    assert "no longer active" in result["message"]
    assert result["executed"] is False


@pytest.mark.asyncio
async def test_the_form_of_an_email_code_is_unchanged():
    api = standard_api()
    ctx = FakeContext(AcceptedElicitation[OtpForm](data=OtpForm(otp="123456")))

    await start(api, ctx)

    assert ctx.elicit.await_args.kwargs["schema"] is OtpForm
    assert "was sent to a***@example.com" in ctx.elicit.await_args.kwargs["message"]
    assert verify_bodies(api) == [{"otp": "123456"}]


# --- the chat fallback --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_without_a_form_the_ai_is_told_to_ask_for_the_code_of_the_app():
    api = app_api()

    result = await start(api, None)

    assert result["step_up_required"] is True and result["executed"] is False
    assert result["channel"] == "TOTP"
    assert "Nothing was sent" in result["message"]
    assert "authenticator app" in result["message"]
    assert "verify_step_up" in result["message"]
    assert "was sent to" not in result["message"]
    assert stepup._pending[7].channel == "TOTP"


@pytest.mark.asyncio
async def test_the_chat_accepts_the_six_digit_code_of_the_app():
    api = app_api()
    await start(api, None)

    with patch("utils.stepup.make_request", api):
        result = await verify_pending(7, " 123456 ", auth=AUTH)

    assert result == {"resourceId": 99}
    assert verify_bodies(api) == [{"otp": "123456"}]


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", [RECOVERY, "ABCDEFGHJK", "12345", "1234567", "12345a", ""])
async def test_the_chat_never_takes_a_recovery_code_or_a_malformed_code_and_does_not_ask_the_bank(typed):
    api = app_api()
    await start(api, None)

    with patch("utils.stepup.make_request", api):
        result = await verify_pending(7, typed, auth=AUTH)

    assert result["error"] is True and result["executed"] is False
    assert result["step_up_required"] is True
    assert "Recovery codes cannot be given in the chat" in result["message"]
    assert verify_bodies(api) == []  # no attempt of the bank was used
    assert 7 in stepup._pending  # the operation still waits for a good code


@pytest.mark.asyncio
async def test_the_recovery_code_is_not_echoed_back_to_the_ai():
    api = app_api()
    await start(api, None)
    with patch("utils.stepup.make_request", api):
        result = await verify_pending(7, RECOVERY, auth=AUTH)
    assert RECOVERY not in json.dumps(result)


@pytest.mark.asyncio
async def test_an_app_code_cannot_be_resent_and_the_bank_is_not_asked():
    api = app_api()
    await start(api, None)

    with patch("utils.stepup.make_request", api):
        result = await resend_pending(7, auth=AUTH)

    assert result["error"] is True and result["executed"] is False
    assert "cannot be sent again" in result["message"]
    assert api.calls_to("POST", "/self/stepup/challenges/7/resend") == []
    assert 7 in stepup._pending


@pytest.mark.asyncio
async def test_an_email_code_can_still_be_resent():
    api = standard_api(**{"POST /self/stepup/challenges/7/resend": CHALLENGE})
    await start(api, None)
    with patch("utils.stepup.make_request", api):
        result = await resend_pending(7, auth=AUTH)
    assert result["step_up_required"] is True
    assert len(api.calls_to("POST", "/self/stepup/challenges/7/resend")) == 1


@pytest.mark.asyncio
async def test_the_chat_can_be_forbidden_for_the_app_too(monkeypatch):
    monkeypatch.setenv("MIFOS_STEP_UP_ALLOW_CHAT_OTP", "false")
    api = app_api()

    result = await start(api, None)

    assert result["executed"] is False
    assert "cannot ask for it securely" in result["message"]
    assert api.calls == []
