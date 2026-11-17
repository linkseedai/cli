"""Local CLI configuration. One file holds the API origin and a single access token."""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import cast


def config_path() -> Path:
    override = os.environ.get("LINKSEED_CONFIG", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".config" / "linkseed" / "config.toml"


def load_config() -> tuple[str | None, str | None]:
    """Return the base URL and access token. Environment variables win over the file."""
    file_base, file_token = _read_file(config_path())
    env_base = os.environ.get("LINKSEED_API_BASE_URL", "").strip()
    env_token = os.environ.get("LINKSEED_TOKEN", "").strip()
    base = env_base or file_base
    token = env_token or file_token
    return (base or None, token or None)


def save_config(base_url: str, access_token: str | None) -> None:
    """Atomically write config (0600 on POSIX; inherited directory ACL on Windows). `access_token` is omitted when None."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(path.name + ".tmp")
    payload = _render(base_url, access_token).encode("utf-8")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        _ = os.write(descriptor, payload)
    finally:
        os.close(descriptor)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def _render(base_url: str, access_token: str | None) -> str:
    lines = [f"base_url = {_toml_string(base_url)}"]
    if access_token:
        lines.append(f"access_token = {_toml_string(access_token)}")
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    """JSON basic strings are valid TOML basic strings, including ``\\u`` escapes."""
    return json.dumps(value, ensure_ascii=True)


def _read_file(path: Path) -> tuple[str | None, str | None]:
    if not path.is_file():
        return None, None
    with path.open("rb") as handle:
        parsed = tomllib.load(handle)
    body = cast(dict[str, object], parsed)
    return _string(body.get("base_url")), _string(body.get("access_token"))


def _string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
