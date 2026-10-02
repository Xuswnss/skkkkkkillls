#!/usr/bin/env python3

import argparse
from datetime import datetime
import hashlib
import json
import re
import sys


_SCHEMA_VERSION = "2.0"
_MUTATION_MODES = {"mutation-ready", "retry-ready"}
_APPROVAL_KINDS = ("source_record", "pdf", "task_candidates", "bundle")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_RELATIONSHIP_TYPES = {
    "required_deliverable",
    "implementation_stage",
    "parent_scope",
    "meeting_explicit_split",
    "repository_existing_structure",
}
_RELATIONSHIP_CLAIM_FIELDS = {
    "required_deliverable": ("parent_goal", "task_contribution"),
    "implementation_stage": ("parent_feature", "implementation_stage"),
    "parent_scope": ("parent_scope_item", "task_output"),
    "meeting_explicit_split": ("larger_work", "split_task"),
    "repository_existing_structure": ("repository_parent", "repository_child"),
}
_EVIDENCE_KEYS = {"timestamp", "line_range", "record_section", "speaker", "quote"}
_EVIDENCE_LOCATORS = {"timestamp", "line_range", "record_section"}
_DATE_ONLY_BASIS = re.compile(
    r"^(?:"
    r"(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2})|"
    r"(?:\d{4}년\s*\d{1,2}월\s*\d{1,2}일)|"
    r"(?:same\s+)?date|"
    r"(?:같은\s*)?날짜"
    r")$",
    re.IGNORECASE,
)
_OPERATION_ORDER = {
    "create_parent": 0,
    "resolve_parent": 0,
    "create_subissue": 1,
    "resolve_subissue": 1,
    "link_subissue": 2,
    "add_to_project": 3,
}
_CREATE_OPERATIONS = {"create_parent", "create_subissue"}
_ISSUE_OPERATIONS = {
    "create_parent",
    "resolve_parent",
    "create_subissue",
    "resolve_subissue",
}
_LEDGER_STATUSES = {"planned", "succeeded", "failed", "unattempted"}
_INVALID_RELATIONSHIP_QUOTES = {
    "same date",
    "same owner",
    "same meeting",
    "similar words",
    "같은 날짜",
    "같은 담당자",
    "같은 회의",
    "비슷한 단어",
}
_INVALID_RELATIONSHIP_CUES = re.compile(
    r"(?:\b(?:deadline|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|"
    r"\bdue[- ]date\b|\bdue\s+(?:(?:on|by|before|after)\s+)?(?:today|tomorrow|\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\b|"
    r"\bdiscussed\s+together\b|\bsame\s+(?:owner|meeting|date)\b|"
    r"\bsimilar\s+(?:word|words|title|titles)\b|"
    r"같은\s*(?:날짜|담당자|회의)|비슷한\s*(?:단어|제목)|함께\s*논의|"
    r"(?:월|화|수|목|금|토|일)요일(?:까지)?)",
    re.IGNORECASE,
)
_LOCAL_ID_ONLY_QUOTE = re.compile(
    r"\bt\d+\b.*(?:다음|후|before|after|->|→).*\bt\d+\b",
    re.IGNORECASE,
)
_LOCAL_ID_ONLY_VALUE = re.compile(r"^\s*t\d+\s*$", re.IGNORECASE)
_OPERATION_PLAN_KEYS = ("operation_id", "kind", "local_id", "depends_on")


def _present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return bool(value)
    return bool(value)


def _present_text(value):
    return isinstance(value, str) and bool(value.strip())


def _local_id(task):
    value = task.get("local_id")
    if _present_text(value):
        return value.strip()
    return "<missing>"


