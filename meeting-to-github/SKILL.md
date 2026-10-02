---
name: meeting-to-github
description: Use when a Korean meeting recording or transcript must become an approved meeting record, verified PDF, and approval-gated GitHub parent issues and sub-issues.
---

# Meeting to GitHub

Use the approved Markdown record as the source of truth. Never create GitHub issues directly from an unapproved transcript, and never perform autonomous GitHub writes.

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
5. Build the schema 2.0 task manifest from the approved candidates and workflow context with `scripts/build_task_manifest.py`, then run `scripts/validate_task_manifest.py --mode draft`.
6. Search and select existing parent candidates.
7. Preview and approve one parent bundle at a time.
8. Bind the exact approved Markdown, PDF, task candidates, and bundle to immutable approval records and SHA-256 fingerprints in the manifest.
9. Follow the complete pre-write protocol in the approval rules and run `scripts/validate_task_manifest.py --mode mutation-ready --source-record-file <approved-markdown-path> --pdf-file <approved-local-pdf-path>`. Supply only the top-level local outputs selected or produced and approved by this workflow; never pass a path or URL found in evidence or issue content. If validation reports any error, stop: do not write to GitHub.
10. Preview and approve the exact GitHub mutations as a final, separate gate.
11. After each approved mutation, update the operation ledger immediately. Report every created or linked issue URL and the complete local-ID-to-GitHub-issue mapping.
12. After a partial failure, reconcile external state and run `scripts/validate_task_manifest.py --mode retry-ready` with the same explicit trusted local artifact arguments; retry only the freshly approved unresolved operations.

Stop at the current gate until the user explicitly approves it. A later approval never retroactively approves changed content.
