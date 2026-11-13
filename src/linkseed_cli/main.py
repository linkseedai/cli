"""Argument parsing for the Linkseed CLI."""

from __future__ import annotations

import argparse
import sys

from linkseed_cli.commands import login, logout, whoami


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(sys.argv[1:] if argv is None else argv))


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="linkseed")
    commands = parser.add_subparsers(dest="command", required=True)
    auth = commands.add_parser("auth")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)

    login_parser = auth_commands.add_parser("login")
    _ = login_parser.add_argument("--base-url")
    _ = login_parser.add_argument("--username")
    _ = login_parser.add_argument("--password", nargs="?", const="", default=None)
    _ = login_parser.add_argument("--directus-token", nargs="?", const="", default=None)
    _ = login_parser.add_argument("--json", action="store_true")

    whoami_parser = auth_commands.add_parser("whoami")
    _ = whoami_parser.add_argument("--json", action="store_true")

    logout_parser = auth_commands.add_parser("logout")
    _ = logout_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    command = cast_command(getattr(args, "command", None))
    if command != "auth":
        parser.error(f"unknown command {command}")
    auth_command = cast_command(getattr(args, "auth_command", None))
    if auth_command == "login":
        return login(
            base_url=_optional_str(getattr(args, "base_url", None)),
            username=_optional_str(getattr(args, "username", None)),
            password=_optional_str(getattr(args, "password", None)),
            directus_token=_optional_str(getattr(args, "directus_token", None)),
            as_json=bool(getattr(args, "json", False)),
        )
    if auth_command == "whoami":
        return whoami(as_json=bool(getattr(args, "json", False)))
    if auth_command == "logout":
        return logout(as_json=bool(getattr(args, "json", False)))
    parser.error(f"unknown auth command {auth_command}")


def cast_command(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def _optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None
