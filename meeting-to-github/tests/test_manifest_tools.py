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


if __name__ == "__main__":
    unittest.main()
