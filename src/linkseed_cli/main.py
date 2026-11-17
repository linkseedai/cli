"""Argument parsing for the Linkseed CLI."""

from __future__ import annotations

import argparse
import sys
from typing import cast

from linkseed_cli.activities import edit_evaluation, generate_evaluation, list_activities, show_activity
from linkseed_cli.commands import login, logout, whoami
from linkseed_cli.http import write_error


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

    activities = commands.add_parser("activities")
    activity_commands = activities.add_subparsers(dest="activity_command", required=True)
    list_parser = activity_commands.add_parser("list")
    _ = list_parser.add_argument("--user-id", type=int)
    _ = list_parser.add_argument("--status", action="append")
    _ = list_parser.add_argument("--mode")
    _ = list_parser.add_argument("--plan-type")
    _ = list_parser.add_argument("--query")
    _ = list_parser.add_argument("--updated-from")
    _ = list_parser.add_argument("--updated-to")
    _ = list_parser.add_argument("--limit", type=int)
    _ = list_parser.add_argument("--offset", type=int)
    _ = list_parser.add_argument("--json", action="store_true")

    show_parser = activity_commands.add_parser("show")
    _ = show_parser.add_argument("activity_id", type=int)
    _ = show_parser.add_argument("--messages", action="store_true")
    _ = show_parser.add_argument("--limit", type=int)
    _ = show_parser.add_argument("--offset", type=int)
    _ = show_parser.add_argument("--json", action="store_true")

    evaluation = activity_commands.add_parser("evaluation")
    evaluation_commands = evaluation.add_subparsers(dest="evaluation_command", required=True)
    generate_parser = evaluation_commands.add_parser("generate")
    _ = generate_parser.add_argument("activity_id", type=int)
    _ = generate_parser.add_argument("--no-wait", action="store_true")
    _ = generate_parser.add_argument("--json", action="store_true")
    edit_parser = evaluation_commands.add_parser("edit")
    _ = edit_parser.add_argument("activity_id", type=int)
    _ = edit_parser.add_argument("--file")
    _ = edit_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    command = cast_command(getattr(args, "command", None))
    if command == "activities":
        return _run_activity(args)
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


def _run_activity(args: argparse.Namespace) -> int:
    activity_command = cast_command(getattr(args, "activity_command", None))
    if activity_command == "list":
        statuses = getattr(args, "status", None)
        status_values = (
            [item for item in cast(list[object], statuses) if isinstance(item, str)]
            if isinstance(statuses, list)
            else None
        )
        return list_activities(
            user_id=_optional_int(getattr(args, "user_id", None)),
            statuses=status_values,
            mode=_optional_str(getattr(args, "mode", None)),
            plan_type=_optional_str(getattr(args, "plan_type", None)),
            query=_optional_str(getattr(args, "query", None)),
            updated_from=_optional_str(getattr(args, "updated_from", None)),
            updated_to=_optional_str(getattr(args, "updated_to", None)),
            limit=_optional_int(getattr(args, "limit", None)),
            offset=_optional_int(getattr(args, "offset", None)),
            as_json=bool(getattr(args, "json", False)),
        )
    activity_id = _optional_int(getattr(args, "activity_id", None))
    if activity_id is None:
        raise SystemExit("activity id is required")
    if activity_command == "show":
        limit = _optional_int(getattr(args, "limit", None))
        offset = _optional_int(getattr(args, "offset", None))
        messages = bool(getattr(args, "messages", False))
        if not messages and (limit is not None or offset is not None):
            return write_error(None, "Pass --messages to page through messages.")
        return show_activity(
            activity_id,
            messages=messages,
            limit=limit,
            offset=offset,
            as_json=bool(getattr(args, "json", False)),
        )
    if activity_command == "evaluation":
        evaluation_command = cast_command(getattr(args, "evaluation_command", None))
        if evaluation_command == "generate":
            return generate_evaluation(
                activity_id,
                wait=not bool(getattr(args, "no_wait", False)),
                as_json=bool(getattr(args, "json", False)),
            )
        if evaluation_command == "edit":
            return edit_evaluation(
                activity_id,
                file_path=_optional_str(getattr(args, "file", None)),
                as_json=bool(getattr(args, "json", False)),
            )
    raise SystemExit(f"unknown activity command {activity_command}")


def cast_command(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None
