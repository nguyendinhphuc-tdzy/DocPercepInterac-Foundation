# Foundation v2 Error Catalog

**Foundation architecture generation:** v2

**Contract schema version:** 0.1.0

**Date:** 2026-09-07

**Status:** C2 pre-freeze behavioral contract.

An ErrorDefinition is immutable contract data keyed by code. Every occurrence is recorded on the domain object and AuditEvent that first detects it; an ExceptionRecord carries scenario-specific facts and remediation. Codes describe material causes rather than generic failure summaries.

## ErrorDefinition

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| code | ErrorCode | Yes | Stable closed error identifier from status-model.md. |
| layer | Layer | Yes | Layer that owns detection and remediation semantics. |
| severity | Severity | Yes | Operational and governance impact. |
| blocking | Bool | Yes | Whether the affected operation/target/release must stop. |
| retryable | Bool | Yes | Whether an unchanged request may safely be retried after a transient condition. |
| user_resolvable | Bool | Yes | Whether governed user action can supply or select corrective input. |
| invalidates_authorization | Bool | Yes | Whether an existing dependent ApprovedChangeSet must become INVALIDATED. |
| default_system_action | SystemAction | Yes | Minimum automatic response. |
| user_message | Text | Yes | Safe default message; details belong in the ExceptionRecord. |
| audit_required | Bool | Yes | Whether detection and response require AuditEvents. Material Foundation errors are always audited. |

retryable true never means blind replay. The recorded cause must be remediated, authorization must remain valid, and replay concurrency/idempotency rules still apply. invalidates_authorization true affects only authorizations dependent on the failed fact. No error permits mutation to continue through a blocking gate.

## Canonical definitions

