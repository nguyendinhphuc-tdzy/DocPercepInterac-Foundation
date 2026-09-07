# Foundation v2 Status Model

**Contract version:** 2.0.0  
**Date:** 2026-09-07

## Transition rules

The tables below are exhaustive allowed edges. A comma-separated source or destination expands to individual edges with the same guard; no other transition is legal. Every transition requires the named guard, authenticated authority, optimistic revision matching and an AuditEvent. An unknown or forbidden transition returns INVALID_STATE_TRANSITION without changing the historical record.

Statuses are server-owned projections of append-only events and immutable snapshots. A status is never proof of authorization. Human/AI clients cannot PATCH status fields. Repeated reads and duplicate idempotent requests do not create transitions.

Initial states can only be created by the responsible service. Terminal outcomes are not rewritten. Where new evidence is required, create a new evaluation, proposal, attempt, decision or successor task, and retain links to the prior record. Completion of a historical task does not suppress later exceptions or quarantine of its released document.

Verification, approval, execution success and release are separate dimensions:

- VERIFIED is a deterministic EvidenceAssessment or TargetRegion verdict, not a model score.
- APPROVED on ChangeProposal records a review outcome but has zero execution authority.
- ApprovedChangeSet is the only native mutation authorization; its latest eligibility must still be checked.
- SUCCEEDED means mechanical replay completed into staging.
- PASSED means required independent checks passed for the report's approved scope.
- RELEASED additionally requires all task-required targets and release gates.

## Legal lifecycles

### Task

Enum: TaskStatus. Initial: CREATED. Terminal: COMPLETED, FAILED, CANCELLED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| CREATED | ANALYZING, CANCELLED | Orchestrator accepts pinned inputs or records cancellation. |
| ANALYZING | AWAITING_REVIEW, BLOCKED, FAILED, CANCELLED | Deterministic analysis completes, records gaps, fails or cancels. |
| AWAITING_REVIEW | READY_FOR_EXECUTION, BLOCKED, CANCELLED | Explicit review and all gates produce an eligible set; otherwise block. |
| READY_FOR_EXECUTION | EXECUTING, BLOCKED, CANCELLED | Recheck set eligibility and input hash; do not infer authority from task status. |
| EXECUTING | VALIDATING, BLOCKED, FAILED | Staged success proceeds to independent validation; refusal/failure records exceptions. |
| VALIDATING | COMPLETED, BLOCKED, FAILED | Complete only if every required target and release gate passes; partial valid results remain blocked. |
| BLOCKED | ANALYZING, AWAITING_REVIEW, READY_FOR_EXECUTION, CANCELLED | New evidence or a separately eligible in-scope subset allows governed progress; unrelated blockers still withhold whole-document release. |

### Document

Enum: DocumentStatus. Initial: REGISTERED (input), STAGED (generated output). Terminal: REJECTED, SUPERSEDED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| REGISTERED | PREFLIGHTING, REJECTED | Intake registers immutable binary then inspects it. |
| PREFLIGHTING | READY, BLOCKED, REJECTED | Capability/protection/format detection is explicit. |
| READY | BLOCKED, SUPERSEDED | A new version supersedes selection; new risk blocks its use. |
| BLOCKED | PREFLIGHTING, SUPERSEDED, REJECTED | Recorded remediation permits a new inspection; no silent support upgrade. |
| STAGED | RELEASED, QUARANTINED | Only the release gate can publish; failure or unauthorized change quarantines. |
| QUARANTINED | STAGED, SUPERSEDED | New independent evidence and authorized remediation may return the same unchanged binary to staging; never directly release. |
| RELEASED | QUARANTINED, SUPERSEDED | New findings withdraw availability by a new event; historical release evidence is retained. |

### SourceAssessment

