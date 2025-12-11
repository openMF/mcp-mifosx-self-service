from pydantic import BaseModel, Field


class TransferRequest(BaseModel):
    """Transfer request model"""

    to_office_id: int = Field(alias="toOfficeId")
    to_client_id: int = Field(alias="toClientId")
    to_account_type: int = Field(alias="toAccountType")
    to_account_id: str = Field(alias="toAccountId")
    transfer_amount: float = Field(alias="transferAmount")
    transfer_date: str = Field(alias="transferDate")
    transfer_description: str = Field(alias="transferDescription")
    date_format: str = Field(default="dd MMMM yyyy", alias="dateFormat")
    locale: str = "en"
    from_account_id: str = Field(alias="fromAccountId")
    from_account_type: str = Field(alias="fromAccountType")
    from_client_id: int = Field(alias="fromClientId")
    from_office_id: int = Field(alias="fromOfficeId")
