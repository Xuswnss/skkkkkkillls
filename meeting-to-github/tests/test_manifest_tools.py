from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample_manifest():
    return {
        "schema_version": "1.0",
        "meeting_id": "2026-09-28",
        "source_record": "minutes.md",
        "pdf": "minutes.pdf",
        "tasks": [{
            "local_id": "T06",
            "title": "K-pop 영상 파이프라인 구축",
            "topic": "콘텐츠",
            "owner_name": None,
            "owner_github": None,
            "due_date": None,
            "outcome": "반복 가능한 영상 생성 공정",
            "completion_criteria": ["샘플 영상 생성과 검수 완료"],
            "verification": ["승인된 샘플을 재생해 영상과 배경을 확인"],
            "evidence": [{"timestamp": "09:38-10:55"}],
            "relationship": {"proposed_parent": None, "basis": None, "approved": False},
            "github": {"issue_number": None, "url": None, "project_item_id": None},
        }],
    }


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
        self.assertEqual("1.0", manifest["schema_version"])
        self.assertIsNone(manifest["tasks"][0]["owner_github"])
        self.assertIsNone(manifest["tasks"][0]["due_date"])

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
                    "schema_version": "1.0",
                    "meeting_id": "2026-09-28",
                    "source_record": "minutes.md",
                    "pdf": "minutes.pdf",
                    "tasks": tasks,
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
            "approved PDF path or accessible URL",
            "task candidate JSON array file",
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

    def test_rejects_unapproved_parent_for_mutation(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["relationship"] = {
            "proposed_parent": 448,
            "basis": "같은 날짜",
            "approved": False,
        }
        errors = self.module.validate_manifest(manifest, mode="mutation-ready")
        self.assertIn("T06: proposed parent is not approved", errors)

    def test_rejects_github_owner_without_confirmed_name(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["owner_github"] = "guessed-user"
        errors = self.module.validate_manifest(manifest, mode="mutation-ready")
        self.assertIn("T06: GitHub owner exists without a confirmed owner name", errors)

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

    def test_rejects_empty_relationship_basis_for_mutation(self):
        manifest = sample_manifest()
        manifest["tasks"][0]["relationship"] = {
            "proposed_parent": 448,
            "basis": [],
            "approved": True,
        }
        errors = self.module.validate_manifest(manifest, mode="mutation-ready")
        self.assertIn("T06: approved parent requires a relationship basis", errors)

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
