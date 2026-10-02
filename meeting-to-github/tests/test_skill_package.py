from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillPackageTests(unittest.TestCase):
    def test_required_files_exist(self):
        required = [
            ROOT / "SKILL.md",
            ROOT / "agents/openai.yaml",
            ROOT / "references/minutes-schema.md",
            ROOT / "references/github-issue-schema.md",
            ROOT / "references/approval-and-relationship-rules.md",
        ]
        self.assertEqual([], [str(path) for path in required if not path.exists()])

    def test_skill_routes_to_each_reference(self):
        body = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in (
            "references/minutes-schema.md",
            "references/github-issue-schema.md",
            "references/approval-and-relationship-rules.md",
        ):
            self.assertIn(name, body)


if __name__ == "__main__":
    unittest.main()
