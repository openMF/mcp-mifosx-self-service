# MifosX Self Service MCP

This project provides a set of tools, implemented as a FastAPI server, to interact with the Fineract self-service API. It is designed to be used as a Model-Coded-Processor (MCP) server.

## Features

*   Register new self-service users.
*   Confirm user registration.
*   User login and authentication.
*   Manage client information.
*   Manage beneficiaries (add, list, update, delete).
*   View client accounts and transactions.
*   Perform third-party account transfers.


## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/openMF/mcp-mifosx-self-service.git
    cd mcp-mifosx-self-service.
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

For authentication, the application uses default credentials (`maria`/`password`), but these can be overridden using environment variables for better security and flexibility.

Use this configuration file with Claude Desktop or any other IDE where you use MCP
```bash
{
  "mcpServers": {
    "tt-mobile-banking": {
      "command": "/home/keshav/anaconda3/bin/python", #your path
      "args": [
        "/home/keshav/Documents/mcp-mifosx-self-service/main.py" #directory where you have cloned
      ],
      "env": {
        "MIFOS_BASE_URL": "https://tt.mifos.community",
        "MIFOS_TENANT": "default"
      }
    }
  }
}
```

## Running the Server

To run the MCP server, execute the following command from the project's root directory:

```bash
python3 main.py
```

The server will start and be accessible at `http://0.0.0.0:7000`. The OpenAPI documentation (Swagger UI) will be available at `http://0.0.0.0:7000/docs`.

## Available Tools (API Endpoints)

The following tools are exposed by the server:

*   `POST /mobile-banking/register-self-service`: Register a self-service user.
*   `POST /mobile-banking/confirm-registration`: Confirm user registration with a token.
*   `POST /mobile-banking/login`: Authenticate a self-service user.
*   `GET /mobile-banking/clients`: Get client information.
*   `POST /mobile-banking/beneficiaries`: Add a new beneficiary.
*   `GET /mobile-banking/beneficiaries`: Get the list of beneficiaries.
*   `PUT /mobile-banking/beneficiaries/{beneficiary_id}`: Update a beneficiary.
*   `DELETE /mobile-banking/beneficiaries/{beneficiary_id}`: Delete a beneficiary.
*   `GET /mobile-banking/clients/{client_id}/accounts`: Get a list of client accounts.
*   `GET /mobile-banking/clients/{client_id}/transactions`: Get a list of client transactions.
*   `POST /mobile-banking/transfers/third-party`: Perform a third-party account transfer.
