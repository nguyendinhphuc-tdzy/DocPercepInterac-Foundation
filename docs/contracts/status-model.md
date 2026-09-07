# Foundation v2 Status Model

**Foundation architecture generation:** v2

**Contract schema version:** 0.1.0

**Date:** 2026-09-07

**Status:** Pre-freeze architecture contract.

## Transition rules

The tables below are exhaustive allowed edges. Comma-separated source or destination states expand into individual edges subject to the same guard. No other edge is legal. Every transition requires the named guard, authenticated authority, optimistic revision matching and an immutable AuditEvent. An unknown or forbidden transition returns INVALID_STATE_TRANSITION without rewriting a historical record.

Statuses are server-owned projections of append-only events and immutable snapshots. A status alone never proves authority. Human/AI clients cannot PATCH status fields. Repeated reads and duplicate idempotent requests do not create transitions.

Initial states can only be created by the responsible service. Terminal outcomes are not rewritten. New evidence or decisions create new records and events, preserving old findings. The mutable latest-state projection does not make historical snapshots mutable.

## Separate state dimensions

| Dimension | Owner | Meaning |
| --- | --- | --- |
| Workflow progress and release | FoundationTask and document/release governance | Task readiness, aggregate completion and released artifact availability. |
| Document preflight lifecycle | DocumentPreflightAssessment.status | Progress of observing one exact binary; completed assessment does not imply universal operation support. |
| Source assessment lifecycle | SourceAssessment.status | Whether the assessment is pending, running, completed, superseded or technically failed. |
| Source business outcome | SourceAssessment.outcome | Sufficiency verdict on completed deterministic assessment; not a lifecycle state. |
| Evidence verification | EvidenceAssessment.status and TargetRegion.verification_status | Deterministic evidence verdict, never AI confidence. |
| Proposal review | ChangeProposal.status and immutable ReviewDecision | Proposed content and human review; no execution authority. |
| Authorization validity | ApprovedChangeSet.status | APPROVED, INVALIDATED, REVOKED or SUPERSEDED only. |
| Execution progress | ExecutionResult.status | Mechanical attempt, including staged success or refusal. |
| Independent validation | ValidationReport.status | Independent checks on exact input, output and approved scope. |

An ApprovedChangeSet may remain APPROVED before, during and after successful execution and validation, unless new events invalidate, revoke or supersede it. This does not allow a second application: execution identity, attempt history, exact input version and mutation ownership separately enforce idempotency and exclusivity.

SUCCEEDED on execution, PASSED on validation and RELEASED on task/document release are not authorization states. ExecutionResult and ValidationReport do not own mutable release_status fields.

## Legal lifecycles

### Task

Enum: TaskStatus. Initial: CREATED. Terminal: COMPLETED, FAILED, CANCELLED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| CREATED | ANALYZING, CANCELLED | Before ANALYZING, pin the TargetContractDefinition, registered task/document TargetContractInstance and RulePack, exact input versions and a nonempty required target set from the definition. Native binding may be completed during analysis. CREATED may omit these pins; cancellation does not require them. |
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
| PREFLIGHTING | READY, BLOCKED, REJECTED | Derive readiness from pinned DocumentPreflightAssessment observations and coverage. READY admits the intended workflow phase; it is not universal mutation support. |
| READY | BLOCKED, SUPERSEDED | A new version supersedes selection; new risk blocks its use. |
| BLOCKED | PREFLIGHTING, SUPERSEDED, REJECTED | Recorded remediation permits a new inspection; no silent support upgrade. |
| STAGED | RELEASED, QUARANTINED | Only the release gate can publish; failure or unauthorized change quarantines. |
| QUARANTINED | STAGED, SUPERSEDED | New independent evidence and authorized remediation may return the same unchanged binary to staging; never directly release. |
| RELEASED | QUARANTINED, SUPERSEDED | New findings withdraw availability by a new event; historical release evidence is retained. |

### DocumentPreflightAssessment