Enum: SourceAssessmentStatus. Initial: PENDING. Terminal: SUPERSEDED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| PENDING | ASSESSING, SUPERSEDED | Deterministic sufficiency evaluator starts or input is replaced. |
| ASSESSING | SUFFICIENT, INSUFFICIENT, CONFLICTED, STALE | Check all required fields, authority, roles, period, consistency and source versions. |
| SUFFICIENT | STALE, SUPERSEDED | New source/version/policy evidence invalidates applicability or replaces assessment. |
| INSUFFICIENT, CONFLICTED, STALE | SUPERSEDED | Create a new assessment for new inputs; do not overwrite the failed finding. |

### MappingProposal

Enum: MappingProposalStatus. Initial: PROPOSED. Terminal: REJECTED, SUPERSEDED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| PROPOSED | UNDER_REVIEW, BLOCKED, SUPERSEDED | Mapping candidate enters governed review or a gap blocks it. |
| UNDER_REVIEW | ACCEPTED, BLOCKED, REJECTED, SUPERSEDED | Deterministic evidence and explicit review resolve the association. |
| BLOCKED | UNDER_REVIEW, REJECTED, SUPERSEDED | Documented remediation and rechecked evidence; changed mapping content is a new revision. |
| ACCEPTED | SUPERSEDED | A revised association needs renewed downstream approval; acceptance itself never authorizes execution. |

### ChangeProposal

Enum: ChangeProposalStatus. Initial: DRAFT. Terminal: REJECTED, SUPERSEDED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| DRAFT | READY_FOR_REVIEW, BLOCKED, SUPERSEDED | Exact candidate payload, native identity and evidence are complete or explicitly blocked. |
| BLOCKED | READY_FOR_REVIEW, SUPERSEDED | Deterministic re-evaluation removes all blockers; no human override of missing evidence or protection. |
| READY_FOR_REVIEW | IN_REVIEW, BLOCKED, SUPERSEDED | Human review opens; changed inputs may block or supersede. |
| IN_REVIEW | APPROVED, REJECTED, BLOCKED, SUPERSEDED | Explicit ReviewDecision and current deterministic gates; DEFER leaves IN_REVIEW or BLOCKED when there is a blocker. |
| APPROVED | SUPERSEDED | Any payload, policy, evidence or target binding change invalidates dependent authorization; proposal status is never replay authority. |

### ApprovedChangeSet

Enum: ApprovedChangeSetStatus. Initial: APPROVED (governance materialization only). Terminal: RELEASED, INVALIDATED, REVOKED, FAILED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| APPROVED | EXECUTING, INVALIDATED, REVOKED | Admission validates sealed content, human decisions, exact hash and current eligibility; start EXECUTING only after preflight passes. |
| EXECUTING | EXECUTED, FAILED, INVALIDATED | Complete all approved mechanical operations or quarantine failure; concurrent invalidation prevents release. |
| EXECUTED | VALIDATED, FAILED, INVALIDATED | Independent mandatory validation passes or records a failure/invalidation. An INCONCLUSIVE report leaves EXECUTED and withholds release. |
| VALIDATED | RELEASED, INVALIDATED, REVOKED | Whole-task release checks pass or a new blocker revokes eligibility. |

### Execution

Enum: ExecutionStatus. Initial: QUEUED. Terminal: SUCCEEDED, REFUSED, FAILED, CANCELLED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| QUEUED | PREFLIGHTING, CANCELLED | Orchestrator starts an identified dispatch. |
| PREFLIGHTING | RUNNING, REFUSED, CANCELLED | Only eligible ApprovedChangeSet and unique exact locators can run. |
| RUNNING | SUCCEEDED, FAILED | Engine stages the exact approved changes or quarantines partial/uncertain output. No automatic running cancellation that evades validation. |

### Validation

