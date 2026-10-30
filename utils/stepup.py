"""Step-up (one-time code) confirmation of sensitive operations.

When the self-service API answers ``error.msg.selfservice.stepup.required`` the person who owns the
account must confirm the operation with a one-time code sent to their phone or e-mail, or shown by
their authenticator app (channel ``TOTP``, when they paired one). This module runs that confirmation
and then repeats the original request with the single-use step-up token.

The AI never sees the code or the token:

* If the client supports MCP elicitation, the person types the code in a form shown by the client.
  The value goes straight to this server, and the whole operation finishes inside the same tool call.
* Otherwise the tool returns ``step_up_required`` and the person gives the code to the AI, which
  passes it to the ``verify_step_up`` tool. The code then passes through the chat, so an operator can
  forbid this fallback with ``MIFOS_STEP_UP_ALLOW_CHAT_OTP=false``.

A recovery code of the authenticator app (for a lost phone) is only ever asked for in the elicitation
form, never through the chat: it is a long-lived credential, unlike a code that is valid for seconds.
Pairing or removing the authenticator is not offered as a tool at all: the secret must not pass through
an AI conversation, so that stays in the bank's own app or website.

The request that is repeated is the one that was approved: it is kept here, not taken from the AI
again, and the server also binds the code to the accounts and the amount.
"""

import copy
import json
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field

from mcp_app import mcp
from utils.auth import clear_login
from utils.errors import KEPT_FIELDS
from utils.http import make_request

STEP_UP_HEADER = "X-Step-Up-Token"
ERROR_PREFIX = "error.msg.selfservice.stepup."

CHANNEL_ENV = "MIFOS_STEP_UP_CHANNEL"
APP_CHANNEL = "TOTP"
APP_CODE_LENGTH = 6
ALLOW_CHAT_OTP_ENV = "MIFOS_STEP_UP_ALLOW_CHAT_OTP"

# Fields of the request that the server binds the code to, per protected action (see the plugin's
# StepUpAction). The challenge must be created with exactly these values.
_TRANSFER_FIELDS = ("fromAccountId", "fromAccountType", "toAccountId", "toAccountType", "transferAmount")
PAYLOAD_FIELDS: Dict[str, Tuple[str, ...]] = {
    "TPT_TRANSFER": _TRANSFER_FIELDS,
    "OWN_TRANSFER": _TRANSFER_FIELDS,
    "CHANGE_PASSWORD": (),
}

PENDING_TTL_SECONDS = 600
MAX_PENDING = 5
MAX_ELICITATION_ROUNDS = 10

CHALLENGES_PATH = "/self/stepup/challenges"


class OtpForm(BaseModel):
    """What the person is asked for. Only a primitive field is allowed in an elicitation form."""

    otp: str = Field(title="Verification code", description="The one-time code you received")


class AppCodeForm(BaseModel):
    """The form for an authenticator app: the code it shows now, or a recovery code (lost phone)."""

    otp: str = Field(
        default="",
        title="Code from your authenticator app",
        description="The 6-digit code your app shows now",
    )
    recovery_code: str = Field(
        default="",
        title="Recovery code",
        description="Only if you lost your phone: one of the recovery codes you saved (each works once)",
    )


@dataclass
class PendingStepUp:
    """An operation waiting for its code (chat fallback only)."""

    challenge_id: int
    method: str
    endpoint: str
    data: Optional[Dict[str, Any]]
    action: str
    summary: str
    created: float
    channel: str = ""


_pending: "OrderedDict[int, PendingStepUp]" = OrderedDict()


def clear_pending() -> None:
    """Forget every operation waiting for a code."""
    _pending.clear()


# --- reading API answers ----------------------------------------------------------------------


def _body(result: Any) -> Dict[str, Any]:
    """The error code and step-up details of a failed request.

    make_request returns the bank's error code in ``code`` (see utils.errors); an answer that still carries
    the raw JSON body in ``message`` is read too.
    """
    if not isinstance(result, dict) or not result.get("error"):
        return {}
    if "code" in result:
        body = {key: result[key] for key in KEPT_FIELDS if key in result}
        body["userMessageGlobalisationCode"] = result["code"]
        return body
    message = result.get("message")
    if isinstance(message, dict):
        return message
    if isinstance(message, str):
        try:
            parsed = json.loads(message)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def step_up_code(result: Any) -> Optional[str]:
    """``required``, ``otp.invalid``, ... when the answer is a step-up error, else ``None``."""
    code = _body(result).get("userMessageGlobalisationCode")
    if isinstance(code, str) and code.startswith(ERROR_PREFIX):
        return code[len(ERROR_PREFIX) :]
    return None


