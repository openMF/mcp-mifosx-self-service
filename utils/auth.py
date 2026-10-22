"""Self-service login state.

The MCP server keeps the login itself, so tools never take a username or password
and the AI client never sees the access token. The server runs over stdio, one
process per user, so a module-level session is enough.
"""

import base64
import os
from typing import Any, Dict, Optional

# Fields of the /self/authentication response that must not be sent back to the AI.
SECRET_LOGIN_FIELDS = ("base64EncodedAuthenticationKey", "refreshToken")

NOT_LOGGED_IN_MESSAGE = (
    "Not logged in. Call the login tool first, or set MIFOS_USERNAME and MIFOS_PASSWORD "
    "in the MCP server environment."
)

_access_key: Optional[str] = None


class NotLoggedInError(Exception):
    """Raised when a tool needs a login and there is none."""


def basic_auth(username: str, password: str) -> str:
    """Build a Basic auth header from a username and password."""
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {encoded}"


def save_login(login_response: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the access key from a successful login and return the response without secrets."""
    global _access_key
    key = login_response.get("base64EncodedAuthenticationKey")
    if key:
        _access_key = key
    return {k: v for k, v in login_response.items() if k not in SECRET_LOGIN_FIELDS}


def clear_login() -> None:
    """Forget the saved login."""
    global _access_key
    _access_key = None


def env_credentials() -> Optional[tuple]:
    """Username and password from the server environment, if both are set."""
    username = os.getenv("MIFOS_USERNAME")
    password = os.getenv("MIFOS_PASSWORD")
    if username and password:
        return username, password
    return None


def get_auth_header() -> str:
    """Authorization header for the current login.

    Uses the access key saved by the login tool, or else MIFOS_USERNAME / MIFOS_PASSWORD.
    """
    if _access_key:
        return f"Basic {_access_key}"
    credentials = env_credentials()
    if credentials:
        return basic_auth(*credentials)
    raise NotLoggedInError(NOT_LOGGED_IN_MESSAGE)
