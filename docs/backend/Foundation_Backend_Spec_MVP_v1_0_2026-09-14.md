# FOUNDATION - ĐẶC TẢ BACKEND MVP
**Business Logic + Working Logic Specification**  
**Ngày cập nhật:** 14/09/2026  
**Repo baseline:** `master@41c92f7c775b12bf2dac5cf3091924d7dc293d24`  
**Contract baseline:** Foundation Contract v0.1.0 FROZEN  
**Trạng thái:** Backend Spec v1.0 đề xuất cho vertical MVP. Không tự thay Frozen Contract.

## 0. Mục đích

Backend phải biến business intent thành một governed, auditable change path. Spec này không mô tả "AI pipeline" theo technology stage, mà mô tả:
- business rules;
- authority;
- record ownership;
- runtime working logic;
- invalidation;
- API/read models;
- acceptance criteria.

### Non-goal
- không support mọi Local File / mọi Office construct;
- không dùng legacy direct writeback;
- không thêm enum/status vào Frozen Contract chỉ để khớp UI;
- không coi AI confidence là evidence;
- không coi generated DOCX là final nếu chưa validation/release.

## 1. Kiến trúc authority

```text
UI / Client
  -> Application API
     -> Business orchestration
        -> Frozen domain records / state / invariants
        -> Ports
           -> Preflight / Perception / Native Identity
           -> Source & Evidence evaluators
           -> AI semantic adapter
           -> Replay
           -> Validation
        -> Append-only persistence / Audit
```

### Quy tắc authority
1. Backend là source of truth cho lifecycle và allowed actions.
2. `BusinessTargetID != SemanticReference != NativeLocator`.
3. Mapping/AI không có execution authority.
4. Chỉ `ApprovedChangeSet` vào Replay.
5. Replay success không đồng nghĩa release.
6. Mọi input/policy/binding thay đổi phải invalidate đúng dependent approval.

## 2. Current repo alignment

Repo được rà soát tại `master@41c92f7c775b12bf2dac5cf3091924d7dc293d24`. Phương pháp audit dùng ba lớp: 
(1) `docs/CURRENT_BASELINE.md`, ADR và Foundation Contract v0.1 làm nguồn thẩm quyền; 
(2) audit component-level đã có tại `docs/backend/B0_REPOSITORY_AUDIT.md`; 
(3) so sánh toàn bộ delta từ B0 accepted đến current master và đọc lại các file active được thêm/sửa trong B1 và Frontend U0. 
Cách làm này cho phép bao phủ repository-wide mà không coi code legacy hoặc prototype là kiến trúc hiện hành.

### Giữ nguyên / phát huy
- `foundation/domain/*`;
- `foundation/governance/state/*`;
- `foundation/governance/invariants/*`;
- `foundation/audit/*`;
- `foundation/ports/*`;
- B1 preflight adapters;
- B1 qualification harness;
- generated frontend contract projection.

### Không dùng làm v2 authority
- legacy `foundation/output/writeback.py`;
- direct element PATCH;
- agent proposal -> action executor write path;
- legacy rollforward mutable manifest/state machine;
- fuzzy anchor fallback;
- generic confidence/editability flags.

### Adapt sau interface
- intake/hash/source-role mechanics;
- XLSX source profiling;
- data reconciliation algorithms;
- semantic binding candidate signals;
- package diff checks;
- persistence/storage infrastructure.

## 3. Application unit: ChangeCaseView

`ChangeCaseView` là read model, không phải Frozen Contract record.

Proposed fields:
```text
case_id
task_ref
business_target_id
business_label
target_region_ref
current_value
proposed_value
source_state
evidence_state
mapping_state
binding_state
review_state
dependency_state
execution_state
validation_state
blocking_reasons[]
allowed_actions[]
source_refs[]
evidence_refs[]
proposal_refs[]
decision_refs[]
impact_targets[]
updated_at
```

`allowed_actions` chỉ backend tính. Frontend không tự infer từ status.

## 4. Target baseline

Nếu workflow chỉ có Template + Prior LF + Current Sources:
1. register Template as `DocumentArtifact(role=TEMPLATE)`;
2. create a byte-identical target copy as `DocumentArtifact(role=TARGET)`;
3. target DocumentVersion `derived_from = template_version_ref`;
4. preflight exact target version;
5. all mutations bind to this target;
6. Prior LF remains `HISTORICAL_SOURCE`.

No auto-copy from Prior LF. Carry-forward requires rules/evidence and proposals.

## 5. Source & Evidence Logic

### Business rule
Source existence không bằng source sufficiency.

### SourceAssessment required checks
- permitted role;
- authority;
- applicable period;
- freshness;
- required fields;
- conflicts;
- ambiguity.

### Evidence flow
`EvidenceRecord -> EvidenceCheck -> EvidenceAssessment`

Mỗi deterministic evaluator phải pin:
- evaluator key;
- exact version;
- configuration ref.

