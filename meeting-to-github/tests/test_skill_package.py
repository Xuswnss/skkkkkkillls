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

    def test_reference_boundaries_are_explicit(self):
        rules = (ROOT / "references/approval-and-relationship-rules.md").read_text(encoding="utf-8")
        self.assertIn("날짜는 관계 근거가 아니다", rules)
        self.assertIn("최대 3개", rules)
        self.assertIn("부분 실패", rules)

    def test_issue_schema_separates_parent_and_sub_issue(self):
        schema = (ROOT / "references/github-issue-schema.md").read_text(encoding="utf-8")
        self.assertIn("## 상위 이슈", schema)
        self.assertIn("## 하위 이슈", schema)
        self.assertIn("기존 이슈 검색", schema)


if __name__ == "__main__":
    unittest.main()