Enum: DocumentPreflightStatus. Initial: PENDING. Terminal: FAILED, SUPERSEDED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| PENDING | ASSESSING, SUPERSEDED | Deterministic assessor starts against the pinned binary/configuration, or an explicit replacement supersedes the unstarted request. |
| ASSESSING | COMPLETED, FAILED, SUPERSEDED | Finish the planned inspection with preserved observations, record technical failure, or explicitly supersede the attempt. |
| COMPLETED | SUPERSEDED | A new applicable assessment replaces the prior observations; preserve its completed findings and capability entries. |

COMPLETED includes assessments that find protected, unsupported or unknown structures/capabilities. It never means all operations are SUPPORTED. FAILED is an assessment failure, not the ordinary result of recognizing an unsupported operation. New engine/configuration/qualification observations create new assessments; DocumentVersion does not gain evolving fields or lifecycle revisions. Supersession is explicit and scoped; assessing another engine/profile does not automatically invalidate unrelated evidence.

### SourceAssessment

Enum: SourceAssessmentStatus. Initial: PENDING. Terminal: SUPERSEDED, FAILED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| PENDING | ASSESSING, SUPERSEDED | Deterministic evaluator starts or a newer assessment supersedes the unstarted request. |
| ASSESSING | COMPLETED, FAILED, SUPERSEDED | Finish with one business outcome, record technical failure without an outcome, or supersede the attempt. |
| COMPLETED | SUPERSEDED | New evidence creates a new assessment. Preserve the completed outcome and all findings; never transition outcome labels as lifecycle states. |

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
| IN_REVIEW | APPROVED, REJECTED, BLOCKED, SUPERSEDED | Explicit ReviewDecision and current deterministic gates. APPROVE permits APPROVED only with no blockers; REJECT rejects; DEFER leaves IN_REVIEW or BLOCKED; REQUEST_MORE_SOURCE records named requirements and moves to BLOCKED. |
| APPROVED | SUPERSEDED | Any payload, policy, evidence or target binding change invalidates dependent authorization; proposal status is never replay authority. |

### ApprovedChangeSet

Enum: ApprovedChangeSetStatus. Initial: APPROVED (governance materialization only). Terminal: INVALIDATED, REVOKED, SUPERSEDED.

| From | To | Guard and responsible action |
| --- | --- | --- |
| APPROVED | INVALIDATED | Deterministic checks detect changed binary, evidence, policy, payload, locator, protected scope or validation obligations. |
| APPROVED | REVOKED | Authenticated authorized human/governance revokes permission; append the decision/event. |
| APPROVED | SUPERSEDED | A newly approved replacement set explicitly supersedes this set; preserve both sealed authorizations. |

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

## SourceAssessment lifecycle and outcome rules

| Lifecycle status | Outcome requirement | Meaning |
| --- | --- | --- |
| PENDING | null | Assessment has not begun. |
| ASSESSING | null | No final business verdict yet. |
| COMPLETED | Exactly one SourceSufficiencyOutcome | Deterministic assessment finished; only SUFFICIENT passes a blocking source gate. |
| FAILED | null | A technical failure prevented assessment; never use FAILED to mean missing business evidence. |
| SUPERSEDED | Preserve the previous outcome, including null | New assessment replaces applicability without rewriting the earlier finding. |

| SourceSufficiencyOutcome | Business meaning |
| --- | --- |
| SUFFICIENT | Every blocking requirement is satisfied by current applicable authoritative evidence, without unresolved ambiguity/conflict. |
| MISSING | Required source or required business fields are absent. |
| STALE | Source version, period or freshness applicability no longer meets the pinned requirement; record the distinct failed check and policy. |
| CONFLICTING | Material source facts conflict under the applicable policy. |
| NOT_AUTHORITATIVE | Available material lacks required source authority. |
| AMBIGUOUS | Source identity, scope or interpretation remains unresolved. |

