"""`linkseed auth` commands."""

from __future__ import annotations

import getpass
import json
import sys
from typing import cast

from linkseed_cli.config import load_config, save_config
from linkseed_cli.http import ApiError, JsonObject, request_json, write_error

CLI_CLIENT_ID = "linkseed-cli"
_LOGIN_PATH = "/api/v1/auth/login"
_ME_PATH = "/api/v1/auth/cli/me"
_LOGOUT_PATH = "/api/v1/auth/logout"


def login(
    *,
    base_url: str | None,
    username: str | None,
    password: str | None,
    directus_token: str | None,
    as_json: bool,
) -> int:
    """Store one access token after a password login or a Directus token check."""
    origin = _origin(base_url)
    if origin is None:
        return write_error(None, "base_url is required. Set LINKSEED_API_BASE_URL or pass --base-url.")
    password_login = username is not None or password is not None
    if password_login and directus_token is not None:
        return write_error(None, "Pass either --username and --password, or --directus-token.")
    if directus_token is not None:
        token = directus_token.strip()
        if not token:
            entered = _prompt_secret("Access token: ")
            token = entered.strip() if entered is not None else ""
        if not token:
            return write_error(None, "Pass --directus-token, or type it in a terminal.")
        return _login_with_directus(origin, token, as_json=as_json)
    if username is None or not username.strip():
        return write_error(None, "Pass --username and --password, or --directus-token.")
    secret = password if password else _prompt_secret("Password: ")
    if secret is None:
        return write_error(None, "Pass --password, or type it in a terminal.")
    password = secret
    try:
        _status, payload = request_json(
            "POST",
            origin,
            _LOGIN_PATH,
            body={
                "username": username,
                "password": password,
                "client_id": CLI_CLIENT_ID,
            },
        )
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    token = _access_token(payload)
    if token is None:
        return write_error(None, "Login response did not include an access token.")
    save_config(origin, token)
    return _print_identity(payload, as_json=as_json)


def whoami(*, as_json: bool) -> int:
    origin, token = load_config()
    if origin is None or token is None:
        return write_error(None, "Not logged in.")
    try:
        _status, payload = request_json("GET", origin, _ME_PATH, token=token)
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    return _print_identity(payload, as_json=as_json)


def logout(*, as_json: bool) -> int:
    origin, token = load_config()
    if origin is None or token is None:
        return write_error(None, "Not logged in.")
    try:
        _ = request_json("POST", origin, _LOGOUT_PATH, token=token)
    except ApiError as exc:
        if exc.status == 401:
            save_config(origin, None)
        return write_error(exc.status, exc.detail)
    save_config(origin, None)
    if as_json:
        print("null")
    else:
        print("Logged out.")
    return 0


def _login_with_directus(origin: str, token: str, *, as_json: bool) -> int:
    try:
        _status, payload = request_json("GET", origin, _ME_PATH, token=token)
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    save_config(origin, token)
    return _print_identity(payload, as_json=as_json)


def _origin(base_url: str | None) -> str | None:
    if base_url is not None and base_url.strip():
        return base_url.strip().rstrip("/")
    stored, _token = load_config()
    return stored


def _access_token(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    token = cast(JsonObject, payload).get("access_token")
    if isinstance(token, str) and token.strip():
        return token
    return None


def _prompt_secret(label: str) -> str | None:
    if not sys.stdin.isatty():
        return None
    value = getpass.getpass(label)
    if not value.strip():
        return None
    return value


def _public_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    body = dict(cast(JsonObject, payload))
    _ = body.pop("access_token", None)
    return body


def _print_identity(payload: object, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(_public_payload(payload), ensure_ascii=False))
        return 0
    if not isinstance(payload, dict):
        return write_error(None, "Authentication response was not a JSON object.")
    body = cast(JsonObject, payload)
    user_id = body.get("user_id")
    link = body.get("directus_link")
    print(f"Logged in as user {user_id} (directus_link={link}).")
    return 0
