"""Account statements and spending insights for savings accounts.

Read-only tools built on the account's own transaction list
(`GET /self/savingsaccounts/{id}?associations=transactions`). Everything here is
computed locally from those rows: no other API is called, no value is invented,
and rows the tool cannot classify are labelled ``unknown`` rather than guessed.

Direction is resolved in this order, strongest evidence first:

1. Fineract's per-type boolean flags on ``transactionType`` (``deposit``,
   ``withdrawal``, ``interestPosting``, ``feeDeduction``, ``overdraftInterest``,
   ``withholdTax``, ``dividendPayout``, ...), applied the way Fineract's own
   ``SavingsAccountTransactionType.isCredit()`` / ``isDebit()`` applies them
   (apache/fineract): deposit, interest posting and dividend payout are
   credits; withdrawal, fees, charges, overdraft interest and withheld tax are
   debits. Flags that Fineract gives no direction — accrual, write-off, the
   transfer lifecycle markers, amount hold / release, escheat — stay unknown.
2. explicit ``credit`` / ``debit`` booleans on the transaction type, for API
   variants that publish those instead;
3. the transaction's own ``entryType`` (``CREDIT`` / ``DEBIT``) when present;
4. the type name, only when the response publishes no flags at all — a
   heuristic for stripped-down API variants, never a substitute for the flags.

Everything that remains unclassified — including a bare "Transfer", which does
not say whether money entered or left *this* account — is reported as
``unknown`` and counted separately, never guessed into income or spending.
Reversed rows keep their own ``reversed`` flag rather than being folded into
the original transaction.
"""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from mcp_app import mcp
from utils.auth import get_auth_header
from utils.http import make_request

_TRANSACTIONS_PATH = "/self/savingsaccounts/{savings_id}?associations=transactions"

# The account endpoint returns the whole history in one response; this caps how many
# rows a single tool call processes so a long history cannot stall the conversation.
# When the cap bites, the result carries truncated=True and the caller should narrow
# the date range and ask again.
_MAX_ROWS = 500

# Largest page get_account_statement will return; larger asks are clamped and echoed back.
_MAX_LIMIT = 200

DIRECTIONS = ("debit", "credit", "unknown")

# Fineract's transaction-type flags and the direction Fineract itself gives them
# (apache/fineract: SavingsAccountTransactionEnumData flags, SavingsAccountTransactionType
# entryType + isCredit()/isDebit()). Types absent from both lists are the ones Fineract
# deliberately gives no usable direction: accrual, write-off, initiate/approve/withdraw/
# reject transfer, amount hold, amount release, escheat, waive-charges.
_CREDIT_FLAGS = ("deposit", "interestPosting", "dividendPayout")
_DEBIT_FLAGS = ("withdrawal", "feeDeduction", "overdraftInterest", "overdraftFee", "withholdTax")
_TYPE_FLAGS = (
    _CREDIT_FLAGS
    + _DEBIT_FLAGS
    + (
        "accrual",
        "writtenoff",
        "initiateTransfer",
        "approveTransfer",
        "withdrawTransfer",
        "rejectTransfer",
        "amountHold",
        "amountRelease",
        "escheat",
    )
)

# Name rules are the LAST resort, for API variants that publish no flags at all.
_CREDIT_WORDS = (
    "deposit",
    "interest posting",
    "interest posted",
    "dividend",
    "credit",
    "transfer in",
)
_DEBIT_WORDS = (
    "withdraw",
    "fee",
    "charge",
    "penalty",
    "tax",
    "debit",
    "transfer out",
    "repayment",
    "loan payment",
)


def _error(message: str, **extra: Any) -> Dict[str, Any]:
    """Same shape as the errors make_request returns, so callers handle one format."""
    payload: Dict[str, Any] = {"error": True, "message": message}
    payload.update(extra)
    return payload