If multiple failures apply, retain all findings and use the pinned deterministic policy to select the primary outcome; do not collapse uncertainty into SUFFICIENT. New source evidence creates a new assessment. Previously COMPLETED/SUFFICIENT records are superseded, not edited into STALE. A new assessment with status COMPLETED and outcome STALE can record stale applicability.

PERIOD_INDEPENDENT resolves to no source period. CURRENT_PERIOD and PRIOR_PERIOD require explicit task period context; SPECIFIC_PERIOD uses the reusable requirement's fixed specific_period. A completed period-sensitive assessment must record its resolved source period. It never guesses a prior fiscal period by subtracting a calendar year.

FreshnessPolicy is independent of PeriodPolicy. A source can concern the correct business period and still be stale or superseded. PERIOD_INDEPENDENT removes a required business period, not freshness governance. The source requirement must pin a FreshnessPolicy revision; COMPLETED/SUFFICIENT requires a recorded deterministic FreshnessEvaluation with outcome PASS.

Freshness evaluation records the exact policy, trusted as_of, input observations, evaluator identity/version and any policy-derived valid_until. Null valid_until never means valid forever. A policy with no age-based constraint still requires an explicit evaluated policy result. No current age limit, renewal window or other threshold is introduced by this contract.

Recheck freshness applicability at approval and execution. Expiry, supersession, revocation or changed policy inputs generate new checks/assessments and invalidate affected approval when necessary; they do not rewrite a prior successful record. FreshnessEvaluation outcome uses CheckOutcome but permits only PASS, FAIL or BLOCKED; NOT_APPLICABLE cannot bypass the source freshness gate.

## Review and supporting semantics

REQUEST_MORE_SOURCE is an explicit ReviewOutcome. It requires nonempty requested_source_requirement_refs, records the source request and moves an affected in-review proposal to BLOCKED. It does not update prior SourceAssessment or EvidenceAssessment records. APPROVE still requires every blocking gate to pass; REJECT is a rejection and DEFER records a pending decision without creating authorization.

BindingStatus progresses from PROPOSED to RESOLVED, AMBIGUOUS or UNSUPPORTED through native inspection. Changed bindings are new revisions. RESOLVED does not imply a one-to-one semantic/native relationship; exact unique execution resolution is checked per inline change.

EvidenceStatus starts UNASSESSED. A deterministic assessment may produce VERIFIED, INSUFFICIENT, CONFLICTED or STALE. These evidence labels are intentionally distinct from SourceSufficiencyOutcome and must not be copied into SourceAssessment.status. New evidence is a new immutable assessment snapshot. AI cannot author verification transitions.

TargetVerificationStatus begins UNVERIFIED. Deterministic evidence permits VERIFIED, missing/conflicting evidence gives BLOCKED, and obsolete inputs give STALE. Human acceptance of a model score cannot resolve a blocking state.

CapabilityStatus describes one inline CapabilityResult in a pinned DocumentPreflightAssessment revision, not an entire TargetRegion or DocumentVersion. A CapabilityResultRef selects that entry and exact native scope. SUPPORTED for one operation/native structure/engine/version/conformance does not grant support for another. Unknown or absent qualification is not a pass.

RuleType is a required business-policy classification on every BusinessRule, not a lifecycle or MutationOperation. evaluator_key is an opaque deterministic implementation identifier. RuleEvaluation, SourceAssessment, EvidenceCheck and EvidenceAssessment each pin the exact EvaluatorBinding used. EvidenceCheckKind is required on every EvidenceCheck; PERIOD and FRESHNESS have separate semantics and must not substitute for each other. Neither taxonomy changes any passed C1 state machine.

ConditionKind selects a closed typed shape in domain-model.md. ConditionValueTargetKind distinguishes an exact input native object from an output validation subject identified inside the approved set; it introduces no new native execution address or global ApprovedChange record. BusinessValueKind selects kind-specific fields only after mandatory kind and review_text are present.

CheckOutcome PASS is required for every mandatory independent validation check. FAIL and BLOCKED prevent passage. NOT_APPLICABLE is permitted only for a plan requirement explicitly marked optional, with a recorded reason; it cannot satisfy a mandatory check.

