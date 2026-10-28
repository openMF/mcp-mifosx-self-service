from mcp_app import mcp
from typing import Dict, Any
from utils.auth import get_auth_header
from utils.stepup import resend_pending, verify_pending


@mcp.tool(name="verify_step_up")
async def verify_step_up(challengeId: int, otp: str) -> Dict[str, Any]:
    """Verify Step-Up - Gives the one-time code to a sensitive operation that is waiting for it.

    Use this only after a tool answered step_up_required. The code must come from the USER (it was
    sent to their phone or e-mail, or it is the 6-digit code their authenticator app shows now):
    never guess, invent or reuse one. If the code is right, the waiting operation runs exactly as it
    was requested and its result is returned. Recovery codes of an authenticator app are not accepted
    here.
    """
    return await verify_pending(challengeId, otp, auth=get_auth_header())


@mcp.tool(name="resend_step_up")
async def resend_step_up(challengeId: int) -> Dict[str, Any]:
    """Resend Step-Up Code - Sends the one-time code again for an operation that is waiting for it.

    The server limits how soon and how often a code can be sent again. A code from an authenticator
    app cannot be sent again: ask the USER for the code the app shows now.
    """
    return await resend_pending(challengeId, auth=get_auth_header())
