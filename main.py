from mcp_app import mcp
from config.config import BASE_URL, DEFAULT_TENANT



# import routers to register tools with mcp

import routers.auth_tools 
import routers.client_tools 
import routers.beneficiary_tools 
import routers.transfer_tools 




if __name__ == "__main__":
    print("Starting TT Mobile Banking MCP Server")
    print(f"Base URL: {BASE_URL}")
    print(f"Default Tenant: {DEFAULT_TENANT}")



mcp.run()