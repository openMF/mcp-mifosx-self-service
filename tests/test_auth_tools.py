import pytest
from unittest.mock import patch, AsyncMock
from routers.auth_tools import (
    register_self_service,
    confirm_registration,
    login_mifos,
    confirm_registration_get,
    update_password_self,
    verify_user_registration_alias,
    authenticate_user_alias,
)


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_register_self_service(mock_make_request):
    mock_make_request.return_value = {"status": "success"}
    result = await register_self_service(
        username="user1",
        accountNumber="123",
        password="pwd",
        firstName="John",
        middleName="Robert",
        lastName="Doe",
        mobileNumber="1234567890",
        email="john@example.com",
        authenticationMode="email",
    )
    assert result == {"status": "success"}
    mock_make_request.assert_called_once_with(
        "POST",
        "/self/registration",
        data={
            "username": "user1",
            "accountNumber": "123",
            "password": "pwd",
            "firstName": "John",
            "middleName": "Robert",
            "lastName": "Doe",
            "mobileNumber": "1234567890",
            "email": "john@example.com",
            "authenticationMode": "email",
        },
    )


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_confirm_registration(mock_make_request):
    mock_make_request.return_value = {"status": "confirmed"}
    result = await confirm_registration(requestId=1, authenticationToken="token123")
    assert result == {"status": "confirmed"}
    mock_make_request.assert_called_once_with(
        "POST", "/self/registration/user", data={"requestId": 1, "authenticationToken": "token123"}
    )


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_login_mifos(mock_make_request):
    mock_make_request.return_value = {"token": "auth_token"}
    result = await login_mifos("user1", "pwd")
    assert result == {"token": "auth_token"}
    mock_make_request.assert_called_once_with(
        "POST", "/self/authentication", data={"username": "user1", "password": "pwd"}
    )


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
@patch("routers.auth_tools.get_auth_header")
async def test_confirm_registration_get(mock_get_auth_header, mock_make_request):
    mock_get_auth_header.return_value = "Basic dXNlcjE6cHdk"
    mock_make_request.return_value = {"clients": []}
    result = await confirm_registration_get("user1", "pwd")
    assert result == {"clients": []}
    mock_get_auth_header.assert_called_once_with("user1", "pwd")
    mock_make_request.assert_called_once_with("GET", "/self/clients", auth="Basic dXNlcjE6cHdk")


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
@patch("routers.auth_tools.get_auth_header")
async def test_update_password_self(mock_get_auth_header, mock_make_request):
    mock_get_auth_header.return_value = "Basic dXNlcjE6b2xkX3B3ZA=="
    mock_make_request.return_value = {"status": "updated"}
    result = await update_password_self("user1", "old_pwd", "new_pwd")
    assert result == {"status": "updated"}
    mock_get_auth_header.assert_called_once_with("user1", "old_pwd")
    mock_make_request.assert_called_once_with(
        "PUT",
        "/self/user",
        auth="Basic dXNlcjE6b2xkX3B3ZA==",
        data={"password": "old_pwd", "newPassword": "new_pwd", "repeatNewPassword": "new_pwd"},
    )


@pytest.mark.asyncio
@patch("routers.auth_tools.confirm_registration", new_callable=AsyncMock)
async def test_verify_user_registration_alias(mock_confirm_registration):
    mock_confirm_registration.return_value = {"status": "verified"}
    result = await verify_user_registration_alias(1, "token")
    assert result == {"status": "verified"}
    mock_confirm_registration.assert_called_once_with(1, "token")


@pytest.mark.asyncio
@patch("routers.auth_tools.login_mifos", new_callable=AsyncMock)
async def test_authenticate_user_alias(mock_login_mifos):
    mock_login_mifos.return_value = {"status": "authenticated"}
    result = await authenticate_user_alias("user1", "pwd")
    assert result == {"status": "authenticated"}
    mock_login_mifos.assert_called_once_with("user1", "pwd")
