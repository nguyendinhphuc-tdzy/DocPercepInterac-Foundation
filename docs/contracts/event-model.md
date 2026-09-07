# Foundation v2 Audit Event Model

**Foundation architecture generation:** v2

**Contract schema version:** 0.1.0

**Date:** 2026-09-07

**Status:** C2 pre-freeze behavioral contract.

AuditEvent is the immutable, append-only account of material Foundation actions and outcomes. Events record what happened and why; they do not replace the referenced domain records, authorize replay or establish validation by themselves.

## AuditEvent

AuditEvent uses its own event envelope and is a top-level ObjectType.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| event_id | ID | Yes | Stable logical event identifier. |
| event_version | PositiveInt | Yes | Event schema-envelope revision; 1 for this immutable event. |
| schema_version | SchemaVersion | Yes | Contract schema version 0.1.0. |
| event_type | EventType | Yes | Closed material event vocabulary from status-model.md. |
| occurred_at | Timestamp | Yes | Trusted UTC event time. |
| actor | Actor | Yes | Authenticated or attested actor responsible for the event. |
| task_id | ID | Yes | Owning FoundationTask ID. |
| correlation_id | ID | Yes | Root correlation shared by one governed workflow attempt or remediation chain. |
| causation_event_id | Nullable<ID> | Yes | Direct causal AuditEvent ID; null only for the root TASK_CREATED event. |
| document_version_refs | DocumentVersionRef[] | Yes | Exact input/output/source binaries material to this event. |
| business_target_ids | BusinessTargetID[] | Yes | Affected business targets; empty only when the event is task/document-wide. |
| object_refs | Reference[] | Yes | Material governed objects at the time of the event. |
| input_refs | Reference[] | Yes | Immutable domain inputs consumed by this action. |
| output_refs | Reference[] | Yes | Immutable domain outputs created by this action. |
| error_codes | ErrorCode[] | Yes | Specific errors first detected or propagated by this event. Empty for success. |
| metadata | AuditMetadata | Yes | Closed event-family metadata. It cannot add authority or hide required references. |
| integrity_payload_hash | SHA256 | Yes | Integrity hash of the canonical event payload defined below. |

All arrays are explicit, including empty arrays. References pin immutable revisions. An event cannot use latest aliases. AuditEvent references use object_type AuditEvent, object_id equal to event_id and revision equal to event_version.

## AuditMetadata

AuditMetadata is a closed union selected by metadata_kind. Every variant contains metadata_kind and summary. Unknown variants and extra executable fields are rejected.

| Common field | Type | Required | Meaning |
| --- | --- | --- | --- |
| metadata_kind | AuditMetadataKind | Yes | Selects the exact metadata shape. |
| summary | Text | Yes | Concise observable result; never hidden reasoning. |

### GOVERNANCE

Used for task, document, proposal, review, authorization, release and status events.

| Additional field | Type | Required | Meaning |
| --- | --- | --- | --- |
| prior_status | NullableText | Yes | Prior closed-enum state when this event represents a transition; otherwise null. |
| resulting_status | NullableText | Yes | Resulting closed-enum state when this event represents a transition; otherwise null. |
| decision_ref | Reference | No | Exact human/governance decision when applicable. |
| first_material_failure_event_id | ID | No | Required on downstream blocking responses; points to the event where the material failure was first established. |

### DETERMINISTIC_EVALUATION

Used by DOCUMENT_PREFLIGHT_COMPLETED, RULE_EVALUATED, SOURCE_ASSESSED, EVIDENCE_CHECKED and EVIDENCE_ASSESSED. DocumentPreflightAssessment supplies its assessor/engine/version/configuration as an equivalent deterministic binding; the other evaluation records contain EvaluatorBinding.

| Additional field | Type | Required | Meaning |
| --- | --- | --- | --- |
| evaluation_ref | Reference | Yes | Exact DocumentPreflightAssessment, RuleEvaluation, SourceAssessment, EvidenceCheck or EvidenceAssessment output. |
| evaluator_binding | EvaluatorBinding | Yes | Exact deterministic implementation/version/configuration used. |
| outcome | Text | Yes | Closed outcome from the referenced record, serialized as reviewable text. |
| first_material_failure_event_id | ID | No | Required when this event propagates an earlier failure; omitted when this event first establishes it or succeeds. |

### AI_INTERACTION

Used only by AI_INTERACTION_RECORDED.

