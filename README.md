# MifosX Self Service MCP

MifosX Self Service MCP is a Model Context Protocol (MCP) server built using FastMCP (Python).
It exposes a set of AI-callable tools that allow MCP-compatible clients (such as Claude Desktop or DeepChat) to securely interact with the Apache Fineract / MifosX Self-Service APIs.

This project enables AI-driven banking workflows such as authentication, account access, beneficiary management, and transfers — while keeping all sensitive logic on the server side.

## Features

*   Register new self-service users.
*   Confirm user registration.
*   User login and authentication.
*   Manage client information.
*   Manage beneficiaries (add, list, update, delete).
*   View client accounts and transactions.
*   Perform third-party account transfers.

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
│   ├── auth_tools.py
│   ├── client_tools.py
│   ├── beneficiary_tools.py
│   └── transfer_tools.py
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
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The application connects to a Fineract API. The base URL and tenant ID are hardcoded in `main.py`:

*   `FINERACT_BASE_URL`: `https://tt.mifos.community/fineract-provider/api/v1`
*   `FINERACT_TENANT_ID`: `default`


## Using with Claude Desktop (MCP)
* In Claude Desktop → Settings → Developer → Local MCP servers → Edit Config, add:

For authentication, the application uses default credentials (`maria`/`password`), but these can be overridden using environment variables for better security and flexibility.

Use this configuration file with Claude Desktop or any other IDE where you use MCP
```bash
{
  "mcpServers": {
    "tt-mobile-banking": {
      "command": "/home/keshav/mcp-mifosx-self-service/venv/bin/python3", #your path
      "args": [
        "/home/keshav/mcp-mifosx-self-service/main.py" #directory where you have cloned
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

If these commands return valid responses, your MCP server is successfully connected and operational.

## Available MCP Tools

The MCP server exposes the following AI-callable tools.
Each tool internally maps to a Fineract self-service API call.
These tools are invoked by MCP-compatible AI clients, not directly via HTTP.


### Authentication

| Method | MCP Tool Name              | Description                              |
|------|----------------------------|------------------------------------------|
| POST | `register_self_service`    | Register a new self-service user          |
| POST | `confirm_registration`     | Confirm user registration with token     |
| POST | `login_self_service`       | Authenticate a self-service user          |

### Client & Accounts

| Method | MCP Tool Name              | Description                              |
|------|----------------------------|------------------------------------------|
| GET  | `get_client_info`          | Retrieve client information               |
| GET  | `get_client_accounts`      | Retrieve client accounts                  |
| GET  | `get_client_transactions`  | Retrieve client transactions              |

### Beneficiaries

| Method | MCP Tool Name              | Description                              |
|------|----------------------------|------------------------------------------|
| GET  | `get_beneficiaries`        | List all beneficiaries                    |
| POST | `add_beneficiary`          | Add a new beneficiary                     |
| PUT  | `update_beneficiary`       | Update an existing beneficiary            |
| DELETE | `delete_beneficiary`     | Delete a beneficiary                      |

### Transfers

| Method | MCP Tool Name                  | Description                              |
|------|--------------------------------|------------------------------------------|
| GET  | `get_transfer_template`        | Retrieve transfer options                |
| POST | `make_third_party_transfer`    | Perform a third-party account transfer   |
