# GitHub 이슈 계약

기본 대상은 `DEVUNLIMIT/supernova-mobile`와 `https://github.com/orgs/DEVUNLIMIT/projects/5`이다. 누락된 완료 조건이나 테스트 시나리오는 지어내지 않고 질문 대상으로 표시한다. 담당자, 기한, 라벨, 프로젝트 필드를 추측하지 않는다. 확인되지 않은 값은 질문 대상으로 표시하거나 미설정으로 둔다.

## 상위 이슈

- 작업 유형
- 문제·배경
- 목표
- 작업 범위
- 완료 조건
- 테스트 시나리오
- 참고

Every completion criterion must be nonblank and observable. Every test scenario must state a concrete verification or review procedure; missing data blocks mutation readiness.

## 하위 이슈

- 상위 목표
- 작업 내용
- 제외 범위
- 완료 조건
- 확인 방법
- 관계
- 근거

Each sub-issue has one outcome, nonblank completion criteria, nonblank verification steps, shaped meeting-record evidence, and a typed relationship basis with the type-specific functional claim fields defined in the approval rules when a parent is proposed.

## 담당자 매핑

`owner_github` requires an exact `owner_name` plus `assignee_mapping_provenance` with matching values, `source: explicit-user-confirmation`, confirmer, and confirmation time. A plausible name/login pair without that provenance is not assignable.

## 기존 이슈 검색

기존 이슈 검색은 `open → Project 5 포함 항목 → closed` 순서로 수행한다. 기능 목표·제품·산출물·범위·상태를 기준으로 최대 3개 후보를 제안한다.

Every candidate contains all of these details:

- URL
- title
- state
- match rationale based on functional goal, product/module, deliverable, and scope
- material mismatch risk
- recommendation to select, reject, or ask the user

A closed candidate requires explicit approval to reuse or reopen. Never infer that approval from candidate selection or prior issue history.

## Bundle references

A local PDF path is never an accessible GitHub attachment. It may remain in the local manifest as an approved artifact locator, but the GitHub issue body may include the PDF only when an approved, accessible publication URL or actual uploaded attachment exists. Never disguise a local filesystem path as a link.

The exact repository, project URL, parent action/title/body, one sub-issue title/body per approved local task ID, accessible HTTPS references, relationships, assignees, labels, project fields, and ordered operation plan form the bundle. Fingerprint that bundle and obtain approval for the same fingerprint used at mutation time. The runtime ledger may add searches, statuses, timestamps, errors, and typed results, but its complete material projection must match the approved bundle operation plan exactly. Each approved task maps to exactly one create-or-resolve, one link, and one project-add operation. A successful issue result URL must be the HTTPS URL for its recorded number in the configured repository.

Every bundle operation and runtime ledger operation carries the same complete material payload. That payload includes all writable targets and values: repository or project, issue IDs or local references, title, body, assignees, labels, and project fields as applicable. Only runtime status, typed duplicate-search data, recorded result/error, and timestamps may differ. Local filesystem references are forbidden recursively in GitHub-facing bundle and ledger content, including encoded/file URLs and Markdown or HTML link destinations.

`resolve_parent` and `resolve_subissue` never accept string or nonpositive issue IDs. A resolved sub-issue includes its exact `https://github.com/DEVUNLIMIT/supernova-mobile/issues/{number}` URL and matching approved/current state, update marker, content fingerprint, and timezone-aware check time. Closed reuse or reopen requires explicit action-specific approval.
