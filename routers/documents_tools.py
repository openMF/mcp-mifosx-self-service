"""Document capture gate + client document files.

`validate_capture_quality` runs the deterministic document capture-quality
gate (see utils/capture_gate.py) on a
photo BEFORE anything is uploaded: an unreadable capture returns RETAKE and
never reaches Fineract, borderline ones are flagged for human REVIEW, usable
ones proceed. Purely local: no network call, no LLM.

`get_client_documents` / `upload_client_document` work on the self-service
client-document endpoints. The upload composes the pre-flight gate with the
multipart POST, so an unreadable capture is refused instead of stored
server-side. The bank only lets a self-service user work with documents of
their own linked client; that remains Fineract's job to enforce.

`verify_client_details` covers the content side: the AI client's vision
model (GLM, Claude, anything with image input) reads the photo and extracts
fields; this tool fetches the client's record from Fineract and compares
them deterministically (utils/verify_fields.py) — per-field MATCH / REVIEW
/ MISMATCH verdicts, never an LLM guess.
"""

import os
from typing import Any, Dict, Optional

from mcp_app import mcp

from utils.auth import get_auth_header
from utils.capture_gate import VERDICT_RETAKE, assess_image
from utils.http import make_request, make_upload_request
from utils.verify_fields import verify_fields

_MAX_CAPTURE_BYTES = 40 * 1024 * 1024


@mcp.tool(name="validate_capture_quality")
def validate_capture_quality(image_path: str) -> Dict[str, Any]:
    """Run the document capture-quality gate on a photo BEFORE uploading it.

    Deterministic and offline (no LLM, nothing leaves this machine): returns
    verdict RETAKE (unreadable — take the photo again) / REVIEW (borderline —
    a human should judge) / PASS (usable), the exact reasons, and the
    measured signals (sharpness, contrast, ink_ratio, brightness).
    Reads local image files (jpg/png/webp/tiff...).
    """
    return _gate_result(image_path)


def _gate_result(image_path: str) -> Dict[str, Any]:
    """Gate one image file by path, with the same error shape as the bank errors."""
    try:
        size = os.path.getsize(image_path)
        if size == 0:
            return {"error": True, "status_code": 400, "message": f"{image_path} is empty — capture again"}
        if size > _MAX_CAPTURE_BYTES:
            over = f"{image_path} is {size} bytes; captures over {_MAX_CAPTURE_BYTES} are rejected before reading"
            return {"error": True, "status_code": 400, "message": over}
        with open(image_path, "rb") as fh:
            return assess_image(fh.read(), filename=image_path)
    except IsADirectoryError:
        return {"error": True, "status_code": 400, "message": f"{image_path} is a directory — pass the photo file"}
    except FileNotFoundError:
        return {"error": True, "status_code": 404, "message": f"image not found: {image_path}"}
    except ValueError as e:
        # gate-reported decode failure: which file, why
        return {"error": True, "status_code": 400, "message": str(e)}
    except ImportError as e:
        return {"error": True, "status_code": 500, "message": str(e)}
    except OSError as e:
        return {"error": True, "status_code": 400, "message": f"cannot read {image_path}: {e}"}


@mcp.tool(name="get_client_documents")
async def get_client_documents(client_id: int) -> Dict[str, Any]:
    """List the documents uploaded for a client."""
    auth = get_auth_header()
    return await make_request("GET", f"/self/clients/{client_id}/documents", auth=auth)


@mcp.tool(name="upload_client_document")
async def upload_client_document(
    client_id: int,
    image_path: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Gate-then-upload a photo as a client document.

    The capture-quality gate runs first: an unreadable (RETAKE) capture is
    refused with its reasons and is NOT sent to the bank, unless force=True;
    REVIEW verdicts upload but stay flagged in the capture_gate audit object.
    """
    gate = _gate_result(image_path)
    if gate.get("error"):
        return gate
    verdict = gate.get("verdict")
    if verdict is None:
        # fail closed: a gate result without a verdict never uploads
        return {"error": True, "status_code": 500, "message": f"capture gate could not assess {image_path}"}
    if verdict == VERDICT_RETAKE and not force:
        return {
            "error": True,
            "status_code": 400,
            "message": (
                f"Capture rejected ({verdict}): {'; '.join(gate['reasons'])}. "
                "The document was NOT uploaded — ask the user to take the photo again "
                "(a readable re-capture means the same document can pass)."
            ),
            "upload_rejected": True,
            "capture_gate": gate,
        }

    form: Dict[str, str] = {}
    if name:
        form["name"] = name
    if description:
        form["description"] = description
    if not form:
        form = {"name": os.path.basename(image_path)}

    result = await make_upload_request(
        "POST",
        f"/self/clients/{client_id}/documents",
        auth=get_auth_header(),
        form=form,
        file_path=image_path,
    )
    if result.get("error"):
        return result
    # the capture made it to Fineract: the gate verdict + signals ride along
    # so any upload past the gate stays auditable
    result["capture_gate"] = {k: gate[k] for k in ("verdict", "reasons", "signals") if k in gate}
    return result


@mcp.tool(name="verify_client_details")
async def verify_client_details(client_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Check details extracted from a document photo against the client's bank record.

    The vision model in the AI client extracts the fields from the photo
    (full_name / national_id / mobile_no — only these are comparable), then
    this tool fetches the client record from Fineract and compares each
    field deterministically: per-field MATCH / REVIEW / MISMATCH verdicts,
    an overall VERIFIED / NEEDS_REVIEW / FAILED result, and what each
    verdict was decided from. No LLM is involved in the comparison.
    """
    if not isinstance(fields, dict) or not any(str(v or "").strip() for v in fields.values()):
        return {
            "error": True,
            "status_code": 400,
            "message": (
                "fields must carry at least one non-empty extracted value " "(full_name, national_id, mobile_no)"
            ),
        }
    auth = get_auth_header()
    profile = await make_request("GET", f"/self/clients/{client_id}", auth=auth)
    if profile.get("error"):
        return profile
    return verify_fields(fields, profile)
