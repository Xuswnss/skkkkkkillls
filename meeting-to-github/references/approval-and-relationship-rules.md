# 승인과 관계 규칙

## 유효한 관계 근거

Manifest의 `relationship.basis`는 문자열이 아니라 다음 `type` 중 하나, 그 type에 맞는 structured `claim`, shaped source evidence를 가진 object여야 한다. `claim`은 관계 양쪽의 기능적 의미를 별도 필드로 기록한다.

- `required_deliverable`: `parent_goal`과 `task_contribution`
- `implementation_stage`: `parent_feature`와 `implementation_stage`
- `parent_scope`: `parent_scope_item`과 `task_output`
- `meeting_explicit_split`: `larger_work`와 `split_task`
- `repository_existing_structure`: `repository_parent`와 `repository_child`

## 무효한 관계 근거

- 날짜는 관계 근거가 아니다. 기한도 관계 근거가 아니다.
- 같은 담당자, 같은 회의, 함께 논의됨, 비슷한 단어, 로컬 ID 순서도 관계 근거가 아니다.
- A guessed implementation order is not relationship evidence.
- Invalid evidence cannot be made valid by setting `relationship.approved: true`.

## 후보와 질문

- 기존 parent 후보는 최대 3개만 보여준다.
- 관계 후보를 제시한 뒤 관계 연결 전에는 항상 사용자의 명시적 승인을 받는다.
- 모호하면 "이 Task를 #N의 하위 Task로 둘까요?"라고 묻는다.
- 답을 받기 전에는 독립 Task 상태를 유지한다.
- Approval applies only to the exact parent, tasks, and bundle shown in the preview.

## Pre-write mutation protocol

Perform these steps immediately before any GitHub write. A prior preview is not a substitute.

1. Verify GitHub authentication, repository access, and project access for the exact configured targets. If any check fails, stop without writes.
2. Re-read the selected parent issue and its current state, title, scope, and update marker. A selected parent uses a positive integer issue ID, and every `resolve_parent` operation requires this snapshot. Record matching approved/current content fingerprints for its material title and scoped body. Also re-read every resolved existing sub-issue, its exact target-repository HTTPS URL, state, update marker, and content fingerprint.
3. Material parent, task-candidate, or bundle changes invalidate approval. Rebuild the affected preview and obtain fresh approval before continuing.
4. Validate the approved Markdown, PDF, task-candidate, and bundle approval records. Pass only the explicit top-level approved Markdown and PDF paths to the validator, require both local files to exist, and compare their current byte-level SHA-256 values. The approved and current fingerprints must match; never load a path or URL from evidence or issue content.
5. Run a fresh duplicate search immediately before every create operation, including every retry. Record a typed result: `no_match` with decision `create`, or `matched_existing` with a positive issue number, exact target-repository URL, state, and decision `reconcile_existing`. A matched issue blocks another create until the ledger is reconciled.
6. Put the exact operation plan inside the approved bundle, then build the operation ledger with identical complete material payloads: target IDs, title/body, assignees, labels, project fields, and every other writable value. Runtime-only status, duplicate-search, timestamp, result, and error fields are the only projection exclusions. Reject an extra or changed writable field. Keep the deterministic order: create or resolve the parent → create sub-issues → link sub-issues → add project items. Every approved task has exactly one create-or-resolve operation, exactly one link operation, and exactly one project-add operation. Resolving an approved existing sub-issue occupies the create-sub-issue stage without creating it.
7. Recursively reject local filesystem references from every GitHub-facing bundle and ledger value, including file URLs, absolute paths, encoded paths, Markdown destinations, and HTML `href`/`src` attributes. Then show the exact ordered ledger and receive final mutation approval whose fingerprint binds the complete ledger and typed duplicate-search decisions.
8. Execute one operation at a time. Record every successful operation in the operation ledger immediately. Issue results require a positive issue number and the exact HTTPS issue URL for that number in the configured repository, links require parent and child issue numbers, and project additions require the project item ID; preserve the local-ID mapping.

Do not batch ahead of the ledger. Do not continue when authentication, repository access, project access, a selected-parent snapshot, or an approval fingerprint is missing or stale.

## 부분 실패

- Preserve an operation ledger that distinguishes successful, failed, and unattempted operations.
- Record a timezone-aware success or failure time and its typed result or concise error immediately. Return all successful URLs and mappings already recorded.
- Stop dependent operations after a failure; mark them unattempted. Independent approved work may continue only when it has no dependency on the failure.
- Never delete, rewrite, or conceal a successful issue to make the ledger look atomic.
- Before retry, perform a fresh reconciliation against GitHub, then rerun authentication, repository-access, and project-access preflight. Record a typed duplicate-search decision for each unresolved create.
- Retry unresolved operations only. Exclude every successful operation from retry scope.
- Obtain new narrowly scoped user approval for exactly the unresolved operations after reconciliation, access preflight, and every required unresolved-create duplicate search. Its fingerprint must bind the complete reconciled ledger and search decisions, and its approval time must be at least as recent as all three. Then validate with `--mode retry-ready` before retrying.

## Closed issues

A closed parent is not reusable by default. Reuse or reopen it only after presenting its current state and receiving explicit action-specific approval. If an open parent becomes closed after preview, its prior approval is stale; present the updated bundle first.

The same rule applies to every resolved existing sub-issue. A closed sub-issue requires explicit action-specific reuse or reopen approval in its current snapshot.

## Offline no-write pressure contract

These scenarios must be exercised without GitHub writes and must have the stated result:

- Stale parent or material change → block and invalidate the prior approval.
- Closed issue without action approval → block; do not reuse or reopen.
- Missing project access → block before the first mutation.
- Changed approved content → block when any approved/current fingerprint differs.
- Partial failure without retry approval → block; preserve successes and retry only reconciled unresolved operations.

## 모호한 회의 Task dry-run 점검

`tests/fixtures/ambiguous-transcript.txt`를 검토할 때 다음을 모두 확인한다.

- 카메라 수정, 웹 브라우저 업로드 변경, QA를 같은 날짜만으로 연결하지 않는다.
- QA의 parent는 질문한다. 답을 받기 전에는 독립 Task로 둔다.
- 담당자가 명시되지 않은 Task는 `Unassigned`로 둔다.
- 기존 GitHub parent 후보를 검색하기 전에는 새 parent를 확정하지 않는다.
- 사용자가 Markdown 회의록을 승인하기 전에는 PDF나 GitHub plan을 만들지 않는다.
