# Foundation v2 Behavioral Invariants

**Foundation architecture generation:** v2

**Contract schema version:** 0.1.0

**Date:** 2026-09-07

**Status:** C2.1 pre-freeze behavioral contract.

These invariants govern every service, persisted projection, event and interface. The [current baseline](../CURRENT_BASELINE.md), active [ADRs](../adr/README.md), [domain model](domain-model.md), [status model](status-model.md), [error catalog](error-catalog.md) and [event model](event-model.md) must be interpreted together.

Violation outcomes name the minimum required response. A service may add a more restrictive response, but it cannot continue through a blocking gate.

## Document and identity invariants

### FND-INV-DOC-001 — Immutable document versions

| Attribute | Contract |
| --- | --- |
| Rule | A DocumentVersion identifies exactly one immutable byte sequence by SHA-256. Its binary_hash, byte_length and content_ref never change, and every DocumentVersionRef pins document_id, version_id and the same binary hash. |
| Rationale | Execution, evidence and validation must be reproducible against exact bytes. |
| Violation outcome | Reject inconsistent registration with INVALID_CONTRACT. Refuse use of changed bytes with STALE_DOCUMENT_VERSION and invalidate any affected authorization. |
| Owning layer | INTAKE |
| Example | Scenario 03 changes the selected target binary after approval and is refused before mutation. |

### FND-INV-ID-001 — Separated identities

| Attribute | Contract |
| --- | --- |
| Rule | BusinessTargetID, SemanticReference and NativeLocator are distinct values with distinct authority. None may be copied or coerced into another identity type. |
| Rationale | Business intent, semantic perception and native execution address different concerns and have different stability. |
| Violation outcome | Reject the contract with INVALID_CONTRACT; no mapping, approval or replay authority is created. |
| Owning layer | CONTRACT |

### FND-INV-ID-002 — Native binding is association only

| Attribute | Contract |
| --- | --- |
| Rule | NativeBinding records semantic-to-native association. Only a NativeLocator can provide the exact native execution address, and each approved change names one locator. |
| Rationale | A semantic association can be one-to-many or unresolved and therefore cannot safely direct mutation. |
| Violation outcome | Block the proposal with NATIVE_BINDING_MISSING or refuse execution with LOCATOR_NOT_FOUND, as applicable. |
| Owning layer | NATIVE_IDENTITY |

### FND-INV-LOC-001 — Exact version-scoped native resolution

| Attribute | Contract |
| --- | --- |
| Rule | A NativeLocator belongs to exactly one DocumentVersion and must resolve to exactly one object on that binary through its typed address, then pass its structural fingerprint. |
| Rationale | Exact resolution prevents silent movement to a similar but unauthorized object. |
| Violation outcome | Zero matches produces LOCATOR_NOT_FOUND; multiple matches produces LOCATOR_AMBIGUOUS; fingerprint mismatch produces LOCATOR_FINGERPRINT_MISMATCH. All refuse execution. |
| Owning layer | NATIVE_IDENTITY |
| Example | Scenario 04 records two matches and refuses without fallback. |

### FND-INV-LOC-002 — No fuzzy execution

| Attribute | Contract |
| --- | --- |
| Rule | Text similarity, nearest position, semantic similarity, fingerprint search and other fuzzy techniques may assist discovery but may never repair or replace a locator during replay. |
| Rationale | Discovery confidence is not native execution authority. |
| Violation outcome | Refuse execution with LOCATOR_NOT_FOUND or LOCATOR_AMBIGUOUS and require reanalysis/new approval. |
| Owning layer | EXECUTION |

### FND-INV-CAP-001 — Operation-specific capability

| Attribute | Contract |
| --- | --- |
| Rule | Capability is established only for the exact document version, native locator scope, operation, engine, engine version, conformance class and qualification evidence recorded by a completed DocumentPreflightAssessment. |
| Rationale | File readability or support for a neighboring operation does not qualify mutation. |
| Violation outcome | Refuse before replay with CAPABILITY_UNKNOWN, EXECUTION_UNSUPPORTED, UNSUPPORTED_NATIVE_OBJECT, PROTECTED_OBJECT or STRICT_OOXML_MUTATION_UNQUALIFIED. |
| Owning layer | NATIVE_IDENTITY |
| Example | Scenario 08 refuses unqualified Strict OOXML mutation during preflight. |

## Deterministic governance and evidence invariants

### FND-INV-EVAL-001 — Exact deterministic evaluator identity

| Attribute | Contract |
| --- | --- |
| Rule | Every business-critical RuleEvaluation, SourceAssessment, EvidenceCheck and EvidenceAssessment records an EvaluatorBinding containing evaluator_key, exact evaluator_version and configuration_ref. The key must agree with its declared policy/rule. |
| Rationale | A deterministic result is reproducible only when its implementation and configuration are pinned. |
| Violation outcome | Block the result with EVALUATOR_BINDING_UNAVAILABLE or EVALUATOR_CONFIGURATION_MISMATCH. It cannot support VERIFIED, approval or release. |
| Owning layer | CONTRACT |

