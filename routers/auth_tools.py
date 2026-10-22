from mcp_app import mcp
from typing import Dict, Any, Optional
from utils.http import make_request
from utils.auth import (
    NOT_LOGGED_IN_MESSAGE,
    NotLoggedInError,
    clear_login,
    env_credentials,
    get_auth_header,
    save_login,
)
from utils.stepup import resolve_step_up


@mcp.tool(name="register_self_service_existing_client")
async def register_self_service(
    username: str,
    accountNumber: str,
    password: str,
    firstName: str,
    lastName: str,
    mobileNumber: str,
    email: str,
    middleName: Optional[str] = None,
    authenticationMode: str = "email",
) -> Dict[str, Any]:
    """Register Self Service for Existing Client - Registers a new user."""
    data = {
        "username": username,
        "accountNumber": accountNumber,
        "password": password,
        "firstName": firstName,
        "middleName": middleName,
        "lastName": lastName,
        "mobileNumber": mobileNumber,
        "email": email,
        "authenticationMode": authenticationMode,
    }
    return await make_request("POST", "/self/registration", data=data)


@mcp.tool(name="confirm_self_service_user_registration")
async def confirm_registration(requestId: int, authenticationToken: str) -> Dict[str, Any]:
    """Confirm Self Service User Registration - Confirms user registration."""
    data = {"requestId": requestId, "authenticationToken": authenticationToken}
    return await make_request("POST", "/self/registration/user", data=data)


@mcp.tool(name="login")
async def login_mifos(username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    """Login - Authenticates the user and keeps the session in the server.

    Other tools then use this session, so they do not need a password. If username and
    password are left out, MIFOS_USERNAME and MIFOS_PASSWORD from the server environment are used.
    The access token is never returned.
    """
    if not (username and password):
        credentials = env_credentials()
        if credentials is None:
            return {"error": True, "status_code": 400, "message": NOT_LOGGED_IN_MESSAGE}
        username, password = credentials
    data = {"username": username, "password": password}
    result = await make_request("POST", "/self/authentication", data=data)
    if isinstance(result, dict) and not result.get("error"):
        return save_login(result)
    return result


@mcp.tool(name="logout")
async def logout_mifos() -> Dict[str, Any]:
    """Logout - Ends the session on the server and forgets it locally."""
    try:
        auth = get_auth_header()
    except NotLoggedInError:
        return {"message": "Not logged in."}
    result = await make_request("POST", "/self/authentication/logout", auth=auth)
    clear_login()
    return result


@mcp.tool(name="confirm_self_service_user_registration_status")
async def confirm_registration_get() -> Dict[str, Any]:
    """Confirm Self Service User Registration (Status Check) - Confirms status via Clients list."""
    auth = get_auth_header()
    return await make_request("GET", "/self/clients", auth=auth)


@mcp.tool(name="update_account_password")
async def update_password_self(current_password: str, new_password: str) -> Dict[str, Any]:
    """Update Account Password - Changes the password of the logged-in user, then logs out.

    The bank asks the user for a one-time verification code first. The user types it, never you.
    The API does not use the current password (the logged-in session and the code authorize the
    change), so current_password is not sent.
    """
    auth = get_auth_header()
    data = {"password": new_password, "repeatPassword": new_password}
    result = await make_request("PUT", "/self/user", auth=auth, data=data)
    result = await resolve_step_up(result, "PUT", "/self/user", auth=auth, data=data)
    if isinstance(result, dict) and not result.get("error") and not result.get("step_up_required"):
        clear_login()
    return result


@mcp.tool(name="verify_user_registration")
async def verify_user_registration_alias(requestId: int, authenticationToken: str) -> Dict[str, Any]:
    """Verify User Registration - Verifies user registration with authentication token."""
    return await confirm_registration(requestId, authenticationToken)


@mcp.tool(name="authenticate_user_self_service")
async def authenticate_user_alias(username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    """Authenticate User (Self Service) - Same as login."""
    return await login_mifos(username, password)
