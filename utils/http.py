from typing import Any, Dict, Optional

import httpx

from config.config import API_BASE_PATH, BASE_URL, DEFAULT_TENANT


async def make_request(
    method: str,
    endpoint: str,
    auth: Optional[str] = None,
    data: Optional[Dict] = None,
    tenant: str = DEFAULT_TENANT,
) -> Dict[str, Any]:
    """Make HTTP request to the API."""
    url = f"{BASE_URL}{API_BASE_PATH}{endpoint}"
    headers = {
        "Fineract-Platform-TenantId": tenant,
        "Content-Type": "application/json",
    }

    if auth:
        headers["Authorization"] = auth

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method=method, url=url, headers=headers, json=data)

            if response.status_code >= 400:
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": response.text,
                }

            try:
                return response.json()
            except ValueError:
                return {"message": "Success", "status_code": response.status_code}

    except httpx.TimeoutException:
        return {"error": True, "status_code": 408, "message": f"Request timed out for {method} {url}"}
    except httpx.ConnectError:
        return {"error": True, "status_code": 503, "message": f"Cannot connect to server: {url}"}
    except Exception as e:
        return {"error": True, "status_code": 500, "message": str(e)}
