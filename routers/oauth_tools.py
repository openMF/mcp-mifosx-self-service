from mcp_app import mcp
from typing import Dict, Any
import httpx

# OAUTH endpoints use a different base URL than Mifos
OAUTH_BASE_URL = "https://apis.flexcore.mx/v1.0/oauth"


@mcp.tool(name="OAuth Login")
async def oauth_login(username: str, password: str, client_id: str = "web-app") -> Dict[str, Any]:
    """OAuth Login - Authenticate via flexcore OAUTH."""
    url = f"{OAUTH_BASE_URL}/token"
    # httpx.post(data=...) sends content-type: application/x-www-form-urlencoded
    data = {"username": username, "password": password, "client_id": client_id, "grant_type": "password"}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        return response.json()


@mcp.tool(name="OAuth Refresh Token")
async def oauth_refresh_token(username: str, refresh_token: str, client_id: str = "web-app") -> Dict[str, Any]:
    """OAuth Refresh Token - Refresh access token using refresh_token."""
    url = f"{OAUTH_BASE_URL}/token"
    data = {"username": username, "refresh_token": refresh_token, "client_id": client_id, "grant_type": "refresh_token"}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        return response.json()


@mcp.tool(name="OAuth Logout")
async def oauth_logout(username: str, refresh_token: str, client_id: str = "web-app") -> Dict[str, Any]:
    """OAuth Logout - Terminate OAUTH session."""
    url = f"{OAUTH_BASE_URL}/logout"
    data = {"username": username, "refresh_token": refresh_token, "client_id": client_id}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        return response.json()
