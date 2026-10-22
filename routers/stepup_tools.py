from mcp_app import mcp
from typing import Dict, Any
from utils.auth import get_auth_header
from utils.stepup import resend_pending, verify_pending


@mcp.tool(name="verify_step_up")
async def verify_step_up(challengeId: int, otp: str) -> Dict[str, Any]:
    """Verify Step-Up - Gives the one-time code to a sensitive operation that is waiting for it.

    Use this only after a tool answered step_up_required. The code must come from the USER (it was
    sent to their phone or e-mail): never guess, invent or reuse one. If the code is right, the
    waiting operation runs exactly as it was requested and its result is returned.
    """
    return await verify_pending(challengeId, otp, auth=get_auth_header())


@mcp.tool(name="resend_step_up")
async def resend_step_up(challengeId: int) -> Dict[str, Any]:
    """Resend Step-Up Code - Sends the one-time code again for an operation that is waiting for it.

    The server limits how soon and how often a code can be sent again.
    """
    return await resend_pending(challengeId, auth=get_auth_header())