| Additional field | Type | Required | Meaning |
| --- | --- | --- | --- |
| ai_interaction_ref | Ref<AIInteractionRecord> | Yes | Exact bounded AI record. |
| provider | Text | Yes | Provider identity. |
| model | Text | Yes | Model identity. |
| model_version | NullableText | Yes | Exact exposed model version or null when unavailable. |
| instruction_ref | ContentRef | Yes | Pinned instruction/version artifact. |
| context_refs | ContentRef[+] | Yes | Exact context artifacts supplied to the model. |
| output_ref | ContentRef | Yes | Preserved structured observable output. |

No hidden chain-of-thought, private reasoning or dependency on unrecoverable internal model state is stored. The event may preserve an output summary through the referenced AIInteractionRecord. Model confidence, probability, similarity and self-assessment do not create verification or execution authority.

### REPLAY

Used by REPLAY_REQUESTED, EXECUTION_COMPLETED and EXECUTION_REFUSED.

| Additional field | Type | Required | Meaning |
| --- | --- | --- | --- |
| approved_change_set_ref | Ref<ApprovedChangeSet> | Yes | Exact sealed authorization considered. |
| execution_ref | Ref<ExecutionResult> | No | Exact attempt result; absent only on REPLAY_REQUESTED before result creation. |
| engine | Text | Yes | Replay engine identity selected from sealed qualified policy. |
| engine_version | Text | Yes | Exact replay engine version. |
| input_document_version_ref | DocumentVersionRef | Yes | Exact approved/observed execution input. |
| output_document_version_ref | Nullable<DocumentVersionRef> | Yes | Exact staged output, or null when refused before mutation. |
| first_material_failure_event_id | ID | No | Required for refusal propagated from an earlier event; when replay first detects failure, the current event is the first material failure. |

REPLAY metadata cannot carry locator, operation or payload overrides. Those are resolved only from approved_change_set_ref. A refused event has no output; a mechanically successful event does not imply validation or release.

### VALIDATION

Used by VALIDATION_COMPLETED and OUTPUT_QUARANTINED.

| Additional field | Type | Required | Meaning |
| --- | --- | --- | --- |
| validation_report_ref | Ref<ValidationReport> | Yes | Exact independent report. |
| validator | Actor | Yes | actor_type VALIDATOR and operationally independent from replay. |
| validator_version | Text | Yes | Exact independent validator implementation version. |
| configuration_ref | ContentRef | Yes | Pinned validator configuration/qualification profile. |
| input_document_version_ref | DocumentVersionRef | Yes | Exact preserved replay input. |
| output_document_version_ref | DocumentVersionRef | Yes | Exact staged output inspected. |
| observation_refs | ContentRef[+] | Yes | Independent observations supporting the outcome. |
| first_material_failure_event_id | ID | No | Required on downstream quarantine when validation failure was established by an earlier event. |

The replay engine cannot emit VALIDATION metadata as the responsible validator. Validation observations must be independently generated and pinned.

### EXCEPTION

Used by EXCEPTION_RECORDED and EXCEPTION_RESOLVED.

| Additional field | Type | Required | Meaning |
| --- | --- | --- | --- |
| exception_ref | Ref<ExceptionRecord> | Yes | Exact exception revision. |
| first_material_failure_event_id | ID | Yes | Event that first established the material failure. For a first-detection EXCEPTION_RECORDED event, this equals its own event_id. |
| remediation_refs | Reference[] | Yes | New records proving attempted or completed remediation; empty on initial detection. |

## Integrity payload hash

integrity_payload_hash is calculated over an object containing every AuditEvent field except integrity_payload_hash itself:

1. Serialize the payload with RFC 8785 JSON Canonicalization Scheme.
2. Encode the canonical JSON as UTF-8.
3. Hash those bytes with SHA-256.
4. Store exactly 64 lowercase hexadecimal characters.

Array order is significant and must be deterministic. The hash is an integrity control, not a signature or authorization digest. Changes require a new event; an event is never rehashed in place. Signature, tenant anchoring and retention mechanisms remain deployment decisions outside schema 0.1.0.

## Causation and first material failure

- TASK_CREATED is the only root event and has causation_event_id null.
- Every other event names one earlier event in the same task and correlation chain as its direct cause.
- Event causation is acyclic. A downstream response such as proposal blocking, execution refusal, validation quarantine or release withholding carries first_material_failure_event_id in its metadata and preserves the first specific error code in error_codes.
- A detector event that first establishes a failure is itself the first material failure. It does not point first_material_failure_event_id to a later response.
- Parallel successful target branches may share an earlier cause. Their events remain distinct and do not erase a failure on another required target.
- Remediation starts a new causal branch or correlation as governed by orchestration, but references the prior exception/decision in object_refs and preserves the original events.