| code | layer | severity | blocking | retryable | user_resolvable | invalidates_authorization | default_system_action | user_message | audit_required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INVALID_CONTRACT | CONTRACT | ERROR | true | false | true | true | REJECT_REQUEST | The submitted contract does not satisfy the required schema or invariant. | true |
| INVALID_STATE_TRANSITION | CONTRACT | ERROR | true | false | false | false | REJECT_REQUEST | The requested lifecycle transition is not permitted. | true |
| REFERENCE_NOT_FOUND | CONTRACT | ERROR | true | true | true | true | REJECT_REQUEST | A required pinned record or artifact reference could not be resolved. | true |
| EVALUATOR_BINDING_UNAVAILABLE | CONTRACT | ERROR | true | true | false | true | HALT_AND_ESCALATE | The exact deterministic evaluator implementation or version is unavailable. | true |
| EVALUATOR_CONFIGURATION_MISMATCH | CONTRACT | ERROR | true | false | false | true | HALT_AND_ESCALATE | The evaluator configuration does not match the pinned configuration reference. | true |
| STALE_DOCUMENT_VERSION | EXECUTION | CRITICAL | true | false | true | true | REFUSE_EXECUTION | The target bytes do not match the approved document version and hash. | true |
| LOCATOR_NOT_FOUND | NATIVE_IDENTITY | ERROR | true | false | true | true | REANALYZE | The approved native locator did not resolve an object on the approved binary. | true |
| LOCATOR_AMBIGUOUS | NATIVE_IDENTITY | ERROR | true | false | true | true | REANALYZE | The approved native locator resolved more than one object; execution was refused. | true |
| LOCATOR_FINGERPRINT_MISMATCH | NATIVE_IDENTITY | ERROR | true | false | true | true | REANALYZE | The addressed native object does not match the approved structural fingerprint. | true |
| CAPABILITY_UNKNOWN | NATIVE_IDENTITY | ERROR | true | true | false | true | REANALYZE | Required operation capability has not been established for this exact native scope and engine profile. | true |
| UNSUPPORTED_NATIVE_OBJECT | NATIVE_IDENTITY | ERROR | true | false | false | true | REFUSE_EXECUTION | The requested native structure is outside the qualified mutation profile. | true |
| PROTECTED_OBJECT | AUTHORIZATION | CRITICAL | true | false | false | true | REFUSE_EXECUTION | The requested operation targets an object that must be preserved. | true |
| EXECUTION_UNSUPPORTED | EXECUTION | ERROR | true | false | false | true | REFUSE_EXECUTION | The exact operation, structure, engine, version and conformance tuple is unsupported. | true |
| STRICT_OOXML_MUTATION_UNQUALIFIED | EXECUTION | ERROR | true | false | false | true | REFUSE_EXECUTION | Mutation of Strict OOXML is not qualified and was refused before replay. | true |
| SOURCE_MISSING | SOURCE | ERROR | true | true | true | true | REQUEST_SOURCE | A required authoritative source or required source field is missing. | true |
| SOURCE_STALE | SOURCE | ERROR | true | true | true | true | REQUEST_SOURCE | Required evidence is no longer current under the pinned freshness policy or applicable period. | true |
| SOURCE_NOT_AUTHORITATIVE | SOURCE | ERROR | true | true | true | true | REQUEST_SOURCE | The available source does not meet the required authority policy. | true |
| SOURCE_CONFLICTING | SOURCE | ERROR | true | true | true | true | REQUEST_SOURCE | Material source facts conflict under the pinned deterministic policy. | true |
| SOURCE_AMBIGUOUS | SOURCE | ERROR | true | true | true | true | REQUEST_SOURCE | The required source identity, scope or meaning cannot be resolved deterministically. | true |
| EVIDENCE_INSUFFICIENT | EVIDENCE | ERROR | true | true | true | true | BLOCK_PROPOSAL | Required evidence checks did not establish sufficiency for the business target. | true |
| EVIDENCE_NOT_VERIFIED | EVIDENCE | ERROR | true | true | true | true | BLOCK_PROPOSAL | The business target does not have a current deterministic VERIFIED evidence assessment. | true |
| AI_AUTHORITY_VIOLATION | AUTHORIZATION | CRITICAL | true | false | false | true | HALT_AND_ESCALATE | AI output attempted to create verification, approval or mutation authority. | true |
| APPROVAL_REQUIRED | AUTHORIZATION | ERROR | true | true | true | false | REQUIRE_REVIEW | An explicit eligible human approval and ApprovedChangeSet are required before replay. | true |
| APPROVAL_CONTENT_MISMATCH | AUTHORIZATION | CRITICAL | true | false | true | true | REFUSE_EXECUTION | Current authorization content does not match the sealed approved content or digest. | true |
| AUTHORIZATION_NOT_APPROVED | AUTHORIZATION | ERROR | true | false | true | false | REFUSE_EXECUTION | The referenced change set is invalidated, revoked, superseded or otherwise ineligible. | true |
| IDEMPOTENCY_CONFLICT | EXECUTION | CRITICAL | true | false | false | true | HALT_AND_ESCALATE | The execution identity was reused with different authorization content. | true |
| EXECUTION_CONFLICT | EXECUTION | CRITICAL | true | false | false | false | HALT_AND_ESCALATE | Another or uncertain attempt prevents safe application of this authorization. | true |
| PRECONDITION_FAILED | EXECUTION | ERROR | true | true | true | true | REFUSE_EXECUTION | A sealed typed execution precondition failed. | true |
| REPLAY_ENGINE_FAILURE | EXECUTION | CRITICAL | true | false | false | false | QUARANTINE_OUTPUT | The replay engine failed after execution admission; any staged or uncertain output is quarantined. | true |
| INDEPENDENT_VALIDATOR_NOT_QUALIFIED | VALIDATION | CRITICAL | true | false | false | false | QUARANTINE_OUTPUT | The validator does not satisfy the pinned independent qualification policy. | true |
| VALIDATION_OBSERVATION_UNAVAILABLE | VALIDATION | ERROR | true | true | false | false | QUARANTINE_OUTPUT | A mandatory independent validation observation could not be obtained. | true |
| UNAUTHORIZED_CHANGE_DETECTED | VALIDATION | CRITICAL | true | false | false | true | QUARANTINE_OUTPUT | Independent validation detected a document change outside the approved scope. | true |
| PROTECTED_SCOPE_VIOLATION | VALIDATION | CRITICAL | true | false | false | true | QUARANTINE_OUTPUT | Independent validation detected a change in protected content or structure. | true |
| RELEASE_BLOCKED_INCOMPLETE_TARGETS | VALIDATION | ERROR | true | true | true | false | WITHHOLD_RELEASE | One or more required business targets remain blocked, so whole-task release is withheld. | true |
| EVENT_INTEGRITY_MISMATCH | AUDIT | CRITICAL | true | false | false | true | HALT_AND_ESCALATE | An audit event does not match its recorded integrity payload hash. | true |
| EVENT_CAUSATION_INVALID | AUDIT | ERROR | true | false | false | false | REJECT_REQUEST | The audit event causation reference is missing, cyclic or inconsistent with the task correlation chain. | true |

## Use rules

- Emit the most specific material cause at the layer where it is first established. A later layer may carry the same code but must not replace it with a generic summary.
- INVALID_CONTRACT and REFERENCE_NOT_FOUND describe contract mechanics. If the missing or invalid item establishes a material business failure, also record the specific source, evidence, native, authorization or validation code.
- PRECONDITION_FAILED identifies a failed closed typed condition only when no more specific code applies. Hash, locator, capability, evidence and protection failures use their specific codes.
- A blocking error prevents the affected transition. A task with an independent eligible target may retain that target's successful records, but RELEASE_BLOCKED_INCOMPLETE_TARGETS withholds whole-task release.
- Human remediation creates new evidence, assessment, proposal, decision or authorization records. It never changes an ErrorDefinition or rewrites a prior error occurrence.
