from mcp_app import mcp
from config.config import BASE_URL, DEFAULT_TENANT

import routers.auth_tools  # noqa: F401
import routers.client_tools  # noqa: F401
import routers.beneficiary_tools  # noqa: F401
import routers.transfer_tools  # noqa: F401


if __name__ == "__main__":
    print("Starting TT Mobile Banking MCP Server")
    print(f"Base URL: {BASE_URL}")
    print(f"Default Tenant: {DEFAULT_TENANT}")

    mcp.run()
