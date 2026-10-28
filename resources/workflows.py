from mcp_app import mcp


@mcp.resource("file:///resources/sample-workflows")
async def get_workflows() -> str:
    """Sample workflows for common operations"""
    return """
    # Sample Workflows

    Tools do not take a username or password. After login, every tool uses the saved session.

    ## 1. New User Registration
    ```
    1. Call register_self_service_existing_client with user details
    2. User receives authentication token via email
    3. Call confirm_self_service_user_registration with requestId and authenticationToken
    4. User can now log in
    ```

    ## 2. View Account Information
    ```
    1. Call login once (skip if the server has MIFOS_USERNAME / MIFOS_PASSWORD set)
    2. Call get_clients_linked_to_user to get client ID
    3. Call get_client_accounts with client ID
    4. Call get_client_transactions for transaction history
    ```

    ## 3. Setup and Make Transfer
    ```
    1. Call login once (skip if the server has MIFOS_USERNAME / MIFOS_PASSWORD set)
    2. Call create_beneficiary_savings (or create_beneficiary_loan) to add the recipient
    3. Call get_third_party_transfer_template to see the beneficiary accounts
    4. Call prepare_transfer (third_party true) and show the user the summary it returns
    5. Only after the user says yes, call confirm_transfer with the confirmation_id (cancel_transfer if not)
    6. If the bank needs a verification code, the user types it in the form the client shows. If the tool
       answers step_up_required instead, ask the USER for the code and call verify_step_up
    ```

    ## 4. Manage Beneficiaries
    ```
    1. Call login once (skip if the server has MIFOS_USERNAME / MIFOS_PASSWORD set)
    2. Call get_beneficiary_list to list all
    3. Call update_beneficiary_savings or update_beneficiary_loan to modify limits
    4. Call delete_beneficiary to remove
    ```

    ## 5. Review a Statement and Spending Habits
    ```
    1. Call login once (skip if the server has MIFOS_USERNAME / MIFOS_PASSWORD set)
    2. Call get_clients_linked_to_user to get client ID
    3. Call get_client_accounts to get the savings account ID
    4. Call get_account_statement for the period the user asked about
       (from_date / to_date, direction debit|credit)
    5. Call get_spending_summary for totals and monthly buckets
    6. Call find_recurring_payments for subscriptions and instalments
    7. Report the "unknown" figures honestly instead of folding them into spending
    ```
    """
