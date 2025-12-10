from mcp_app import mcp


@mcp.resource()
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

