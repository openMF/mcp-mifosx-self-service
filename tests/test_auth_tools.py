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
    logout_mifos,
)
from utils import auth


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


LOGIN_RESPONSE = {
    "authenticated": True,
    "username": "user1",
    "clients": [3],
    "base64EncodedAuthenticationKey": "YWNjZXNzLWtleQ==",
    "refreshToken": "cmVmcmVzaC1rZXk=",
}


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_login_mifos_keeps_token_and_hides_it(mock_make_request):
    mock_make_request.return_value = dict(LOGIN_RESPONSE)
    result = await login_mifos("user1", "pwd")
    assert result == {"authenticated": True, "username": "user1", "clients": [3]}
    mock_make_request.assert_called_once_with(
        "POST", "/self/authentication", data={"username": "user1", "password": "pwd"}
    )
    assert auth.get_auth_header() == "Basic YWNjZXNzLWtleQ=="


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_login_mifos_uses_env_credentials(mock_make_request, monkeypatch):
    monkeypatch.setenv("MIFOS_USERNAME", "envuser")
    monkeypatch.setenv("MIFOS_PASSWORD", "envpwd")
    mock_make_request.return_value = dict(LOGIN_RESPONSE)
    await login_mifos()
    mock_make_request.assert_called_once_with(
        "POST", "/self/authentication", data={"username": "envuser", "password": "envpwd"}
    )


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_login_mifos_without_credentials(mock_make_request):
    result = await login_mifos()
    assert result["error"] is True
    assert result["message"] == auth.NOT_LOGGED_IN_MESSAGE
    mock_make_request.assert_not_called()


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_failed_login_does_not_save_session(mock_make_request):
    mock_make_request.return_value = {"error": True, "status_code": 401, "message": "Unauthorized"}
    result = await login_mifos("user1", "wrong")
    assert result["status_code"] == 401
    with pytest.raises(auth.NotLoggedInError):
        auth.get_auth_header()


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_logout_clears_session(mock_make_request):
    auth.save_login(dict(LOGIN_RESPONSE))
    mock_make_request.return_value = {"message": "Success", "status_code": 200}
    await logout_mifos()
    mock_make_request.assert_called_once_with("POST", "/self/authentication/logout", auth="Basic YWNjZXNzLWtleQ==")
    with pytest.raises(auth.NotLoggedInError):
        auth.get_auth_header()


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_logout_when_not_logged_in(mock_make_request):
    result = await logout_mifos()
    assert result == {"message": "Not logged in."}
    mock_make_request.assert_not_called()


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
@patch("routers.auth_tools.get_auth_header")
async def test_confirm_registration_get(mock_get_auth_header, mock_make_request):
    mock_get_auth_header.return_value = "Basic dXNlcjE6cHdk"
    mock_make_request.return_value = {"clients": []}
    result = await confirm_registration_get()
    assert result == {"clients": []}
    mock_get_auth_header.assert_called_once_with()
    mock_make_request.assert_called_once_with("GET", "/self/clients", auth="Basic dXNlcjE6cHdk")


@pytest.mark.asyncio
@patch("routers.auth_tools.make_request", new_callable=AsyncMock)
async def test_update_password_self(mock_make_request):
    auth.save_login(dict(LOGIN_RESPONSE))
    mock_make_request.return_value = {"status": "updated"}
    result = await update_password_self("old_pwd", "new_pwd")
    assert result == {"status": "updated"}
    mock_make_request.assert_called_once_with(
        "PUT",
        "/self/user",
        auth="Basic YWNjZXNzLWtleQ==",
        data={"password": "old_pwd", "newPassword": "new_pwd", "repeatNewPassword": "new_pwd"},
    )
    # The old session is dropped after a password change.
    with pytest.raises(auth.NotLoggedInError):
        auth.get_auth_header()


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