### FND-INV-SRC-001 — Blocking source sufficiency

| Attribute | Contract |
| --- | --- |
| Rule | Every blocking SourceRequirement must have a completed SourceAssessment with outcome SUFFICIENT and the required deterministic evidence checks before its target can be verified. |
| Rationale | Plausible content and human preference cannot manufacture authoritative source evidence. |
| Violation outcome | SOURCE_MISSING, SOURCE_STALE, SOURCE_NOT_AUTHORITATIVE, SOURCE_CONFLICTING or SOURCE_AMBIGUOUS blocks the affected target and dependent authorization. |
| Owning layer | SOURCE |
| Example | Scenarios 02, 05 and 07 preserve a blocked conclusion when required benchmark evidence is absent. |

### FND-INV-EVD-001 — Deterministic verification only

| Attribute | Contract |
| --- | --- |
| Rule | EvidenceAssessment may become VERIFIED only from applicable deterministic SourceAssessments and EvidenceChecks. Model confidence, reviewer sentiment and a successful parser response are not evidence checks. |
| Rationale | Verification must be grounded in replayable inputs and governed policy. |
| Violation outcome | EVIDENCE_INSUFFICIENT or EVIDENCE_NOT_VERIFIED; block proposal/authorization. |
| Owning layer | EVIDENCE |

### FND-INV-FRESH-001 — Period and freshness are independent

| Attribute | Contract |
| --- | --- |
| Rule | Every SourceRequirement pins a FreshnessPolicy independent of PeriodPolicy. A sufficient assessment records a passing FreshnessEvaluation using the exact evaluator and trusted as_of context. A prior pass is not perpetual. |
| Rationale | Evidence can concern the correct business period and still be obsolete, revoked or superseded. |
| Violation outcome | SOURCE_STALE; block the affected target and invalidate dependent authorization when applicability changes. |
| Owning layer | SOURCE |

### FND-INV-AI-001 — AI has zero execution authority

| Attribute | Contract |
| --- | --- |
| Rule | AIInteractionRecord may propose, interpret, draft or explain. It cannot independently create VERIFIED, APPROVED, an ApprovedChangeSet, a ReplayRequest or a native mutation. |
| Rationale | AI output is bounded assistance, not deterministic evidence or authorization. |
| Violation outcome | Reject the attempted transition with AI_AUTHORITY_VIOLATION; preserve the AI record and audit the violation. |
| Owning layer | AUTHORIZATION |
| Example | Scenario 05 records a correct AI proposal while deterministic evidence remains insufficient and no authorization exists. |

## Authorization and replay invariants

### FND-INV-AUTH-001 — Proposal has no execution authority

| Attribute | Contract |
| --- | --- |
| Rule | MappingProposal and ChangeProposal have zero execution authority in every lifecycle state. Human APPROVE is necessary where required but cannot bypass source, evidence, protection or capability gates. |
| Rationale | Proposal quality and review intent are different from sealed executable authority. |
| Violation outcome | APPROVAL_REQUIRED, EVIDENCE_NOT_VERIFIED, PROTECTED_OBJECT or EXECUTION_UNSUPPORTED; do not create a ReplayRequest. |
| Owning layer | AUTHORIZATION |

### FND-INV-AUTH-002 — Sealed exact authorization

| Attribute | Contract |
| --- | --- |
| Rule | An ApprovedChangeSet seals the exact input version/hash, definitions, RulePack, assessments, human decisions, inline operations/payloads/locators, conditions, protected scope, qualification and validation plan. Its authorization_digest uses RFC 8785, UTF-8, SHA-256 and lowercase hex. |
| Rationale | Review must cover exactly what replay may perform. |
| Violation outcome | APPROVAL_CONTENT_MISMATCH and authorization invalidation; changed content requires new review and a new set. |
| Owning layer | AUTHORIZATION |

### FND-INV-AUTH-003 — Authorization validity is independent

| Attribute | Contract |
| --- | --- |
| Rule | APPROVED, INVALIDATED, REVOKED and SUPERSEDED describe authorization validity only. Execution, validation and release results never rewrite sealed authorization or masquerade as its state. |
| Rationale | A valid permission, an execution attempt and a release decision have independent histories. |
| Violation outcome | INVALID_STATE_TRANSITION; append the correct record/event instead. |
| Owning layer | AUTHORIZATION |

### FND-INV-REPLAY-001 — Replay derives only from authorization

| Attribute | Contract |
| --- | --- |
| Rule | ReplayRequest contains only execution_id and approved_change_set_ref. No caller may supply locator, operation, payload, engine profile or free-form override. |
| Rationale | The replay boundary must not let frontend or orchestration expand approved scope. |
| Violation outcome | INVALID_CONTRACT or APPROVAL_CONTENT_MISMATCH; reject/refuse before mutation. |
| Owning layer | EXECUTION |

### FND-INV-REPLAY-002 — Fail-closed replay preflight

