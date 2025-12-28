import httpx
import json
from typing import Optional, Dict, Any
from config.config import BASE_URL, API_BASE_PATH, DEFAULT_TENANT


async def make_request(
    method: str,
    endpoint: str,
    auth: Optional[str] = None,
    data: Optional[Dict] = None,
    tenant: str = DEFAULT_TENANT,
) -> Dict[str, Any]:
    """Make HTTP request to the Fineract self-service API with normalized errors."""
    url = f"{BASE_URL}{API_BASE_PATH}{endpoint}"
    headers = {
        "Fineract-Platform-TenantId": tenant,
        "Content-Type": "application/json",
    }

    if auth:
        headers["Authorization"] = auth

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
        )

        # ---- Normalized error handling ----
        if response.status_code >= 400:
            parsed_error = None
            try:
                parsed_error = response.json()
            except (ValueError, json.JSONDecodeError):
                parsed_error = None

            return {
                "error": True,
                "status_code": response.status_code,
                "method": method,
                "endpoint": endpoint,
                # Backward-compatible field
                "message": response.text,
                # Structured error for MCP / AI clients
                "details": parsed_error,
            }

        try:
            return response.json()
        except ValueError:
            return {
                "error": False,
                "status_code": response.status_code,
                "message": "Success",
            }
