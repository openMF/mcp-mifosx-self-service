# # main.py
# import base64
# import httpx
# from fastapi import FastAPI, Body, Header, HTTPException, Path
# from pydantic import BaseModel, Field
# from typing import Optional, List, Dict, Any
# from fastapi_mcp import FastApiMCP
# # --- Configuration ---
# # It's recommended to move these to environment variables for production
# FINERACT_BASE_URL = "https://tt.mifos.community/fineract-provider/api/v1"
# FINERACT_TENANT_ID = "default"

# app = FastAPI(
#     title="Fineract Mobile Banking Tools for MCP",
#     description="A set of tools, based on a Postman collection, to interact with the Fineract self-service API.",
#     version="1.0.0",
# )

# # --- Reusable HTTP Client ---
# # Using a single, reusable client is more efficient.
# client = httpx.AsyncClient(base_url=FINERACT_BASE_URL)

# mcp = FastApiMCP(
#    app
# )
# mcp.mount() 

# async def get_auth_headers(
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ) -> Dict[str, str]:
#     """Creates Basic Authentication headers from username and password."""
#     credentials = f"{username}:{password}"
#     token = base64.b64encode(credentials.encode()).decode("utf-8")
#     return {
#         "Fineract-Platform-TenantId": FINERACT_TENANT_ID,
#         "Authorization": f"Basic {token}",
#     }

# # --- Pydantic Models for Request Bodies ---
# # These models ensure that the data sent to our tools is valid.

# class SelfServiceRegistrationPayload(BaseModel):
#     username: str = Field(..., example="maria")
#     accountNumber: str = Field(..., example="000000104")
#     password: str = Field(..., example="T3l3c0m2025#")
#     firstName: str = Field(..., example="MARIA")
#     mobileNumber: str = Field(..., example="5522649495")
#     lastName: str = Field(..., example="MERCEDES")
#     email: str = Field(..., example="devops@fintecheando.mx")
#     authenticationMode: str = Field(..., example="email")

# class ConfirmRegistrationPayload(BaseModel):
#     requestId: int = Field(..., example=45)
#     authenticationToken: str = Field(..., example="1311")

# class LoginPayload(BaseModel):
#     username: str = Field(..., example="maria")
#     password: str = Field(..., example="password")

# class BeneficiaryPayload(BaseModel):
#     locale: str = Field("en", example="en")
#     name: str
#     officeName: str = Field(..., example="Head Office")
#     accountNumber: str
#     accountType: int = Field(..., description="1 for Savings, 2 for Loan")
#     transferLimit: float

# class UpdateBeneficiaryPayload(BaseModel):
#     name: str
#     transferLimit: float

# class AccountTransferPayload(BaseModel):
#     toOfficeId: int
#     toClientId: int
#     toAccountType: int
#     toAccountId: str
#     transferAmount: float
#     transferDate: str = Field(..., example="03 March 2025")
#     transferDescription: str
#     dateFormat: str = "dd MMMM yyyy"
#     locale: str = "en"
#     fromAccountId: str
#     fromAccountType: str
#     fromClientId: int
#     fromOfficeId: int


# # --- Tool Definitions (API Endpoints) ---

# @app.post("/mobile-banking/register-self-service", summary="REGISTER SELF SERVICE FOR EXISTING CLIENT")
# async def register_self_service(payload: SelfServiceRegistrationPayload = Body(...)):
#     """Registers a new self-service user for an existing client."""
#     headers = {"Fineract-Platform-TenantId": FINERACT_TENANT_ID}
#     try:
#         response = await client.post("/self/registration", json=payload.dict(), headers=headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
    