def _parse_date(value: Any) -> Optional[date]:
    """Read the date shapes the API returns: [y, m, d], ISO strings, 'dd MMM yyyy'."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return date(int(value[0]), int(value[1]), int(value[2]))
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            try:
                return date.fromisoformat(text[:10])
            except ValueError:
                return None
        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    return None


def _iso(value: Any) -> Optional[str]:
    parsed = _parse_date(value)
    return parsed.isoformat() if parsed else None


def _normalise_words(*parts: Any) -> str:
    """Flatten type name/value/code into lowercase words ('interestPosting' -> 'interest posting')."""
    text = " ".join(str(part) for part in parts if part)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return text.replace("_", " ").replace("-", " ").replace(".", " ").lower()


def _direction_of(tx: Dict[str, Any]) -> str:
    """Classify a transaction as credit / debit / unknown (see module docstring)."""
    tx_type = tx.get("transactionType")

    # 1. Fineract's per-type flags, with Fineract's own isCredit()/isDebit() exclusions.
    if isinstance(tx_type, dict) and any(flag in tx_type for flag in _TYPE_FLAGS):
        if any(tx_type.get(flag) is True for flag in _CREDIT_FLAGS):
            return "credit"
        if any(tx_type.get(flag) is True for flag in _DEBIT_FLAGS):
            return "debit"
        return "unknown"

    # 2. Variant APIs that publish explicit credit / debit booleans.
    if isinstance(tx_type, dict):
        if tx_type.get("credit") is True and tx_type.get("debit") is not True:
            return "credit"
        if tx_type.get("debit") is True and tx_type.get("credit") is not True:
            return "debit"

    # 3. The transaction's own entryType when the response publishes one.
    entry = tx.get("entryType") or (tx_type.get("entryType") if isinstance(tx_type, dict) else None)
    entry_word = _normalise_words(entry.get("name") or entry.get("value") if isinstance(entry, dict) else entry)
    if entry_word == "credit":
        return "credit"
    if entry_word == "debit":
        return "debit"

    # 4. Name rules, only when nothing above applied (see module docstring).
    if isinstance(tx_type, dict):
        name = _normalise_words(tx_type.get("name"), tx_type.get("value"), tx_type.get("code"))
    else:
        name = _normalise_words(tx_type)
    credit = any(word in name for word in _CREDIT_WORDS)
    debit = any(word in name for word in _DEBIT_WORDS)
    if credit and not debit:
        return "credit"
    if debit and not credit:
        return "debit"
    return "unknown"


def _amount(value: Any) -> Optional[float]:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _row(tx: Dict[str, Any]) -> Dict[str, Any]:
    """One transaction as a statement row."""
    tx_type = tx.get("transactionType")
    type_name = tx_type.get("name") or tx_type.get("value") if isinstance(tx_type, dict) else tx_type
    return {
        "id": tx.get("id"),
        "date": _iso(tx.get("date")),
        "direction": _direction_of(tx),
        "amount": _amount(tx.get("amount")),
        "running_balance": _amount(tx.get("runningBalance")),
        "type": type_name,
        "reversed": bool(tx.get("reversed") or tx.get("manuallyReversed")),
    }


def _extract_rows(result: Any) -> List[Dict[str, Any]]:
    """Pull the transaction list out of the response shapes we have seen."""
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    if isinstance(result, dict):
        for key in ("transactions", "pageItems"):
            value = result.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


async def _fetch(savings_id: int) -> Tuple[Optional[List[Dict[str, Any]]], bool, Optional[Dict[str, Any]]]:
    """Fetch the account's transactions once.

    Returns ``(rows, truncated, error)`` — exactly one of the three carries meaning:
    on success ``error`` is None, on failure ``rows`` is None.
    """
    auth = get_auth_header()
    path = _TRANSACTIONS_PATH.format(savings_id=savings_id)
    result = await make_request("GET", path, auth=auth)
    if isinstance(result, dict) and result.get("error"):
        return None, False, dict(result)
    rows = _extract_rows(result)
    return rows[:_MAX_ROWS], len(rows) > _MAX_ROWS, None


def _resolve_range(
    from_date: Optional[Any], to_date: Optional[Any]
) -> Tuple[Optional[date], Optional[date], Optional[Dict[str, Any]]]:
    """Parse and validate the period bounds. Returns (start, end, error)."""
    start = None
    end = None
    if from_date is not None:
        start = _parse_date(from_date)
        if start is None:
            return (
                None,
                None,
                _error(
                    f"Could not read from_date={from_date!r}. Use YYYY-MM-DD (also accepts [y, m, d]).",
                    parameter="from_date",
                ),
            )
    if to_date is not None:
        end = _parse_date(to_date)
        if end is None:
            return (
                None,
                None,
                _error(
                    f"Could not read to_date={to_date!r}. Use YYYY-MM-DD (also accepts [y, m, d]).",
                    parameter="to_date",
                ),
            )
    if start and end and start > end:
        return (
            None,
            None,
            _error(
                f"from_date {start.isoformat()} is after to_date {end.isoformat()}.",
                parameter="from_date",
            ),
        )
    return start, end, None


def _in_range(day: Optional[date], start: Optional[date], end: Optional[date]) -> bool:
    """Keep a row when its date falls inside the requested period.

    With no bounds at all every row stays. With bounds, a row whose date could not
    be read is dropped rather than guessed into a period.
    """
    if start is None and end is None:
        return True
    if day is None:
        return False
    if start and day < start:
        return False
    if end and day > end:
        return False
    return True


def _filtered_rows(
    rows: List[Dict[str, Any]], start: Optional[date], end: Optional[date]
) -> List[Tuple[Optional[date], Dict[str, Any]]]:
    """Parse dates once, filter to the period, sort newest first (undated last)."""
    filtered: List[Tuple[Optional[date], Dict[str, Any]]] = []
    for tx in rows:
        day = _parse_date(tx.get("date"))
        if not _in_range(day, start, end):
            continue
        filtered.append((day, _row(tx)))
    filtered.sort(key=lambda pair: (pair[0] is None, -(pair[0].toordinal() if pair[0] else 0)))
    return filtered


def _period_note(raw_truncated: bool, has_more: bool) -> str:
    note = (
        "Rows are the bank's own transactions, filtered and sorted by this tool (newest first). "
        "direction is classified from the transaction type: 'unknown' means this tool could not "
        "classify the type, not that no money moved."
    )
    if has_more:
        note += " More matching rows exist beyond this page — raise offset or limit to fetch them."
    if raw_truncated:
        note += (
            " The account history is longer than this tool's working cap, so rows beyond the first"
            " 500 the API returned are not part of this answer — narrow the date range and ask again."
        )
    return note


@mcp.tool(name="get_account_statement")
async def get_account_statement(
    savings_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    direction: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
) -> Dict[str, Any]:
    """Get Account Statement - a dated list of one savings account's transactions.

    Use it when the user asks for a statement, a money-in / money-out list, or "what
    happened on this account between X and Y". Pass from_date / to_date (YYYY-MM-DD)
    to bound the period and direction ("debit", "credit" or "unknown") to see only
    money out or money in. Rows come back newest first, paged by offset / limit;
    total_matching says how many rows the filters matched so you can page further.

    Honest limits: this statement is assembled from the bank's transaction records
    by this tool — it is not a bank-issued document. Rows whose transaction type the
    rules cannot classify carry direction "unknown" instead of a guess. The two
    partial-result flags are separate: has_more means matching rows exist beyond
    this page (page forward to fetch them), while truncated means only that the
    account's history is longer than this tool's 500-row working cap (narrow the
    date range and ask again). Neither means the account ended there.
    """
    if direction is not None and direction not in DIRECTIONS:
        return _error(
            f"direction must be one of {', '.join(DIRECTIONS)} (got {direction!r}).",
            parameter="direction",
        )
    if offset < 0:
        return _error("offset must be 0 or greater.", parameter="offset")
    if limit < 1:
        return _error("limit must be 1 or greater.", parameter="limit")
    limit = min(limit, _MAX_LIMIT)

    start, end, problem = _resolve_range(from_date, to_date)
    if problem:
        return problem

    rows, raw_truncated, failure = await _fetch(savings_id)
    if failure:
        return failure

    matched = _filtered_rows(rows, start, end)
    if direction is not None:
        matched = [item for item in matched if item[1]["direction"] == direction]

    total = len(matched)
    page = [item[1] for item in matched[offset : offset + limit]]
    returned = len(page)
    has_more = offset + returned < total

    return {
        "savings_id": savings_id,
        "filters": {
            "from_date": start.isoformat() if start else None,
            "to_date": end.isoformat() if end else None,
            "direction": direction,
        },
        "transactions": page,
        "total_matching": total,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "truncated": raw_truncated,
        "notes": _period_note(raw_truncated, has_more),
    }


@mcp.tool(name="get_spending_summary")
async def get_spending_summary(
    savings_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Spending Summary - totals, monthly buckets and a per-type breakdown for one savings account.

    Use it when the user asks how much they spent or received, wants a month-by-month
    overview, or asks which kinds of transactions dominate the account. Bound the
    period with from_date / to_date (YYYY-MM-DD); without them the whole available
    history is summarised.

    Honest limits: the totals are computed by this tool from the account's own
    transaction records (absolute amounts summed per direction) — this is not a
    bank-generated statement. Rows the tool cannot classify are reported under
    totals.unknown / counts.unknown rather than being counted as spending, so
    credit + debit + unknown always adds up to the rows examined; mention the
    unknown figure to the user when it is not zero.
    """
    start, end, problem = _resolve_range(from_date, to_date)
    if problem:
        return problem

    rows, raw_truncated, failure = await _fetch(savings_id)
    if failure:
        return failure

    totals = {"credit": 0.0, "debit": 0.0, "unknown": 0.0}
    counts = {"credit": 0, "debit": 0, "unknown": 0}
    by_month: Dict[str, Dict[str, Any]] = {}
    by_type: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for day, item in _filtered_rows(rows, start, end):
        direction = item["direction"]
        amount = abs(item["amount"]) if item["amount"] is not None else 0.0
        totals[direction] = round(totals[direction] + amount, 2)
        counts[direction] += 1

        month = day.isoformat()[:7] if day else "unknown"
        bucket = by_month.setdefault(month, {"count": 0, "credit": 0.0, "debit": 0.0, "unknown": 0.0})
        bucket["count"] += 1
        bucket[direction] = round(bucket[direction] + amount, 2)

        type_key = (str(item["type"] or "unclassified"), direction)
        type_bucket = by_type.setdefault(type_key, {"count": 0, "total": 0.0})
        type_bucket["count"] += 1
        type_bucket["total"] = round(type_bucket["total"] + amount, 2)

    months = sorted(
        ({"month": month, **values} for month, values in by_month.items()),
        key=lambda entry: (entry["month"] == "unknown", entry["month"]),
    )
    types = sorted(
        (
            {"type": type_label, "direction": direction, "count": values["count"], "total": values["total"]}
            for (type_label, direction), values in by_type.items()
        ),
        key=lambda entry: (-entry["total"], entry["type"]),
    )

    return {
        "savings_id": savings_id,
        "period": {"from_date": start.isoformat() if start else None, "to_date": end.isoformat() if end else None},
        "totals": totals,
        "counts": counts,
        "by_month": months,
        "by_type": types,
        "rows_examined": sum(counts.values()),
        "truncated": raw_truncated,
        "basis": (
            "Computed by this MCP tool from the account's own transaction list (absolute amounts, "
            "grouped by the direction rules in the statement tool). This is an aid for the "
            "conversation, not a bank-generated statement; rows classified 'unknown' are counted "
            "separately and never silently counted as spending."
            + (
                " Partial result: only the first 500 rows the API returned were examined (working"
                " cap), so these figures do not cover the whole account."
                if raw_truncated
                else ""
            )
        ),
    }