### Manual evidence
Manual assertion phải thành governed content/evidence:
- actor;
- timestamp;
- target;
- period;
- rationale;
- authority;
- attachment/content ref nếu có.

Manual input không bypass deterministic gate.

## 6. Source Request working logic

Không cần object mới trong MVP.

```text
IN_REVIEW
 -> ReviewDecision.REQUEST_MORE_SOURCE
 -> AuditEvent.SOURCE_REQUESTED
 -> ChangeProposal BLOCKED
 -> DocumentVersion mới
 -> SourceAssessment PENDING -> ASSESSING -> COMPLETED
 -> EvidenceAssessment
 -> old Mapping/ChangeProposal SUPERSEDED
 -> new proposal
 -> READY_FOR_REVIEW
```

Backend query projection trả `SourceRequestView` với business stage:
`REQUEST / INTAKE / ASSESSMENT / EVIDENCE / REVISED_PROPOSAL`.

## 7. Mapping & Native Binding

### MappingProposal
Chứa business mapping hypothesis. Có thể BLOCKED/UNDER_REVIEW/ACCEPTED nhưng không execute.

### Formal ChangeProposal
Chỉ tạo khi:
- target document version pinned;
- target contract/rule pack pinned;
- mapping đủ rõ;
- exact native locator có thể tham chiếu;
- proposed/current values và operation/payload xác định;
- source/evidence assessments được bind.

Nếu mapping còn ambiguous, ChangeCase tồn tại nhưng chưa phải executable ChangeProposal.

## 8. Reviewer Edit / Reassessment

`EDIT` là application command.

Working logic:
1. verify reviewer authority;
2. record edit intent + reason in audit;
3. transition current proposal to `SUPERSEDED` khi phù hợp;
4. create revised proposal draft with new payload/value;
5. dependency service selects checks to rerun;
6. run source/evidence/rule/binding preconditions;
7. only after pass -> `READY_FOR_REVIEW`;
8. old ReviewDecision/ApprovedChangeSet cannot authorize revised payload.

UI derived label: `ĐANG_ĐÁNH_GIÁ_LẠI`.

## 9. DependencyIndex & Invalidation

### Minimal data model
Application persistence table/index:
```text
dependency_id
task_id
upstream_object_type
upstream_ref
downstream_object_type
downstream_ref
business_target_id
dependency_kind
created_at
```

No graph DB requirement.

### Dependency kinds
- SOURCE_INPUT
- TARGET_BINARY
- TARGET_CONTRACT
- RULE_PACK
- EVIDENCE
- MAPPING
- NATIVE_BINDING
- REVIEW_DECISION
- VALIDATION_OBLIGATION

### Invalidation engine
Input: changed/superseded Ref.  
Output:
- affected refs;
- action: REASSESS / SUPERSEDE / INVALIDATE_AUTHORIZATION / RERUN_VALIDATION;
- reason;
- scheduled AnalysisRuns.

### Critical rule
Không invalidate unrelated BusinessTargetID nếu không có dependency path.

## 10. Human Review Service

Commands:
- approve;
- reject;
- defer;
- request_more_source;
- edit_proposal.

Approval guard:
- proposal `IN_REVIEW`;
- blocking source/evidence gates pass;
- native binding exact;
- operation capability supported;
- target/input versions current;
- reviewer authority valid.

Human approval không override missing evidence/protection/unsupported operation.

## 11. ApprovedChangeSet Materializer

Input:
- APPROVED ChangeProposals;
- ReviewDecision refs;
- evidence/source assessments;
- exact native locators;
- target/source versions;
- validation plan.

Output:
- sealed `ApprovedChangeSet`;
- authorization digest.

Materializer không nhận arbitrary JSON từ frontend.

Any changed payload/evidence/policy/locator/version -> `INVALIDATED`.

## 12. Replay Service

Interface: existing `ReplayExecutor` port.

Admission:
1. ApprovedChangeSet still APPROVED;
2. target hash exact;
3. preflight capability still valid;
4. NativeLocator unique;
5. preconditions pass;
6. protected scope valid;
7. no concurrent execution conflict.

First vertical slice typed operations:
- `REPLACE_RUN_TEXT`;
- `REPLACE_SDT_TEXT`;
- `REPLACE_SIMPLE_TABLE_CELL_TEXT`.

Any unsupported case -> REFUSED, no best-effort fallback.

## 13. Independent Validation & Business Reconciliation

Validation service must be separately invoked from replay.

Mandatory checks:
- exact input/output version;
- schema/package;
- target postcondition;
- package diff;
- intra-part diff;
- protected scope;
- semantic re-perception where required;
- business postcondition;
- audit integrity.

Business reconciliation creates results per fact/target:
- reporting period consistency;
- NCP current-year consistency;
- RPT amount consistency;
- regulatory wording scope.

Golden comparison is a separate evaluation service and cannot modify validation/source verdict.

## 14. Processing Outcome, Release và Artifact

