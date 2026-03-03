from mcp_app import mcp
from typing import Dict, Any, Optional
from utils.http import make_request
from utils.auth import get_auth_header


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
async def login_mifos(username: str, password: str) -> Dict[str, Any]:
    """Login - Authenticates user."""
    data = {"username": username, "password": password}
    return await make_request("POST", "/self/authentication", data=data)


@mcp.tool(name="confirm_self_service_user_registration_status")
async def confirm_registration_get(username: str, password: str) -> Dict[str, Any]:
    """Confirm Self Service User Registration (Status Check) - Confirms status via Clients list."""
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/clients", auth=auth)


@mcp.tool(name="update_account_password")
async def update_password_self(username: str, current_password: str, new_password: str) -> Dict[str, Any]:
    """Update Account Password - Updates user password."""
    auth = get_auth_header(username, current_password)
    data = {"password": current_password, "newPassword": new_password, "repeatNewPassword": new_password}
    return await make_request("PUT", "/self/user", auth=auth, data=data)


@mcp.tool(name="verify_user_registration")
async def verify_user_registration_alias(requestId: int, authenticationToken: str) -> Dict[str, Any]:
    """Verify User Registration - Verifies user registration with authentication token."""
    return await confirm_registration(requestId, authenticationToken)


@mcp.tool(name="authenticate_user_self_service")
async def authenticate_user_alias(username: str, password: str) -> Dict[str, Any]:
    """Authenticate User (Self Service) - Authenticates user credentials for self-service."""
    return await login_mifos(username, password)
