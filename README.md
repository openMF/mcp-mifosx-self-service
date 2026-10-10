# MifosX Self Service MCP

MifosX Self Service MCP is a Model Context Protocol (MCP) server built using FastMCP (Python).
It exposes a set of AI-callable tools that allow MCP-compatible clients (such as Claude Desktop or DeepChat) to securely interact with the Apache Fineract / MifosX Self-Service APIs.

This project enables AI-driven banking workflows such as authentication, account access, beneficiary management, loans, savings, and transfers — while keeping all sensitive logic on the server side.

## Features

*   Register new self-service users.
*   Confirm user registration.
*   User login and authentication.
*   Manage client information.
*   Manage beneficiaries (add, list, update, delete).
*   View client accounts and transactions.
*   Manage loans (view products, applications, transactions, charges).
*   Manage savings accounts (products, applications, transactions, charges).
*   Manage guarantors for loans.
*   Manage share accounts and products.
*   Register for push notifications.
*   Perform third-party account transfers.

## Architecture

The MCP server acts as a secure bridge between your AI client and the Mifos/Fineract backend.

```mermaid
graph LR
    A[AI Client] -- MCP Protocol --> B[FastMCP Server]
    B -- REST API --> C[MifosX / Fineract]
    C -- Data --> B
    B -- Context --> A
```

## Project Structure

```text
The codebase is organized into a modular, maintainable structure:

mcp-mifosx-self-service/
│
├── main.py              # MCP server entry point
├── mcp_app.py           # FastMCP app initialization
│
├── config/
│   └── config.py        # Environment-based configuration
│
├── routers/             # MCP tools grouped by domain
│   ├── auth_tools.py        # User registration & authentication
│   ├── client_tools.py      # Client information & accounts
│   ├── beneficiary_tools.py # Beneficiary management
│   ├── transfer_tools.py   # Third-party transfers
│   ├── loan_tools.py        # Loan products & accounts
│   ├── savings_tools.py     # Savings accounts & products
│   ├── guarantor_tools.py  # Loan guarantor management
│   ├── shares_tools.py     # Share accounts & products
│   └── notification_tools.py # Push notification registration
│
├── schemas/             # Pydantic request/response models
│   ├── registration.py
│   ├── authentication.py
│   ├── confirm.py
│   ├── beneficiary.py
│   └── transfer.py
│
├── utils/               # Shared helpers
│   ├── http.py          # Centralized HTTP client
│   └── auth.py          # Auth helpers (Basic Auth)
│
├── resources/           # MCP resources (context & docs)
│   ├── overview.py
│   ├── endpoints.py
│   └── workflows.py
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/openMF/mcp-mifosx-self-service.git
    cd mcp-mifosx-self-service
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The application connects to a Fineract API. Use environment variables (or a `.env` file) for customization:

| Variable | Description | Default |
|----------|-------------|---------|
| `MIFOS_BASE_URL` | Base URL of Fineract instance | `https://tt.mifos.community` |
| `MIFOS_TENANT` | Tenant identifier | `default` |

For authentication, the application uses default credentials (`maria`/`password`), but these can be overridden using environment variables for better security and flexibility.

## Running with Docker

The project includes Docker support for easy deployment:

```bash
# Build and run with docker-compose
docker-compose up --build
```

## Using with Claude Desktop (MCP)

* In Claude Desktop → Settings → Developer → Local MCP servers → Edit Config, add:

```json
{
  "mcpServers": {
    "mifos-banking": {
      "command": "/ABSOLUTE/PATH/TO/venv/bin/python",
      "args": [
        "/ABSOLUTE/PATH/TO/main.py"
      ],
      "env": {
        "MIFOS_BASE_URL": "https://tt.mifos.community",
        "MIFOS_TENANT": "default"
      }
    }
  }
}
```
Restart Claude Desktop after saving.

## Running the Server

To run the MCP server, execute the following command from the project's root directory:

```bash
python3 main.py
```

## Example Usage (Natural Language) on Claude

Once the MCP server is connected, Claude can invoke the available tools automatically.
You can paste the following prompts in Claude Desktop to verify that your configuration is working correctly:

- Login using username `maria` and password `password`
- Get my client information
- Show my client accounts
- List my beneficiaries
- Get my loan accounts
- Show my savings accounts

If these commands return valid responses, your MCP server is successfully connected and operational.

## Available MCP Tools

The MCP server exposes the following AI-callable tools.
Each tool internally maps to a Fineract self-service API call.
These tools are invoked by MCP-compatible AI clients, not directly via HTTP.

