from mcp_app import mcp


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
