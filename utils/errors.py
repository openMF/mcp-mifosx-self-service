"""Turns a failed bank response into a short answer the assistant can read and repeat to the user.

Fineract answers errors with a JSON body (``defaultUserMessage``, ``userMessageGlobalisationCode`` and,
for validation errors, one entry per field in ``errors``); some servers in front of it answer a Spring
error object or an HTML page. Passing that raw text on makes the assistant guess, and it can expose
internal details (developer messages, paths, stack traces). This keeps only what the user needs.
"""

import json
from typing import Any, Dict, List, Optional

MAX_MESSAGE_LENGTH = 500
MAX_FIELD_ERRORS = 10

# Extra fields of an error body that clients act on (step-up: what is being confirmed, attempts and
# waiting time). They are kept as they are; everything else is dropped.
KEPT_FIELDS = ("action", "attemptsRemaining", "retryAfterSeconds", "resendAvailableAt")

_GENERIC = {
    400: "The bank rejected the request.",
    401: "The bank did not accept the login. Log in again.",
    403: "The bank does not allow this operation for this user.",
    404: "The bank could not find what was asked for.",
    405: "The bank does not support this operation.",
    409: "The request conflicts with the current state of the account.",
    429: "Too many requests. Try again later.",
}


def _short(text: Any) -> Optional[str]:
    if not isinstance(text, str):
        return None
    text = " ".join(text.split())
    if not text:
        return None
    return text if len(text) <= MAX_MESSAGE_LENGTH else text[: MAX_MESSAGE_LENGTH - 3] + "..."


def _generic(status_code: int) -> str:
    if status_code in _GENERIC:
        return _GENERIC[status_code]
    if status_code >= 500:
        return "The bank had an internal error. Try again later."
    return f"The bank answered with an error (HTTP {status_code})."


def _field_errors(body: Dict[str, Any]) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []
    for item in body.get("errors") or []:
        if not isinstance(item, dict):
            continue
        message = _short(item.get("defaultUserMessage")) or _short(item.get("developerMessage"))
        if not message:
            continue
        entry = {"message": message}
        if isinstance(item.get("parameterName"), str) and item["parameterName"]:
            entry["parameter"] = item["parameterName"]
        if entry not in errors:
            errors.append(entry)
        if len(errors) == MAX_FIELD_ERRORS:
            break
    return errors


def api_error(status_code: int, text: str) -> Dict[str, Any]:
    """The error result of a failed request: ``message``, field ``errors`` and the bank's error ``code``."""
    result: Dict[str, Any] = {"error": True, "status_code": status_code}
    try:
        body = json.loads(text) if text else None
    except ValueError:
        body = None

    if not isinstance(body, dict):
        # an HTML error page or plain text from a proxy: never pass it on
        result["message"] = _generic(status_code)
        return result

    errors = _field_errors(body)
    if errors:
        # the headline is often generic ("Validation errors exist.", "The requested resource is not
        # available."); the field errors say what is actually wrong
        message = "; ".join(e["message"] for e in errors[:3])
    else:
        # a Spring error object has "error" ("Not Found") but no user message
        message = _short(body.get("defaultUserMessage")) or _generic(status_code)
    result["message"] = _short(message) or _generic(status_code)
    if errors:
        result["errors"] = errors
    code = body.get("userMessageGlobalisationCode")
    if isinstance(code, str) and code:
        result["code"] = code
    for key in KEPT_FIELDS:
        if key in body:
            result[key] = body[key]
    return result
