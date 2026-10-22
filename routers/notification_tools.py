from mcp_app import mcp
from typing import Dict, Any
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="get_user_notification_details")
async def get_notification_registration_details(client_id: int) -> Dict[str, Any]:
    """
    Get notification registration details for a client.
    """
    auth = get_auth_header()
    return await make_request("GET", f"/self/device/registration/client/{client_id}", auth=auth)


@mcp.tool(name="register_for_notifications")
async def register_for_notifications(client_id: int, registration_id: str, platform: str = "android") -> Dict[str, Any]:
    """
    Register user device ID to receive push notifications.
    """
    auth = get_auth_header()
    data = {"clientId": client_id, "registrationId": registration_id, "platform": platform}
    return await make_request("POST", "/self/device/registration", auth=auth, data=data)


@mcp.tool(name="update_notification_registration")
async def update_notification_registration(
    registration_id_internal: int, registration_token: str, platform: str = "android"
) -> Dict[str, Any]:
    """
    Update an existing notification registration.
    """
    auth = get_auth_header()
    data = {"registrationId": registration_token, "platform": platform}
    return await make_request("PUT", f"/self/device/registration/{registration_id_internal}", auth=auth, data=data)