### Authentication

| Method | MCP Tool Name              | Description                              |
|--------|----------------------------|------------------------------------------|
| POST   | `register_self_service`    | Register a new self-service user          |
| POST   | `confirm_registration`     | Confirm user registration with token     |
| POST   | `login_self_service`       | Authenticate a self-service user          |

### Client & Accounts

| Method | MCP Tool Name              | Description                              |
|--------|----------------------------|------------------------------------------|
| GET    | `get_client_info`          | Retrieve client information               |
| GET    | `get_client_accounts`      | Retrieve client accounts                  |
| GET    | `get_client_charges`       | Retrieve client charges                   |
| GET    | `get_client_transactions`  | Retrieve client transactions              |

### Beneficiaries

| Method | MCP Tool Name              | Description                              |
|--------|----------------------------|------------------------------------------|
| GET    | `get_beneficiaries`        | List all beneficiaries                    |
| GET    | `get_beneficiary_template` | Get beneficiary template for an account  |
| POST   | `add_beneficiary`          | Add a new beneficiary                     |
| PUT    | `update_beneficiary`      | Update an existing beneficiary            |
| DELETE | `delete_beneficiary`      | Delete a beneficiary                      |

### Loans

| Method | MCP Tool Name                    | Description                              |
|--------|-----------------------------------|------------------------------------------|
| GET    | `get_loan_products`              | Retrieve available loan products         |
| GET    | `get_loan_product_details`       | Retrieve loan product details           |
| GET    | `get_loan_account_details`       | Retrieve loan account details           |
| GET    | `get_loan_transaction_detail`    | Retrieve loan transaction detail        |
| GET    | `get_loan_account_charges`       | Retrieve loan charges                    |
| GET    | `get_loan_template`              | Retrieve loan application template       |
| POST   | `calculate_loan_repayment_calendar` | Calculate loan repayment schedule    |
| POST   | `submit_loan_application`        | Submit loan application                  |
| PUT    | `update_loan_application`        | Update loan application                  |
| POST   | `withdraw_loan_application`      | Withdraw loan application                |

### Savings

| Method | MCP Tool Name                    | Description                              |
|--------|-----------------------------------|------------------------------------------|
| GET    | `get_savings_products`            | Get list of savings products             |
| GET    | `get_savings_product_details`     | Get savings product details              |
| GET    | `get_savings_account_details`     | Get savings account details              |
| GET    | `get_savings_account_transactions`| Get savings account transactions         |
| GET    | `get_savings_account_transaction_details` | Get transaction details          |
| GET    | `get_savings_account_charges`     | Get savings account charges              |
| GET    | `get_savings_account_template_raw`| Get savings account template             |
| POST   | `submit_savings_application`     | Submit savings account application       |
| PUT    | `update_savings_account_application` | Update savings account application    |

### Guarantors

| Method | MCP Tool Name              | Description                              |
|--------|----------------------------|------------------------------------------|
| GET    | `get_guarantor_template`  | Get template for creating guarantors      |
| GET    | `get_guarantor_list`      | Get list of guarantors for a loan        |
| POST   | `create_guarantor`        | Add a new guarantor for a loan           |
| PUT    | `update_guarantor`        | Update an existing guarantor              |
| DELETE | `delete_guarantor`        | Delete a loan guarantor                  |

### Shares

| Method | MCP Tool Name              | Description                              |
|--------|----------------------------|------------------------------------------|
| GET    | `get_share_product_list`  | Get list of share products               |
| GET    | `get_share_product_details` | Get share product details              |

### Notifications

| Method | MCP Tool Name                  | Description                              |
|--------|--------------------------------|------------------------------------------|
| GET    | `get_user_notification_details` | Get notification registration details  |
| POST   | `register_for_notifications`  | Register device for push notifications   |
| PUT    | `update_notification_registration` | Update notification registration     |

### Transfers

| Method | MCP Tool Name                  | Description                              |
|--------|--------------------------------|------------------------------------------|
| GET    | `get_transfer_template`        | Retrieve transfer options                |
| POST   | `make_third_party_transfer`   | Perform a third-party account transfer  |

## MCP Marketplace

This server can be discovered on MCP marketplaces. See [MARKETPLACE.md](MARKETPLACE.md) for the full list of listings and submission instructions.

| Marketplace | Reference (sister project) |
|---|---|
| Glama | [openMF/mcp-mifosx](https://glama.ai/mcp/servers/openMF/mcp-mifosx) |

## License

This project is licensed under the terms included in the LICENSE file.