# @app.post("/mobile-banking/confirm-registration", summary="CONFIRM SELF SERVICE USER REGISTRATION")
# async def confirm_registration(payload: ConfirmRegistrationPayload = Body(...)):
#     """Confirms the user registration with a token."""
#     headers = {"Fineract-Platform-TenantId": FINERACT_TENANT_ID}
#     try:
#         response = await client.post("/self/registration/user", json=payload.dict(), headers=headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# @app.post("/mobile-banking/login", summary="LOGIN (SELF SERVICE)")
# async def self_service_login(payload: LoginPayload = Body(...)):
#     """Authenticates a self-service user and returns a user object with a base64 encoded token."""
#     headers = {"Fineract-Platform-TenantId": FINERACT_TENANT_ID}
#     try:
#         # The Fineract API uses the payload itself for authentication
#         response = await client.post("/self/authentication", json=payload.dict(), headers=headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# @app.get("/mobile-banking/clients", summary="GET CLIENTS (SELF SERVICE)")
# async def get_self_service_clients(
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ):
#     """Retrieves client information for the authenticated self-service user."""
#     auth_headers = await get_auth_headers(username, password)
#     try:
#         response = await client.get("/self/clients", headers=auth_headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# @app.post("/mobile-banking/beneficiaries", summary="ADD BENEFICIARY (SELF SERVICE)")
# async def add_beneficiary(
#     payload: BeneficiaryPayload = Body(...),
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ):
#     """Adds a new beneficiary (TPT) for the authenticated user."""
#     auth_headers = await get_auth_headers(username, password)
#     try:
#         response = await client.post("/self/beneficiaries/tpt", json=payload.dict(), headers=auth_headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# @app.get("/mobile-banking/beneficiaries", summary="GET LIST OF BENEFICIARIES (SELF SERVICE)")
# async def get_beneficiaries(
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ):
#     """Retrieves the list of beneficiaries for the authenticated user."""
#     auth_headers = await get_auth_headers(username, password)
#     try:
#         response = await client.get("/self/beneficiaries/tpt", headers=auth_headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# @app.put("/mobile-banking/beneficiaries/{beneficiary_id}", summary="UPDATE BENEFICIARY (SELF SERVICE)")
# async def update_beneficiary(
#     beneficiary_id: int = Path(..., description="The ID of the beneficiary to update."),
#     payload: UpdateBeneficiaryPayload = Body(...),
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ):
#     """Updates an existing beneficiary's name and transfer limit."""
#     auth_headers = await get_auth_headers(username, password)
#     try:
#         response = await client.put(f"/self/beneficiaries/tpt/{beneficiary_id}", json=payload.dict(), headers=auth_headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# @app.delete("/mobile-banking/beneficiaries/{beneficiary_id}", summary="DELETE BENEFICIARY (SELF SERVICE)")
# async def delete_beneficiary(
#     beneficiary_id: int = Path(..., description="The ID of the beneficiary to delete."),
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ):
#     """Deletes a beneficiary for the authenticated user."""
#     auth_headers = await get_auth_headers(username, password)
#     try:
#         response = await client.delete(f"/self/beneficiaries/tpt/{beneficiary_id}", headers=auth_headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# @app.get("/mobile-banking/clients/{client_id}/accounts", summary="GET LIST OF ACCOUNTS (SELF SERVICE)")
# async def get_client_accounts(
#     client_id: int = Path(..., description="The ID of the client."),
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ):
#     """Retrieves a list of accounts (savings and loans) for a given client."""
#     auth_headers = await get_auth_headers(username, password)
#     try:
#         response = await client.get(f"/self/clients/{client_id}/accounts", headers=auth_headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
        
# @app.get("/mobile-banking/clients/{client_id}/transactions", summary="GET LIST OF TRANSACTIONS (SELF SERVICE)")
# async def get_client_transactions(
#     client_id: int = Path(..., description="The ID of the client."),
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ):
#     """Retrieves a list of transactions for a given client."""
#     auth_headers = await get_auth_headers(username, password)
#     try:
#         response = await client.get(f"/self/clients/{client_id}/transactions", headers=auth_headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# @app.post("/mobile-banking/transfers/third-party", summary="TRANSFER TO THIRD PARTY")
# async def transfer_to_third_party(
#     payload: AccountTransferPayload = Body(...),
#     username: str = Header(..., description="User's login username."),
#     password: str = Header(..., description="User's login password."),
# ):
#     """Performs a third-party account transfer."""
#     auth_headers = await get_auth_headers(username, password)
#     try:
#         response = await client.post("/self/accounttransfers?type=tpt", json=payload.dict(), headers=auth_headers)
#         response.raise_for_status()
#         return response.json()
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.json())


# if __name__ == "__main__":
#    import uvicorn
#    uvicorn.run(app, host="0.0.0.0", port=7000) 

# 

import base64
import httpx
import os
from fastapi import FastAPI, Body, Header, HTTPException, Path
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from fastapi_mcp import FastApiMCP

# --- Configuration ---
# It's recommended to move these to environment variables for production
FINERACT_BASE_URL = "https://tt.mifos.community/fineract-provider/api/v1"
FINERACT_TENANT_ID = "default"

# Default credentials (can be overridden by environment variables)
DEFAULT_USERNAME = os.getenv("FINERACT_USERNAME", "maria")
DEFAULT_PASSWORD = os.getenv("FINERACT_PASSWORD", "password")

