from mcp_app import mcp
from typing import Optional, Dict, Any
from schemas.registration import RegistrationRequest
from schemas.authentication import LoginRequest
from utils.http import make_request

@mcp.tool()
async def register_self_service(
    username: str,
    account_number: str,
    password: str,
    first_name: str,
    last_name: str,
    mobile_number: str,
    email: str,
    authentication_mode: str = "email",
) -> Dict[str, Any]:
    """
    Register a new self-service user for mobile banking

    Args:
        username: Desired username
        account_number: Existing account number
        password: Strong password for the account
        first_name: User's first name
        last_name: User's last name
        mobile_number: Mobile phone number
        email: Email address
        authentication_mode: Mode of authentication (default: email)

    Returns:
        Registration response with request ID
    """
    data = {
        "username": username,
        "accountNumber": account_number,
        "password": password,
        "firstName": first_name,
        "mobileNumber": mobile_number,
        "lastName": last_name,
        "email": email,
        "authenticationMode": authentication_mode,
    }

    return await make_request("POST", "/self/registration", data=data)


@mcp.tool()
async def confirm_registration(request_id: int, authentication_token: str) -> Dict[str, Any]:
    """
    Confirm self-service user registration with token

    Args:
        request_id: Registration request ID
        authentication_token: Token received via email/SMS

    Returns:
        Confirmation response
    """
    data = {"requestId": request_id, "authenticationToken": authentication_token}

    return await make_request("POST", "/self/registration/user", data=data)


@mcp.tool()
async def login_self_service(username: str, password: str) -> Dict[str, Any]:
    """
    Login to self-service mobile banking

    Args:
        username: Username
        password: Password

    Returns:
        Authentication response with user details
    """
    data = {"username": username, "password": password}

    return await make_request("POST", "/self/authentication", data=data)
