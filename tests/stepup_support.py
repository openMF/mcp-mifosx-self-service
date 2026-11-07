"""Shared fixtures data for the step-up tests: canned API answers and a fake ``make_request``."""

import json

from utils import stepup

AUTH = "Basic c2Vzc2lvbg=="
TOKEN = "SECRET-ONE-TIME-TOKEN"
TRANSFER = {
    "fromAccountId": 11,
    "fromAccountType": 2,
    "toAccountId": 22,
    "toAccountType": 2,
    "transferAmount": 100.5,
    "transferDate": "21 October 2026",
    "transferDescription": "rent",
    "dateFormat": "dd MMMM yyyy",
    "locale": "en",
}
TRANSFER_PAYLOAD = {k: TRANSFER[k] for k in stepup.PAYLOAD_FIELDS["TPT_TRANSFER"]}
CHALLENGE = {
    "challengeId": 7,
    "action": "TPT_TRANSFER",
    "channel": "EMAIL",
    "maskedDestination": "a***@example.com",
    "expiresAt": "2026-10-21T12:05:00",
    "attemptsRemaining": 5,
    "resendAvailableAt": "2026-10-21T12:00:30",
    "resendsRemaining": 3,
}
CONFIG = {"enabled": True, "availableChannels": ["EMAIL", "SMS"], "otpLength": 6}


def api_error(code, status=403, **details):
    body = {"userMessageGlobalisationCode": f"error.msg.selfservice.stepup.{code}", "httpStatusCode": str(status)}
    body.update(details)
    return {"error": True, "status_code": status, "message": json.dumps(body)}


def required(action="TPT_TRANSFER"):
    return api_error("required", action=action)


class FakeApi:
    """Stands in for make_request: answers by (method, endpoint), in order, and records every call."""

    def __init__(self, **routes):
        self.routes = {}
        for key, value in routes.items():
            method, endpoint = key.split(" ", 1)
            self.routes[(method, endpoint)] = list(value) if isinstance(value, list) else [value]
        self.calls = []

    async def __call__(self, method, endpoint, auth=None, data=None, tenant=None, headers=None):
        self.calls.append({"method": method, "endpoint": endpoint, "auth": auth, "data": data, "headers": headers})
        answers = self.routes[(method, endpoint)]
        return answers.pop(0) if len(answers) > 1 else answers[0]

    def calls_to(self, method, endpoint):
        return [c for c in self.calls if (c["method"], c["endpoint"]) == (method, endpoint)]


def standard_api(**overrides):
    routes = {
        "GET /self/stepup/config": CONFIG,
        "POST /self/stepup/challenges": CHALLENGE,
        "POST /self/stepup/challenges/7/verify": {"stepUpToken": TOKEN, "action": "TPT_TRANSFER"},
        "POST /self/accounttransfers?type=tpt": {"resourceId": 99},
    }
    routes.update(overrides)
    return FakeApi(**routes)


# --- two-step transfers (prepare_transfer / confirm_transfer) ------------------------------------


def account_option(account_id, account_type=2, client_id=5, office_id=1, name="ANA LOPEZ"):
    type_value = "Savings Account" if account_type == 2 else "Loan Account"
    return {
        "accountId": account_id,
        "accountNo": f"{account_id:09d}",
        "accountType": {"id": account_type, "value": type_value},
        "clientId": client_id,
        "clientName": name,
        "officeId": office_id,
        "officeName": "CENTRAL",
    }


OWN_TEMPLATE = {
    "fromAccountOptions": [account_option(11), account_option(33, 1)],
    "toAccountOptions": [account_option(11), account_option(33, 1)],
}
TPT_TEMPLATE = {
    "fromAccountOptions": [account_option(11)],
    "toAccountOptions": [account_option(22, client_id=9, office_id=2, name="LUIS MORA")],
}
SAVINGS_11 = {
    "id": 11,
    "currency": {"code": "USD"},
    "summary": {"accountBalance": 500.0, "availableBalance": 500.0},
    "withdrawalFeeForTransfers": False,
}
# What prepare_transfer(11 -> 22, 100.5, "rent", third_party=True) sends, apart from the date.
TPT_SENT = {
    "fromOfficeId": 1,
    "fromClientId": 5,
    "fromAccountType": 2,
    "fromAccountId": 11,
    "toOfficeId": 2,
    "toClientId": 9,
    "toAccountType": 2,
    "toAccountId": 22,
    "transferAmount": 100.5,
    "transferDescription": "rent",
    "dateFormat": "dd MMMM yyyy",
    "locale": "en",
}


def bank_routes(**overrides):
    """Template and account answers that prepare_transfer reads, plus the step-up routes."""
    routes = {
        "GET /self/accounttransfers/template": OWN_TEMPLATE,
        "GET /self/accounttransfers/template?type=tpt": TPT_TEMPLATE,
        "GET /self/savingsaccounts/11": SAVINGS_11,
    }
    routes.update(overrides)
    return standard_api(**routes)
