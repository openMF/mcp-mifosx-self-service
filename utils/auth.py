import base64


def get_auth_header(username: str, password: str) -> str:
    """Generate Basic Auth header"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"