Current contract already separates:
- TaskStatus;
- ExecutionStatus;
- ValidationStatus;
- ReleaseStatus.

Release working logic:
- start `WITHHELD`;
- validation + required target gates pass -> `ELIGIBLE`;
- atomic publication -> `RELEASED`;
- contrary evidence -> new WITHHELD projection + quarantine event.

Output DocumentArtifact:
- `STAGED` after replay;
- `RELEASED` only through release gate;
- `QUARANTINED` when validation/new evidence fails.

## 15. Proposed Application APIs

Các endpoint này là **application API proposal**, không tự sửa frozen OpenAPI.

```text
POST /v2/tasks/local-file-roll-forward
POST /v2/tasks/{task}/inputs
GET  /v2/tasks/{task}/readiness
POST /v2/tasks/{task}/analysis-runs
GET  /v2/tasks/{task}/change-cases
GET  /v2/tasks/{task}/change-cases/{business_target_id}
POST /v2/change-proposals/{id}/review
POST /v2/change-proposals/{id}/edit
POST /v2/change-proposals/{id}/request-source
POST /v2/tasks/{task}/approved-change-sets
POST /v2/approved-change-sets/{id}/execute
POST /v2/executions/{id}/validate
GET  /v2/tasks/{task}/result
GET  /v2/tasks/{task}/artifacts
GET  /v2/tasks/{task}/audit
```

Responses to UI must include `allowed_actions` and plain-language blocker reasons.

## 16. Persistence

Required:
- append-only domain snapshots/revisions;
- immutable DocumentVersion/content;
- AuditEvent;
- DependencyIndex;
- application read-model projections;
- output artifact bytes;
- idempotency keys;
- evaluator/model/configuration identities.

Không dùng `latest` alias làm execution authority. Mọi execution path phải resolve exact Ref/hash.

## 17. AI Boundary

AI adapter chỉ nhận bounded context:
- business target;
- candidate sources;
- relevant semantic excerpts;
- rule context;
- explicit task.

AI output:
- structured classification/hypothesis/draft;
- provenance/context refs;
- provider/model/prompt version.

AI cannot:
- write document;
- mark evidence VERIFIED;
- select arbitrary target;
- approve;
- release.

## 18. Security / Privacy

- zip bomb/resource limits;
- malware scanning integration point;
- external relationship/macro policy;
- prompt injection separation;
- approved AI provider only;
- retention/data residency policy;
- tenant/task isolation;
- audit access control;
- no sensitive data in public qualification artifacts.

## 19. Acceptance Criteria cho vertical slice

| ID | Acceptance |
|---|---|
| BE-01 | Target baseline được version/hash đúng và không chỉnh source binary. |
| BE-02 | 3-5 Business Targets có Target Contract/Rule/Source Requirement. |
| BE-03 | Missing/conflicting source không tạo executable change. |
| BE-04 | Reviewer Edit không reuse approval cũ. |
| BE-05 | Source thay đổi chỉ invalidate affected targets. |
| BE-06 | Mapping ambiguity không lọt vào ApprovedChangeSet. |
| BE-07 | ApprovedChangeSet là duy nhất input cho replay. |
| BE-08 | Supported mutation tạo actual STAGED DOCX. |
| BE-09 | Unauthorized business/structural changes = 0 trong qualified corpus. |
| BE-10 | Validation fail/inconclusive giữ release WITHHELD. |
| BE-11 | Golden mismatch không sửa root-cause verdict. |
| BE-12 | Audit tái dựng được full lineage. |

## 20. Backend build order

1. Documentation/governance sync.
2. Run-002 representative qualification.
3. ChangeCase read model + DependencyIndex design.
4. Target Contract/Rule/Source for selected targets.
5. Native identity/binding.
6. Source/Evidence engines.
7. Review service.
8. ApprovedChangeSet materialization.
9. Replay.
10. Validation/reconciliation/release.
11. E2E evaluation.

## 21. Nguồn

| Nguồn | Vai trò |
|---|---|
| GitHub repository `master@41c92f7` | Current implementation evidence và source code audit. |
| `docs/CURRENT_BASELINE.md` | Architecture authority hiện hành. |
| `docs/contracts/*` + ADR-001...ADR-005 | Frozen contract, identity, state, authority và replay boundaries. |
| `docs/backend/B0_REPOSITORY_AUDIT.md` | Component-level migration/audit baseline. |
| B1 implementation/qualification reports + representative summary | Current preflight/perception evidence và open gates. |
| UI Product Principles + UI Backend Dependency Matrix | Accepted frontend authority boundary và capability availability. |
| Foundation Research Consolidated 07/09/2026 | Research/technical baseline trước meeting. |
| Foundation Implementation Plan 07/09/2026 | Plan baseline trước cập nhật. |
| Project Summary after Khang Review 10/09/2026 | Meeting decisions, corrections và product direction. |
| Foundation Clean MVP v4 | UX/prototype evidence; không phải production capability. |