ReleaseStatus belongs to task/document release governance. It starts WITHHELD; all independent validation and task-required target gates permit ELIGIBLE; atomic publication gives RELEASED. New contrary evidence creates a new WITHHELD projection and document quarantine event without erasing a historical release.

## Retry, concurrency and invalidation

- The same execution_id and same ApprovedChangeSet reference are idempotent: return the same attempt, never apply twice. Different content under the same execution identity returns IDEMPOTENCY_CONFLICT.
- Preflight refusal without mutation may be retried under a new execution_id only after the cause is resolved and authorization is still valid. Changed binary, evidence, policy or authorization needs a new approved set.
- A RUNNING, SUCCEEDED or uncertain prior attempt blocks concurrent or repeated application for the same authorized input. EXECUTION_CONFLICT prevents admission. Partial/uncertain output is quarantined; no blind retry.
- A transient validation failure can create a new ValidationReport for the same staged output and pinned plan. It does not replay the mutation or overwrite a previous report.
- A stale binary hash returns STALE_DOCUMENT_VERSION and execution REFUSED; affected authorization becomes INVALIDATED. Locator/fingerprint failure also refuses execution without fuzzy repair.
- Changed evidence, definition/instance or RulePack revision, approved payload, locator, conditions, protected scope or required validation invalidates affected authorization. Failure/progress alone is not an authorization lifecycle transition.
- Revocation and supersession are new explicit decisions/events. An invalidated/revoked/superseded set never returns to APPROVED; renewed approval creates a new set.
- An eligible factual NCP change may proceed while another target remains blocked only if its own gates and protection obligations pass. Missing benchmark evidence still blocks the arm's-length conclusion and whole-document release.

## Canonical enum registry

These are closed vocabularies for schema version 0.1.0. Identifiers such as provider/model names, business periods and descriptions are text, not enums. ObjectType includes only top-level records and deliberately excludes ApprovedChange and ReplayRequest. ErrorCode and EventType align with the C2 error and event contracts.

### SchemaVersion

`0.1.0`.

### TaskStatus

`CREATED`, `ANALYZING`, `AWAITING_REVIEW`, `READY_FOR_EXECUTION`, `EXECUTING`, `VALIDATING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELLED`.

### DocumentStatus

`REGISTERED`, `PREFLIGHTING`, `READY`, `BLOCKED`, `REJECTED`, `SUPERSEDED`, `STAGED`, `RELEASED`, `QUARANTINED`.

### DocumentPreflightStatus

`PENDING`, `ASSESSING`, `COMPLETED`, `FAILED`, `SUPERSEDED`.

### SourceAssessmentStatus

`PENDING`, `ASSESSING`, `COMPLETED`, `SUPERSEDED`, `FAILED`.

### MappingProposalStatus

`PROPOSED`, `UNDER_REVIEW`, `ACCEPTED`, `BLOCKED`, `REJECTED`, `SUPERSEDED`.

### ChangeProposalStatus

`DRAFT`, `BLOCKED`, `READY_FOR_REVIEW`, `IN_REVIEW`, `APPROVED`, `REJECTED`, `SUPERSEDED`.

### ApprovedChangeSetStatus

`APPROVED`, `INVALIDATED`, `REVOKED`, `SUPERSEDED`.

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

`APPROVE`, `REJECT`, `DEFER`, `REQUEST_MORE_SOURCE`.

### ActorType

`HUMAN`, `SYSTEM`, `AI`, `REPLAY_ENGINE`, `VALIDATOR`.

### ReleaseStatus

`WITHHELD`, `ELIGIBLE`, `RELEASED`.

### ChangeExecutionStatus

`APPLIED`, `REFUSED`, `FAILED`, `NOT_ATTEMPTED`.

### MutationOperation

`REPLACE_RUN_TEXT`, `REPLACE_SDT_TEXT`, `REPLACE_SIMPLE_TABLE_CELL_TEXT`.

