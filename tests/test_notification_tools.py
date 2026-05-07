import pytest
from unittest.mock import patch, AsyncMock
from routers.notification_tools import (
    get_notification_registration_details,
    register_for_notifications,
    update_notification_registration,
)
 
 
@pytest.fixture
def mock_auth():
    return "Basic dXNlcjE6cHdk"
 
 
@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_get_user_notification_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"clientId": 1, "registrationId": "abc123", "platform": "android"}
 
    result = await get_notification_registration_details(1, "user1", "pwd")
    assert result == {"clientId": 1, "registrationId": "abc123", "platform": "android"}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/device/registration/client/1", auth=mock_auth)
 
 
@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_register_for_notifications_android(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 10}
 
    result = await register_for_notifications(1, "token_xyz", "user1", "pwd", platform="android")
    assert result == {"resourceId": 10}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "POST",
        "/self/device/registration",
        auth=mock_auth,
        data={"clientId": 1, "registrationId": "token_xyz", "platform": "android"},
    )
 
 
@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_register_for_notifications_default_platform(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 11}
 
    # Call without specifying platform — should default to "android"
    result = await register_for_notifications(2, "token_abc", "user1", "pwd")
    assert result == {"resourceId": 11}
    mock_make_request.assert_called_once_with(
        "POST",
        "/self/device/registration",
        auth=mock_auth,
        data={"clientId": 2, "registrationId": "token_abc", "platform": "android"},
    )
 
 
@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_register_for_notifications_ios(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 12}
 
    result = await register_for_notifications(3, "ios_token_123", "user1", "pwd", platform="ios")
    assert result == {"resourceId": 12}
    mock_make_request.assert_called_once_with(
        "POST",
        "/self/device/registration",
        auth=mock_auth,
        data={"clientId": 3, "registrationId": "ios_token_123", "platform": "ios"},
    )
 
 
@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_update_notification_registration(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 10}
 
    result = await update_notification_registration(10, "new_token_xyz", "user1", "pwd", platform="android")
    assert result == {"resourceId": 10}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "PUT",
        "/self/device/registration/10",
        auth=mock_auth,
        data={"registrationId": "new_token_xyz", "platform": "android"},
    )
 
 
@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_update_notification_registration_default_platform(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"resourceId": 10}
 
    # Call without specifying platform — should default to "android"
    result = await update_notification_registration(10, "new_token_xyz", "user1", "pwd")
    assert result == {"resourceId": 10}
    mock_make_request.assert_called_once_with(
        "PUT",
        "/self/device/registration/10",
        auth=mock_auth,
        data={"registrationId": "new_token_xyz", "platform": "android"},
    )
 
 
@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_get_user_notification_details_not_found(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"error": True, "status_code": 404, "message": "Client not found"}
 
    result = await get_notification_registration_details(999, "user1", "pwd")
    assert result["error"] is True
    assert result["status_code"] == 404
 
 
@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_register_for_notifications_error(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"error": True, "status_code": 400, "message": "Invalid registration ID"}
 
    result = await register_for_notifications(1, "", "user1", "pwd")
    assert result["error"] is True
    assert result["status_code"] == 400
 