def _failure(status_code: int, message: str, **extra: Any) -> Dict[str, Any]:
    return {"error": True, "status_code": status_code, "message": message, **extra}


def _api_failure(result: Dict[str, Any], message: str, **extra: Any) -> Dict[str, Any]:
    """A short, safe failure built from an API error (never echoes the raw response)."""
    body = _body(result)
    details: Dict[str, Any] = {key: body[key] for key in ("attemptsRemaining", "retryAfterSeconds") if key in body}
    code = step_up_code(result)
    if code:
        details["code"] = code
    return _failure(int(result.get("status_code", 400)), message, **details, **extra)


# --- what is being approved -------------------------------------------------------------------


def _payload(action: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {field: data[field] for field in PAYLOAD_FIELDS[action] if data and field in data}


def _summary(action: str, payload: Dict[str, Any]) -> str:
    if action == "CHANGE_PASSWORD":
        return "change the password of your self-service user"
    amount = payload.get("transferAmount", "?")
    source = payload.get("fromAccountId", "?")
    target = payload.get("toAccountId", "?")
    kind = "third-party transfer" if action == "TPT_TRANSFER" else "transfer between your accounts"
    return f"{kind} of {amount} from account {source} to account {target}"


# --- how the person is asked ------------------------------------------------------------------


def _allow_chat_otp() -> bool:
    return os.getenv(ALLOW_CHAT_OTP_ENV, "true").strip().lower() not in ("0", "false", "no", "off")


def _elicitation_context() -> Any:
    """The request context when the connected client can show a form, else ``None``."""
    try:
        ctx = mcp.get_context()
        client_params = ctx.request_context.session.client_params
        elicitation = client_params.capabilities.elicitation if client_params else None
        # An empty capability means form mode (the original elicitation); a client that lists only
        # URL mode cannot show our form.
        if elicitation is not None and (
            getattr(elicitation, "form", None) is not None or getattr(elicitation, "url", None) is None
        ):
            return ctx
    except Exception:  # outside a request, or a client without the capability
        pass
    return None


async def _choose_channel(auth: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """The delivery channel to use, or an error result."""
    config = await make_request("GET", "/self/stepup/config", auth=auth)
    if isinstance(config, dict) and config.get("error"):
        return None, _api_failure(config, "Could not read the step-up configuration.", executed=False)
    available = [str(channel).upper() for channel in (config or {}).get("availableChannels", [])]
    if not available:
        return None, _failure(
            400,
            "No channel is available to send the verification code to this user. Contact the bank.",
            step_up_required=True,
            executed=False,
        )
    preferred = os.getenv(CHANNEL_ENV, "").strip().upper()
    if preferred in available:
        return preferred, None
    # The authenticator app is the safer way (nothing travels by SMS or e-mail): use it when paired.
    return (APP_CHANNEL if APP_CHANNEL in available else available[0]), None


# --- running the confirmation -----------------------------------------------------------------


def _challenge_view(challenge: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: challenge[key]
        for key in (
            "challengeId",
            "channel",
            "maskedDestination",
            "expiresAt",
            "attemptsRemaining",
            "resendAvailableAt",
            "resendsRemaining",
        )
        if key in challenge
    }


async def resolve_step_up(
    result: Any,
    method: str,
    endpoint: str,
    *,
    auth: str,
    data: Optional[Dict[str, Any]] = None,
) -> Any:
    """Return ``result`` unless it asks for step-up; then confirm with the person and repeat the call.

    Call it with the answer of the first attempt of a sensitive request, which is sent without a token.
    """
    code = step_up_code(result)
    if code == "session.required":
        return _session_failure(result)
    if code != "required":
        return result
    action = _body(result).get("action")
    if action not in PAYLOAD_FIELDS:
        return result

    payload = _payload(action, data)
    summary = _summary(action, payload)

    ctx = _elicitation_context()
    if ctx is None and not _allow_chat_otp():
        return _failure(
            403,
            "This operation needs a verification code, and this client cannot ask for it securely "
            "(no elicitation support). Confirm it in the bank's own app or website instead.",
            step_up_required=True,
            executed=False,
        )

    channel, failure = await _choose_channel(auth)
    if failure:
        return failure

    request: Dict[str, Any] = {"action": action, "channel": channel}
    if payload:
        request["payload"] = payload
    challenge = await make_request("POST", CHALLENGES_PATH, auth=auth, data=request)
    if challenge.get("error"):
        return _challenge_failure(challenge)

    if ctx is not None:
        outcome = await _confirm_by_form(ctx, challenge, method, endpoint, auth, data, summary)
        if outcome is not None:
            return outcome
        # The client announced elicitation but could not show the form: fall back to the chat.

    if not _allow_chat_otp():
        return _failure(
            403,
            "The verification form could not be shown, and entering the code in the chat is disabled.",
            step_up_required=True,
            executed=False,
        )
    return _remember_and_ask(challenge, method, endpoint, data, action, summary)


def _session_failure(result: Dict[str, Any]) -> Dict[str, Any]:
    return _api_failure(
        result,
        "Verification needs a login session. Call the login tool first: the credentials in the "
        "server environment are not enough for this step.",
        step_up_required=True,
        executed=False,
    )


def _challenge_failure(challenge: Dict[str, Any]) -> Dict[str, Any]:
    if step_up_code(challenge) == "session.required":
        return _session_failure(challenge)
    return _api_failure(challenge, "Could not start the verification.", step_up_required=True, executed=False)


async def _send_verified(
    token: str, method: str, endpoint: str, auth: str, data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Repeat the approved request with the one-time token."""
    return await make_request(method, endpoint, auth=auth, data=data, headers={STEP_UP_HEADER: token})


async def _confirm_by_form(
    ctx: Any,
    challenge: Dict[str, Any],
    method: str,
    endpoint: str,
    auth: str,
    data: Optional[Dict[str, Any]],
    summary: str,
) -> Optional[Dict[str, Any]]:
    """Ask the person for the code through the client. ``None`` means the form cannot be shown."""
    challenge_id = challenge["challengeId"]
    app = challenge.get("channel") == APP_CHANNEL
    notice = ""
    for _ in range(MAX_ELICITATION_ROUNDS):
        if app:
            prompt = (
                f"{notice}Open your authenticator app and enter the {APP_CODE_LENGTH}-digit code it shows to "
                f"confirm: {summary}. If you lost your phone, leave that empty and enter a recovery code."
            )
        else:
            prompt = (
                f"{notice}A verification code was sent to {challenge.get('maskedDestination', 'you')}. "
                f"Enter it to confirm: {summary}."
            )
        try:
            answer = await ctx.elicit(message=prompt, schema=AppCodeForm if app else OtpForm)
        except Exception:
            return None
        if getattr(answer, "action", None) != "accept":
            return _failure(
                400,
                "The verification was cancelled by the user. The operation was not executed.",
                step_up_required=True,
                executed=False,
                cancelled=True,
            )
        otp = answer.data.otp.strip()
        recovery = getattr(answer.data, "recovery_code", "").strip()
        if app and bool(otp) == bool(recovery):
            # Nothing, or both: ask again without bothering the bank (and without a wrong attempt).
            notice = "Enter the code of your app, or a recovery code, but not both. "
            continue
        body = {"recoveryCode": recovery} if app and recovery else {"otp": otp}
        verified = await make_request("POST", f"{CHALLENGES_PATH}/{challenge_id}/verify", auth=auth, data=body)
        if not verified.get("error"):
            return await _send_verified(str(verified.get("stepUpToken", "")), method, endpoint, auth, data)
        if step_up_code(verified) == "otp.invalid":
            left = _body(verified).get("attemptsRemaining")
            notice = f"That code was not correct ({left} attempts left). " if left is not None else "Incorrect code. "
            continue
        return _verify_failure(verified)
    return _failure(429, "Too many incorrect codes. The operation was not executed.", executed=False)


def _verify_failure(verified: Dict[str, Any]) -> Dict[str, Any]:
    code = step_up_code(verified)
    reasons = {
        "locked": "Too many incorrect codes. Try again later.",
        "otp.expired": "The code has expired. Repeat the operation to get a new one.",
        "totp.not.enrolled": "The authenticator app is no longer active. Repeat the operation to start again.",
        "invalid": "This verification is no longer valid. Repeat the operation to start a new one.",
        "rate.limited": "Too many verification requests. Try again later.",
    }
    return _api_failure(
        verified,
        reasons.get(code or "", "The verification failed.") + " The operation was not executed.",
        step_up_required=True,
        executed=False,
    )


def _remember_and_ask(
    challenge: Dict[str, Any],
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]],
    action: str,
    summary: str,
) -> Dict[str, Any]:
    """Chat fallback: keep the approved request and ask the AI to get the code from the person."""
    _purge_pending()
    challenge_id = challenge["challengeId"]
    _pending[challenge_id] = PendingStepUp(
        challenge_id,
        method,
        endpoint,
        copy.deepcopy(data),
        action,
        summary,
        time.monotonic(),
        str(challenge.get("channel", "")),
    )
    while len(_pending) > MAX_PENDING:
        _pending.popitem(last=False)
    if challenge.get("channel") == APP_CHANNEL:
        where = (
            "Nothing was sent: the code is the one the USER's authenticator app shows now. Ask the USER to open the "
            f"app and read the {APP_CODE_LENGTH}-digit code to you"
        )
    else:
        where = (
            f"A one-time code was sent to {challenge.get('maskedDestination', 'the user')}. Ask the USER for the code"
        )
    return {
        "step_up_required": True,
        "executed": False,
        "action": action,
        "summary": summary,
        **_challenge_view(challenge),
        "message": (
            f"Verification needed before this can run. {where}, "
            "and then call verify_step_up with the challengeId and the code. "
            "Never guess, invent or reuse a code. "
            f"The code only approves this operation: {summary}. It has NOT been executed yet."
        ),
    }


def _purge_pending() -> None:
    now = time.monotonic()
    for challenge_id in [k for k, v in _pending.items() if now - v.created > PENDING_TTL_SECONDS]:
        del _pending[challenge_id]


def _pending_for(challenge_id: int) -> Optional[PendingStepUp]:
    _purge_pending()
    return _pending.get(challenge_id)


_UNKNOWN = (
    "There is no operation waiting for this verification (it may have expired, finished or the "
    "server restarted). Repeat the original operation to start a new verification."
)


async def verify_pending(challenge_id: int, otp: str, *, auth: str) -> Dict[str, Any]:
    """Check the code the person gave and, if it is right, run the operation that was waiting."""
    pending = _pending_for(challenge_id)
    if pending is None:
        return _failure(404, _UNKNOWN, executed=False)
    code_text = otp.strip()
    if pending.channel == APP_CHANNEL and not (code_text.isdigit() and len(code_text) == APP_CODE_LENGTH):
        # Only the short-lived code of the app may pass through the chat; a recovery code may not.
        # Nothing is sent to the bank, so this cannot use up an attempt.
        return _failure(
            400,
            f"For an authenticator app the code is the {APP_CODE_LENGTH} digits the app shows now. "
            "Recovery codes cannot be given in the chat: confirm in the bank's own app or website instead.",
            step_up_required=True,
            executed=False,
            challengeId=challenge_id,
        )
    verified = await make_request(
        "POST", f"{CHALLENGES_PATH}/{challenge_id}/verify", auth=auth, data={"otp": code_text}
    )
    if verified.get("error"):
        code = step_up_code(verified)
        if code == "otp.invalid":
            left = _body(verified).get("attemptsRemaining")
            return _api_failure(
                verified,
                (
                    f"Incorrect code ({left} attempts left). Ask the user to check the code and try again."
                    if left is not None
                    else "Incorrect code. Ask the user to check the code and try again."
                ),
                step_up_required=True,
                executed=False,
                challengeId=challenge_id,
            )
        _pending.pop(challenge_id, None)
        return _verify_failure(verified)
    _pending.pop(challenge_id, None)
    result = await _send_verified(
        str(verified.get("stepUpToken", "")), pending.method, pending.endpoint, auth, pending.data
    )
    if pending.action == "CHANGE_PASSWORD" and not result.get("error"):
        clear_login()  # the server ended every session of the user
    return result


async def resend_pending(challenge_id: int, *, auth: str) -> Dict[str, Any]:
    """Ask the server to send the code again."""
    pending = _pending_for(challenge_id)
    if pending is None:
        return _failure(404, _UNKNOWN, executed=False)
    if pending.channel == APP_CHANNEL:
        return _failure(
            400,
            "A code from an authenticator app cannot be sent again: ask the USER for the code the app shows now "
            "and call verify_step_up.",
            step_up_required=True,
            executed=False,
            challengeId=challenge_id,
        )
    resent = await make_request("POST", f"{CHALLENGES_PATH}/{challenge_id}/resend", auth=auth)
    if resent.get("error"):
        return _api_failure(resent, "The code could not be sent again.", step_up_required=True, executed=False)
    return {
        "step_up_required": True,
        "executed": False,
        "summary": pending.summary,
        **_challenge_view(resent),
        "message": "A new code was sent. Ask the USER for it and call verify_step_up.",
    }
