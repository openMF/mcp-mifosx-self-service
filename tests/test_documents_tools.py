"""Document capture gate, upload and verify tools (routers/documents_tools.py).

The gate verdicts are checked on synthetic captures whose truth is known by
construction; the upload flow and the verification are checked with a
stubbed HTTP layer — no bank, no network.
"""

import io
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image, ImageDraw

from routers.documents_tools import (
    get_client_documents,
    upload_client_document,
    validate_capture_quality,
    verify_client_details,
)
from utils import verify_fields as vf
from utils.capture_gate import RETAKE_INK_MIN, REVIEW_SHARP_MIN, VERDICT_PASS, VERDICT_RETAKE

AUTH = "Basic dXNlcjE6cHdk"


def _png(pil_image):
    buf = io.BytesIO()
    pil_image.save(buf, "PNG")
    return buf.getvalue()


def _crisp_page():
    """Dark text-like strokes on white paper: a usable capture by construction."""
    im = Image.new("L", (512, 384), 245)
    d = ImageDraw.Draw(im)
    for i, y in enumerate(range(60, 340, 24)):
        d.line([(40, y), (100 + (i * 7) % 120, y)], fill=20, width=2)
        d.line([(200 + (i * 5) % 250, y + 6), (420, y + 6)], fill=40, width=3)
    return im


# ── capture gate ─────────────────────────────────────────────────────


