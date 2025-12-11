from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login request model"""

    username: str
    password: str
