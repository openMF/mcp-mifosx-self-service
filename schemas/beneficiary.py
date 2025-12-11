from pydantic import BaseModel, Field


class BeneficiaryRequest(BaseModel):
    """Beneficiary request model"""

    name: str
    office_name: str = Field(alias="officeName")
    account_number: str = Field(alias="accountNumber")
    account_type: int = Field(alias="accountType")  # 1=Savings, 2=Loan
    transfer_limit: float = Field(alias="transferLimit")
    locale: str = "en"
