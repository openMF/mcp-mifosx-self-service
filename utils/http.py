import httpx
from typing import Optional, Dict, Any
from config.config import BASE_URL, API_BASE_PATH, DEFAULT_TENANT
from utils.errors import api_error


async def make_request(
    method: str,
    endpoint: str,
    auth: Optional[str] = None,
    data: Optional[Dict] = None,
    tenant: str = DEFAULT_TENANT,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Make HTTP request to the API. `headers` are extra request headers (e.g. a step-up token)."""
    url = f"{BASE_URL}{API_BASE_PATH}{endpoint}"
    request_headers = {
        "Fineract-Platform-TenantId": tenant,
        "Content-Type": "application/json",
    }
    if headers:
        request_headers.update(headers)

    if auth:
        request_headers["Authorization"] = auth

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method=method, url=url, headers=request_headers, json=data)

            if response.status_code >= 400:
                return api_error(response.status_code, response.text)

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
