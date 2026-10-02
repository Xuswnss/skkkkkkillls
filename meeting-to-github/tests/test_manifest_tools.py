from pathlib import Path
from copy import deepcopy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
APPROVED_MINUTES = ROOT / "tests" / "fixtures" / "approved-minutes.md"
APPROVED_PDF = ROOT / "tests" / "fixtures" / "approved-report.pdf"


def load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trusted_artifact_paths():
    return {
        "source_record": str(APPROVED_MINUTES),
        "pdf": str(APPROVED_PDF),
    }


def approval_record(artifact, fingerprint):
    return {
        "artifact": artifact,
        "approved": True,
        "approved_sha256": fingerprint,
        "current_sha256": fingerprint,
        "approved_by": "meeting owner",
        "approved_at": "2026-10-02T09:00:00+09:00",
    }


def sample_task():
    return {
        "local_id": "T06",
        "title": "K-pop 영상 파이프라인 구축",
        "topic": "콘텐츠",
        "owner_name": None,
        "owner_github": None,
        "assignee_mapping_provenance": None,
        "due_date": None,
        "outcome": "반복 가능한 영상 생성 공정",
        "completion_criteria": ["샘플 영상 생성과 검수 완료"],
        "verification": ["승인된 샘플을 재생해 영상과 배경을 확인"],
        "evidence": [{
            "timestamp": "09:38-10:55",
            "quote": "샘플 영상을 생성한 뒤 검수합니다.",
        }],
        "relationship": {
            "proposed_parent": "bundle-parent",
            "basis": {
                "type": "required_deliverable",
                "claim": {
                    "parent_goal": "반복 가능한 콘텐츠 파이프라인",
                    "task_contribution": "검증 가능한 영상 생성 공정",
                },
                "evidence": [{
                    "record_section": "작업 범위",
                    "quote": "영상 생성은 콘텐츠 파이프라인의 필수 산출물이다.",
                }],
            },
            "approved": True,
        },
        "github": {"issue_number": None, "url": None, "project_item_id": None},
    }


def sample_manifest():
    tasks = [sample_task()]
    operation_plan = [
        {
            "operation_id": "op-01",
            "kind": "create_parent",
            "local_id": None,
            "depends_on": [],
        },
        {
            "operation_id": "op-02",
            "kind": "create_subissue",
            "local_id": "T06",
            "depends_on": ["op-01"],
        },
        {
            "operation_id": "op-03",
            "kind": "link_subissue",
            "local_id": "T06",
            "depends_on": ["op-01", "op-02"],
        },
        {
            "operation_id": "op-04",
            "kind": "add_to_project",
            "local_id": "T06",
            "depends_on": ["op-02", "op-03"],
        },
    ]
    bundle = {
        "repository": "DEVUNLIMIT/supernova-mobile",
        "parent": {
            "action": "create",
            "title": "콘텐츠 파이프라인",
            "body": "승인된 콘텐츠 파이프라인 작업 묶음",
        },
        "project_url": "https://github.com/orgs/DEVUNLIMIT/projects/5",
        "task_local_ids": ["T06"],
        "subissues": [{
            "local_id": "T06",
            "title": "K-pop 영상 파이프라인 구축",
            "body": "반복 가능한 영상 생성 공정을 구축하고 승인된 절차로 검증한다.",
        }],
        "references": [],
        "operations": operation_plan,
    }
    task_fingerprint = canonical_sha256(tasks)
    bundle_fingerprint = canonical_sha256(bundle)
    return {
        "schema_version": "2.0",
        "meeting_id": "2026-09-28",
        "source_record": str(APPROVED_MINUTES),
        "pdf": str(APPROVED_PDF),
        "tasks": tasks,
        "bundle": bundle,
        "approval_records": {
            "source_record": approval_record(str(APPROVED_MINUTES), file_sha256(APPROVED_MINUTES)),
            "pdf": approval_record(str(APPROVED_PDF), file_sha256(APPROVED_PDF)),
            "task_candidates": approval_record("tasks.json", task_fingerprint),
            "bundle": approval_record("bundle.json", bundle_fingerprint),
        },
        "preflight": {
            "checked_at": "2026-10-02T09:05:00+09:00",
            "auth_verified": True,
            "repository_access_verified": True,
            "project_access_verified": True,
            "selected_parent": None,
        },
        "operation_ledger": [
            dict(
                deepcopy(operation),
                status="planned",
                **(
                    {"duplicate_search_at": f"2026-10-02T09:05:{10 + index * 10:02d}+09:00"}
                    if operation["kind"].startswith("create_")
                    else {}
                ),
            )
            for index, operation in enumerate(operation_plan)
        ],
        "retry_approval": None,
    }


