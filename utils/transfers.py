"""Two-step transfers (US-E13-07): ``prepare`` shows what will happen, ``confirm`` runs it once.

The assistant can never move money in one call:

* ``prepare`` checks the accounts against the bank's transfer template (only the user's own accounts, or
  saved beneficiaries for third-party transfers), checks the amount against the operator's limit and keeps
  the exact request here under a short-lived confirmation id. Nothing is sent to the bank's transfer endpoint.
* ``confirm`` takes only that id. It runs the stored request (not one rebuilt by the AI), at most once and
  only before the id expires. When the client can show a form, the person confirms there first. When the
  bank asks for a one-time code (step-up), the code is required as well.
"""

import copy
import os
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field

MAX_AMOUNT_ENV = "MIFOS_TRANSFER_MAX_AMOUNT"
TTL_ENV = "MIFOS_TRANSFER_CONFIRM_TTL_SECONDS"
TIMEZONE_ENV = "MIFOS_TIMEZONE"

DEFAULT_TTL_SECONDS = 300
MAX_PREPARED = 5

SAVINGS = 2
LOAN = 1

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class ConfirmTransferForm(BaseModel):
    """What the person is asked in the client's form. Only a primitive field is allowed."""

    confirm: bool = Field(title="Send this transfer", description="Tick to send the transfer")


@dataclass
class PreparedTransfer:
    confirmation_id: str
    endpoint: str
    data: Dict[str, Any]
    summary: Dict[str, Any]
    text: str
    created: float
    kind: str = "transfer"


_prepared: "OrderedDict[str, PreparedTransfer]" = OrderedDict()


def clear_prepared() -> None:
    """Forget every prepared transfer."""
    _prepared.clear()


def failure(status_code: int, message: str, **extra: Any) -> Dict[str, Any]:
    return {"error": True, "status_code": status_code, "message": message, "executed": False, **extra}


# --- settings ---------------------------------------------------------------------------------


def ttl_seconds() -> int:
    try:
        value = int(os.getenv(TTL_ENV, ""))
    except ValueError:
        return DEFAULT_TTL_SECONDS
    return value if value > 0 else DEFAULT_TTL_SECONDS


def max_amount() -> Optional[Decimal]:
    """The operator's limit, ``None`` for no limit. A value that is not a number refuses every transfer."""
    raw = os.getenv(MAX_AMOUNT_ENV, "").strip()
    if not raw:
        return None
    try:
        limit = Decimal(raw)
    except InvalidOperation:
        return Decimal(0)
    return limit if limit.is_finite() else Decimal(0)


def today() -> date:
    """Today in the bank's time zone when ``MIFOS_TIMEZONE`` is set (the bank rejects future dates)."""
    name = os.getenv(TIMEZONE_ENV, "").strip()
    if name:
        try:
            return datetime.now(ZoneInfo(name)).date()
        except ZoneInfoNotFoundError:
            pass
    return date.today()


def format_date(value: date) -> str:
    return f"{value.day:02d} {_MONTHS[value.month - 1]} {value.year}"


# --- prepared transfers -----------------------------------------------------------------------


def remember(
    endpoint: str, data: Dict[str, Any], summary: Dict[str, Any], text: str, kind: str = "transfer"
) -> PreparedTransfer:
    _purge()
    prepared = PreparedTransfer(
        secrets.token_urlsafe(9), endpoint, copy.deepcopy(data), summary, text, time.monotonic(), kind
    )
    _prepared[prepared.confirmation_id] = prepared
    while len(_prepared) > MAX_PREPARED:
        _prepared.popitem(last=False)
    return prepared


def take(confirmation_id: str, kind: str = "transfer") -> Optional[PreparedTransfer]:
    """Remove and return a prepared operation of this kind, so it can be used only once."""
    _purge()
    prepared = _prepared.get(confirmation_id)
    if prepared is None or prepared.kind != kind:
        return None
    return _prepared.pop(confirmation_id)


def _purge() -> None:
    limit = ttl_seconds()
    now = time.monotonic()
    for key in [k for k, v in _prepared.items() if now - v.created > limit]:
        del _prepared[key]


class ConfirmApplicationForm(BaseModel):
    """The form for applications (e.g. shares). Only a primitive field is allowed."""

    confirm: bool = Field(title="Submit this application", description="Tick to submit the application")