app = FastAPI(
    title="Fineract Mobile Banking Tools for MCP",
    description="A set of tools, based on a Postman collection, to interact with the Fineract self-service API.",
    version="1.0.0",
)

# --- Reusable HTTP Client ---
# Using a single, reusable client is more efficient.
client = httpx.AsyncClient(base_url=FINERACT_BASE_URL)

async def get_auth_headers(
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, str]:
    """Creates Basic Authentication headers from username and password."""
    # Use provided credentials or fall back to defaults
    auth_username = username or DEFAULT_USERNAME
    auth_password = password or DEFAULT_PASSWORD
    
    credentials = f"{auth_username}:{auth_password}"
    token = base64.b64encode(credentials.encode()).decode("utf-8")
    return {
        "Fineract-Platform-TenantId": FINERACT_TENANT_ID,
        "Authorization": f"Basic {token}",
    }

# --- Pydantic Models for Request Bodies ---
# These models ensure that the data sent to our tools is valid.

class SelfServiceRegistrationPayload(BaseModel):
    username: str = Field(..., example="maria")
    accountNumber: str = Field(..., example="000000104")
    password: str = Field(..., example="T3l3c0m2025#")
    firstName: str = Field(..., example="MARIA")
    mobileNumber: str = Field(..., example="5522649495")
    lastName: str = Field(..., example="MERCEDES")
    email: str = Field(..., example="devops@fintecheando.mx")
    authenticationMode: str = Field(..., example="email")

class ConfirmRegistrationPayload(BaseModel):
    requestId: int = Field(..., example=45)
    authenticationToken: str = Field(..., example="1311")

class LoginPayload(BaseModel):
    username: str = Field(..., example="maria")
    password: str = Field(..., example="password")

class BeneficiaryPayload(BaseModel):
    locale: str = Field("en", example="en")
    name: str
    officeName: str = Field(..., example="Head Office")
    accountNumber: str
    accountType: int = Field(..., description="1 for Savings, 2 for Loan")
    transferLimit: float

class UpdateBeneficiaryPayload(BaseModel):
    name: str
    transferLimit: float

class AccountTransferPayload(BaseModel):
    toOfficeId: int
    toClientId: int
    toAccountType: int
    toAccountId: str
    transferAmount: float
    transferDate: str = Field(..., example="03 March 2025")
    transferDescription: str
    dateFormat: str = "dd MMMM yyyy"
    locale: str = "en"
    fromAccountId: str
    fromAccountType: str
    fromClientId: int
    fromOfficeId: int

# --- Tool Definitions (API Endpoints) ---