Enum: ValidationStatus. Initial: PENDING. Terminal: PASSED, FAILED, INCONCLUSIVE, CANCELLED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| PENDING | RUNNING, CANCELLED | Independent validator accepts exact input, output and plan. |
| RUNNING | PASSED, FAILED, INCONCLUSIVE, CANCELLED | All mandatory checks PASS -> PASSED; any violation -> FAILED; unavailable evidence -> INCONCLUSIVE. Cancellation and inconclusive results withhold release. |

### Exception

Enum: ExceptionStatus. Initial: OPEN. Terminal: CLOSED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| OPEN | ACKNOWLEDGED, REMEDIATION_PENDING | Owner acknowledges or begins recorded remediation. |
| ACKNOWLEDGED | REMEDIATION_PENDING | A recorded action addresses the underlying cause. |
| REMEDIATION_PENDING | RESOLVED, OPEN | New evidence and deterministic rechecks resolve the cause, or unsuccessful remediation reopens it. |
| RESOLVED | CLOSED, OPEN | Governance records verified closure or reopens after contrary evidence. |

### AnalysisRun

Enum: AnalysisStatus. Initial: QUEUED. Terminal: COMPLETED, BLOCKED, FAILED, CANCELLED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| QUEUED | RUNNING, CANCELLED | Orchestrator admits pinned analysis inputs. |
| RUNNING | COMPLETED, BLOCKED, FAILED, CANCELLED | Analysis publishes typed outputs, records blockers or fails. COMPLETED describes run completion, not target verification. |

## Supporting state semantics

BindingStatus progresses from PROPOSED to RESOLVED, AMBIGUOUS or UNSUPPORTED only after native inspection. New mappings are new revisions. RESOLVED does not imply a one-to-one semantic/native relationship; unique native resolution is enforced per ApprovedChange.

EvidenceStatus begins UNASSESSED. A deterministic assessment can produce VERIFIED, INSUFFICIENT, CONFLICTED or STALE. A VERIFIED assessment becomes STALE when its inputs cease to apply; changed evidence requires a new assessment. AI cannot author these transitions.

TargetVerificationStatus begins UNVERIFIED; deterministic current evidence permits VERIFIED, missing/conflicting evidence gives BLOCKED, and superseded inputs give STALE. Re-evaluation, not human acceptance of a score, is required to leave BLOCKED or STALE.

ReviewOutcome is an immutable decision, not a lifecycle. APPROVE is the approval outcome. DEFER cannot issue authorization. Supersession creates a new ReviewDecision and event.

CheckOutcome PASS is necessary for each mandatory validation check. FAIL and BLOCKED prevent passage. NOT_APPLICABLE is permissible only for an explicitly optional plan requirement with a recorded reason; it cannot satisfy a mandatory requirement.

ReleaseStatus begins WITHHELD. The independent release gate may set ELIGIBLE only after validation and all task-required targets pass. Atomic publication sets RELEASED. New contrary evidence creates a new WITHHELD projection and quarantine event; prior release records remain immutable.

## Retry, concurrency and invalidation

- The same execution_id and same ApprovedChangeSet reference is idempotent: return the same attempt, never apply the mutation twice. The same identity with different content returns IDEMPOTENCY_CONFLICT.
- Preflight refusal with no mutation may be retried using a new execution_id only after the cause is resolved and the same authorization is still eligible. Stale inputs or changed authorization require a new approved set.
- A RUNNING, SUCCEEDED or uncertain prior attempt prevents another concurrent attempt for the same set and input. EXECUTION_CONFLICT blocks admission. Partial/uncertain mutation is quarantined; no blind retry.
- A transient validation failure can create a new ValidationReport for the same staged output and plan. This does not replay the mutation or overwrite the prior report.
- A stale hash returns STALE_DOCUMENT_VERSION and REFUSED; the affected set is INVALIDATED. Changed evidence, rule/contract revisions, locators, payloads, pre/postconditions, protected scope or validation obligations invalidate affected approval.
- Revocation is a new explicit human/governance event. Neither revocation nor human override rewrites an earlier approval, AI interaction or machine evidence.
- A valid numeric-only change may advance independently of a blocked conclusion only if its own source requirements and preservation checks pass. The task returns to BLOCKED and release remains WITHHELD while any required target is unresolved.

