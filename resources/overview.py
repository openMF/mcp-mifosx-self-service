from mcp_app import mcp


@mcp.resource("file:///resources/overview")
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
