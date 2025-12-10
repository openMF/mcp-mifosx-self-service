import httpx
from typing import Optional, Dict, Any
from config.config import BASE_URL, API_BASE_PATH, DEFAULT_TENANT


async def make_request(
    method: str, endpoint: str, auth: Optional[str] = None, data: Optional[Dict] = None, tenant: str = DEFAULT_TENANT
) -> Dict[str, Any]:
    """Make HTTP request to the API"""
    url = f"{BASE_URL}{API_BASE_PATH}{endpoint}"
    headers = {"Fineract-Platform-TenantId": tenant, "Content-Type": "application/json"}

    if auth:
        headers["Authorization"] = auth

    async with httpx.AsyncClient() as client:
        response = await client.request(method=method, url=url, headers=headers, json=data)

        if response.status_code >= 400:
            return {"error": True, "status_code": response.status_code, "message": response.text}

        try:
            return response.json()
        except ValueError:
            return {"message": "Success", "status_code": response.status_code}