@mcp.tool(name="find_recurring_payments")
async def find_recurring_payments(
    savings_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    min_occurrences: int = 3,
) -> Dict[str, Any]:
    """Find Recurring Payments - debits that repeat on a regular schedule in one savings account.

    Use it when the user asks what subscriptions, instalments or standing debits they
    pay, or which payments repeat monthly. It groups same-amount, same-type debits and
    keeps the groups whose dates are evenly spaced (a few days of slack allowed).
    Raise min_occurrences for stricter matching, lower it to 2 to see a first hint.

    Honest limits: this is a heuristic over the account's own records, not a list the
    bank publishes — it sees only debits that actually cleared inside the period, knows
    nothing about contracts or cancellations, and skips payments whose amount changes
    or whose dates drift beyond the slack (those appear in irregular_groups_ignored).
    Confirm anything important with the user before acting on it.
    """
    if min_occurrences < 2:
        return _error("min_occurrences must be 2 or greater.", parameter="min_occurrences")

    start, end, problem = _resolve_range(from_date, to_date)
    if problem:
        return problem

    rows, raw_truncated, failure = await _fetch(savings_id)
    if failure:
        return failure

    groups: Dict[Tuple[str, str], List[Optional[date]]] = {}
    amounts: Dict[Tuple[str, str], float] = {}
    for day, item in _filtered_rows(rows, start, end):
        if item["direction"] != "debit" or item["amount"] is None or day is None:
            continue
        key = (str(item["type"] or "unclassified"), f"{abs(item['amount']):.2f}")
        groups.setdefault(key, []).append(day)
        amounts[key] = round(abs(item["amount"]), 2)

    candidates: List[Dict[str, Any]] = []
    irregular = 0
    for (type_label, amount_text), dates in groups.items():
        if len(dates) < min_occurrences:
            continue
        ordered = sorted(dates)
        gaps = [(b - a).days for a, b in zip(ordered, ordered[1:]) if b > a]
        if len(gaps) < min_occurrences - 1 or not gaps:
            irregular += 1
            continue
        middle = sorted(gaps)[len(gaps) // 2]
        slack = max(7, middle * 0.25)
        if max(gaps) - min(gaps) > slack:
            irregular += 1
            continue
        candidates.append(
            {
                "amount": amounts[(type_label, amount_text)],
                "type": type_label,
                "occurrences": len(ordered),
                "first_date": ordered[0].isoformat(),
                "last_date": ordered[-1].isoformat(),
                "typical_interval_days": middle,
                "interval_spread_days": max(gaps) - min(gaps),
                "dates": [day.isoformat() for day in ordered],
            }
        )
    candidates.sort(key=lambda entry: (-entry["occurrences"], -entry["amount"]))

    return {
        "savings_id": savings_id,
        "period": {"from_date": start.isoformat() if start else None, "to_date": end.isoformat() if end else None},
        "candidates": candidates,
        "groups_considered": len(groups),
        "irregular_groups_ignored": irregular,
        "rows_examined": sum(len(dates) for dates in groups.values()),
        "truncated": raw_truncated,
        "basis": (
            "Heuristic computed by this MCP tool: same-amount, same-type debits whose dates are "
            "evenly spaced (within a quarter of the typical gap, minimum 7 days). It reads only "
            "the transactions that actually cleared in this period, does not know about contracts "
            "or cancellations, and makes no promise about future payments."
            + (
                " Partial result: only the first 500 rows the API returned were examined (working"
                " cap), so these figures do not cover the whole account."
                if raw_truncated
                else ""
            )
        ),
    }
