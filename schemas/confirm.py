from pydantic import BaseModel, Field


class ConfirmRegistrationRequest(BaseModel):
    """Registration confirmation request model"""

    request_id: int = Field(alias="requestId")
    authentication_token: str = Field(alias="authenticationToken")