def retry_manifest():
    manifest = sample_manifest()
    manifest["operation_ledger"][0].update({
        "status": "succeeded",
        "recorded_at": "2026-10-02T09:06:00+09:00",
        "result": {
            "issue_number": 501,
            "issue_url": "https://github.com/DEVUNLIMIT/supernova-mobile/issues/501",
        },
    })
    manifest["operation_ledger"][1].update({
        "status": "failed",
        "recorded_at": "2026-10-02T09:06:10+09:00",
        "error": "GitHub API timeout",
        "duplicate_search_at": "2026-10-02T09:09:10+09:00",
    })
    manifest["operation_ledger"][2]["status"] = "unattempted"
    manifest["operation_ledger"][3]["status"] = "unattempted"
    manifest["retry_approval"] = {
        "reconciliation_completed": True,
        "reconciled_at": "2026-10-02T09:09:00+09:00",
        "duplicate_search_operation_ids": ["op-02"],
        "unresolved_operation_ids": ["op-02", "op-03", "op-04"],
        "approved_operation_ids": ["op-02", "op-03", "op-04"],
        "approved": True,
        "approved_by": "meeting owner",
        "approved_at": "2026-10-02T09:10:00+09:00",
    }
    return manifest


class BuildManifestTests(unittest.TestCase):
    def test_builds_normalized_manifest_without_inventing_values(self):
        module = load_script("build_task_manifest.py")
        manifest = module.build_manifest(
            meeting_id="2026-09-28",
            source_record="minutes.md",
            pdf=None,
            tasks=[{
                "local_id": "T06",
                "title": "K-pop 영상 파이프라인 구축",
                "topic": "콘텐츠",
                "owner_name": None,
                "owner_github": None,
                "due_date": None,
                "outcome": "반복 가능한 영상 생성 공정",
                "completion_criteria": [],
                "verification": [],
                "evidence": [{"timestamp": "09:38-10:55"}],
                "relationship": {"proposed_parent": None, "basis": None, "approved": False},
                "github": {"issue_number": None, "url": None, "project_item_id": None},
            }],
        )
        self.assertEqual("2.0", manifest["schema_version"])
        self.assertIsNone(manifest["tasks"][0]["owner_github"])
        self.assertIsNone(manifest["tasks"][0]["due_date"])
        self.assertEqual({}, manifest["approval_records"])
        self.assertEqual([], manifest["operation_ledger"])

    def test_builds_manifest_with_immutable_approval_and_workflow_context(self):
        module = load_script("build_task_manifest.py")
        tasks = [sample_task()]
        context = {
            "bundle": {"task_local_ids": ["T06"]},
            "approval_records": {"source_record": approval_record("minutes.md", "a" * 64)},
            "preflight": {"auth_verified": True},
            "operation_ledger": [{"operation_id": "op-01"}],
            "retry_approval": None,
        }

        manifest = module.build_manifest(
            "meeting", "minutes.md", "minutes.pdf", tasks, context=context
        )
        context["approval_records"]["source_record"]["approved"] = False

        self.assertTrue(manifest["approval_records"]["source_record"]["approved"])
        self.assertEqual(["T06"], manifest["bundle"]["task_local_ids"])

    def test_build_manifest_deep_copies_tasks(self):
        module = load_script("build_task_manifest.py")
        tasks = [{"owner_name": {"unresolved": True}, "relationship": {"basis": "verbatim"}}]

        manifest = module.build_manifest("meeting", "minutes.md", "minutes.pdf", tasks)
        tasks[0]["owner_name"]["unresolved"] = False

        self.assertTrue(manifest["tasks"][0]["owner_name"]["unresolved"])
        self.assertEqual("verbatim", manifest["tasks"][0]["relationship"]["basis"])

    def test_cli_reads_tasks_json_and_writes_utf8_manifest(self):
        script = ROOT / "scripts" / "build_task_manifest.py"
        tasks = [{"title": "K-pop 영상", "owner_github": None, "due_date": "미정"}]

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            tasks_path = directory / "tasks.json"
            output_path = directory / "manifest.json"
            tasks_path.write_text(json.dumps(tasks, ensure_ascii=False), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--meeting-id",
                    "2026-09-28",
                    "--source-record",
                    "minutes.md",
                    "--pdf",
                    "minutes.pdf",
                    "--tasks",
                    str(tasks_path),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(
                {
                    "schema_version": "2.0",
                    "meeting_id": "2026-09-28",
                    "source_record": "minutes.md",
                    "pdf": "minutes.pdf",
                    "tasks": tasks,
                    "bundle": None,
                    "approval_records": {},
                    "preflight": {},
                    "operation_ledger": [],
                    "retry_approval": None,
                },
                json.loads(output_path.read_text(encoding="utf-8")),
            )

    def test_cli_help_explains_inputs_and_output(self):
        script = ROOT / "scripts" / "build_task_manifest.py"

        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        for explanation in (
            "meeting identifier",
            "approved Markdown meeting record path",
            "approved local PDF path",
            "task candidate JSON array file",
            "workflow context JSON object file",
            "output manifest JSON file",
        ):
            self.assertIn(explanation, result.stdout)

    def test_cli_reports_missing_tasks_file_without_traceback(self):
        script = ROOT / "scripts" / "build_task_manifest.py"
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            missing_tasks = directory / "missing.json"
            output_path = directory / "manifest.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--meeting-id",
                    "2026-09-28",
                    "--source-record",
                    "minutes.md",
                    "--tasks",
                    str(missing_tasks),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertFalse(output_path.exists())

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("input error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_reports_malformed_tasks_json_without_traceback(self):
        script = ROOT / "scripts" / "build_task_manifest.py"
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            tasks_path = directory / "tasks.json"
            output_path = directory / "manifest.json"
            tasks_path.write_text("{", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--meeting-id",
                    "2026-09-28",
                    "--source-record",
                    "minutes.md",
                    "--tasks",
                    str(tasks_path),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertFalse(output_path.exists())

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("input error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_rejects_tasks_json_that_is_not_an_array(self):
        script = ROOT / "scripts" / "build_task_manifest.py"
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            tasks_path = directory / "tasks.json"
            output_path = directory / "manifest.json"
            tasks_path.write_text('{"title": "not an array"}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--meeting-id",
                    "2026-09-28",
                    "--source-record",
                    "minutes.md",
                    "--tasks",
                    str(tasks_path),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertFalse(output_path.exists())

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("input error: tasks must be a JSON array", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_reports_output_file_error_without_traceback(self):
        script = ROOT / "scripts" / "build_task_manifest.py"
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            tasks_path = directory / "tasks.json"
            tasks_path.write_text("[]", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--meeting-id",
                    "2026-09-28",
                    "--source-record",
                    "minutes.md",
                    "--tasks",
                    str(tasks_path),
                    "--output",
                    str(directory),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("output error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


class ValidateManifestTests(unittest.TestCase):
    def setUp(self):
        self.module = load_script("validate_task_manifest.py")
        validate_manifest = self.module.validate_manifest
        self.raw_validate_manifest = validate_manifest

        def validate_with_trusted_artifacts(manifest, mode="draft", artifact_paths=None):
            return validate_manifest(
                manifest,
                mode=mode,
                artifact_paths=artifact_paths or trusted_artifact_paths(),
            )

        self.module.validate_manifest = validate_with_trusted_artifacts

    def test_mutation_requires_explicit_trusted_artifact_paths(self):
        errors = self.raw_validate_manifest(sample_manifest(), mode="mutation-ready")
        self.assertIn("trusted local artifact paths are required for mutation validation", errors)

    def test_rejects_unapproved_parent_for_mutation(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["relationship"] = {
            "proposed_parent": 448,
            "basis": "같은 날짜",
            "approved": False,
        }
        errors = self.module.validate_manifest(manifest, mode="mutation-ready")
        self.assertIn("T06: proposed parent is not approved", errors)

    def test_accepts_complete_mutation_ready_manifest(self):
        self.assertEqual([], self.module.validate_manifest(sample_manifest(), mode="mutation-ready"))

    def test_rejects_github_owner_without_confirmed_name(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["owner_github"] = "guessed-user"
        errors = self.module.validate_manifest(manifest, mode="mutation-ready")
        self.assertIn("T06: GitHub owner exists without a confirmed owner name", errors)

    def test_rejects_assignee_without_user_confirmed_mapping_provenance(self):
        manifest = sample_manifest()
        task = manifest["tasks"][0]
        task["owner_name"] = "민수"
        task["owner_github"] = "minsu-dev"

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("T06: GitHub assignee requires confirmed mapping provenance", errors)

    def test_rejects_assignee_mapping_that_does_not_match_task_owner(self):
        manifest = sample_manifest()
        task = manifest["tasks"][0]
        task["owner_name"] = "민수"
        task["owner_github"] = "minsu-dev"
        task["assignee_mapping_provenance"] = {
            "owner_name": "민수",
            "owner_github": "fabricated-user",
            "source": "explicit-user-confirmation",
            "confirmed_by": "meeting owner",
            "confirmed_at": "2026-10-02T09:00:00+09:00",
        }

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("T06: assignee mapping does not match owner fields", errors)

    def test_rejects_duplicate_local_ids(self):
        manifest = sample_manifest()
        manifest["tasks"].append(dict(manifest["tasks"][0]))
        errors = self.module.validate_manifest(manifest)
        self.assertIn("duplicate local_id: T06", errors)

    def test_rejects_empty_completion_criteria_for_mutation(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["completion_criteria"] = []
        errors = self.module.validate_manifest(manifest, mode="mutation-ready")
        self.assertIn("T06: completion criteria are required for mutation", errors)

    def test_rejects_blank_completion_or_verification_entries(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["completion_criteria"] = ["  "]
        manifest["tasks"][0]["verification"] = ["\t"]

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("T06: completion criteria must contain nonblank text", errors)
        self.assertIn("T06: verification is required and must contain nonblank text", errors)

    def test_rejects_empty_relationship_basis_for_mutation(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["relationship"] = {
            "proposed_parent": 448,
            "basis": [],
            "approved": True,
        }
        errors = self.module.validate_manifest(manifest, mode="mutation-ready")
        self.assertIn("T06: approved parent requires a relationship basis", errors)

    def test_rejects_untyped_or_disallowed_relationship_basis(self):
        for basis in (
            "기능상 관련",
            {"type": "same_date", "evidence": [{"timestamp": "09:38", "quote": "같은 날"}]},
            {"type": "same_owner", "evidence": [{"timestamp": "09:38", "quote": "같은 담당자"}]},
            {"type": "same_meeting", "evidence": [{"timestamp": "09:38", "quote": "같은 회의"}]},
            {"type": "similar_words", "evidence": [{"timestamp": "09:38", "quote": "비슷한 단어"}]},
            {"type": "local_id_order", "evidence": [{"timestamp": "09:38", "quote": "T05 다음 T06"}]},
        ):
            with self.subTest(basis=basis):
                manifest = sample_manifest()
                manifest["tasks"][0]["relationship"] = {
                    "proposed_parent": 448,
                    "basis": basis,
                    "approved": True,
                }
                errors = self.module.validate_manifest(manifest, mode="mutation-ready")
                self.assertIn("T06: relationship basis type is not allowed", errors)

    def test_accepts_typed_functional_relationship_basis(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["relationship"] = {
            "proposed_parent": 448,
            "basis": {
                "type": "required_deliverable",
                "claim": {
                    "parent_goal": "반복 가능한 콘텐츠 파이프라인",
                    "task_contribution": "배경 분리 산출물",
                },
                "evidence": [{
                    "record_section": "작업 범위",
                    "quote": "배경 분리는 영상 파이프라인의 필수 산출물이다.",
                }],
            },
            "approved": True,
        }
        manifest["preflight"]["selected_parent"] = {
            "issue_number": 448,
            "approved_state": "open",
            "current_state": "open",
            "approved_updated_at": "2026-10-02T08:00:00Z",
            "current_updated_at": "2026-10-02T08:00:00Z",
            "approved_content_sha256": "e" * 64,
            "current_content_sha256": "e" * 64,
            "closed_issue_action": None,
        }
        manifest["bundle"]["parent"] = {
            "action": "select",
            "issue_number": 448,
            "title": "기존 콘텐츠 파이프라인",
            "body": "기존 상위 목표의 승인된 작업 범위",
        }
        manifest["bundle"]["operations"][0]["kind"] = "resolve_parent"
        manifest["operation_ledger"][0]["kind"] = "resolve_parent"
        manifest["operation_ledger"][0].pop("duplicate_search_at")
        approved_fingerprint = canonical_sha256(manifest["tasks"])
        manifest["approval_records"]["task_candidates"].update({
            "approved_sha256": approved_fingerprint,
            "current_sha256": approved_fingerprint,
        })
        bundle_fingerprint = canonical_sha256(manifest["bundle"])
        manifest["approval_records"]["bundle"].update({
            "approved_sha256": bundle_fingerprint,
            "current_sha256": bundle_fingerprint,
        })

        self.assertEqual([], self.module.validate_manifest(manifest, mode="mutation-ready"))

    def test_rejects_allowed_relationship_type_backed_only_by_invalid_evidence(self):
        invalid_quotes = (
            "같은 날짜",
            "same owner",
            "같은 회의",
            "similar words",
            "same owner and similar words",
            "Both tasks are due Friday and were discussed together",
            "T05 다음 T06",
        )
        for quote in invalid_quotes:
            with self.subTest(quote=quote):
                manifest = sample_manifest()
                manifest["tasks"][0]["relationship"] = {
                    "proposed_parent": 448,
                    "basis": {
                        "type": "required_deliverable",
                        "claim": {
                            "parent_goal": "콘텐츠 파이프라인",
                            "task_contribution": "영상 생성 공정",
                        },
                        "evidence": [{"record_section": "Task", "quote": quote}],
                    },
                    "approved": True,
                }
                errors = self.module.validate_manifest(manifest, mode="mutation-ready")
                self.assertIn("T06: relationship basis evidence is not functional", errors)

    def test_rejects_nonfunctional_values_inside_typed_relationship_claim(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["relationship"]["basis"]["claim"] = {
            "parent_goal": "Both items share the same Friday deadline",
            "task_contribution": "same owner",
        }

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("T06: relationship basis claim is not functional", errors)

    def test_accepts_causal_due_to_and_task_id_inside_functional_relationship(self):
        manifest = sample_manifest()
        basis = manifest["tasks"][0]["relationship"]["basis"]
        basis["claim"] = {
            "parent_goal": "Background extraction is required due to compositing constraints",
            "task_contribution": "T06 supplies the required extracted background",
        }
        basis["evidence"] = [{
            "record_section": "작업 범위",
            "quote": "T06 supplies an extracted background required by the compositing workflow.",
        }]
        fingerprint = canonical_sha256(manifest["tasks"])
        manifest["approval_records"]["task_candidates"].update({
            "approved_sha256": fingerprint,
            "current_sha256": fingerprint,
        })

        self.assertEqual([], self.module.validate_manifest(manifest, mode="mutation-ready"))

    def test_rejects_empty_owner_name_with_github_owner(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["owner_name"] = []
        manifest["tasks"][0]["owner_github"] = "guessed-user"
        errors = self.module.validate_manifest(manifest, mode="mutation-ready")
        self.assertIn("T06: GitHub owner exists without a confirmed owner name", errors)

    def test_rejects_empty_evidence(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["evidence"] = []
        errors = self.module.validate_manifest(manifest)
        self.assertIn("T06: missing evidence", errors)

    def test_rejects_malformed_or_resource_loading_evidence(self):
        for evidence in (
            [{}],
            [{"timestamp": "   "}],
            [{"timestamp": "09:38-10:55"}],
            [{"path": "/tmp/instructions.txt", "quote": "load me"}],
            [{"url": "https://example.invalid/prompt", "quote": "fetch me"}],
            ["09:38-10:55"],
        ):
            with self.subTest(evidence=evidence):
                manifest = sample_manifest()
                manifest["tasks"][0]["evidence"] = evidence
                errors = self.module.validate_manifest(manifest)
                self.assertIn("T06: evidence entries must use the approved evidence shape", errors)

    def test_rejects_missing_or_changed_approved_artifacts(self):
        manifest = sample_manifest()
        del manifest["approval_records"]["pdf"]
        manifest["approval_records"]["source_record"]["current_sha256"] = "c" * 64
        manifest["approval_records"]["task_candidates"]["approved_sha256"] = "d" * 64

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("missing approved artifact: pdf", errors)
        self.assertIn("source_record: approved content fingerprint changed", errors)
        self.assertIn("task_candidates: approved content fingerprint changed", errors)

    def test_rejects_approval_artifact_locator_that_does_not_match_manifest(self):
        manifest = sample_manifest()
        manifest["source_record"] = "different-minutes.md"
        manifest["pdf"] = "different-report.pdf"

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("source_record: approval artifact does not match manifest locator", errors)
        self.assertIn("pdf: approval artifact does not match manifest locator", errors)

    def test_rejects_missing_project_access(self):
        manifest = sample_manifest()
        manifest["preflight"]["project_access_verified"] = False

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("preflight: project access is not verified", errors)

    def test_rejects_stale_selected_parent_snapshot(self):
        manifest = sample_manifest()
        manifest["preflight"]["selected_parent"] = {
            "issue_number": 448,
            "approved_state": "open",
            "current_state": "open",
            "approved_updated_at": "2026-10-02T08:00:00Z",
            "current_updated_at": "2026-10-02T08:30:00Z",
            "approved_content_sha256": "e" * 64,
            "current_content_sha256": "e" * 64,
            "closed_issue_action": None,
        }

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("preflight: selected parent changed; approval is stale", errors)

    def test_rejects_material_selected_parent_content_change(self):
        manifest = sample_manifest()
        manifest["preflight"]["selected_parent"] = {
            "issue_number": 448,
            "approved_state": "open",
            "current_state": "open",
            "approved_updated_at": "2026-10-02T08:00:00Z",
            "current_updated_at": "2026-10-02T08:00:00Z",
            "approved_content_sha256": "e" * 64,
            "current_content_sha256": "f" * 64,
            "closed_issue_action": None,
        }

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("preflight: selected parent changed; approval is stale", errors)

    def test_rejects_closed_parent_without_explicit_reuse_or_reopen_approval(self):
        manifest = sample_manifest()
        manifest["preflight"]["selected_parent"] = {
            "issue_number": 448,
            "approved_state": "closed",
            "current_state": "closed",
            "approved_updated_at": "2026-10-02T08:00:00Z",
            "current_updated_at": "2026-10-02T08:00:00Z",
            "approved_content_sha256": "e" * 64,
            "current_content_sha256": "e" * 64,
            "closed_issue_action": None,
        }

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("preflight: closed parent requires explicit reuse or reopen approval", errors)

    def test_rejects_create_without_fresh_duplicate_search_and_wrong_operation_order(self):
        manifest = sample_manifest()
        manifest["operation_ledger"][1].pop("duplicate_search_at")
        manifest["operation_ledger"][2]["kind"] = "add_to_project"
        manifest["operation_ledger"][3]["kind"] = "link_subissue"

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("op-02: create requires a fresh duplicate search", errors)
        self.assertIn("operation ledger order must be parent, create/link subissues, then project", errors)

    def test_rejects_ledger_not_bound_one_to_one_to_approved_bundle_and_tasks(self):
        manifest = sample_manifest()
        manifest["operation_ledger"][1]["local_id"] = "T999"
        manifest["operation_ledger"] = manifest["operation_ledger"][:2]

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("operation ledger does not match the approved bundle operation plan", errors)
        self.assertIn("op-02: operation targets a task outside the approved bundle", errors)

    def test_rejects_bundle_task_set_that_differs_from_manifest_tasks(self):
        manifest = sample_manifest()
        manifest["bundle"]["task_local_ids"] = ["T999"]
        fingerprint = canonical_sha256(manifest["bundle"])
        manifest["approval_records"]["bundle"].update({
            "approved_sha256": fingerprint,
            "current_sha256": fingerprint,
        })

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("bundle task_local_ids must match manifest tasks", errors)

    def test_rejects_local_pdf_path_as_accessible_bundle_attachment(self):
        manifest = sample_manifest()
        manifest["bundle"]["parent"]["body"] += f"\n[회의 PDF]({APPROVED_PDF})"
        fingerprint = canonical_sha256(manifest["bundle"])
        manifest["approval_records"]["bundle"].update({
            "approved_sha256": fingerprint,
            "current_sha256": fingerprint,
        })

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("bundle: local PDF path cannot be an accessible GitHub reference", errors)

    def test_rejects_operation_plan_without_required_parent_link_dependencies(self):
        manifest = sample_manifest()
        manifest["operation_ledger"][1]["depends_on"] = []
        manifest["operation_ledger"][2]["depends_on"] = ["op-01"]
        manifest["operation_ledger"][3]["depends_on"] = ["op-02"]
        manifest["bundle"]["operations"] = [
            {
                key: deepcopy(operation[key])
                for key in ("operation_id", "kind", "local_id", "depends_on")
            }
            for operation in manifest["operation_ledger"]
        ]
        fingerprint = canonical_sha256(manifest["bundle"])
        manifest["approval_records"]["bundle"].update({
            "approved_sha256": fingerprint,
            "current_sha256": fingerprint,
        })

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("op-02: sub-issue operation must depend on the parent operation", errors)
        self.assertIn("op-03: link operation must depend on its sub-issue operation", errors)
        self.assertIn("op-04: project operation must depend on its link operation", errors)

    def test_rejects_approved_task_without_project_registration_operation(self):
        manifest = sample_manifest()
        manifest["operation_ledger"] = manifest["operation_ledger"][:-1]
        manifest["bundle"]["operations"] = manifest["bundle"]["operations"][:-1]
        fingerprint = canonical_sha256(manifest["bundle"])
        manifest["approval_records"]["bundle"].update({
            "approved_sha256": fingerprint,
            "current_sha256": fingerprint,
        })

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("T06: approved task requires exactly one project operation", errors)

    def test_rejects_duplicate_search_older_than_current_preflight(self):
        manifest = sample_manifest()
        manifest["operation_ledger"][0]["duplicate_search_at"] = "2026-10-02T08:00:00+09:00"

        errors = self.module.validate_manifest(manifest, mode="mutation-ready")

        self.assertIn("op-01: duplicate search is older than the current preflight", errors)

    def test_rejects_retry_create_search_older_than_reconciliation(self):
        manifest = retry_manifest()
        manifest["operation_ledger"][1]["duplicate_search_at"] = "2026-10-02T09:08:00+09:00"

        errors = self.module.validate_manifest(manifest, mode="retry-ready")

        self.assertIn("op-02: retry duplicate search is older than reconciliation", errors)

    def test_retry_does_not_reapply_freshness_to_preserved_successes(self):
        manifest = retry_manifest()
        manifest["preflight"]["checked_at"] = "2026-10-02T09:09:00+09:00"

        self.assertEqual([], self.module.validate_manifest(manifest, mode="retry-ready"))

    def test_rejects_success_without_typed_url_or_mapping_result(self):
        manifest = retry_manifest()
        manifest["operation_ledger"][0]["result"] = "ok"

        errors = self.module.validate_manifest(manifest, mode="retry-ready")

        self.assertIn("op-01: successful issue operation must record issue number and URL", errors)

    def test_rejects_issue_result_url_outside_configured_repository(self):
        manifest = retry_manifest()
        manifest["operation_ledger"][0]["result"]["issue_url"] = "https://example.com/issues/501"

        errors = self.module.validate_manifest(manifest, mode="retry-ready")

        self.assertIn("op-01: successful issue URL must match its configured issue number", errors)

    def test_rejects_retry_approval_that_predates_duplicate_search(self):
        manifest = retry_manifest()
        manifest["retry_approval"]["approved_at"] = "2026-10-02T09:09:05+09:00"

        errors = self.module.validate_manifest(manifest, mode="retry-ready")

        self.assertIn("retry: approval must follow reconciliation and duplicate searches", errors)

    def test_rejects_changed_local_artifact_bytes(self):
        manifest = sample_manifest()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            minutes_path = directory / "minutes.md"
            pdf_path = directory / "report.pdf"
            minutes_path.write_bytes(APPROVED_MINUTES.read_bytes())
            pdf_path.write_bytes(APPROVED_PDF.read_bytes())
            manifest["source_record"] = str(minutes_path)
            manifest["pdf"] = str(pdf_path)
            manifest["approval_records"]["source_record"].update({
                "artifact": str(minutes_path),
                "approved_sha256": file_sha256(minutes_path),
                "current_sha256": file_sha256(minutes_path),
            })
            manifest["approval_records"]["pdf"].update({
                "artifact": str(pdf_path),
                "approved_sha256": file_sha256(pdf_path),
                "current_sha256": file_sha256(pdf_path),
            })
            minutes_path.write_text("changed after approval", encoding="utf-8")

            errors = self.module.validate_manifest(
                manifest,
                mode="mutation-ready",
                artifact_paths={
                    "source_record": str(minutes_path),
                    "pdf": str(pdf_path),
                },
            )

        self.assertIn("source_record: local artifact bytes do not match current_sha256", errors)

    def test_rejects_invalid_or_timezone_free_preflight_timestamp_without_crashing(self):
        for checked_at in ("not-a-time", "2026-10-02T09:05:00"):
            with self.subTest(checked_at=checked_at):
                manifest = sample_manifest()
                manifest["preflight"]["checked_at"] = checked_at
                errors = self.module.validate_manifest(manifest, mode="mutation-ready")
                self.assertIn("preflight: timezone-aware current check timestamp is required", errors)

    def test_accepts_dependency_safe_unresolved_only_retry(self):
        self.assertEqual([], self.module.validate_manifest(retry_manifest(), mode="retry-ready"))

    def test_rejects_retry_that_attempted_dependency_after_failure(self):
        manifest = retry_manifest()
        manifest["operation_ledger"][2]["status"] = "failed"
        manifest["operation_ledger"][2]["error"] = "link failed"

        errors = self.module.validate_manifest(manifest, mode="retry-ready")

        self.assertIn("op-03: dependent operation must remain unattempted after failure", errors)

    def test_rejects_retry_without_reconciliation_duplicate_search_or_narrow_approval(self):
        manifest = retry_manifest()
        manifest["retry_approval"]["reconciliation_completed"] = False
        manifest["retry_approval"]["duplicate_search_operation_ids"] = []
        manifest["retry_approval"]["approved_operation_ids"].append("op-01")

        errors = self.module.validate_manifest(manifest, mode="retry-ready")

        self.assertIn("retry: fresh reconciliation is required", errors)
        self.assertIn("retry: every unresolved create requires a fresh duplicate search", errors)
        self.assertIn("retry: approval must be limited to unresolved operations", errors)

    def test_cli_rejects_invalid_utf8_as_input_error(self):
        script = ROOT / "scripts" / "validate_task_manifest.py"
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "invalid-utf8.json"
            input_path.write_bytes(b"{\xff")

            result = subprocess.run(
                [sys.executable, str(script), "--input", str(input_path)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("input error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