### LocatorType

`DOCX_CONTENT_CONTROL`, `DOCX_BOOKMARK`, `DOCX_PARAGRAPH`, `DOCX_RUN`, `DOCX_TABLE_CELL`, `DOCX_RELATIONSHIP`, `XLSX_CELL`, `XLSX_DEFINED_NAME`, `XLSX_TABLE_RANGE`.

### EvidenceKind

`NATIVE_VALUE`, `FORMULA_IDENTITY`, `SOURCE_EXCERPT`, `VALIDATION_OUTPUT`.

### SourceAuthority

`AUTHORITATIVE`, `CONTEXT_ONLY`, `UNDETERMINED`.

### AssessmentMethod

`DETERMINISTIC`.

### RuleType

`ALWAYS_UPDATE`, `UPDATE_IF_CHANGED`, `DERIVED_UPDATE`, `CARRY_FORWARD`, `TEMPLATE_CONTROLLED`, `PROTECTED`.

### EvidenceCheckKind

`SOURCE_PRESENCE`, `PERIOD`, `FRESHNESS`, `AUTHORITY`, `COMPLETENESS`, `CONSISTENCY`, `VALUE_TYPE`, `UNIT`, `FORMULA`, `PROVENANCE`.

### ConditionValueTargetKind

`INPUT_NATIVE_OBJECT`, `OUTPUT_APPROVED_CHANGE`.

### ConditionKind

`BINARY_HASH_EQUALS`, `TEXT_EQUALS`, `VALUE_EQUALS`, `CAPABILITY_SUPPORTED`, `EVIDENCE_VERIFIED`, `PRESERVE_SCOPE`.

### ValidationCheckKind

`SCHEMA_PACKAGE`, `PACKAGE_DIFF`, `INTRA_PART_DIFF`, `PROTECTED_SCOPE`, `SEMANTIC_REPERCEPTION`, `BUSINESS_POSTCONDITION`.

### Layer

`CONTRACT`, `INTAKE`, `PERCEPTION`, `NATIVE_IDENTITY`, `SOURCE`, `EVIDENCE`, `MAPPING`, `REVIEW`, `AUTHORIZATION`, `EXECUTION`, `VALIDATION`, `AUDIT`.

### Severity

`INFO`, `WARNING`, `ERROR`, `CRITICAL`.

### SystemAction

`REJECT_REQUEST`, `REFUSE_EXECUTION`, `BLOCK_PROPOSAL`, `REQUEST_SOURCE`, `REQUIRE_REVIEW`, `REANALYZE`, `QUARANTINE_OUTPUT`, `WITHHOLD_RELEASE`, `RETRY_WITH_BACKOFF`, `HALT_AND_ESCALATE`.

### EventType

`TASK_CREATED`, `DOCUMENT_REGISTERED`, `DOCUMENT_PREFLIGHT_COMPLETED`, `ANALYSIS_COMPLETED`, `RULE_EVALUATED`, `SOURCE_ASSESSED`, `EVIDENCE_CHECKED`, `EVIDENCE_ASSESSED`, `MAPPING_PROPOSED`, `AI_INTERACTION_RECORDED`, `CHANGE_PROPOSED`, `REVIEW_DECIDED`, `SOURCE_REQUESTED`, `DECISION_SUPERSEDED`, `CHANGE_SET_APPROVED`, `APPROVAL_INVALIDATED`, `APPROVAL_REVOKED`, `REPLAY_REQUESTED`, `EXECUTION_COMPLETED`, `EXECUTION_REFUSED`, `VALIDATION_COMPLETED`, `RELEASE_ELIGIBILITY_CONFIRMED`, `RELEASE_WITHHELD`, `OUTPUT_QUARANTINED`, `OUTPUT_RELEASED`, `EXCEPTION_RECORDED`, `EXCEPTION_RESOLVED`, `STATUS_TRANSITIONED`.

### AuditMetadataKind

