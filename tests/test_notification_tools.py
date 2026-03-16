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
async def test_get_notification_registration_details(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"id": 1}

    result = await get_notification_registration_details(1, "user1", "pwd")
    assert result == {"id": 1}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/device/registration/client/1", auth=mock_auth)


@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_register_for_notifications(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"status": "success"}

    result = await register_for_notifications(1, "reg_id_123", "user1", "pwd", platform="ios")
    assert result == {"status": "success"}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "POST",
        "/self/device/registration",
        auth=mock_auth,
        data={"clientId": 1, "registrationId": "reg_id_123", "platform": "ios"},
    )


@pytest.mark.asyncio
@patch("routers.notification_tools.make_request", new_callable=AsyncMock)
@patch("routers.notification_tools.get_auth_header")
async def test_update_notification_registration(mock_get_auth_header, mock_make_request, mock_auth):
    mock_get_auth_header.return_value = mock_auth
    mock_make_request.return_value = {"status": "updated"}

    result = await update_notification_registration(2, "new_token", "user1", "pwd", platform="android")
    assert result == {"status": "updated"}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with(
        "PUT",
        "/self/device/registration/2",
        auth=mock_auth,
        data={"registrationId": "new_token", "platform": "android"},
    )