## Canonical enum registry

Every closed vocabulary in domain, error, event, API and example contracts is defined here. ObjectType uses domain class names. Free-form names such as model IDs, periods and descriptions are identifiers or text, not enums. ErrorCode values are enumerated with their full semantics in error-catalog.md; this file imports that closed ErrorCode vocabulary.

### SchemaVersion

`2.0.0`.

### TaskStatus

`CREATED`, `ANALYZING`, `AWAITING_REVIEW`, `READY_FOR_EXECUTION`, `EXECUTING`, `VALIDATING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELLED`.

### DocumentStatus

`REGISTERED`, `PREFLIGHTING`, `READY`, `BLOCKED`, `REJECTED`, `SUPERSEDED`, `STAGED`, `RELEASED`, `QUARANTINED`.

### SourceAssessmentStatus

`PENDING`, `ASSESSING`, `SUFFICIENT`, `INSUFFICIENT`, `CONFLICTED`, `STALE`, `SUPERSEDED`.

### MappingProposalStatus

`PROPOSED`, `UNDER_REVIEW`, `ACCEPTED`, `BLOCKED`, `REJECTED`, `SUPERSEDED`.

### ChangeProposalStatus

`DRAFT`, `BLOCKED`, `READY_FOR_REVIEW`, `IN_REVIEW`, `APPROVED`, `REJECTED`, `SUPERSEDED`.

### ApprovedChangeSetStatus

`APPROVED`, `EXECUTING`, `EXECUTED`, `VALIDATED`, `RELEASED`, `INVALIDATED`, `REVOKED`, `FAILED`.

### ExecutionStatus

`QUEUED`, `PREFLIGHTING`, `RUNNING`, `SUCCEEDED`, `REFUSED`, `FAILED`, `CANCELLED`.

### ValidationStatus

`PENDING`, `RUNNING`, `PASSED`, `FAILED`, `INCONCLUSIVE`, `CANCELLED`.

### ExceptionStatus

`OPEN`, `ACKNOWLEDGED`, `REMEDIATION_PENDING`, `RESOLVED`, `CLOSED`.

### AnalysisStatus

`QUEUED`, `RUNNING`, `COMPLETED`, `BLOCKED`, `FAILED`, `CANCELLED`.

### DocumentRole

`TARGET`, `CURRENT_SOURCE`, `HISTORICAL_SOURCE`, `TEMPLATE`, `EVALUATION_ONLY`, `GENERATED_OUTPUT`.

### DocumentFormat

`DOCX`, `XLSX`, `PDF`, `IMAGE`.

### ConformanceClass

`TRANSITIONAL`, `STRICT`, `UNKNOWN`, `NOT_APPLICABLE`.

### CapabilityStatus

`SUPPORTED`, `PROTECTED`, `UNSUPPORTED`, `UNKNOWN`.

### BindingStatus

`PROPOSED`, `RESOLVED`, `AMBIGUOUS`, `UNSUPPORTED`.

### EvidenceStatus

`UNASSESSED`, `VERIFIED`, `INSUFFICIENT`, `CONFLICTED`, `STALE`.

### TargetVerificationStatus

`UNVERIFIED`, `VERIFIED`, `BLOCKED`, `STALE`.

### CheckOutcome

`PASS`, `FAIL`, `BLOCKED`, `NOT_APPLICABLE`.

### ReviewOutcome

`APPROVE`, `REJECT`, `DEFER`.

### ActorType

`HUMAN`, `SYSTEM`, `AI`, `REPLAY_ENGINE`, `VALIDATOR`.

### ReleaseStatus

`WITHHELD`, `ELIGIBLE`, `RELEASED`.

### ChangeExecutionStatus

