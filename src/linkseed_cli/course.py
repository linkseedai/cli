"""Snap a question image, confirm it, and create or relearn a course."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO, cast

from linkseed_cli.config import load_config
from linkseed_cli.http import (
    LONG_RUNNING_TIMEOUT_SECONDS,
    ApiError,
    JsonObject,
    request_json,
    request_multipart,
    write_error,
)

_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}
_COURSE_MODES = {"teaching", "tutoring"}
_TEACHING_MODES = {"voice_only", "voice_pen"}
_TOPIC_STRATEGY_IDS = {"sum_multiple"}


def snap_image(
    image_path: str,
    *,
    out_path: str | None,
    create: bool,
    assume_yes: bool,
    course_mode: str | None,
    teaching_mode: str | None,
    grade_level: str | None,
    topic_strategy_id: str | None,
    as_json: bool,
) -> int:
    if not create and any(
        value is not None for value in (course_mode, teaching_mode, grade_level, topic_strategy_id)
    ):
        return write_error(None, "Pass --create to choose how the course is created.")
    if assume_yes and not create:
        return write_error(None, "Pass --create together with --yes.")
    pending = _pending_course(
        course_mode=course_mode,
        teaching_mode=teaching_mode,
        grade_level=grade_level,
        topic_strategy_id=topic_strategy_id,
    )
    if isinstance(pending, int):
        return pending
    image = _read_image(image_path)
    if isinstance(image, int):
        return image
    filename, content, content_type = image
    try:
        _status, payload = _request_multipart(
            "/api/v1/course/snap",
            filename=filename,
            content=content,
            content_type=content_type,
        )
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    body = _dict(payload)
    if body is None:
        return write_error(None, "Snap response was not a JSON object.")
    if out_path is not None:
        written = _write_question(out_path, body)
        if written is not None:
            return written
    failed = _failed_extraction(body)
    if failed is not None:
        return failed
    if not create:
        if as_json:
            _print_json(body)
        else:
            print(_summary(body, image_path=image_path, pending=None))
        return 0
    assert pending is not None
    resolved = _with_grade(pending, _text(body.get("recommended_grade_level")))
    if as_json:
        _print_pending(resolved, sys.stderr)
    else:
        print(_summary(body, image_path=image_path, pending=resolved))
    confirmed = _confirm(assume_yes=assume_yes, as_json=as_json)
    if confirmed is not None:
        return confirmed
    return _create_from_question(_question_text(body), resolved, as_json=as_json)


def create_course(
    *,
    question_file: str | None,
    learning_plan_id: int | None,
    course_mode: str | None,
    teaching_mode: str | None,
    grade_level: str | None,
    topic_strategy_id: str | None,
    as_json: bool,
) -> int:
    has_file = question_file is not None
    has_plan = learning_plan_id is not None
    if has_file == has_plan:
        return write_error(None, "Pass exactly one of --question-file or --learning-plan-id.")
    pending = _pending_course(
        course_mode=course_mode,
        teaching_mode=teaching_mode,
        grade_level=grade_level,
        topic_strategy_id=topic_strategy_id,
    )
    if isinstance(pending, int):
        return pending
    if question_file is not None:
        loaded = _load_question(question_file)
        if isinstance(loaded, int):
            return loaded
        text, body = loaded
        failed = _failed_extraction(body)
        if failed is not None:
            return failed
        resolved = _with_grade(pending, _text(body.get("recommended_grade_level")))
        return _create_from_question(text, resolved, as_json=as_json)
    assert learning_plan_id is not None
    if learning_plan_id < 1:
        return write_error(None, "Learning plan id must be a positive integer.")
    return _post_course(
        _course_body(pending, learning_plan_id=learning_plan_id, question_json=None),
        source_course_id=None,
        as_json=as_json,
    )


def relearn_course(course_id: int, *, as_json: bool) -> int:
    if course_id < 1:
        return write_error(None, "Course id must be a positive integer.")
    try:
        _status, payload = _request("POST", f"/api/v1/course/{course_id}/relearn", timeout=None)
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    if as_json:
        _print_json(payload)
        return 0
    _print_course(payload, source_course_id=course_id)
    return 0


def _pending_course(
    *,
    course_mode: str | None,
    teaching_mode: str | None,
    grade_level: str | None,
    topic_strategy_id: str | None,
) -> _Pending | int:
    mode = course_mode or "teaching"
    if mode not in _COURSE_MODES:
        return write_error(None, "Pass --course-mode teaching or tutoring.")
    if mode == "tutoring" and teaching_mode is not None and teaching_mode != "voice_pen":
        return write_error(None, "Tutoring courses use teaching mode voice_pen.")
    lesson = "voice_pen" if mode == "tutoring" else (teaching_mode or "voice_only")
    if lesson not in _TEACHING_MODES:
        return write_error(None, "Pass --teaching-mode voice_only or voice_pen.")
    topic = _text(topic_strategy_id)
    if topic is not None and topic not in _TOPIC_STRATEGY_IDS:
        return write_error(None, "Unknown topic strategy.")
    return _Pending(
        course_mode=mode,
        teaching_mode=lesson,
        grade_level=_text(grade_level),
        topic_strategy_id=topic,
    )


def _with_grade(pending: _Pending, recommended: str | None) -> _Pending:
    if pending.grade_level is not None:
        return pending
    return _Pending(
        course_mode=pending.course_mode,
        teaching_mode=pending.teaching_mode,
        grade_level=recommended,
        topic_strategy_id=pending.topic_strategy_id,
    )


def _read_image(image_path: str) -> tuple[str, bytes, str] | int:
    path = Path(image_path)
    content_type = _IMAGE_TYPES.get(path.suffix.lower())
    if content_type is None:
        return write_error(None, "Use a jpg, jpeg, png, webp, or bmp image.")
    if not path.is_file():
        return write_error(None, "Image file not found.")
    return path.name, path.read_bytes(), content_type


def _load_question(path: str) -> tuple[str, JsonObject] | int:
    file_path = Path(path)
    if not file_path.is_file():
        return write_error(None, "Question file not found.")
    text = file_path.read_text(encoding="utf-8")
    body = _parse_question(text)
    if isinstance(body, int):
        return body
    return text, body


def _parse_question(text: str) -> JsonObject | int:
    try:
        parsed = cast(object, json.loads(text))
    except json.JSONDecodeError:
        return write_error(None, "Question file is not a JSON object.")
    body = _dict(parsed)
    if body is None:
        return write_error(None, "Question file is not a JSON object.")
    return body


def _failed_extraction(body: JsonObject) -> int | None:
    if body.get("extraction_status") != "failed":
        return None
    reason = _text(body.get("failure_reason")) or "Question extraction failed."
    return write_error(422, reason)


def _write_question(path: str, body: JsonObject) -> int | None:
    try:
        _ = Path(path).write_text(_question_text(body), encoding="utf-8")
    except OSError as exc:
        return write_error(None, f"Could not write the question file: {exc.strerror or exc}.")
    return None


def _question_text(body: JsonObject) -> str:
    return json.dumps(body, ensure_ascii=False, indent=2) + "\n"


def _create_from_question(question_json: str, pending: _Pending, *, as_json: bool) -> int:
    return _post_course(
        _course_body(pending, learning_plan_id=None, question_json=question_json),
        source_course_id=None,
        as_json=as_json,
    )


def _post_course(body: JsonObject, *, source_course_id: int | None, as_json: bool) -> int:
    try:
        _status, payload = _request(
            "POST",
            "/api/v1/course/create",
            body=body,
            timeout=LONG_RUNNING_TIMEOUT_SECONDS,
        )
    except ApiError as exc:
        return write_error(exc.status, exc.detail)
    if as_json:
        _print_json(payload)
        return 0
    _print_course(payload, source_course_id=source_course_id)
    return 0


def _course_body(
    pending: _Pending,
    *,
    learning_plan_id: int | None,
    question_json: str | None,
) -> JsonObject:
    body: JsonObject = {
        "ai_agent": "tutor",
        "course_mode": pending.course_mode,
        "teaching_mode": pending.teaching_mode,
    }
    if learning_plan_id is not None:
        body["learning_plan_id"] = learning_plan_id
    if question_json is not None:
        body["question_json"] = question_json
    if pending.grade_level is not None:
        body["grade_level"] = pending.grade_level
    if pending.topic_strategy_id is not None:
        body["topic_strategy_id"] = pending.topic_strategy_id
    return body


def _confirm(*, assume_yes: bool, as_json: bool) -> int | None:
    if assume_yes:
        return None
    if not sys.stdin.isatty():
        return write_error(None, "Pass --yes, or run course create --question-file.")
    print("创建这门课程？[y/N]", file=sys.stderr)
    answer = sys.stdin.readline().strip().lower()
    if answer in {"y", "yes"}:
        return None
    print("未创建课程。", file=sys.stderr)
    if as_json:
        _print_json({"created": False})
    return 0


def _summary(body: JsonObject, *, image_path: str, pending: _Pending | None) -> str:
    question = _dict(body.get("question")) or {}
    lines: list[str] = []
    number = _text(body.get("question_number"))
    if number is not None:
        lines.append(f"题号：{number}")
    grade = _grade_line(_text(body.get("recommended_grade_level")), _text(body.get("recommended_grade_reason")))
    if grade is not None:
        lines.append(grade)
    confidence = _confidence(body.get("extraction_confidence"))
    if confidence is not None:
        lines.append(f"置信度：{confidence}")
    _append_blocks(lines, "题干", question.get("stem"))
    _append_options(lines, question.get("options"))
    _append_value(lines, "答案", question.get("answer"))
    _append_blocks(lines, "解析", question.get("analysis"))
    notes = _text(body.get("notes"))
    if notes is not None:
        lines.append(f"说明：{notes}")
    lines.extend(_image_lines(image_path, question.get("attachments")))
    _append_observed(lines, body)
    if pending is not None:
        lines.extend(_pending_lines(pending))
    return "\n".join(lines)


def _print_pending(pending: _Pending, stream: TextIO) -> None:
    print("\n".join(_pending_lines(pending)), file=stream)


def _pending_lines(pending: _Pending) -> list[str]:
    lines = [
        f"课程模式：{pending.course_mode}",
        f"教学模式：{pending.teaching_mode}",
    ]
    if pending.grade_level is not None:
        lines.append(f"提交年级：{pending.grade_level}")
    if pending.topic_strategy_id is not None:
        lines.append(f"题目策略：{pending.topic_strategy_id}")
    return lines


def _grade_line(level: str | None, reason: str | None) -> str | None:
    if level is None and reason is None:
        return None
    if level is None:
        return f"年级：{reason}"
    if reason is None:
        return f"年级：{level}"
    return f"年级：{level}（{reason}）"


def _append_blocks(lines: list[str], label: str, content: object) -> None:
    rendered = _block_lines(content)
    if not rendered:
        return
    lines.append(f"{label}：")
    lines.extend(rendered)


def _append_value(lines: list[str], label: str, content: object) -> None:
    if isinstance(content, str) and content.strip():
        lines.append(f"{label}：{content.strip()}")
        return
    _append_blocks(lines, label, content)


def _append_options(lines: list[str], content: object) -> None:
    if not isinstance(content, list):
        return
    rendered = [item.strip() for item in cast(list[object], content) if isinstance(item, str) and item.strip()]
    if not rendered:
        return
    lines.append("选项：")
    lines.extend(rendered)


def _append_observed(lines: list[str], body: JsonObject) -> None:
    student = _text(body.get("observed_student_answer"))
    reference = _text(body.get("observed_reference_answer"))
    analysis = _block_lines(body.get("observed_reference_analysis"))
    if student is None and reference is None and not analysis:
        return
    lines.append("识别到的作答：")
    if student is not None:
        lines.append(f"学生作答：{student}")
    if reference is not None:
        lines.append(f"参考答案：{reference}")
    if analysis:
        lines.append("参考解析：")
        lines.extend(analysis)


def _image_lines(image_path: str, attachments: object) -> list[str]:
    lines = ["图片：", f"本地：{image_path}"]
    if not isinstance(attachments, list):
        return lines
    for item in cast(list[object], attachments):
        attachment = _dict(item)
        if attachment is None:
            continue
        label = _attachment_label(attachment.get("sort"))
        url = _text(attachment.get("url"))
        svg_url = _text(attachment.get("svg_url"))
        if url is not None:
            lines.append(f"{label}：{url}")
        if svg_url is not None:
            lines.append(f"{label} SVG：{svg_url}")
    return lines


def _attachment_label(sort: object) -> str:
    if not isinstance(sort, int) or isinstance(sort, bool) or sort <= 0:
        return "题干"
    index = sort - 1
    if index < 26:
        return f"选项 {chr(ord('A') + index)}"
    return f"选项 {sort}"


def _block_lines(content: object) -> list[str]:
    if isinstance(content, str):
        text = content.strip()
        return [text] if text else []
    if isinstance(content, list):
        lines: list[str] = []
        for item in cast(list[object], content):
            lines.extend(_block_lines(item))
        return lines
    block = _dict(content)
    if block is None:
        return []
    latex = _text(block.get("latex"))
    if block.get("type") == "math" or latex is not None:
        return [latex] if latex is not None else []
    value = _text(block.get("value"))
    return [value] if value is not None else []


def _print_course(payload: object, *, source_course_id: int | None) -> None:
    body = _dict(payload)
    if body is None:
        print("课程已创建。")
        return
    course_id = body.get("course_id")
    plan_id = body.get("learning_plan_id")
    if isinstance(course_id, int) and not isinstance(course_id, bool):
        print(f"课程 {course_id}")
    if isinstance(plan_id, int) and not isinstance(plan_id, bool):
        print(f"学案 {plan_id}")
    teaching_mode = _text(body.get("teaching_mode"))
    course_mode = _text(body.get("course_mode"))
    if teaching_mode is not None:
        print(f"教学模式 {teaching_mode}")
    if course_mode is not None:
        print(f"课程模式 {course_mode}")
    if source_course_id is not None:
        print(f"来自课程 {source_course_id}")
    if isinstance(course_id, int) and not isinstance(course_id, bool):
        print(f"在 App 中用课程编号 {course_id} 打开这门课。")


def _confidence(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return format(value, "g")


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _request(
    method: str,
    path: str,
    *,
    body: JsonObject | None = None,
    timeout: float | None,
) -> tuple[int, object]:
    base_url, token = _origin()
    return request_json(method, base_url, path, token=token, body=body, timeout=timeout)


def _request_multipart(
    path: str,
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> tuple[int, object]:
    base_url, token = _origin()
    return request_multipart(
        "POST",
        base_url,
        path,
        token=token,
        file_field="image",
        filename=filename,
        content=content,
        content_type=content_type,
        timeout=LONG_RUNNING_TIMEOUT_SECONDS,
    )


def _origin() -> tuple[str, str | None]:
    base_url, token = load_config()
    if base_url is None or token is None:
        raise ApiError(None, "Not logged in.")
    return base_url, token


def _dict(value: object) -> JsonObject | None:
    if isinstance(value, dict):
        return cast(JsonObject, value)
    return None


class _Pending:
    course_mode: str
    teaching_mode: str
    grade_level: str | None
    topic_strategy_id: str | None

    def __init__(
        self,
        *,
        course_mode: str,
        teaching_mode: str,
        grade_level: str | None,
        topic_strategy_id: str | None,
    ) -> None:
        self.course_mode = course_mode
        self.teaching_mode = teaching_mode
        self.grade_level = grade_level
        self.topic_strategy_id = topic_strategy_id
