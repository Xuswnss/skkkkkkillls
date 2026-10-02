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

    def test_default_github_targets_are_defined(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        schema = (ROOT / "references/github-issue-schema.md").read_text(encoding="utf-8")
        for target in (
            "DEVUNLIMIT/supernova-mobile",
            "https://github.com/orgs/DEVUNLIMIT/projects/5",
        ):
            self.assertIn(target, skill)
            self.assertIn(target, schema)

    def test_relationships_require_explicit_approval_before_linking(self):
        rules = (ROOT / "references/approval-and-relationship-rules.md").read_text(encoding="utf-8")
        self.assertIn("관계 연결 전에는 항상 사용자의 명시적 승인을 받는다", rules)
        self.assertIn("답을 받기 전에는 독립 Task 상태를 유지한다", rules)

    def test_issue_schema_forbids_guessing_mutation_fields(self):
        schema = (ROOT / "references/github-issue-schema.md").read_text(encoding="utf-8")
        self.assertIn("담당자, 기한, 라벨, 프로젝트 필드를 추측하지 않는다", schema)
        self.assertIn("질문 대상으로 표시하거나 미설정으로 둔다", schema)

    def test_report_template_has_required_semantics(self):
        html = (ROOT / "assets/meeting-report-template/template.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/meeting-report-template/styles.css").read_text(encoding="utf-8")
        for token in ("<main", "meeting-cover", "meeting-section", "open-questions"):
            self.assertIn(token, html)
        self.assertIn("@page", css)
        self.assertIn("size: A4", css)
        self.assertIn("break-inside: avoid", css)


if __name__ == "__main__":
    unittest.main()