def test_crisp_capture_passes(tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    p = tmp_path / "cap.png"
    p.write_bytes(_png(_crisp_page()))
    r = validate_capture_quality(str(p))
    assert r["verdict"] == VERDICT_PASS
    assert r["reasons"] == []
    assert r["signals"]["brightness"] > 0.5


def test_blank_capture_retakes_on_no_content(tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    p = tmp_path / "blank.png"
    p.write_bytes(_png(Image.new("L", (512, 384), 244)))
    r = validate_capture_quality(str(p))
    assert r["verdict"] == VERDICT_RETAKE
    assert any("content" in x for x in r["reasons"])
    assert r["signals"]["ink_ratio"] < RETAKE_INK_MIN


def test_dark_capture_retakes_on_too_dark(tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    arr = Image.eval(_crisp_page(), lambda px: int(px * 0.01))
    p = tmp_path / "dark.png"
    p.write_bytes(_png(arr))
    r = validate_capture_quality(str(p))
    assert r["verdict"] == VERDICT_RETAKE
    assert any("dark" in x for x in r["reasons"])


def test_readability_review_band_boundaries():
    from utils import capture_gate as cg

    def verdict(sharpness):
        return cg._decide(
            {
                "sharpness": sharpness,
                "contrast": 0.5,
                "ink_ratio": 0.01,
                "brightness": 0.95,
                "exposure": 0.45,
            }
        )[0]

    assert verdict(0.05) == VERDICT_RETAKE
    assert verdict(0.079) == VERDICT_RETAKE
    assert verdict(0.088) == "REVIEW"
    assert verdict(0.125) == "REVIEW"
    assert verdict(REVIEW_SHARP_MIN) == "PASS"


def test_gate_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    data = _png(_crisp_page())
    p = tmp_path / "cap.png"
    p.write_bytes(data)
    assert validate_capture_quality(str(p)) == validate_capture_quality(str(p))


def test_gate_error_shapes(tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    r = validate_capture_quality(str(tmp_path / "nope.png"))
    assert r["status_code"] == 404
    assert validate_capture_quality(str(tmp_path))["error"] is True
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"corrupt")
    r = validate_capture_quality(str(bad))
    assert r["error"] is True and "bad.png" in r["message"]


def test_gate_rejects_capture_outside_the_capture_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    r = validate_capture_quality("/etc/passwd")
    assert r["error"] is True and r["status_code"] == 400 and "capture directory not allowed" in r["message"]


def test_gate_refuses_every_capture_when_no_capture_dir_is_set(tmp_path, monkeypatch):
    # A crisp image in the server's working directory must not be readable without MIFOSX_CAPTURE_DIR
    monkeypatch.delenv("MIFOSX_CAPTURE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "id.png").write_bytes(_png(_crisp_page()))
    for path in ("id.png", str(tmp_path / "id.png")):
        r = validate_capture_quality(path)
        assert r["error"] is True and r["status_code"] == 400 and "capture directory not allowed" in r["message"]


# ── upload flow (stubbed bank) ───────────────────────────────────────


@pytest.mark.asyncio
@patch("routers.documents_tools.make_upload_request", new_callable=AsyncMock)
async def test_upload_refuses_when_no_capture_dir_is_set(mock_post, tmp_path, monkeypatch):
    monkeypatch.delenv("MIFOSX_CAPTURE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "id.png").write_bytes(_png(_crisp_page()))
    r = await upload_client_document(7, "id.png")
    mock_post.assert_not_awaited()
    assert r["error"] is True and "capture directory not allowed" in r["message"]


@pytest.mark.asyncio
@patch("routers.documents_tools.make_upload_request", new_callable=AsyncMock)
async def test_upload_refuses_retake_capture(mock_post, tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    p = tmp_path / "blank.png"
    p.write_bytes(_png(Image.new("L", (512, 384), 244)))
    r = await upload_client_document(7, str(p))
    mock_post.assert_not_awaited()  # the bank never sees an unreadable capture
    assert r["upload_rejected"] is True
    assert r["capture_gate"]["verdict"] == VERDICT_RETAKE
    assert "NOT uploaded" in r["message"]


@pytest.mark.asyncio
@patch("routers.documents_tools.make_upload_request", new_callable=AsyncMock)
@patch("routers.documents_tools.get_auth_header", return_value=AUTH)
async def test_upload_passes_gate_then_posts_multipart(mock_auth, mock_post, tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    mock_post.return_value = {"resourceId": 7, "documentId": 3}
    p = tmp_path / "good.png"
    p.write_bytes(_png(_crisp_page()))

    r = await upload_client_document(7, str(p), name="kyc-id")
    assert r["resourceId"] == 7
    assert r["capture_gate"]["verdict"] == VERDICT_PASS
    mock_post.assert_awaited_once_with(
        "POST",
        "/self/clients/7/documents",
        auth=AUTH,
        form={"name": "kyc-id"},
        file_path=str(p),
    )
    args, kwargs = mock_post.await_args
    assert kwargs["auth"] == AUTH


@pytest.mark.asyncio
@patch("routers.documents_tools.make_upload_request", new_callable=AsyncMock)
@patch("routers.documents_tools.get_auth_header", return_value=AUTH)
async def test_upload_force_overrides_retake(mock_auth, mock_post, tmp_path, monkeypatch):
    monkeypatch.setenv("MIFOSX_CAPTURE_DIR", str(tmp_path))
    mock_post.return_value = {"resourceId": 9}
    p = tmp_path / "blank.png"
    p.write_bytes(_png(Image.new("L", (512, 384), 244)))
    r = await upload_client_document(7, str(p), force=True)
    assert r["resourceId"] == 9
    assert r["capture_gate"]["verdict"] == VERDICT_RETAKE  # flagged, not hidden


@pytest.mark.asyncio
async def test_get_client_documents_calls_the_bank():
    with patch("routers.documents_tools.make_request", new_callable=AsyncMock) as mock_get, patch(
        "routers.documents_tools.get_auth_header", return_value=AUTH
    ):
        mock_get.return_value = [{"id": 3}]
        assert await get_client_documents(7) == [{"id": 3}]
        mock_get.assert_awaited_once_with("GET", "/self/clients/7/documents", auth=AUTH)


# ── verify_client_details ────────────────────────────────────────────


@pytest.mark.asyncio
@patch("routers.documents_tools.make_request", new_callable=AsyncMock)
@patch("routers.documents_tools.get_auth_header", return_value=AUTH)
async def test_verify_against_a_realistic_profile(mock_auth, mock_get):
    mock_get.return_value = {
        "id": 7,
        "displayName": "Reyyappa Reddy",
        "firstname": "Reyyappa",
        "lastname": "Reddy",
        "mobileNo": "9876543210",
        "identifiers": [{"documentKey": "AB-1234-5678"}],
    }
    r = await verify_client_details(
        7,
        {
            "full_name": "REDDY REYYAPPA",  # order-free token equality
            "national_id": "AB 1234 5678",  # punctuation-folded to the record
            "mobile_no": "+91 98765 43210",  # country-code tolerated
        },
    )
    mock_get.assert_awaited_once_with("GET", "/self/clients/7", auth=AUTH)
    assert r["overall"] == "VERIFIED" and r["verified"] is True
    assert all(v["verdict"] == "MATCH" for v in r["fields"].values())
    assert r["fields"]["national_id"]["source_value"] == "AB-1234-5678"


@pytest.mark.asyncio
@patch("routers.documents_tools.make_request", new_callable=AsyncMock)
@patch("routers.documents_tools.get_auth_header", return_value=AUTH)
async def test_verify_flags_wrong_id_as_failed(mock_auth, mock_get):
    mock_get.return_value = {
        "id": 7,
        "displayName": "Reyyappa Reddy",
        "firstname": "Reyyappa",
        "lastname": "Reddy",
        "identifiers": [{"documentKey": "AB-1234-5678"}],
    }
    r = await verify_client_details(7, {"national_id": "AB-9999-0000"})
    assert r["overall"] == "FAILED"
    assert r["fields"]["national_id"]["verdict"] == "MISMATCH"


@pytest.mark.asyncio
@patch("routers.documents_tools.make_request", new_callable=AsyncMock)
@patch("routers.documents_tools.get_auth_header", return_value=AUTH)
async def test_verify_send_close_names_to_human_review(mock_auth, mock_get):
    mock_get.return_value = {"id": 7, "displayName": "Reyyappa Reddy", "firstname": "Reyyappa", "lastname": "Reddy"}
    r = await verify_client_details(7, {"full_name": "Reyyapa Reddy"})  # OCR slip, one char
    assert r["overall"] == "NEEDS_REVIEW"
    assert r["fields"]["full_name"]["verdict"] == "REVIEW"


@pytest.mark.asyncio
@patch("routers.documents_tools.make_request", new_callable=AsyncMock)
@patch("routers.documents_tools.get_auth_header", return_value=AUTH)
async def test_verify_reports_missing_source_without_failing(mock_auth, mock_get):
    mock_get.return_value = {"id": 7, "displayName": "Reyyappa Reddy"}
    r = await verify_client_details(7, {"mobile_no": "9876543210"})
    assert r["overall"] == "NEEDS_REVIEW"
    assert r["fields"]["mobile_no"]["verdict"] == "NO_SOURCE_DATA"


@pytest.mark.asyncio
@patch("routers.documents_tools.make_request", new_callable=AsyncMock)
@patch("routers.documents_tools.get_auth_header", return_value=AUTH)
async def test_verify_propagates_bank_errors(mock_auth, mock_get):
    mock_get.return_value = {"error": True, "status_code": 404, "message": "not found"}
    r = await verify_client_details(999, {"full_name": "X"})
    assert r["status_code"] == 404


@pytest.mark.asyncio
@patch("routers.documents_tools.make_request", new_callable=AsyncMock)
@patch("routers.documents_tools.get_auth_header", return_value=AUTH)
async def test_verify_rejects_empty_fields(mock_auth, mock_get):
    r = await verify_client_details(7, {"full_name": ""})
    mock_get.assert_not_awaited()
    assert r["error"] is True and r["status_code"] == 400


# ── verify_fields unit corners ───────────────────────────────────────


def test_name_token_set_and_fold_rules():
    assert vf.compare_name("Reddy Reyyappa", ["Reyyappa Reddy"])[0] == "MATCH"
    assert vf.compare_name("reyyappa   reddy", ["Reyyappa Reddy"])[0] == "MATCH"
    # a partial extracted name is never an exact match — it goes to REVIEW
    assert vf.compare_name("Reyyappa Reddy", ["Reyyappa Kumar Reddy"])[0] == "REVIEW"
    assert vf.compare_name("Reddy Reyyappa", []) == ("MISMATCH", None)


def test_name_partial_vs_full_and_multi_source():
    # partial name (missing bank-name tokens) -> REVIEW, never MATCH
    assert vf.compare_name("John", ["John Smith"])[0] == "REVIEW"
    # ...but an exact source elsewhere in the list still MATCHes
    assert vf.compare_name("Janet Doe", ["Jane Doe", "Janet Doe"]) == ("MATCH", "Janet Doe")


def test_id_compare_is_exact_after_folding():
    assert vf.compare_id("ab 1234 5678", ["AB-1234-5678"]) == ("MATCH", "AB-1234-5678")
    assert vf.compare_id("AB12345678", ["AB-1234-5678"]) == ("MATCH", "AB-1234-5678")  # separators ignored
    assert vf.compare_id("AB1234567", ["AB-1234-5678"])[0] == "MISMATCH"  # no fuzzy IDs


def test_mobile_tolerates_country_code_but_short_core():
    assert vf.compare_mobile("+91 98765 43210", ["9876543210"])[0] == "MATCH"
    assert vf.compare_mobile("9876543210", ["+91 98765 43210"])[0] == "MATCH"
    assert vf.compare_mobile("32 10", ["9876543210"])[0] == "MISMATCH"  # too short to trust
    # no suffix/substring matching: a short extracted number never matches a longer bank one
    assert vf.compare_mobile("98765", ["9876543210"])[0] == "MISMATCH"


def test_overall_aggregation_rules():
    assert vf.verify_fields({}, {"displayName": "X"})["overall"] == "NOTHING_TO_VERIFY"
    r = vf.verify_fields(
        {"full_name": "X", "national_id": "Y", "mobile_no": "9"},
        {"displayName": "X", "documentKey": "Y", "mobileNo": "9"},
    )
    assert r["overall"] == "VERIFIED" and r["verified"] is True
