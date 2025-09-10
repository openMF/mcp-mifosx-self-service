"""
TT Mobile Banking MCP Server
FastMCP server implementation for TT Mobile Banking API endpoints
"""

import os
import base64
from typing import Optional, Dict, Any
import httpx
from pydantic import BaseModel, Field
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("Mifos Mobile Banking Server")

# Configuration
BASE_URL = os.getenv("MIFOS_BASE_URL", "https://tt.mifos.community")
DEFAULT_TENANT = os.getenv("MIFOS_TENANT", "default")
API_BASE_PATH = "/fineract-provider/api/v1"


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


class ConfirmRegistrationRequest(BaseModel):
    """Registration confirmation request model"""
    request_id: int = Field(alias="requestId")
    authentication_token: str = Field(alias="authenticationToken")


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class BeneficiaryRequest(BaseModel):
    """Beneficiary request model"""
    name: str
    office_name: str = Field(alias="officeName")
    account_number: str = Field(alias="accountNumber")
    account_type: int = Field(alias="accountType")  # 1=Savings, 2=Loan
    transfer_limit: float = Field(alias="transferLimit")
    locale: str = "en"


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


# Helper functions
def get_auth_header(username: str, password: str) -> str:
    """Generate Basic Auth header"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


async def make_request(
    method: str,
    endpoint: str,
    auth: Optional[str] = None,
    data: Optional[Dict] = None,
    tenant: str = DEFAULT_TENANT
) -> Dict[str, Any]:
    """Make HTTP request to the API"""
    url = f"{BASE_URL}{API_BASE_PATH}{endpoint}"
    headers = {
        "Fineract-Platform-TenantId": tenant,
        "Content-Type": "application/json"
    }
    
    if auth:
        headers["Authorization"] = auth
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=data
        )

        if response.status_code >= 400:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text
            }

        try:
            return response.json()
        except ValueError:
            return {"message": "Success", "status_code": response.status_code}


# MCP Tools

@mcp.tool()
async def register_self_service(
    username: str,
    account_number: str,
    password: str,
    first_name: str,
    last_name: str,
    mobile_number: str,
    email: str,
    authentication_mode: str = "email"
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
        "authenticationMode": authentication_mode
    }
    
    return await make_request("POST", "/self/registration", data=data)


@mcp.tool()
async def confirm_registration(
    request_id: int,
    authentication_token: str
) -> Dict[str, Any]:
    """
    Confirm self-service user registration with token
    
    Args:
        request_id: Registration request ID
        authentication_token: Token received via email/SMS
    
    Returns:
        Confirmation response
    """
    data = {
        "requestId": request_id,
        "authenticationToken": authentication_token
    }
    
    return await make_request("POST", "/self/registration/user", data=data)


@mcp.tool()
async def login_self_service(
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Login to self-service mobile banking
    
    Args:
        username: Username
        password: Password
    
    Returns:
        Authentication response with user details
    """
    data = {
        "username": username,
        "password": password
    }
    
    return await make_request("POST", "/self/authentication", data=data)


