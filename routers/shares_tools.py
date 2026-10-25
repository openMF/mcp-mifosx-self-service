from mcp_app import mcp
from typing import Any
from utils.http import make_request
from utils.auth import get_auth_header


@mcp.tool(name="get_share_product_list")
async def get_shares_products(client_id: int) -> Any:
    """Get List of Share Product"""
    auth = get_auth_header()
    return await make_request("GET", f"/self/products/share?clientId={client_id}", auth=auth)


@mcp.tool(name="get_share_product_details")
async def get_shares_product_details(product_id: int) -> Any:
    """Get the details of one share product."""
    auth = get_auth_header()
    return await make_request("GET", f"/self/products/share/{product_id}", auth=auth)
