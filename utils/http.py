import httpx
from typing import Optional, Dict, Any
from config.config import BASE_URL, API_BASE_PATH, DEFAULT_TENANT


def _categorize_status(status_code: int) -> str:
    """Categorize HTTP status codes into human-readable error categories."""
    categories = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        408: "timeout",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_server_error",
        502: "bad_gateway",
        503: "service_unavailable",
        504: "gateway_timeout",
    }
    if status_code in categories:
        return categories[status_code]
    if 400 <= status_code < 500:
        return "client_error"
    if 500 <= status_code < 600:
        return "server_error"
    return "unknown_error"


def _build_error_response(
    status_code: int,
    message: str,
    method: str,
    endpoint: str,
    details: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build a consistent, AI-friendly error response object."""
    error_response: Dict[str, Any] = {
        "error": True,
        "status_code": status_code,
        "error_category": _categorize_status(status_code),
        "message": message,
        "request_context": {
            "method": method.upper(),
            "endpoint": endpoint,
        },
    }
    if details is not None:
        error_response["details"] = details
    return error_response


def _parse_api_error(response: httpx.Response) -> tuple[str, Optional[Any]]:
    """Attempt to parse structured JSON error from API response.

    Returns a tuple of (message, details) where details may contain
    additional structured error information from the API.
    """
    try:
        error_json = response.json()
        if isinstance(error_json, dict):
            # Fineract often returns errors with these fields
            message = (
                error_json.get("defaultUserMessage")
                or error_json.get("developerMessage")
                or error_json.get("message")
                or error_json.get("error")
                or response.reason_phrase
                or "Unknown error"
            )
            # Collect structured details if present
            details = {}
            if "errors" in error_json:
                details["errors"] = error_json["errors"]
            if "httpStatusCode" in error_json:
                details["httpStatusCode"] = error_json["httpStatusCode"]
            if "userMessageGlobalisationCode" in error_json:
                details["code"] = error_json["userMessageGlobalisationCode"]
            return str(message), details if details else None
        return str(error_json), None
    except (ValueError, KeyError):
        text = response.text.strip()
        return text if text else (response.reason_phrase or "Unknown error"), None


async def make_request(
    method: str,
    endpoint: str,
    auth: Optional[str] = None,
    data: Optional[Dict] = None,
    tenant: str = DEFAULT_TENANT,
) -> Dict[str, Any]:
    """Make HTTP request to the API.

    Returns a structured response dict. On errors, returns a normalized
    error object with status code, category, message, request context,
    and any structured details from the API response.
    """
    url = f"{BASE_URL}{API_BASE_PATH}{endpoint}"
    headers = {
        "Fineract-Platform-TenantId": tenant,
        "Content-Type": "application/json",
    }

    if auth:
        headers["Authorization"] = auth

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method, url=url, headers=headers, json=data
            )

            if response.status_code >= 400:
                message, details = _parse_api_error(response)
                return _build_error_response(
                    status_code=response.status_code,
                    message=message,
                    method=method,
                    endpoint=endpoint,
                    details=details,
                )

            try:
                return response.json()
            except ValueError:
                return {"message": "Success", "status_code": response.status_code}

    except httpx.TimeoutException:
        return _build_error_response(
            status_code=408,
            message="Request timed out",
            method=method,
            endpoint=endpoint,
        )
    except httpx.ConnectError:
        return _build_error_response(
            status_code=503,
            message=f"Cannot connect to server: {url}",
            method=method,
            endpoint=endpoint,
        )
    except Exception as e:
        return _build_error_response(
            status_code=500,
            message=str(e),
            method=method,
            endpoint=endpoint,
        )