## Event responsibility matrix

| EventType | Actor / metadata | Required material references |
| --- | --- | --- |
| TASK_CREATED | SYSTEM or HUMAN / GOVERNANCE | FoundationTask output. |
| DOCUMENT_REGISTERED | SYSTEM / GOVERNANCE | DocumentArtifact and DocumentVersion outputs; exact document_version_refs. |
| DOCUMENT_PREFLIGHT_COMPLETED | SYSTEM / DETERMINISTIC_EVALUATION | DocumentPreflightAssessment output and assessor implementation binding. |
| ANALYSIS_COMPLETED | SYSTEM / GOVERNANCE | AnalysisRun and typed analysis outputs. |
| RULE_EVALUATED | SYSTEM / DETERMINISTIC_EVALUATION | RuleEvaluation and exact EvaluatorBinding. |
| SOURCE_ASSESSED | SYSTEM / DETERMINISTIC_EVALUATION | SourceAssessment and exact EvaluatorBinding. |
| EVIDENCE_CHECKED | SYSTEM / DETERMINISTIC_EVALUATION | EvidenceCheck and exact EvaluatorBinding. |
| EVIDENCE_ASSESSED | SYSTEM / DETERMINISTIC_EVALUATION | EvidenceAssessment and aggregation evaluator binding. |
| MAPPING_PROPOSED | SYSTEM or AI / GOVERNANCE | MappingProposal; AI participation also has a distinct AI_INTERACTION_RECORDED event. |
| AI_INTERACTION_RECORDED | AI / AI_INTERACTION | AIInteractionRecord and instruction/context/output references. |
| CHANGE_PROPOSED | SYSTEM or HUMAN / GOVERNANCE | Exact ChangeProposal revision. |
| REVIEW_DECIDED | HUMAN / GOVERNANCE | ReviewDecision and pinned proposal/evidence. |
| SOURCE_REQUESTED | HUMAN or SYSTEM / GOVERNANCE | REQUEST_MORE_SOURCE ReviewDecision and requested SourceRequirements. |
| DECISION_SUPERSEDED | HUMAN or SYSTEM / GOVERNANCE | Old and new immutable ReviewDecision records. |
| CHANGE_SET_APPROVED | SYSTEM / GOVERNANCE | ApprovedChangeSet and its human ReviewDecisions. |
| APPROVAL_INVALIDATED | SYSTEM / GOVERNANCE | Affected ApprovedChangeSet and first material failure. |
| APPROVAL_REVOKED | HUMAN or SYSTEM / GOVERNANCE | Revocation decision and ApprovedChangeSet. |
| REPLAY_REQUESTED | SYSTEM / REPLAY | ApprovedChangeSet and exact input. |
| EXECUTION_COMPLETED | REPLAY_ENGINE / REPLAY | ExecutionResult, ApprovedChangeSet and exact input/output. |
| EXECUTION_REFUSED | REPLAY_ENGINE / REPLAY | Refused ExecutionResult, ApprovedChangeSet, exact input and specific error. |
| VALIDATION_COMPLETED | VALIDATOR / VALIDATION | ValidationReport, exact input/output and independent observations. |
| RELEASE_ELIGIBILITY_CONFIRMED | SYSTEM / GOVERNANCE | Passing ValidationReport and task/document release projections. |
| RELEASE_WITHHELD | SYSTEM / GOVERNANCE | Blocking target/report/exception and first material failure. |
| OUTPUT_QUARANTINED | SYSTEM or VALIDATOR / VALIDATION | Failed/inconclusive ValidationReport and staged output. |
| OUTPUT_RELEASED | SYSTEM / GOVERNANCE | Eligible output DocumentVersion and release decision. |
| EXCEPTION_RECORDED | SYSTEM, HUMAN, REPLAY_ENGINE or VALIDATOR / EXCEPTION | ExceptionRecord and first material failure. |
| EXCEPTION_RESOLVED | SYSTEM or HUMAN / EXCEPTION | New remediation evidence and resolved ExceptionRecord revision. |
| STATUS_TRANSITIONED | SYSTEM / GOVERNANCE | Object before/after revisions with legal lifecycle transition. |

## Immutability and authority

Events are append-only and immutable. Actor, timestamps, references, metadata, errors and integrity hashes cannot be rewritten. A correction uses a new event and causal link.

An AuditEvent proves that Foundation recorded an action or observation. It does not make an invalid transition valid, transform AI output into evidence, create approval, authorize replay or replace an independent ValidationReport.