`GOVERNANCE`, `DETERMINISTIC_EVALUATION`, `AI_INTERACTION`, `REPLAY`, `VALIDATION`, `EXCEPTION`.

### ObjectType

`FoundationTask`, `DocumentArtifact`, `DocumentVersion`, `DocumentPreflightAssessment`, `PerceptionSnapshot`, `SemanticObject`, `NativeLocator`, `NativeBinding`, `TargetContractDefinition`, `TargetRegionDefinition`, `TargetContractInstance`, `TargetRegion`, `RulePack`, `BusinessRule`, `RuleEvaluation`, `FreshnessPolicy`, `SourceRequirement`, `SourceAssessment`, `EvidenceRecord`, `EvidenceCheck`, `EvidenceAssessment`, `MappingProposal`, `AIInteractionRecord`, `ChangeProposal`, `ReviewDecision`, `ApprovedChangeSet`, `ExecutionResult`, `ChangeExecutionResult`, `ValidationPlan`, `ValidationReport`, `ValidationCheckResult`, `ExceptionRecord`, `AnalysisRun`, `AuditEvent`.

### SourceSufficiencyOutcome

`SUFFICIENT`, `MISSING`, `STALE`, `CONFLICTING`, `NOT_AUTHORITATIVE`, `AMBIGUOUS`.

### PeriodPolicy

`CURRENT_PERIOD`, `PRIOR_PERIOD`, `SPECIFIC_PERIOD`, `PERIOD_INDEPENDENT`.

### EvidencePeriodScope

`SPECIFIC_PERIOD`, `PERIOD_INDEPENDENT`, `UNKNOWN`.

### DefinedNameScope

`WORKBOOK`, `WORKSHEET`.

### XlsxRangeKind

`TABLE`, `RANGE`.

### BusinessValueKind

`TEXT`, `DECIMAL`, `INTEGER`, `DATE`, `BOOLEAN`, `CURRENCY`, `PERCENT`, `STRUCTURED`.

### MutationPayloadType

`RUN_TEXT_REPLACEMENT`, `SDT_TEXT_REPLACEMENT`, `SIMPLE_TABLE_CELL_TEXT_REPLACEMENT`.

### ErrorCode

`INVALID_CONTRACT`, `INVALID_STATE_TRANSITION`, `REFERENCE_NOT_FOUND`, `EVALUATOR_BINDING_UNAVAILABLE`, `EVALUATOR_CONFIGURATION_MISMATCH`, `STALE_DOCUMENT_VERSION`, `LOCATOR_NOT_FOUND`, `LOCATOR_AMBIGUOUS`, `LOCATOR_FINGERPRINT_MISMATCH`, `CAPABILITY_UNKNOWN`, `UNSUPPORTED_NATIVE_OBJECT`, `PROTECTED_OBJECT`, `EXECUTION_UNSUPPORTED`, `STRICT_OOXML_MUTATION_UNQUALIFIED`, `SOURCE_MISSING`, `SOURCE_STALE`, `SOURCE_NOT_AUTHORITATIVE`, `SOURCE_CONFLICTING`, `SOURCE_AMBIGUOUS`, `EVIDENCE_INSUFFICIENT`, `EVIDENCE_NOT_VERIFIED`, `AI_AUTHORITY_VIOLATION`, `APPROVAL_REQUIRED`, `APPROVAL_CONTENT_MISMATCH`, `AUTHORIZATION_NOT_APPROVED`, `IDEMPOTENCY_CONFLICT`, `EXECUTION_CONFLICT`, `PRECONDITION_FAILED`, `REPLAY_ENGINE_FAILURE`, `INDEPENDENT_VALIDATOR_NOT_QUALIFIED`, `VALIDATION_OBSERVATION_UNAVAILABLE`, `UNAUTHORIZED_CHANGE_DETECTED`, `PROTECTED_SCOPE_VIOLATION`, `RELEASE_BLOCKED_INCOMPLETE_TARGETS`, `EVENT_INTEGRITY_MISMATCH`, `EVENT_CAUSATION_INVALID`.
