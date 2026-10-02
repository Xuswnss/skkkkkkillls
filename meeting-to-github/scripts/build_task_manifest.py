#!/usr/bin/env python3

import argparse
from copy import deepcopy
import json
import sys


def build_manifest(meeting_id, source_record, pdf, tasks):
    return {
        "schema_version": "1.0",
        "meeting_id": meeting_id,
        "source_record": source_record,
        "pdf": pdf,
        "tasks": deepcopy(tasks),
    }


def main():
    parser = argparse.ArgumentParser(description="Build a task manifest JSON file.")
    parser.add_argument("--meeting-id", required=True, help="meeting identifier")
    parser.add_argument(
        "--source-record",
        required=True,
        help="approved Markdown meeting record path",
    )
    parser.add_argument(
        "--pdf",
        default=None,
        help="approved PDF path or accessible URL",
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="task candidate JSON array file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="output manifest JSON file",
    )
    args = parser.parse_args()

    try:
        with open(args.tasks, encoding="utf-8") as tasks_file:
            tasks = json.load(tasks_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    if not isinstance(tasks, list):
        print("input error: tasks must be a JSON array", file=sys.stderr)
        return 2

    manifest = build_manifest(args.meeting_id, args.source_record, args.pdf, tasks)
    try:
        with open(args.output, "w", encoding="utf-8") as output_file:
            json.dump(manifest, output_file, ensure_ascii=False, indent=2)
            output_file.write("\n")
    except (OSError, UnicodeError) as exc:
        print(f"output error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