| Attribute | Contract |
| --- | --- |
| Rule | Replay rechecks authorization validity, exact target hash, exact locator resolution/fingerprint, preconditions, source/evidence applicability, protection and the complete capability tuple before mutation. Any unknown or failed gate is a refusal. |
| Rationale | Time and external edits can invalidate previously reviewed assumptions. |
| Violation outcome | ExecutionResult is REFUSED with the specific earliest material error; no output DocumentVersion is created. |
| Owning layer | EXECUTION |
| Example | Scenarios 03 and 04 refuse at target-version and locator-resolution gates. |

### FND-INV-REPLAY-003 — Idempotent, bounded mutation

| Attribute | Contract |
| --- | --- |
| Rule | One execution identity and ApprovedChangeSet pair is idempotent. Concurrent, repeated or uncertain attempts cannot apply the same authorization twice, and replay cannot add operations outside approved_changes. |
| Rationale | Duplicate or expanded mutation would violate sealed authority. |
| Violation outcome | IDEMPOTENCY_CONFLICT or EXECUTION_CONFLICT; halt and quarantine uncertain output. |
| Owning layer | EXECUTION |

## Validation, release and history invariants

### FND-INV-VAL-001 — Independent post-execution validation

| Attribute | Contract |
| --- | --- |
| Rule | Every mechanically successful mutation is validated by a qualified validator identity/version/configuration independent from the replay engine. Replay self-report cannot satisfy a ValidationRequirement. |
| Rationale | The component that made a change cannot be the sole proof that it stayed within authority. |
| Violation outcome | VALIDATION_OBSERVATION_UNAVAILABLE or INDEPENDENT_VALIDATOR_NOT_QUALIFIED; keep output quarantined and release withheld. |
| Owning layer | VALIDATION |

### FND-INV-VAL-002 — Unauthorized changes prevent release

| Attribute | Contract |
| --- | --- |
| Rule | Validation compares the exact input and output, confirms approved postconditions and detects changes outside approved/protected scope. Any unauthorized change fails validation even when the approved target changed correctly. |
| Rationale | Correct intended output does not excuse collateral mutation. |
| Violation outcome | UNAUTHORIZED_CHANGE_DETECTED or PROTECTED_SCOPE_VIOLATION; ValidationReport FAILED, output QUARANTINED, release WITHHELD, authorization invalidated where its assumptions were breached. |
| Owning layer | VALIDATION |
| Example | Scenario 06 detects an unrelated native edit after mechanical success. |

### FND-INV-REL-001 — Partial completion cannot imply whole release

| Attribute | Contract |
| --- | --- |
| Rule | An independently eligible target may progress when policy permits, but FoundationTask cannot become COMPLETED and whole-document release cannot become ELIGIBLE while any required target remains blocked. |
| Rationale | Target-local success must not erase an unsatisfied business conclusion. |
| Violation outcome | RELEASE_BLOCKED_INCOMPLETE_TARGETS and release WITHHELD; preserve successful target-local records. |
| Owning layer | VALIDATION |
| Example | Scenario 02 permits the independently supported factual NCP path but keeps the arm's-length conclusion and whole task blocked. |

### FND-INV-AUD-001 — Immutable append-only history

| Attribute | Contract |
| --- | --- |
| Rule | Domain revisions and AuditEvents are immutable. Correction, supersession, override, invalidation and remediation append new records/events and never rewrite prior machine, AI, human, execution or validation evidence. |
| Rationale | Governance requires a faithful account of what was known and decided at each point. |
| Violation outcome | EVENT_INTEGRITY_MISMATCH or INVALID_STATE_TRANSITION; halt affected processing and escalate. |
| Owning layer | AUDIT |

### FND-INV-AUD-002 — Causal reconstruction

| Attribute | Contract |
| --- | --- |
| Rule | TASK_CREATED is the only task-lineage event with null causation. Every later event references an earlier event in the same task; the acyclic cause may cross correlation_id boundaries because correlations group separate attempts. The chain preserves the first material failure stage and error code. |
| Rationale | Later blocking, refusal or quarantine events must not obscure where the scenario first failed. |
| Violation outcome | EVENT_CAUSATION_INVALID; reject the event and do not claim a complete audit trail. |
| Owning layer | AUDIT |

### FND-INV-AUD-003 — Integrity and implementation traceability

| Attribute | Contract |
| --- | --- |
| Rule | Every AuditEvent has an integrity payload hash. Every material EvidenceCheck has an EVIDENCE_CHECKED event for its exact revision. Deterministic evaluation events record evaluator key/version/configuration; replay events record ApprovedChangeSet, engine/version and exact input/output; validation events record independent validator identity/version/configuration and observations; AI events record provider/model/version/instruction/context/output references without hidden chain-of-thought. |
| Rationale | The audit trail must identify the concrete mechanism and immutable evidence behind each material result. |
| Violation outcome | EVENT_INTEGRITY_MISMATCH or EVALUATOR_BINDING_UNAVAILABLE; the event cannot support approval, validation or release. |
| Owning layer | AUDIT |
