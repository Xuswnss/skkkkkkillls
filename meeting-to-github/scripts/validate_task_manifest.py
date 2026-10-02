#!/usr/bin/env python3

import argparse
import json
import re
import sys


_DATE_ONLY_BASIS = re.compile(
    r"^(?:"
    r"(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2})|"
    r"(?:\d{4}년\s*\d{1,2}월\s*\d{1,2}일)|"
    r"(?:same\s+)?date|"
    r"(?:같은\s*)?날짜"
    r")$",
    re.IGNORECASE,
)


def _present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return bool(value)
    return bool(value)


def _present_text(value):
    return isinstance(value, str) and _present(value)


def _present_list(value):
    return isinstance(value, list) and _present(value)


def _validate_shape(manifest):
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a JSON object")
    if "tasks" in manifest and not isinstance(manifest["tasks"], list):
        raise TypeError("tasks must be a JSON array")
    for task in manifest.get("tasks", []):
        if not isinstance(task, dict):
            raise TypeError("each task must be a JSON object")
        for key in ("relationship", "github"):
            value = task.get(key)
            if value is not None and not isinstance(value, dict):
                raise TypeError(f"task {key} must be a JSON object")


def _local_id(task):
    value = task.get("local_id")
    if isinstance(value, str) and value.strip():
        return value
    return "<missing>"


def _date_only_basis(value):
    return isinstance(value, str) and bool(_DATE_ONLY_BASIS.fullmatch(value.strip()))


def validate_manifest(manifest, mode="draft"):
    if mode not in {"draft", "mutation-ready"}:
        raise ValueError("mode must be draft or mutation-ready")
    _validate_shape(manifest)

    errors = []
    if manifest.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    for key in ("meeting_id", "source_record"):
        if not _present_text(manifest.get(key)):
            errors.append(f"missing top-level field: {key}")
    if not _present_list(manifest.get("tasks")):
        errors.append("missing top-level field: tasks")

    seen_ids = set()
    seen_numbers = set()
    seen_urls = set()
    for task in manifest.get("tasks", []):
        local_id = _local_id(task)
        if local_id == "<missing>":
            errors.append("missing local_id")
        elif local_id in seen_ids:
            errors.append(f"duplicate local_id: {local_id}")
        else:
            seen_ids.add(local_id)

        for key in ("title", "topic", "outcome"):
            if not _present_text(task.get(key)):
                errors.append(f"{local_id}: missing {key}")
        if not _present_list(task.get("evidence")):
            errors.append(f"{local_id}: missing evidence")

        if _present_text(task.get("owner_github")) and not _present_text(task.get("owner_name")):
            errors.append(f"{local_id}: GitHub owner exists without a confirmed owner name")

        relationship = task.get("relationship") or {}
        if not isinstance(relationship.get("approved"), bool):
            errors.append(f"{local_id}: relationship.approved must be boolean")

        parent = relationship.get("proposed_parent")
        if mode == "mutation-ready" and parent is not None:
            if relationship.get("approved") is not True:
                errors.append(f"{local_id}: proposed parent is not approved")
            if not _present_text(relationship.get("basis")):
                errors.append(f"{local_id}: approved parent requires a relationship basis")
        if _date_only_basis(relationship.get("basis")):
            errors.append(f"{local_id}: relationship basis requires user confirmation")

        if mode == "mutation-ready" and not _present_list(task.get("completion_criteria")):
            errors.append(f"{local_id}: completion criteria are required for mutation")

        github = task.get("github") or {}
        number = github.get("issue_number")
        url = github.get("url")
        if number is not None:
            if number in seen_numbers:
                errors.append(f"duplicate GitHub issue_number: {number}")
            seen_numbers.add(number)
        if _present_text(url):
            if url in seen_urls:
                errors.append(f"duplicate GitHub url: {url}")
            seen_urls.add(url)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a task manifest JSON file.")
    parser.add_argument("--input", required=True, help="path to manifest JSON")
    parser.add_argument(
        "--mode",
        choices=("draft", "mutation-ready"),
        default="draft",
        help="validation mode (default: draft)",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.input, encoding="utf-8") as input_file:
            manifest = json.load(input_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    try:
        errors = validate_manifest(manifest, mode=args.mode)
    except (TypeError, ValueError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
