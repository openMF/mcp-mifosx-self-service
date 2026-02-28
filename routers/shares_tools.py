from mcp_app import mcp
from typing import Dict, Any
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="Get List of Share Product")
async def get_shares_products(client_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get List of Share Product"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/products/share?clientId={client_id}", auth=auth)


@mcp.tool(name="Get Share Product Details")
async def get_shares_product_details(client_id: int, product_id: int, username: str, password: str) -> Dict[str, Any]:
    """Get Share Product Details"""
    auth = get_auth_header(username, password)
    return await make_request("GET", f"/self/products/share?clientId={client_id}&productId={product_id}", auth=auth)
