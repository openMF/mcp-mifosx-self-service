import pytest
from unittest.mock import patch, AsyncMock

from routers.statement_tools import (
    find_recurring_payments,
    get_account_statement,
    get_spending_summary,
    _MAX_ROWS,
)


@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"


def savings_response(transactions):
    return {"id": 7, "transactions": transactions}


def tx(id, day, amount, type_name, running=None):
    transaction_type = {"name": type_name}
    if isinstance(type_name, dict):
        transaction_type = type_name
    return {
        "id": id,
        "date": day,
        "amount": amount,
        "runningBalance": running,
        "transactionType": transaction_type,
    }


HISTORY = [
    tx(1, [2026, 1, 5], 5000, "Deposit", 5000),
    tx(2, [2026, 1, 10], 1200, "Withdrawal", 3800),
    tx(3, "2026-01-20", 300, "Interest Posting", 4100),
    tx(4, "25 Jan 2026", 1000, "Withdrawal", 3100),
    tx(5, [2026, 2, 1], 750, "Transfer", 2350),
    tx(6, [2026, 2, 10], 1000, "Withdrawal", 1350),
]


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_returns_normalised_rows_newest_first(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = savings_response(HISTORY)

    result = await get_account_statement(7)

    assert result["savings_id"] == 7
    assert result["total_matching"] == 6
    assert result["truncated"] is False
    dates = [row["date"] for row in result["transactions"]]
    assert dates == ["2026-02-10", "2026-02-01", "2026-01-25", "2026-01-20", "2026-01-10", "2026-01-05"]
    first = result["transactions"][0]
    assert first == {
        "id": 6,
        "date": "2026-02-10",
        "direction": "debit",
        "amount": 1000.0,
        "running_balance": 1350.0,
        "type": "Withdrawal",
        "reversed": False,
    }
    assert result["notes"]
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with(
        "GET", "/self/savingsaccounts/7?associations=transactions", auth=mock_auth
    )


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_reads_every_date_format(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = savings_response(HISTORY)

    result = await get_account_statement(7, from_date="2026-01-01", to_date="2026-01-31")

    assert result["filters"] == {"from_date": "2026-01-01", "to_date": "2026-01-31", "direction": None}
    assert result["total_matching"] == 4  # excludes the two February rows; "25 Jan 2026" was read


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_direction_filter_and_unknown_fallback(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = savings_response(HISTORY)

    debits = await get_account_statement(7, direction="debit")
    assert [row["id"] for row in debits["transactions"]] == [6, 4, 2]
    assert debits["total_matching"] == 3

    credits = await get_account_statement(7, direction="credit")
    assert [row["id"] for row in credits["transactions"]] == [3, 1]

    # A bare "Transfer" says no direction: it is unknown, never guessed.
    unknown = await get_account_statement(7, direction="unknown")
    assert [row["id"] for row in unknown["transactions"]] == [5]
    assert unknown["transactions"][0]["direction"] == "unknown"


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_direction_uses_fineract_flags_entry_type_then_names(
    mock_get_auth_header, mock_make_request, mock_auth
):
    mock_get_auth_header.return_value = mock_auth
    rows = [
        # Fineract's per-type flags decide, exactly as Fineract's own isCredit()/isDebit() does.
        tx(1, [2026, 3, 1], 100, {"value": "Deposit", "deposit": True}),
        tx(2, [2026, 3, 2], 100, {"value": "Withdrawal", "withdrawal": True}),
        tx(3, [2026, 3, 3], 100, {"value": "Interest posting", "interestPosting": True}),
        # Flags win over the name: this says "Deposit" but publishes no direction.
        tx(4, [2026, 3, 4], 100, {"value": "Deposit reversal", "deposit": False, "accrual": False}),
        # Types Fineract gives no usable direction stay unknown (its isDebit() excludes holds).
        tx(5, [2026, 3, 5], 100, {"value": "On hold", "amountHold": True}),
        tx(6, [2026, 3, 6], 100, {"value": "Initiate transfer", "initiateTransfer": True}),
        # entryType when a variant publishes it without flags.
        {"id": 7, "date": [2026, 3, 7], "amount": 100, "entryType": "CREDIT", "transactionType": {"value": "Mystery"}},
        # Generic debit/credit booleans still supported for other API variants.
        tx(8, [2026, 3, 8], 100, {"name": "Something", "debit": True}),
        # Name rules only when nothing else applies (camelCase values included).
        tx(9, [2026, 3, 9], 100, "interestPosting"),
        tx(10, [2026, 3, 10], 100, "Transfer"),
    ]
    mock_make_request.return_value = savings_response(rows)

    result = await get_account_statement(7)

    by_id = {row["id"]: row["direction"] for row in result["transactions"]}
    assert by_id == {
        1: "credit",
        2: "debit",
        3: "credit",
        4: "unknown",  # flags beat a name that would have matched
        5: "unknown",
        6: "unknown",
        7: "credit",
        8: "debit",
        9: "credit",
        10: "unknown",  # a bare transfer says nothing about this account
    }


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_pages_and_flags_truncation_separately(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = savings_response(HISTORY)

    page = await get_account_statement(7, offset=2, limit=2)

    assert [row["id"] for row in page["transactions"]] == [4, 3]
    assert page["total_matching"] == 6
    assert page["offset"] == 2
    # More matching rows exist beyond this page...
    assert page["has_more"] is True
    # ...but nothing was cut short by the processing cap: different flags, different meanings.
    assert page["truncated"] is False
    assert "beyond this page" in page["notes"]
    assert "working cap" not in page["notes"]

    last = await get_account_statement(7, offset=4, limit=10)
    assert last["has_more"] is False
    assert last["truncated"] is False
    assert len(last["transactions"]) == 2


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_rejects_bad_parameters(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = savings_response(HISTORY)

    bad_direction = await get_account_statement(7, direction="sideways")
    assert bad_direction["error"] is True
    assert bad_direction["parameter"] == "direction"

    bad_date = await get_account_statement(7, from_date="not-a-date")
    assert bad_date["error"] is True
    assert bad_date["parameter"] == "from_date"

    backwards = await get_account_statement(7, from_date="2026-02-01", to_date="2026-01-01")
    assert backwards["error"] is True
    assert backwards["parameter"] == "from_date"

    assert (await get_account_statement(7, offset=-1))["error"] is True
    assert (await get_account_statement(7, limit=0))["error"] is True
    # The API was never reached for any of these.
    mock_make_request.assert_not_called()


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_propagates_api_errors(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"error": True, "status_code": 404, "message": "not found"}

    result = await get_account_statement(7)

    assert result["status_code"] == 404
    assert result["error"] is True


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_caps_working_set_and_says_so(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    big = [tx(i, [2026, 3, 1], 10, "Withdrawal") for i in range(_MAX_ROWS + 25)]
    mock_make_request.return_value = savings_response(big)

    result = await get_account_statement(7)

    assert result["truncated"] is True  # the cap cut the history short...
    assert result["has_more"] is True  # ...and, independently, this page is not the end either
    assert result["total_matching"] == _MAX_ROWS
    assert "working cap" in result["notes"]


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_statement_accepts_page_items_and_bare_list_shapes(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"pageItems": HISTORY, "total": 6, "offset": 0}

    from_page_items = await get_account_statement(7)
    assert from_page_items["total_matching"] == 6

    mock_make_request.return_value = HISTORY
    from_bare_list = await get_account_statement(7)
    assert from_bare_list["total_matching"] == 6


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_spending_summary_totals_monthly_and_by_type(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = savings_response(HISTORY)

    result = await get_spending_summary(7, from_date="2026-01-01", to_date="2026-02-28")

    # 5000 + 300 in, 1200 + 1000 + 1000 out, 750 unclassified (bare "Transfer").
    assert result["totals"] == {"credit": 5300.0, "debit": 3200.0, "unknown": 750.0}
    assert result["counts"] == {"credit": 2, "debit": 3, "unknown": 1}
    assert [month["month"] for month in result["by_month"]] == ["2026-01", "2026-02"]
    assert result["rows_examined"] == 6
    assert result["truncated"] is False
    assert "not a bank-generated statement" in result["basis"]
    assert result["totals"]["credit"] + result["totals"]["debit"] + result["totals"]["unknown"] == 9250.0


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_spending_summary_buckets_unknown_dates_and_sorts_by_total(
    mock_get_auth_header, mock_make_request, mock_auth
):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = savings_response(
        [
            tx(1, "05 Feb 2026", 50, "Deposit"),
            tx(2, [2026, 1, 5], 900, "Deposit"),
            tx(3, "unreadable", 20, "Deposit"),
        ]
    )

    result = await get_spending_summary(7)

    assert [month["month"] for month in result["by_month"]] == ["2026-01", "2026-02", "unknown"]
    assert result["by_type"][0]["total"] == 970.0  # grouped: one type, all credits


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_spending_summary_reports_bad_period(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = savings_response(HISTORY)

    result = await get_spending_summary(7, from_date="whenever")

    assert result["error"] is True
    assert result["parameter"] == "from_date"
    mock_make_request.assert_not_called()


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_find_recurring_payments_detects_monthly_debits(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    monthly = [
        tx(1, [2026, 1, 5], 1000, "Withdrawal"),
        tx(2, [2026, 2, 5], 1000, "Withdrawal"),
        tx(3, [2026, 3, 6], 1000, "Withdrawal"),
        tx(4, [2026, 4, 5], 1000, "Withdrawal"),
        tx(5, [2026, 4, 20], 400, "Withdrawal"),
    ]
    mock_make_request.return_value = savings_response(monthly)

    result = await find_recurring_payments(7)

    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["amount"] == 1000.0
    assert candidate["type"] == "Withdrawal"
    assert candidate["occurrences"] == 4
    assert candidate["first_date"] == "2026-01-05"
    assert candidate["last_date"] == "2026-04-05"
    assert candidate["typical_interval_days"] == 30
    assert candidate["dates"][0] == "2026-01-05"
    assert "Heuristic" in result["basis"]
    assert "makes no promise about future payments" in result["basis"]


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_find_recurring_payments_ignores_irregular_and_credits(
    mock_get_auth_header, mock_make_request, mock_auth
):
    mock_get_auth_header.return_value = mock_auth
    messy = [
        tx(1, [2026, 1, 1], 100, "Withdrawal"),
        tx(2, [2026, 1, 20], 100, "Withdrawal"),  # 19-day gap, then a 5-day gap
        tx(3, [2026, 1, 25], 100, "Withdrawal"),
        tx(4, [2026, 2, 10], 100, "Withdrawal"),
        tx(5, [2026, 1, 1], 100, "Deposit"),  # credits are never "payments"
        tx(6, [2026, 2, 1], 100, "Transfer"),  # unknown direction: excluded
    ]
    mock_make_request.return_value = savings_response(messy)

    result = await find_recurring_payments(7)

    assert result["candidates"] == []
    assert result["irregular_groups_ignored"] == 1


@pytest.mark.asyncio
@patch("routers.statement_tools.make_request", new_callable=AsyncMock)
@patch("routers.statement_tools.get_auth_header")
async def test_find_recurring_payments_respects_min_occurrences(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    twice = [
        tx(1, [2026, 1, 1], 50, "Withdrawal"),
        tx(2, [2026, 2, 1], 50, "Withdrawal"),
    ]
    mock_make_request.return_value = savings_response(twice)

    strict = await find_recurring_payments(7)
    assert strict["candidates"] == []

    relaxed = await find_recurring_payments(7, min_occurrences=2)
    assert len(relaxed["candidates"]) == 1
    assert relaxed["candidates"][0]["occurrences"] == 2

    invalid = await find_recurring_payments(7, min_occurrences=1)
    assert invalid["error"] is True
    assert invalid["parameter"] == "min_occurrences"