@app.post("/mobile-banking/register-self-service", summary="REGISTER SELF SERVICE FOR EXISTING CLIENT")
async def register_self_service(payload: SelfServiceRegistrationPayload = Body(...)):
    """Registers a new self-service user for an existing client."""
    headers = {"Fineract-Platform-TenantId": FINERACT_TENANT_ID}
    try:
        response = await client.post("/self/registration", json=payload.dict(), headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.post("/mobile-banking/confirm-registration", summary="CONFIRM SELF SERVICE USER REGISTRATION")
async def confirm_registration(payload: ConfirmRegistrationPayload = Body(...)):
    """Confirms the user registration with a token."""
    headers = {"Fineract-Platform-TenantId": FINERACT_TENANT_ID}
    try:
        response = await client.post("/self/registration/user", json=payload.dict(), headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.post("/mobile-banking/login", summary="LOGIN (SELF SERVICE)")
async def self_service_login(payload: LoginPayload = Body(...)):
    """Authenticates a self-service user and returns a user object with a base64 encoded token."""
    headers = {"Fineract-Platform-TenantId": FINERACT_TENANT_ID}
    try:
        # The Fineract API uses the payload itself for authentication
        response = await client.post("/self/authentication", json=payload.dict(), headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.get("/mobile-banking/clients", summary="GET CLIENTS (SELF SERVICE)")
async def get_self_service_clients(
    username: Optional[str] = Header(default=None, description="User's login username. Uses 'maria' if not provided."),
    password: Optional[str] = Header(default=None, description="User's login password. Uses 'password' if not provided."),
):
    """Retrieves client information for the authenticated self-service user."""
    auth_headers = await get_auth_headers(username, password)
    try:
        response = await client.get("/self/clients", headers=auth_headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.post("/mobile-banking/beneficiaries", summary="ADD BENEFICIARY (SELF SERVICE)")
async def add_beneficiary(
    payload: BeneficiaryPayload = Body(...),
    username: Optional[str] = Header(default=None, description="User's login username. Uses 'maria' if not provided."),
    password: Optional[str] = Header(default=None, description="User's login password. Uses 'password' if not provided."),
):
    """Adds a new beneficiary (TPT) for the authenticated user."""
    auth_headers = await get_auth_headers(username, password)
    try:
        response = await client.post("/self/beneficiaries/tpt", json=payload.dict(), headers=auth_headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.get("/mobile-banking/beneficiaries", summary="GET LIST OF BENEFICIARIES (SELF SERVICE)")
async def get_beneficiaries(
    username: Optional[str] = Header(default=None, description="User's login username. Uses 'maria' if not provided."),
    password: Optional[str] = Header(default=None, description="User's login password. Uses 'password' if not provided."),
):
    """Retrieves the list of beneficiaries for the authenticated user."""
    auth_headers = await get_auth_headers(username, password)
    try:
        response = await client.get("/self/beneficiaries/tpt", headers=auth_headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.put("/mobile-banking/beneficiaries/{beneficiary_id}", summary="UPDATE BENEFICIARY (SELF SERVICE)")
async def update_beneficiary(
    beneficiary_id: int = Path(..., description="The ID of the beneficiary to update."),
    payload: UpdateBeneficiaryPayload = Body(...),
    username: Optional[str] = Header(default=None, description="User's login username. Uses 'maria' if not provided."),
    password: Optional[str] = Header(default=None, description="User's login password. Uses 'password' if not provided."),
):
    """Updates an existing beneficiary's name and transfer limit."""
    auth_headers = await get_auth_headers(username, password)
    try:
        response = await client.put(f"/self/beneficiaries/tpt/{beneficiary_id}", json=payload.dict(), headers=auth_headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.delete("/mobile-banking/beneficiaries/{beneficiary_id}", summary="DELETE BENEFICIARY (SELF SERVICE)")
async def delete_beneficiary(
    beneficiary_id: int = Path(..., description="The ID of the beneficiary to delete."),
    username: Optional[str] = Header(default=None, description="User's login username. Uses 'maria' if not provided."),
    password: Optional[str] = Header(default=None, description="User's login password. Uses 'password' if not provided."),
):
    """Deletes a beneficiary for the authenticated user."""
    auth_headers = await get_auth_headers(username, password)
    try:
        response = await client.delete(f"/self/beneficiaries/tpt/{beneficiary_id}", headers=auth_headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.get("/mobile-banking/clients/{client_id}/accounts", summary="GET LIST OF ACCOUNTS (SELF SERVICE)")
async def get_client_accounts(
    client_id: int = Path(..., description="The ID of the client."),
    username: Optional[str] = Header(default=None, description="User's login username. Uses 'maria' if not provided."),
    password: Optional[str] = Header(default=None, description="User's login password. Uses 'password' if not provided."),
):
    """Retrieves a list of accounts (savings and loans) for a given client."""
    auth_headers = await get_auth_headers(username, password)
    try:
        response = await client.get(f"/self/clients/{client_id}/accounts", headers=auth_headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.get("/mobile-banking/clients/{client_id}/transactions", summary="GET LIST OF TRANSACTIONS (SELF SERVICE)")
async def get_client_transactions(
    client_id: int = Path(..., description="The ID of the client."),
    username: Optional[str] = Header(default=None, description="User's login username. Uses 'maria' if not provided."),
    password: Optional[str] = Header(default=None, description="User's login password. Uses 'password' if not provided."),
):
    """Retrieves a list of transactions for a given client."""
    auth_headers = await get_auth_headers(username, password)
    try:
        response = await client.get(f"/self/clients/{client_id}/transactions", headers=auth_headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.post("/mobile-banking/transfers/third-party", summary="TRANSFER TO THIRD PARTY")
async def transfer_to_third_party(
    payload: AccountTransferPayload = Body(...),
    username: Optional[str] = Header(default=None, description="User's login username. Uses 'maria' if not provided."),
    password: Optional[str] = Header(default=None, description="User's login password. Uses 'password' if not provided."),
):
    """Performs a third-party account transfer."""
    auth_headers = await get_auth_headers(username, password)
    try:
        response = await client.post("/self/accounttransfers?type=tpt", json=payload.dict(), headers=auth_headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

# Initialize MCP after all endpoints are defined
mcp = FastApiMCP(app)
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)