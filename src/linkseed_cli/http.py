"""HTTP calls for the Linkseed CLI."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from typing import cast
from urllib.parse import urlsplit

import httpx

JsonObject = dict[str, object]
QueryParams = Mapping[str, str | int | Sequence[str]]


class ApiError(Exception):
    """The API responded with an error, or the request did not complete."""

    status: int | None
    detail: str

    def __init__(self, status: int | None, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def http_client() -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(30.0), trust_env=True, follow_redirects=False)


def write_error(status: int | None, detail: str, *, reason: str | None = None) -> int:
    """Print one JSON object to stderr and return the process exit code.

    `reason` marks an application outcome. A transport failure leaves it unset,
    so callers can tell a generation failure from an unreachable API.
    """
    body: dict[str, object] = {"status": status, "detail": detail}
    if reason is not None:
        body["reason"] = reason
    print(json.dumps(body, ensure_ascii=False), file=sys.stderr)
    return _exit_code(status)


def request_json(
    method: str,
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    body: JsonObject | None = None,
    params: QueryParams | None = None,
) -> tuple[int, object]:
    """Call the API and return the status code and JSON body. Errors raise `ApiError`."""
    _require_https_for_remote(base_url)
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with http_client() as client:
            response = client.request(
                method,
                base_url.rstrip("/") + path,
                headers=headers,
                json=body,
                params=params,
            )
    except httpx.HTTPError as exc:
        raise ApiError(None, "Could not reach the API.") from exc
    payload = _payload(response)
    if response.status_code >= 400:
        raise ApiError(response.status_code, _detail(payload))
    return response.status_code, payload


def _require_https_for_remote(base_url: str) -> None:
    """Reject remote http:// so passwords and tokens are not sent in cleartext."""
    parts = urlsplit(base_url.strip())
    host = (parts.hostname or "").rstrip(".").lower()
    if parts.scheme == "https" and host:
        return
    if parts.scheme == "http" and host in {"localhost", "127.0.0.1", "::1"}:
        return
    raise ApiError(None, "Use an https:// address for the API.")


def _exit_code(status: int | None) -> int:
    if status == 401:
        return 2
    if status == 404:
        return 3
    if status in {409, 422}:
        return 4
    return 1


def _payload(response: httpx.Response) -> object:
    if not response.content:
        return None
    try:
        return cast(object, response.json())
    except ValueError:
        return None


def _detail(payload: object) -> str:
    if isinstance(payload, dict):
        detail = cast(JsonObject, payload).get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail
    return "Request failed."
