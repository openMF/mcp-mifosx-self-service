import os

import httpx
from typing import Optional, Dict, Any
from config.config import BASE_URL, API_BASE_PATH, DEFAULT_TENANT
from utils.errors import api_error


async def make_request(
    method: str,
    endpoint: str,
    auth: Optional[str] = None,
    data: Optional[Dict] = None,
    tenant: str = DEFAULT_TENANT,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Make HTTP request to the API. `headers` are extra request headers (e.g. a step-up token)."""
    url = f"{BASE_URL}{API_BASE_PATH}{endpoint}"
    request_headers = {
        "Fineract-Platform-TenantId": tenant,
        "Content-Type": "application/json",
    }
    if headers:
        request_headers.update(headers)

    if auth:
        request_headers["Authorization"] = auth

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method=method, url=url, headers=request_headers, json=data)

            if response.status_code >= 400:
                return api_error(response.status_code, response.text)

            try:
                return response.json()
            except ValueError:
                return {"message": "Success", "status_code": response.status_code}

    except httpx.TimeoutException:
        return {"error": True, "status_code": 408, "message": f"Request timed out for {method} {url}"}
    except httpx.ConnectError:
        return {"error": True, "status_code": 503, "message": f"Cannot connect to server: {url}"}
    except Exception as e:
        return {"error": True, "status_code": 500, "message": str(e)}


async def make_upload_request(
    method: str,
    endpoint: str,
    auth: Optional[str] = None,
    form: Optional[Dict[str, str]] = None,
    file_path: str = "",
    tenant: str = DEFAULT_TENANT,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Make a multipart HTTP request (file upload, e.g. client documents).

    ``form`` carries the string fields Fineract expects alongside the file
    (name/description); the file goes out under the part name ``file``,
    which is what Fineract's document upload endpoints read.

    The Content-Type header is deliberately left out: the multipart
    boundary only exists once httpx encodes the body. Error shapes mirror
    ``make_request`` so callers learn one convention.
    """
    url = f"{BASE_URL}{API_BASE_PATH}{endpoint}"
    request_headers = {"Fineract-Platform-TenantId": tenant}
    if headers:
        request_headers.update(headers)
    if auth:
        request_headers["Authorization"] = auth
    if not file_path:
        return api_error(400, "no file provided to upload")
    if not os.path.isfile(file_path):
        return api_error(404, f"file not found: {file_path}")

    try:
        with open(file_path, "rb") as fh:
            content = fh.read()
        if not content:
            return api_error(400, f"{file_path} is empty")
        if len(content) > 40 * 1024 * 1024:
            return api_error(400, f"{file_path} is over 40 MB — compress or retake the capture")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                data=form or {},
                files={"file": (os.path.basename(file_path), content)},
            )

            if response.status_code >= 400:
                return api_error(response.status_code, response.text)
            try:
                return response.json()
            except ValueError:
                return {"message": "Success", "status_code": response.status_code}

    except httpx.TimeoutException:
        return {"error": True, "status_code": 408, "message": f"Request timed out for {method} {url}"}
    except httpx.ConnectError:
        return {"error": True, "status_code": 503, "message": f"Cannot connect to server: {url}"}
    except OSError as e:
        return api_error(400, f"cannot read {file_path}: {str(e)}")
    except Exception as e:
        return {"error": True, "status_code": 500, "message": str(e)}
