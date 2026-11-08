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
    2. Call prepare_beneficiary to add the recipient, show the user what it returns and, only after the user
       says yes, call confirm_beneficiary with the confirmation_id
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
    3. Call prepare_beneficiary_change to change a name or transfer limit, show the user the change and,
       only after the user says yes, call confirm_beneficiary (cancel_beneficiary if not)
    4. Call delete_beneficiary to remove
    ```

    ## 5. Apply for a Loan
    ```
    1. Call login once (skip if the server has MIFOS_USERNAME / MIFOS_PASSWORD set)
    2. Call get_clients_linked_to_user to get client ID
    3. Call get_loan_template without product_id to list the products, then with product_id for its limits
       and loan purposes
    4. Call calculate_loan_repayment_calendar if the user wants to compare amounts or terms
    5. Call prepare_loan_application and show the user the amount, installments, total to repay and schedule
    6. Only after the user says yes, call confirm_loan_application with the confirmation_id
       (cancel_loan_application if not). The bank still has to approve the loan
    ```

    ## 6. Add Guarantors to a Loan Application
    ```
    1. Call login once (skip if the server has MIFOS_USERNAME / MIFOS_PASSWORD set)
    2. The loan application must still be waiting for approval
    3. Call get_guarantor_template for the relationship options
    4. Call create_guarantor for a customer, staff member or external person
    5. To pledge the user's own savings, call prepare_savings_guarantee and show the user the amount that will
       be blocked; only after they say yes call confirm_savings_guarantee (cancel_savings_guarantee if not)
    6. Call get_guarantor_list to check, update_guarantor or delete_guarantor to change or remove one
    ```

    ## 7. Review a Statement and Spending Habits
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