def _canonical_sha256(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _date_only_basis(value):
    return isinstance(value, str) and bool(_DATE_ONLY_BASIS.fullmatch(value.strip()))


def _valid_evidence_entry(value):
    if not isinstance(value, dict) or not value:
        return False
    if not set(value).issubset(_EVIDENCE_KEYS):
        return False
    if not any(_present_text(value.get(key)) for key in _EVIDENCE_LOCATORS):
        return False
    if not _present_text(value.get("quote")):
        return False
    return all(_present_text(item) for item in value.values())


def _valid_evidence_list(value):
    return isinstance(value, list) and bool(value) and all(
        _valid_evidence_entry(item) for item in value
    )


def _functional_relationship_text(value):
    text = value.strip().casefold()
    return (
        not _date_only_basis(text)
        and not any(phrase in text for phrase in _INVALID_RELATIONSHIP_QUOTES)
        and not _INVALID_RELATIONSHIP_CUES.search(text)
        and not _LOCAL_ID_ONLY_QUOTE.search(text)
        and not _LOCAL_ID_ONLY_VALUE.fullmatch(text)
    )


def _functional_relationship_evidence(value):
    quotes = [item.get("quote", "") for item in value if _present_text(item.get("quote"))]
    if not quotes:
        return False
    return all(_functional_relationship_text(quote) for quote in quotes)


def _functional_relationship_claim(claim, fields):
    return all(
        _functional_relationship_text(claim[field])
        for field in fields
    )


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as artifact_file:
        for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_timestamp(value):
    if not _present_text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _validate_shape(manifest):
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a JSON object")
    if "tasks" in manifest and not isinstance(manifest["tasks"], list):
        raise TypeError("tasks must be a JSON array")
    for key in ("approval_records", "preflight"):
        if key in manifest and not isinstance(manifest[key], dict):
            raise TypeError(f"{key} must be a JSON object")
    if "bundle" in manifest and manifest["bundle"] is not None and not isinstance(
        manifest["bundle"], dict
    ):
        raise TypeError("bundle must be a JSON object or null")
    if "operation_ledger" in manifest and not isinstance(manifest["operation_ledger"], list):
        raise TypeError("operation_ledger must be a JSON array")
    if "retry_approval" in manifest and manifest["retry_approval"] is not None and not isinstance(
        manifest["retry_approval"], dict
    ):
        raise TypeError("retry_approval must be a JSON object or null")
    for task in manifest.get("tasks", []):
        if not isinstance(task, dict):
            raise TypeError("each task must be a JSON object")
        for key in ("relationship", "github"):
            value = task.get(key)
            if value is not None and not isinstance(value, dict):
                raise TypeError(f"task {key} must be a JSON object")
        github = task.get("github") or {}
        if github.get("issue_number") is not None and not isinstance(
            github.get("issue_number"), int
        ):
            raise TypeError("github.issue_number must be an integer or null")
        if github.get("url") is not None and not isinstance(github.get("url"), str):
            raise TypeError("github.url must be a string or null")
    for operation in manifest.get("operation_ledger", []):
        if not isinstance(operation, dict):
            raise TypeError("each operation_ledger entry must be a JSON object")
        if not isinstance(operation.get("kind"), str):
            raise TypeError("operation kind must be a string")
        if not isinstance(operation.get("status"), str):
            raise TypeError("operation status must be a string")
        dependencies = operation.get("depends_on")
        if not isinstance(dependencies, list) or not all(
            isinstance(dependency, str) for dependency in dependencies
        ):
            raise TypeError("operation depends_on must be a string array")
    retry = manifest.get("retry_approval")
    if isinstance(retry, dict):
        for key in (
            "duplicate_search_operation_ids",
            "unresolved_operation_ids",
            "approved_operation_ids",
        ):
            value = retry.get(key)
            if value is not None and (
                not isinstance(value, list)
                or not all(isinstance(operation_id, str) for operation_id in value)
            ):
                raise TypeError(f"retry_approval.{key} must be a string array")


def _validate_text_list(errors, value, *, local_id, required_message, invalid_message):
    if not isinstance(value, list) or not value:
        errors.append(f"{local_id}: {required_message}")
        return
    if not all(_present_text(item) for item in value):
        errors.append(f"{local_id}: {invalid_message}")


def _validate_relationship(errors, task, local_id, mode):
    relationship = task.get("relationship") or {}
    if not isinstance(relationship.get("approved"), bool):
        errors.append(f"{local_id}: relationship.approved must be boolean")

    parent = relationship.get("proposed_parent")
    basis = relationship.get("basis")
    if parent is None:
        if basis is not None:
            errors.append(f"{local_id}: relationship basis requires a proposed parent")
        if relationship.get("approved") is True:
            errors.append(f"{local_id}: parentless relationship cannot be approved")
        return

    if mode in _MUTATION_MODES and relationship.get("approved") is not True:
        errors.append(f"{local_id}: proposed parent is not approved")

    if not _present(basis):
        errors.append(f"{local_id}: approved parent requires a relationship basis")
        return
    if not isinstance(basis, dict) or basis.get("type") not in _ALLOWED_RELATIONSHIP_TYPES:
        errors.append(f"{local_id}: relationship basis type is not allowed")
        if _date_only_basis(basis):
            errors.append(f"{local_id}: relationship basis requires user confirmation")
        return
    claim = basis.get("claim")
    claim_fields = _RELATIONSHIP_CLAIM_FIELDS[basis["type"]]
    if not isinstance(claim, dict) or not all(
        _present_text(claim.get(field)) for field in claim_fields
    ):
        errors.append(f"{local_id}: relationship basis requires a typed functional claim")
    elif not _functional_relationship_claim(claim, claim_fields):
        errors.append(f"{local_id}: relationship basis claim is not functional")
    if not _valid_evidence_list(basis.get("evidence")):
        errors.append(f"{local_id}: relationship basis requires shaped source evidence")
    elif not _functional_relationship_evidence(basis["evidence"]):
        errors.append(f"{local_id}: relationship basis evidence is not functional")


def _validate_assignee(errors, task, local_id):
    owner_name = task.get("owner_name")
    owner_github = task.get("owner_github")
    provenance = task.get("assignee_mapping_provenance")
    if _present_text(owner_github) and not _present_text(owner_name):
        errors.append(f"{local_id}: GitHub owner exists without a confirmed owner name")
        return
    if not _present_text(owner_github):
        if provenance is not None:
            errors.append(f"{local_id}: assignee mapping exists without a GitHub owner")
        return
    if not isinstance(provenance, dict):
        errors.append(f"{local_id}: GitHub assignee requires confirmed mapping provenance")
        return
    required = ("owner_name", "owner_github", "confirmed_by", "confirmed_at")
    if provenance.get("source") != "explicit-user-confirmation" or not all(
        _present_text(provenance.get(key)) for key in required
    ):
        errors.append(f"{local_id}: GitHub assignee requires confirmed mapping provenance")
    if provenance.get("owner_name") != owner_name or provenance.get("owner_github") != owner_github:
        errors.append(f"{local_id}: assignee mapping does not match owner fields")


def _validate_approval_records(errors, manifest, artifact_paths):
    records = manifest.get("approval_records") or {}
    if not isinstance(artifact_paths, dict) or not all(
        _present_text(artifact_paths.get(kind)) for kind in ("source_record", "pdf")
    ):
        errors.append("trusted local artifact paths are required for mutation validation")
        artifact_paths = {}
    for kind in _APPROVAL_KINDS:
        record = records.get(kind)
        if not isinstance(record, dict):
            errors.append(f"missing approved artifact: {kind}")
            continue
        if record.get("approved") is not True or not all(
            _present_text(record.get(key))
            for key in ("artifact", "approved_by", "approved_at")
        ):
            errors.append(f"{kind}: approval record is incomplete")
        manifest_locator = manifest.get(kind) if kind in {"source_record", "pdf"} else None
        if manifest_locator is not None and record.get("artifact") != manifest_locator:
            errors.append(f"{kind}: approval artifact does not match manifest locator")
        approved = record.get("approved_sha256")
        current = record.get("current_sha256")
        if not isinstance(approved, str) or not _SHA256.fullmatch(approved):
            errors.append(f"{kind}: approved_sha256 must be a lowercase SHA-256")
            continue
        if not isinstance(current, str) or not _SHA256.fullmatch(current):
            errors.append(f"{kind}: current_sha256 must be a lowercase SHA-256")
            continue
        expected_current = current
        if kind == "task_candidates":
            expected_current = _canonical_sha256(manifest.get("tasks", []))
        elif kind == "bundle":
            expected_current = _canonical_sha256(manifest.get("bundle"))
        if current != expected_current or approved != current:
            errors.append(f"{kind}: approved content fingerprint changed")
        if kind in {"source_record", "pdf"} and kind in artifact_paths:
            trusted_path = artifact_paths[kind]
            if trusted_path != manifest_locator:
                errors.append(f"{kind}: trusted artifact path does not match manifest locator")
                continue
            try:
                actual = _file_sha256(trusted_path)
            except OSError:
                errors.append(f"{kind}: trusted local artifact is unreadable")
                continue
            if actual != current:
                errors.append(f"{kind}: local artifact bytes do not match current_sha256")


def _plan_projection(operations):
    if not isinstance(operations, list) or not all(
        isinstance(operation, dict) for operation in operations
    ):
        return None
    return [
        {key: operation.get(key) for key in _OPERATION_PLAN_KEYS}
        for operation in operations
    ]


def _validate_bundle_binding(errors, manifest):
    bundle = manifest.get("bundle") or {}
    ledger = manifest.get("operation_ledger") or []
    if bundle.get("repository") != "DEVUNLIMIT/supernova-mobile":
        errors.append("bundle repository must match the configured target")
    if bundle.get("project_url") != "https://github.com/orgs/DEVUNLIMIT/projects/5":
        errors.append("bundle project_url must match the configured target")

    parent = bundle.get("parent")
    if not isinstance(parent, dict) or not all(
        _present_text(parent.get(key)) for key in ("title", "body")
    ):
        errors.append("bundle parent requires nonblank title and body")

    manifest_task_ids = [_local_id(task) for task in manifest.get("tasks", [])]
    bundle_task_ids = bundle.get("task_local_ids")
    if (
        not isinstance(bundle_task_ids, list)
        or not all(_present_text(local_id) for local_id in bundle_task_ids)
        or len(bundle_task_ids) != len(set(bundle_task_ids))
        or set(bundle_task_ids) != set(manifest_task_ids)
    ):
        errors.append("bundle task_local_ids must match manifest tasks")
        approved_task_ids = set()
    else:
        approved_task_ids = set(bundle_task_ids)

    task_by_id = {_local_id(task): task for task in manifest.get("tasks", [])}
    subissues = bundle.get("subissues")
    if not isinstance(subissues, list) or not all(isinstance(item, dict) for item in subissues):
        errors.append("bundle subissues must be a JSON object array")
        subissues = []
    subissue_ids = [item.get("local_id") for item in subissues]
    if (
        len(subissue_ids) != len(set(item for item in subissue_ids if isinstance(item, str)))
        or set(item for item in subissue_ids if isinstance(item, str)) != approved_task_ids
    ):
        errors.append("bundle subissues must map one-to-one to approved tasks")
    for subissue in subissues:
        local_id = subissue.get("local_id")
        if not all(_present_text(subissue.get(key)) for key in ("local_id", "title", "body")):
            errors.append("bundle subissue requires nonblank local_id, title, and body")
        elif local_id in task_by_id and subissue.get("title") != task_by_id[local_id].get("title"):
            errors.append(f"{local_id}: bundle subissue title does not match approved task")

    references = bundle.get("references")
    if not isinstance(references, list):
        errors.append("bundle references must be a JSON array")
        references = []
    for reference in references:
        if (
            not isinstance(reference, dict)
            or not _present_text(reference.get("url"))
            or not reference["url"].startswith("https://")
            or "path" in reference
        ):
            errors.append("bundle references must contain accessible HTTPS URLs only")

    pdf_locator = manifest.get("pdf")
    if _present_text(pdf_locator) and not pdf_locator.startswith(("https://", "http://")):
        linked_pdf = re.compile(r"\]\(\s*" + re.escape(pdf_locator) + r"\s*\)")
        bodies = [parent.get("body", "") if isinstance(parent, dict) else ""] + [
            item.get("body", "") for item in subissues if isinstance(item, dict)
        ]
        if any(linked_pdf.search(body) or "file://" in body for body in bodies):
            errors.append("bundle: local PDF path cannot be an accessible GitHub reference")

    approved_plan = _plan_projection(bundle.get("operations"))
    ledger_plan = _plan_projection(ledger)
    if approved_plan is None or ledger_plan is None or approved_plan != ledger_plan:
        errors.append("operation ledger does not match the approved bundle operation plan")

    parent_action = parent.get("action") if isinstance(parent, dict) else None
    parent_kind = {"create": "create_parent", "select": "resolve_parent"}.get(parent_action)
    parent_operations = [
        operation
        for operation in ledger
        if isinstance(operation, dict)
        and operation.get("kind") in {"create_parent", "resolve_parent"}
    ]
    if len(parent_operations) != 1 or parent_kind is None or parent_operations[0].get("kind") != parent_kind:
        errors.append("bundle parent action must match exactly one parent ledger operation")
        parent_id = None
    else:
        parent_id = parent_operations[0].get("operation_id")

    expected_relationship_parent = (
        "bundle-parent" if parent_action == "create" else parent.get("issue_number")
        if isinstance(parent, dict)
        else None
    )
    for task in manifest.get("tasks", []):
        relationship = task.get("relationship") or {}
        if (
            _local_id(task) in approved_task_ids
            and (
                relationship.get("approved") is not True
                or relationship.get("proposed_parent") != expected_relationship_parent
            )
        ):
            errors.append(
                f"{_local_id(task)}: approved relationship does not match the bundle parent"
            )

    subissue_by_task = {}
    link_by_task = {}
    project_by_task = {}
    for operation in ledger:
        if not isinstance(operation, dict):
            continue
        operation_id = operation.get("operation_id")
        kind = operation.get("kind")
        local_id = operation.get("local_id")
        dependencies = operation.get("depends_on")
        dependency_set = set(dependencies) if isinstance(dependencies, list) and all(
            isinstance(item, str) for item in dependencies
        ) else set()
        if kind in {"create_subissue", "resolve_subissue", "link_subissue", "add_to_project"}:
            if local_id is not None and local_id not in approved_task_ids:
                errors.append(f"{operation_id}: operation targets a task outside the approved bundle")
        if kind in {"create_subissue", "resolve_subissue"} and local_id in approved_task_ids:
            subissue_by_task.setdefault(local_id, []).append(operation_id)
            if parent_id not in dependency_set:
                errors.append(f"{operation_id}: sub-issue operation must depend on the parent operation")
        elif kind == "link_subissue" and local_id in approved_task_ids:
            link_by_task.setdefault(local_id, []).append(operation_id)
            matching_subissues = set(subissue_by_task.get(local_id, []))
            if parent_id not in dependency_set or not matching_subissues.intersection(dependency_set):
                errors.append(f"{operation_id}: link operation must depend on its sub-issue operation")
        elif kind == "add_to_project" and local_id in approved_task_ids:
            project_by_task.setdefault(local_id, []).append(operation_id)
            matching_links = set(link_by_task.get(local_id, []))
            if not matching_links.intersection(dependency_set):
                errors.append(f"{operation_id}: project operation must depend on its link operation")

    for local_id in approved_task_ids:
        if len(subissue_by_task.get(local_id, [])) != 1:
            errors.append(f"{local_id}: approved task requires exactly one create or resolve operation")
        if len(link_by_task.get(local_id, [])) != 1:
            errors.append(f"{local_id}: approved task requires exactly one link operation")
        if len(project_by_task.get(local_id, [])) != 1:
            errors.append(f"{local_id}: approved task requires exactly one project operation")


def _validate_selected_parent(errors, manifest):
    preflight = manifest.get("preflight") or {}
    parent = preflight.get("selected_parent")
    proposed_parents = {
        (task.get("relationship") or {}).get("proposed_parent")
        for task in manifest.get("tasks", [])
        if isinstance((task.get("relationship") or {}).get("proposed_parent"), int)
        and not isinstance((task.get("relationship") or {}).get("proposed_parent"), bool)
    }
    if proposed_parents and parent is None:
        errors.append("preflight: selected parent was not re-read")
        return
    if parent is None:
        return
    if not isinstance(parent, dict):
        errors.append("preflight: selected parent snapshot is invalid")
        return
    if parent.get("issue_number") not in proposed_parents and proposed_parents:
        errors.append("preflight: selected parent does not match approved relationships")
    required = (
        "approved_state",
        "current_state",
        "approved_updated_at",
        "current_updated_at",
        "approved_content_sha256",
        "current_content_sha256",
    )
    if not all(_present_text(parent.get(key)) for key in required):
        errors.append("preflight: selected parent snapshot is incomplete")
        return
    if (
        parent.get("approved_state") != parent.get("current_state")
        or parent.get("approved_updated_at") != parent.get("current_updated_at")
        or parent.get("approved_content_sha256") != parent.get("current_content_sha256")
        or not _SHA256.fullmatch(parent.get("approved_content_sha256", ""))
        or not _SHA256.fullmatch(parent.get("current_content_sha256", ""))
    ):
        errors.append("preflight: selected parent changed; approval is stale")
    if parent.get("current_state") == "closed":
        action = parent.get("closed_issue_action")
        if (
            not isinstance(action, dict)
            or action.get("action") not in {"reuse", "reopen"}
            or action.get("approved") is not True
            or not all(_present_text(action.get(key)) for key in ("approved_by", "approved_at"))
        ):
            errors.append("preflight: closed parent requires explicit reuse or reopen approval")


def _validate_preflight(errors, manifest):
    preflight = manifest.get("preflight") or {}
    if _parse_timestamp(preflight.get("checked_at")) is None:
        errors.append("preflight: timezone-aware current check timestamp is required")
    for field, message in (
        ("auth_verified", "authentication is not verified"),
        ("repository_access_verified", "repository access is not verified"),
        ("project_access_verified", "project access is not verified"),
    ):
        if preflight.get(field) is not True:
            errors.append(f"preflight: {message}")
    _validate_selected_parent(errors, manifest)


def _validate_operation_ledger(errors, manifest, mode):
    ledger = manifest.get("operation_ledger")
    if not isinstance(ledger, list) or not ledger:
        errors.append("operation ledger is required")
        return

    ids = []
    by_id = {}
    ranks = []
    preflight_time = _parse_timestamp((manifest.get("preflight") or {}).get("checked_at"))
    for operation in ledger:
        operation_id = operation.get("operation_id")
        if not _present_text(operation_id):
            errors.append("operation ledger entry requires operation_id")
            continue
        if operation_id in by_id:
            errors.append(f"duplicate operation_id: {operation_id}")
            continue
        ids.append(operation_id)
        by_id[operation_id] = operation
        kind = operation.get("kind")
        if kind not in _OPERATION_ORDER:
            errors.append(f"{operation_id}: unsupported operation kind")
        else:
            ranks.append(_OPERATION_ORDER[kind])
        dependencies = operation.get("depends_on")
        if not isinstance(dependencies, list) or not all(
            _present_text(dependency) for dependency in dependencies
        ):
            errors.append(f"{operation_id}: depends_on must be a string array")
        status = operation.get("status")
        if status not in _LEDGER_STATUSES:
            errors.append(f"{operation_id}: invalid ledger status")
        if kind in _CREATE_OPERATIONS:
            search_time = _parse_timestamp(operation.get("duplicate_search_at"))
            if search_time is None:
                errors.append(f"{operation_id}: create requires a fresh duplicate search")
            elif mode == "mutation-ready" and preflight_time is not None and search_time < preflight_time:
                errors.append(f"{operation_id}: duplicate search is older than the current preflight")

    if ranks != sorted(ranks):
        errors.append("operation ledger order must be parent, create/link subissues, then project")

    index = {operation_id: position for position, operation_id in enumerate(ids)}
    for operation_id, operation in by_id.items():
        for dependency in operation.get("depends_on", []):
            if dependency not in index or index[dependency] >= index[operation_id]:
                errors.append(f"{operation_id}: dependency must reference an earlier operation")

    if mode == "mutation-ready":
        for operation_id, operation in by_id.items():
            if operation.get("status") != "planned":
                errors.append(f"{operation_id}: initial mutation operation must be planned")
        return

    unresolved = set()
    unresolved_creates = set()
    recorded_times = []
    for operation_id, operation in by_id.items():
        status = operation.get("status")
        if status == "planned":
            errors.append(f"{operation_id}: retry ledger cannot contain planned operations")
        elif status == "succeeded":
            result = operation.get("result")
            recorded_at = _parse_timestamp(operation.get("recorded_at"))
            if recorded_at is None or not _present(result):
                errors.append(f"{operation_id}: success must be recorded immediately with its result")
            else:
                recorded_times.append(recorded_at)
                if operation.get("kind") in _ISSUE_OPERATIONS and (
                    not isinstance(result, dict)
                    or not isinstance(result.get("issue_number"), int)
                    or result.get("issue_number") <= 0
                    or not _present_text(result.get("issue_url"))
                ):
                    errors.append(
                        f"{operation_id}: successful issue operation must record issue number and URL"
                    )
                elif operation.get("kind") in _ISSUE_OPERATIONS:
                    expected_url = (
                        "https://github.com/DEVUNLIMIT/supernova-mobile/issues/"
                        f"{result['issue_number']}"
                    )
                    if result.get("issue_url") != expected_url:
                        errors.append(
                            f"{operation_id}: successful issue URL must match its configured issue number"
                        )
                elif operation.get("kind") == "link_subissue" and (
                    not isinstance(result, dict)
                    or not isinstance(result.get("parent_issue_number"), int)
                    or not isinstance(result.get("child_issue_number"), int)
                ):
                    errors.append(
                        f"{operation_id}: successful link must record parent and child numbers"
                    )
                elif operation.get("kind") == "add_to_project" and (
                    not isinstance(result, dict)
                    or not _present_text(result.get("project_item_id"))
                ):
                    errors.append(
                        f"{operation_id}: successful project add must record project_item_id"
                    )
        elif status == "failed":
            unresolved.add(operation_id)
            if operation.get("kind") in _CREATE_OPERATIONS:
                unresolved_creates.add(operation_id)
            recorded_at = _parse_timestamp(operation.get("recorded_at"))
            if recorded_at is None or not _present_text(operation.get("error")):
                errors.append(f"{operation_id}: failure must record time and error")
            else:
                recorded_times.append(recorded_at)
        elif status == "unattempted":
            unresolved.add(operation_id)
            if operation.get("kind") in _CREATE_OPERATIONS:
                unresolved_creates.add(operation_id)

        dependency_statuses = [
            by_id[dependency].get("status")
            for dependency in operation.get("depends_on", [])
            if dependency in by_id
        ]
        if any(value in {"failed", "unattempted"} for value in dependency_statuses) and status != "unattempted":
            errors.append(f"{operation_id}: dependent operation must remain unattempted after failure")

    retry = manifest.get("retry_approval")
    if not isinstance(retry, dict):
        errors.append("retry: new narrowly scoped user approval is required")
        return
    reconciled_at = _parse_timestamp(retry.get("reconciled_at"))
    if retry.get("reconciliation_completed") is not True or reconciled_at is None:
        errors.append("retry: fresh reconciliation is required")
    elif recorded_times and reconciled_at < max(recorded_times):
        errors.append("retry: reconciliation must follow all recorded outcomes")
    if set(retry.get("duplicate_search_operation_ids") or []) != unresolved_creates:
        errors.append("retry: every unresolved create requires a fresh duplicate search")
    if set(retry.get("unresolved_operation_ids") or []) != unresolved:
        errors.append("retry: unresolved operation list must match the ledger")
    if set(retry.get("approved_operation_ids") or []) != unresolved:
        errors.append("retry: approval must be limited to unresolved operations")
    unresolved_search_times = []
    if reconciled_at is not None:
        for operation_id in unresolved_creates:
            search_time = _parse_timestamp(by_id[operation_id].get("duplicate_search_at"))
            if search_time is None or search_time < reconciled_at:
                errors.append(f"{operation_id}: retry duplicate search is older than reconciliation")
            else:
                unresolved_search_times.append(search_time)
    approved_at = _parse_timestamp(retry.get("approved_at"))
    if (
        retry.get("approved") is not True
        or not _present_text(retry.get("approved_by"))
        or approved_at is None
        or (reconciled_at is not None and approved_at < reconciled_at)
    ):
        errors.append("retry: new narrowly scoped user approval is required")
    elif unresolved_search_times and approved_at < max(unresolved_search_times):
        errors.append("retry: approval must follow reconciliation and duplicate searches")


def validate_manifest(manifest, mode="draft", artifact_paths=None):
    if mode not in {"draft", "mutation-ready", "retry-ready"}:
        raise ValueError("mode must be draft, mutation-ready, or retry-ready")
    _validate_shape(manifest)

    errors = []
    if manifest.get("schema_version") != _SCHEMA_VERSION:
        errors.append(f"schema_version must be {_SCHEMA_VERSION}")
    for key in ("meeting_id", "source_record"):
        if not _present_text(manifest.get(key)):
            errors.append(f"missing top-level field: {key}")
    if not isinstance(manifest.get("tasks"), list) or not manifest.get("tasks"):
        errors.append("missing top-level field: tasks")
    if mode in _MUTATION_MODES:
        if not _present_text(manifest.get("pdf")):
            errors.append("missing top-level field: pdf")
        if not isinstance(manifest.get("bundle"), dict) or not manifest.get("bundle"):
            errors.append("missing top-level field: bundle")

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
        evidence = task.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{local_id}: missing evidence")
        elif not _valid_evidence_list(evidence):
            errors.append(f"{local_id}: evidence entries must use the approved evidence shape")

        _validate_assignee(errors, task, local_id)
        _validate_relationship(errors, task, local_id, mode)

        if mode in _MUTATION_MODES:
            _validate_text_list(
                errors,
                task.get("completion_criteria"),
                local_id=local_id,
                required_message="completion criteria are required for mutation",
                invalid_message="completion criteria must contain nonblank text",
            )
            _validate_text_list(
                errors,
                task.get("verification"),
                local_id=local_id,
                required_message="verification is required and must contain nonblank text",
                invalid_message="verification is required and must contain nonblank text",
            )
        else:
            for field in ("completion_criteria", "verification"):
                value = task.get(field)
                if value is not None and (
                    not isinstance(value, list) or any(not _present_text(item) for item in value)
                ):
                    errors.append(f"{local_id}: {field} entries must contain nonblank text")

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

    if mode in _MUTATION_MODES:
        _validate_approval_records(errors, manifest, artifact_paths)
        _validate_preflight(errors, manifest)
        _validate_bundle_binding(errors, manifest)
        _validate_operation_ledger(errors, manifest, mode)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a task manifest JSON file.")
    parser.add_argument("--input", required=True, help="path to manifest JSON")
    parser.add_argument(
        "--mode",
        choices=("draft", "mutation-ready", "retry-ready"),
        default="draft",
        help="validation mode (default: draft)",
    )
    parser.add_argument(
        "--source-record-file",
        help="trusted local Markdown path selected or produced by this workflow",
    )
    parser.add_argument(
        "--pdf-file",
        help="trusted local PDF path selected or produced by this workflow",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.input, encoding="utf-8") as input_file:
            manifest = json.load(input_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    try:
        artifact_paths = None
        if args.source_record_file is not None or args.pdf_file is not None:
            artifact_paths = {
                "source_record": args.source_record_file,
                "pdf": args.pdf_file,
            }
        errors = validate_manifest(
            manifest,
            mode=args.mode,
            artifact_paths=artifact_paths,
        )
    except (TypeError, ValueError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
