from pydantic import BaseModel, Field


class RegistrationRequest(BaseModel):
    """Self-service registration request model"""

    username: str
    account_number: str = Field(alias="accountNumber")
    password: str
    first_name: str = Field(alias="firstName")
    mobile_number: str = Field(alias="mobileNumber")
    last_name: str = Field(alias="lastName")
    email: str
    authentication_mode: str = Field(default="email", alias="authenticationMode")
