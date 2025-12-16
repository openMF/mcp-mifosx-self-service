from mcp_app import mcp
from config.config import BASE_URL, DEFAULT_TENANT

# Register MCP tools
import routers.auth_tools
import routers.client_tools  
import routers.beneficiary_tools  
import routers.transfer_tools  

# Register MCP resources
import resources.overview  
import resources.endpoints  
import resources.workflows  


if __name__ == "__main__":
    print("Starting TT Mobile Banking MCP Server")
    print(f"Base URL: {BASE_URL}")
    print(f"Default Tenant: {DEFAULT_TENANT}")

    mcp.run()
