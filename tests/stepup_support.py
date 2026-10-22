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
