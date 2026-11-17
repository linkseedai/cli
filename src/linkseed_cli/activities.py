"""Learning-activity commands. They call the API and do not decide ownership."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import cast

from linkseed_cli.config import load_config
from linkseed_cli.http import ApiError, JsonObject, request_json, write_error

_POLL_SECONDS = 2.0
_POLL_LIMIT_SECONDS = 11 * 60


def list_activities(
    *,
    user_id: int | None,
    statuses: list[str] | None,
    mode: str | None,
    plan_type: str | None,
    query: str | None,
    updated_from: str | None,
    updated_to: str | None,
    limit: int | None,
    offset: int | None,
    as_json: bool,
) -> int:
    params = _query(
        user_id=user_id,
        statuses=statuses,
        mode=mode,
        plan_type=plan_type,
        query=query,
        updated_from=updated_from,
        updated_to=updated_to,
        limit=limit,
        offset=offset,
    )
    try:
        _status, payload = _request("GET", "/api/v1/me/activities", params=params)
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    if as_json:
        _print_json(payload)
        return 0
    return _print_table(payload)


def show_activity(
    activity_id: int,
    *,
    messages: bool,
    limit: int | None,
    offset: int | None,
    as_json: bool,
) -> int:
    if messages:
        return _show_messages(activity_id, limit=limit, offset=offset, as_json=as_json)
    try:
        _status, activity = _request("GET", f"/api/v1/me/activities/{activity_id}")
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    if as_json:
        _print_json(activity)
        return 0
    _print_activity(activity)
    return 0


def _show_messages(
    activity_id: int,
    *,
    limit: int | None,
    offset: int | None,
    as_json: bool,
) -> int:
    params: dict[str, str | int | list[str]] = {}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    if as_json:
        params["include_pen_points"] = "true"
    try:
        _status, payload = _request(
            "GET",
            f"/api/v1/me/activities/{activity_id}/messages",
            params=params or None,
        )
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    if as_json:
        _print_json(payload)
        return 0
    _print_messages(payload)
    return 0


def generate_evaluation(activity_id: int, *, wait: bool, as_json: bool) -> int:
    try:
        _status, started = _request("POST", f"/api/v1/me/activities/{activity_id}/evaluation")
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    if not wait:
        if as_json:
            _print_json(started)
        else:
            print("Evaluation started.")
        return 0
    payload = _poll_evaluation(activity_id)
    if isinstance(payload, int):
        return payload
    if as_json:
        _print_json(payload)
        return 0
    _print_activity(payload)
    return 0


def edit_evaluation(activity_id: int, *, file_path: str | None, as_json: bool) -> int:
    summary = _read_summary(file_path)
    if summary is None:
        return write_error(None, "Pass --file or pipe the evaluation text.")
    try:
        _status, activity = _request("GET", f"/api/v1/me/activities/{activity_id}")
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    expected = _expected_date(activity)
    if expected is None:
        return write_error(None, "This activity has no evaluation to edit.")
    try:
        _patch_status, payload = _request(
            "PATCH",
            f"/api/v1/me/activities/{activity_id}/evaluation",
            body={"summary": summary, "expected_date_updated": expected},
        )
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    if as_json:
        _print_json(payload)
        return 0
    body = _dict(payload)
    summary = body.get("summary") if body is not None else None
    print(summary if isinstance(summary, str) else "")
    return 0


def _request(
    method: str,
    path: str,
    *,
    body: JsonObject | None = None,
    params: dict[str, str | int | list[str]] | None = None,
) -> tuple[int, object]:
    base_url, token = _origin()
    return request_json(method, base_url, path, token=token, body=body, params=params)


def _origin() -> tuple[str, str | None]:
    base_url, token = load_config()
    if base_url is None or token is None:
        raise ApiError(None, "Not logged in.")
    return base_url, token


def _query(**values: str | int | list[str] | None) -> dict[str, str | int | list[str]]:
    params: dict[str, str | int | list[str]] = {}
    rename = {"query": "q", "statuses": "status", "plan_type": "plan_type", "updated_from": "updated_from", "updated_to": "updated_to", "user_id": "user_id"}
    for key, value in values.items():
        if value is None or value == []:
            continue
        params[rename.get(key, key)] = value
    return params


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _print_table(payload: object) -> int:
    body = _dict(payload)
    if body is None:
        return write_error(None, "Activity list was not a JSON object.")
    rows = body.get("activities")
    if not isinstance(rows, list):
        return write_error(None, "Activity list was not a JSON object.")
    print("id\tuser_id\tstatus\ttitle")
    for item in cast(list[object], rows):
        row = _dict(item)
        if row is None:
            continue
        print(f"{row.get('id')}\t{row.get('user_id')}\t{row.get('status')}\t{row.get('title') or ''}")
    return 0


def _print_activity(payload: object) -> None:
    row = _dict(payload)
    if row is None:
        return
    print(f"Activity {row.get('id')} ({row.get('status')})")
    evaluation = _dict(row.get("evaluation"))
    if evaluation is None:
        print("No evaluation.")
    else:
        summary = evaluation.get("summary")
        if isinstance(summary, str) and summary:
            print(summary)
    _print_stats(_dict(row.get("stats")))


_INPUT_LABELS = {
    "voice": "语音",
    "text": "文字",
    "pen": "笔迹",
    "voice_pen": "语音 笔迹",
    "unknown": "未知",
}


def _print_stats(stats: JsonObject | None) -> None:
    if stats is None:
        return
    print(f"消息 {stats.get('message_count')}")
    print(f"笔迹 {stats.get('pen_count')}")
    print(f"语音 {stats.get('voice_count')}")
    print(f"文字 {stats.get('text_count')}")
    print(f"系统异常 {stats.get('system_error_count')}")


def _print_messages(payload: object) -> None:
    body = _dict(payload)
    if body is None:
        return
    messages = body.get("messages")
    if not isinstance(messages, list):
        return
    for item in cast(list[object], messages):
        row = _dict(item)
        if row is None:
            continue
        kind = row.get("input_type")
        label = _INPUT_LABELS.get(kind, "未知") if isinstance(kind, str) else "未知"
        if row.get("system_error") is True:
            label = f"系统异常 {label}"
        print(f"[{row.get('id')}] {label} {row.get('query') or ''}")
        _print_pen_summary(row.get("pen"))
        answer = row.get("answer")
        if isinstance(answer, str) and answer:
            print(answer)


def _print_pen_summary(value: object) -> None:
    if not isinstance(value, list):
        return
    for item in cast(list[object], value):
        stroke = _dict(item)
        if stroke is None:
            continue
        images = stroke.get("image_urls")
        urls = [url for url in cast(list[object], images) if isinstance(url, str)] if isinstance(images, list) else []
        print(f"笔迹 {stroke.get('point_count')} 点 {' '.join(urls)}".rstrip())


def _poll_evaluation(activity_id: int) -> object | int:
    deadline = time.monotonic() + _POLL_LIMIT_SECONDS
    while True:
        try:
            _status, payload = _request("GET", f"/api/v1/me/activities/{activity_id}")
        except ApiError as exc:
            return write_error(exc.status, exc.detail)
        row = _dict(payload)
        evaluation = _dict(row.get("evaluation")) if row is not None else None
        if evaluation is not None:
            failure = _evaluation_failure(evaluation)
            if failure is not None:
                return failure
            if evaluation.get("status") == "published":
                return payload
        if time.monotonic() >= deadline:
            return write_error(None, "Evaluation is still running.", reason="evaluation_timeout")
        print("Waiting for the evaluation.", file=sys.stderr)
        time.sleep(_POLL_SECONDS)


def _evaluation_failure(evaluation: JsonObject) -> int | None:
    """Return an error exit when this poll is terminal and unsuccessful."""
    error = evaluation.get("error_msg")
    status = evaluation.get("status")
    if isinstance(error, str) and error.strip():
        detail = error.strip()
        if status == "published":
            detail = f"{detail} Previous review remains available."
        return write_error(None, detail, reason="evaluation_failed")
    if status == "archived":
        return write_error(
            None,
            "Evaluation was archived before generation completed.",
            reason="evaluation_archived",
        )
    if evaluation.get("is_stale") is True:
        return write_error(
            None,
            "Evaluation attempt expired; generate it again.",
            reason="evaluation_expired",
        )
    return None


def _expected_date(payload: object) -> str | None:
    row = _dict(payload)
    if row is None:
        return None
    evaluation = _dict(row.get("evaluation"))
    if evaluation is None:
        return None
    updated = evaluation.get("date_updated")
    if isinstance(updated, str) and updated:
        return updated
    return None


def _read_summary(file_path: str | None) -> str | None:
    if file_path is not None:
        return Path(file_path).read_text(encoding="utf-8")
    if sys.stdin.isatty():
        return None
    return sys.stdin.read()


def _dict(value: object) -> JsonObject | None:
    if isinstance(value, dict):
        return cast(JsonObject, value)
    return None
