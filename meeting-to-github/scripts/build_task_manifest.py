#!/usr/bin/env python3

import argparse
from copy import deepcopy
import json


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
    parser.add_argument("--meeting-id", required=True)
    parser.add_argument("--source-record", required=True)
    parser.add_argument("--pdf", default=None)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.tasks, encoding="utf-8") as tasks_file:
        tasks = json.load(tasks_file)

    manifest = build_manifest(args.meeting_id, args.source_record, args.pdf, tasks)
    with open(args.output, "w", encoding="utf-8") as output_file:
        json.dump(manifest, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