@mcp.tool()
async def get_client_info(
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Get client information for authenticated user
    
    Args:
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        Client information
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/clients", auth=auth)


@mcp.tool()
async def get_client_accounts(
    client_id: int,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Get list of accounts for a client
    
    Args:
        client_id: Client ID
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        List of client accounts
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/accounts", auth=auth)


@mcp.tool()
async def get_client_charges(
    client_id: int,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Get list of charges for a client
    
    Args:
        client_id: Client ID
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        List of client charges
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/charges", auth=auth)


@mcp.tool()
async def get_client_transactions(
    client_id: int,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Get list of transactions for a client
    
    Args:
        client_id: Client ID
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        List of client transactions
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/clients/{client_id}/transactions", auth=auth)


@mcp.tool()
async def get_beneficiaries(
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Get list of beneficiaries for third-party transfers
    
    Args:
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        List of beneficiaries
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", "/self/beneficiaries/tpt", auth=auth)


@mcp.tool()
async def get_beneficiary_template(
    account_number: str,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Get beneficiary template for a specific account
    
    Args:
        account_number: Account number
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        Beneficiary template
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/beneficiaries/tpt/{account_number}", auth=auth)


@mcp.tool()
async def add_beneficiary(
    name: str,
    office_name: str,
    account_number: str,
    account_type: int,
    transfer_limit: float,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Add a new beneficiary for third-party transfers
    
    Args:
        name: Beneficiary name
        office_name: Office name (e.g., "Head Office")
        account_number: Beneficiary account number
        account_type: Account type (1=Savings, 2=Loan)
        transfer_limit: Maximum transfer limit
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        Created beneficiary details
    """
    auth = get_auth_header(username, password)
    data = {
        "locale": "en",
        "name": name,
        "officeName": office_name,
        "accountNumber": account_number,
        "accountType": account_type,
        "transferLimit": transfer_limit
    }
    
    return await make_request("POST", "/self/beneficiaries/tpt", auth=auth, data=data)


@mcp.tool()
async def update_beneficiary(
    beneficiary_id: int,
    name: Optional[str],
    transfer_limit: Optional[float],
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Update an existing beneficiary
    
    Args:
        beneficiary_id: Beneficiary ID to update
        name: New beneficiary name (optional)
        transfer_limit: New transfer limit (optional)
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        Updated beneficiary details
    """
    auth = get_auth_header(username, password)
    data = {}
    
    if name:
        data["name"] = name
    if transfer_limit is not None:
        data["transferLimit"] = transfer_limit
    
    return await make_request("PUT", f"/self/beneficiaries/tpt/{beneficiary_id}", auth=auth, data=data)


@mcp.tool()
async def delete_beneficiary(
    beneficiary_id: int,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Delete a beneficiary
    
    Args:
        beneficiary_id: Beneficiary ID to delete
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        Deletion confirmation
    """
    auth = get_auth_header(username, password)
    return await make_request("DELETE", f"/self/beneficiaries/tpt/{beneficiary_id}", auth=auth)


@mcp.tool()
async def get_transfer_template(
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Get transfer template for third-party transfers
    
    Args:
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        Transfer template with available options
    """
    auth = get_auth_header(username, password)
    return await make_request("GET", '/self/accounttransfers/template?type="tpt"', auth=auth)


@mcp.tool()
async def make_third_party_transfer(
    from_account_id: str,
    from_account_type: str,
    from_client_id: int,
    from_office_id: int,
    to_account_id: str,
    to_account_type: int,
    to_client_id: int,
    to_office_id: int,
    transfer_amount: float,
    transfer_date: str,
    transfer_description: str,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Make a third-party transfer
    
    Args:
        from_account_id: Source account ID
        from_account_type: Source account type
        from_client_id: Source client ID
        from_office_id: Source office ID
        to_account_id: Destination account ID
        to_account_type: Destination account type (1=Savings, 2=Loan)
        to_client_id: Destination client ID
        to_office_id: Destination office ID
        transfer_amount: Amount to transfer
        transfer_date: Transfer date (format: "dd MMMM yyyy")
        transfer_description: Transfer description
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        Transfer confirmation details
    """
    auth = get_auth_header(username, password)
    data = {
        "toOfficeId": to_office_id,
        "toClientId": to_client_id,
        "toAccountType": to_account_type,
        "toAccountId": to_account_id,
        "transferAmount": transfer_amount,
        "transferDate": transfer_date,
        "transferDescription": transfer_description,
        "dateFormat": "dd MMMM yyyy",
        "locale": "en",
        "fromAccountId": from_account_id,
        "fromAccountType": from_account_type,
        "fromClientId": from_client_id,
        "fromOfficeId": from_office_id
    }
    
    return await make_request("POST", '/self/accounttransfers?type="tpt"', auth=auth, data=data)


# Resources for providing context about the API

@mcp.resource("file:///resources/mobile-banking-overview")
async def get_overview() -> str:
    """Overview of TT Mobile Banking API capabilities"""
    return """
    # TT Mobile Banking API Overview
    
    This MCP server provides access to the TT Mobile Banking API, which includes:
    
    ## User Management
    - Self-service registration for existing clients
    - Registration confirmation with authentication tokens
    - Secure login with username/password
    
    ## Account Management
    - View client information
    - List all accounts (savings, loans)
    - View account charges
    - View transaction history
    
    ## Beneficiary Management
    - Add beneficiaries for third-party transfers
    - Update beneficiary details and limits
    - Delete beneficiaries
    - View beneficiary list
    
    ## Transfers
    - Third-party transfers between accounts
    - Support for both savings and loan accounts
    - Transfer limits and descriptions
    
    ## Security
    - Basic authentication for API calls
    - Tenant-based isolation
    - Authentication tokens for registration
    """


@mcp.resource("file:///resources/api-endpoints")
async def get_endpoints() -> str:
    """List of available API endpoints"""
    return """
    # Available API Endpoints
    
    ## Registration & Authentication
    - POST /self/registration - Register new self-service user
    - POST /self/registration/user - Confirm registration
    - POST /self/authentication - Login
    
    ## Client Information
    - GET /self/clients - Get client details
    - GET /self/clients/{id}/accounts - List accounts
    - GET /self/clients/{id}/charges - List charges
    - GET /self/clients/{id}/transactions - List transactions
    
    ## Beneficiaries
    - GET /self/beneficiaries/tpt - List beneficiaries
    - GET /self/beneficiaries/tpt/{accountNumber} - Get beneficiary template
    - POST /self/beneficiaries/tpt - Add beneficiary
    - PUT /self/beneficiaries/tpt/{id} - Update beneficiary
    - DELETE /self/beneficiaries/tpt/{id} - Delete beneficiary
    
    ## Transfers
    - GET /self/accounttransfers/template?type="tpt" - Transfer template
    - POST /self/accounttransfers?type="tpt" - Make transfer
    """


@mcp.resource("file:///resources/sample-workflows")
async def get_workflows() -> str:
    """Sample workflows for common operations"""
    return """
    # Sample Workflows
    
    ## 1. New User Registration
    ```
    1. Call register_self_service with user details
    2. User receives authentication token via email
    3. Call confirm_registration with request_id and token
    4. User can now login with credentials
    ```
    
    ## 2. View Account Information
    ```
    1. Call login_self_service to authenticate
    2. Call get_client_info to get client ID
    3. Call get_client_accounts with client ID
    4. Call get_client_transactions for transaction history
    ```
    
    ## 3. Setup and Make Transfer
    ```
    1. Login with credentials
    2. Call add_beneficiary to add recipient
    3. Call get_transfer_template for transfer options
    4. Call make_third_party_transfer with details
    ```
    
    ## 4. Manage Beneficiaries
    ```
    1. Login with credentials
    2. Call get_beneficiaries to list all
    3. Call update_beneficiary to modify limits
    4. Call delete_beneficiary to remove
    ```
    """


# Run the server
if __name__ == "__main__":
    
    # You can configure the server with environment variables:
    # MIFOS_BASE_URL - Base URL for the API (default: https://tt.mifos.community)
    # MIFOS_TENANT - Default tenant ID (default: default)
    
    print("Starting TT Mobile Banking MCP Server")
    print(f"Base URL: {BASE_URL}")
    print(f"Default Tenant: {DEFAULT_TENANT}")
    
    # Run with FastMCP's built-in server
    mcp.run()
