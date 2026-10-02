---
name: meeting-to-github
description: Convert Korean meeting recordings or exported transcripts into an approved Markdown meeting record, a verified PDF, person-by-person task candidates, and approval-gated GitHub parent issues and sub-issues. Use when meeting notes must become GitHub work without guessing owners, deadlines, or hierarchy.
---

# Meeting to GitHub

Use the approved Markdown record as the source of truth. Never create GitHub issues directly from an unapproved transcript.

## Default GitHub targets

- Repository: `DEVUNLIMIT/supernova-mobile`
- Project: `https://github.com/orgs/DEVUNLIMIT/projects/5`

## Routing

- For transcript interpretation, Markdown structure, and PDF content, read [references/minutes-schema.md](references/minutes-schema.md).
- For task extraction, issue formats, existing-issue search, and project registration, read [references/github-issue-schema.md](references/github-issue-schema.md).
- Before proposing relationships or any GitHub mutation, read [references/approval-and-relationship-rules.md](references/approval-and-relationship-rules.md).

## Required gates

1. Resolve material transcript ambiguity.
2. Draft the Markdown meeting record in the minutes schema, then obtain its approval.
3. Generate and inspect the PDF from that approved Markdown, then obtain its separate approval.
4. Draft person-by-person task candidates from the approved meeting record, then obtain their separate approval.
5. Build the task manifest from the approved candidates with `scripts/build_task_manifest.py`, then run `scripts/validate_task_manifest.py --mode draft`.
6. Search and select existing parent candidates.
7. Preview and approve one parent bundle at a time.
8. Run `scripts/validate_task_manifest.py --mode mutation-ready` immediately before the final mutation preview. If it reports any error, stop: do not write to GitHub.
9. Preview and approve the exact GitHub mutations as a final, separate gate.
10. After the approved mutations, report every created or linked issue URL and the complete local-ID-to-GitHub-issue mapping. On partial failure, include successful URLs and mappings, identify unresolved operations, and retry only those operations after a duplicate search.

Stop at the current gate until the user explicitly approves it. A later approval never retroactively approves changed content.
