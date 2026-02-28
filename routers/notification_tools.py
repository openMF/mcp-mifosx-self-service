from mcp_app import mcp
from typing import Dict, Any
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="Get User Notification Details")
async def get_notification_registration_details(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """
    Get notification registration details for a client.
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/device/registration/client/{client_id}", auth=auth)


@mcp.tool(name="Register for Notifications")
async def register_for_notifications(
    client_id: int, registration_id: str, username: str, password: str, platform: str = "android"
) -> Dict[str, Any]:
    """
    Register user device ID to receive push notifications.
    """
    auth = get_auth_header(username, password)
    data = {"clientId": client_id, "registrationId": registration_id, "platform": platform}
    return await make_request("POST", "/self/device/registration", auth=auth, data=data)


@mcp.tool(name="Update Notification Registration")
async def update_notification_registration(
    registration_id_internal: int, registration_token: str, username: str, password: str, platform: str = "android"
) -> Dict[str, Any]:
    """
    Update an existing notification registration.
    """
    auth = get_auth_header(username, password)
    data = {"registrationId": registration_token, "platform": platform}
    return await make_request("PUT", f"/self/device/registration/{registration_id_internal}", auth=auth, data=data)
