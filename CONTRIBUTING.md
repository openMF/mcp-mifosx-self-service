# Contributing Guidelines: MifosX Self-Service MCP

Thank you for contributing to the MifosX Self-Service MCP server. This project serves as a critical bridge between modern AI clients and the Apache Fineract backend. To maintain the reliability and security of this banking middleware, we adhere to the following professional contribution standards.

---

## 1. Project Architecture

The codebase is designed with a modular, service-oriented structure. Understanding this flow is essential before making changes:

- **Entry Point**: `main.py` initializes the server and registers all tool modules.
- **App Instance**: `mcp_app.py` contains the shared `FastMCP` instance.
- **Routers**: `routers/` contains the logic for MCP tools, grouped by business domain (e.g., Auth, Loans, Savings).
- **Validation**: `schemas/` (Pydantic models) should be utilized for complex data validation.
- **Core Utilities**: `utils/` handles shared cross-cutting concerns like HTTP handling and session management.

---

## 2. Development Standards for MCP Tools

When adding or modifying a tool, follow these strict technical specifications:

### Tool Signature & Metadata
Use the `@mcp.tool()` decorator with a descriptive, human-readable name.

```python
@mcp.tool(name="Descriptive Title in Sentence Case")
async def function_name_in_snake_case(
    username: str, 
    password: str,
    accountNumber: str, # Use camelCase for Mifos API alignment
    optionalField: Optional[str] = None
) -> Dict[str, Any]:
    """
    Provide a concise docstring explaining the tool's purpose.
    This description is used by the AI to decide when to call the tool.
    """
    # implementation logic...
```

### Naming Conventions
To ensure consistency across the MCP ecosystem:
| Component | Convention | Example |
| :--- | :--- | :--- |
| **Tool Display Name** | Sentence Case | `name="Get Client Loan Accounts"` |
| **Function Name** | snake_case | `async def get_loan_details(...)` |
| **API Parameter Names** | camelCase | `clientId`, `transactionId` |
| **Module Files** | snake_case | `loan_tools.py` |

---

## 3. The Feature Implementation Lifecycle

Follow this process when introducing new capabilities:

1.  **Domain Isolation**: Create a new router in `routers/` if the domain is new.
2.  **Standardized Requests**: Utilize `utils/http.py` for all API calls. It includes a mandatory **30-second timeout** and centralized error orchestration.
3.  **Session Management**: Use `utils/auth.py` to retrieve standardized authentication headers.
4.  **Implicit Registration**: After creating a router, you **must** import it into `main.py` using a side-effect import:
    ```python
    import routers.your_new_tools  # noqa: F401
    ```
5.  **Documentation**: If you expose new tools, update the "Available MCP Tools" table in the `README.md`.

---

## 4. Local Testing & Verification

We recommend verifying your changes using the MCP Inspector to simulate AI interaction:

```bash
npx @modelcontextprotocol/inspector python main.py
```

Check for:
-   Argument parsing correctness.
-   Mifos API response mapping (ensure no PII is leaked unintentionally).
-   Timeout handling for slow API responses.

---

## 5. Pull Request Guidelines

1.  **Branching**: Use `feat/`, `fix/`, or `refactor/` prefixes for your branch names.
2.  **Granularity**: Keep PRs focused on a single logical change or domain.
3.  **Summary**: Clearly list the new MCP tools exposed in your PR description.

---

Thank you for helping us build a more accessible financial future.

Happy coding!