`APPLIED`, `REFUSED`, `FAILED`, `NOT_ATTEMPTED`.

### MutationOperation

`REPLACE_RUN_TEXT`, `REPLACE_SDT_TEXT`, `REPLACE_SIMPLE_TABLE_CELL_TEXT`.

### LocatorType

`CONTENT_CONTROL`, `BOOKMARK`, `PART_PATH`, `SHEET_CELL`.

### ValueKind

`TEXT`, `DECIMAL`.

### ValueUnit

`NONE`, `PERCENT`.

### EvidenceKind

`NATIVE_VALUE`, `FORMULA_IDENTITY`, `SOURCE_EXCERPT`, `VALIDATION_OUTPUT`.

### SourceAuthority

`AUTHORITATIVE`, `CONTEXT_ONLY`, `UNDETERMINED`.

### AssessmentMethod

`DETERMINISTIC`.

### ConditionKind

`BINARY_HASH_EQUALS`, `TEXT_EQUALS`, `VALUE_EQUALS`, `CAPABILITY_SUPPORTED`, `EVIDENCE_VERIFIED`, `PRESERVE_SCOPE`.

### ValidationCheckKind

`SCHEMA_PACKAGE`, `PACKAGE_DIFF`, `INTRA_PART_DIFF`, `PROTECTED_SCOPE`, `SEMANTIC_REPERCEPTION`, `BUSINESS_POSTCONDITION`.

### Layer

`CONTRACT`, `INTAKE`, `PERCEPTION`, `NATIVE_IDENTITY`, `SOURCE`, `EVIDENCE`, `MAPPING`, `REVIEW`, `AUTHORIZATION`, `EXECUTION`, `VALIDATION`, `AUDIT`.

### Severity

`INFO`, `WARNING`, `ERROR`, `CRITICAL`.

### SystemAction

`REJECT_REQUEST`, `REFUSE_EXECUTION`, `BLOCK_PROPOSAL`, `REQUEST_SOURCE`, `REQUIRE_REVIEW`, `REANALYZE`, `QUARANTINE_OUTPUT`, `RETRY_WITH_BACKOFF`, `HALT_AND_ESCALATE`.

### EventType

`TASK_CREATED`, `DOCUMENT_REGISTERED`, `ANALYSIS_COMPLETED`, `SOURCE_ASSESSED`, `EVIDENCE_ASSESSED`, `MAPPING_PROPOSED`, `AI_INTERACTION_RECORDED`, `CHANGE_PROPOSED`, `REVIEW_DECIDED`, `DECISION_SUPERSEDED`, `CHANGE_SET_APPROVED`, `APPROVAL_INVALIDATED`, `APPROVAL_REVOKED`, `REPLAY_REQUESTED`, `EXECUTION_COMPLETED`, `EXECUTION_REFUSED`, `VALIDATION_COMPLETED`, `RELEASE_WITHHELD`, `OUTPUT_RELEASED`, `EXCEPTION_RECORDED`, `EXCEPTION_RESOLVED`, `STATUS_TRANSITIONED`.

### ObjectType

`FoundationTask`, `DocumentArtifact`, `DocumentVersion`, `PerceptionSnapshot`, `SemanticObject`, `NativeLocator`, `NativeBinding`, `TargetContract`, `TargetRegion`, `RulePack`, `BusinessRule`, `RuleEvaluation`, `SourceRequirement`, `SourceAssessment`, `EvidenceRecord`, `EvidenceCheck`, `EvidenceAssessment`, `MappingProposal`, `AIInteractionRecord`, `ChangeProposal`, `ReviewDecision`, `ApprovedChange`, `ApprovedChangeSet`, `ExecutionResult`, `ChangeExecutionResult`, `ValidationPlan`, `ValidationReport`, `ValidationCheckResult`, `ExceptionRecord`, `AnalysisRun`, `AuditEvent`.
