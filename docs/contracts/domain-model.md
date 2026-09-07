# Foundation v2 Domain Model

**Contract version:** 2.0.0  
**Date:** 2026-09-07  
**Authority:** [Current baseline](../CURRENT_BASELINE.md) and active [ADRs](../adr/README.md). This is a technology-neutral contract, not runtime implementation.

## Reading and identity conventions

The normative invariants are in [invariants.md](invariants.md); lifecycle and enumeration definitions are in [status-model.md](status-model.md). Wire schemas in [foundation.openapi.yaml](foundation.openapi.yaml) project these contracts and cannot weaken them. Error and event semantics remain in their dedicated documents.

Each record has the following required envelope unless explicitly excluded:

| Field | Type | Meaning |
| --- | --- | --- |
| schema_version | SchemaVersion | 2.0.0, version of this contract. |
| object_type | ObjectType | Exact domain class name. |
| id | ID | Stable logical record identity. |
| revision | PositiveInt | Immutable snapshot revision. |
| created_at | Timestamp | UTC time this snapshot was recorded. |
| task_id | ID | Required for task-owned records; absent on FoundationTask and reusable policy definitions. |

All recorded revisions are immutable. Lifecycle transitions append an event and a new snapshot; they do not edit prior snapshots. Reads without a revision return the latest projection. A reference always pins a revision. New evidence or a human override creates a new record/revision and event, preserving earlier machine/AI results. ApprovedChangeSet authorization content is sealed separately from lifecycle state.

DocumentVersion has revision 1 forever; its id is the version_id used in DocumentVersionRef. ApprovedChange is inline in its parent authorization and is not independently executable. ReplayRequest has exactly its two specified fields and no envelope. AuditEvent has its own envelope in [event-model.md](event-model.md).

| Primitive | Constraint |
| --- | --- |
| ID | Nonempty opaque string matching `^[A-Za-z0-9][A-Za-z0-9._:-]*$`; never a native address. |
| BusinessTargetID | Logical business key matching `^[A-Z][A-Z0-9_.]*$`; stable across document versions. |
| SHA256 | Exactly 64 lowercase hexadecimal characters, SHA-256 of exact bytes. |
| Text / NullableText | Nonempty string / nonempty string or null. |
| Timestamp | RFC 3339 UTC timestamp with Z suffix. |
| URI | Absolute artifact URI; does not authorize fetching arbitrary locations. |
| PositiveInt / NonNegativeInt | Integer >= 1 / integer >= 0. |
| Bool | Boolean, never a string. |
| Ref<T> | Reference with object_type fixed to T. |
| T[] / T[+] | Array of T, permitting empty / requiring at least one. No duplicate record references. |

NativeLocator addresses and semantic IDs are not interchangeable with BusinessTargetID. Confidence is not a verification or authorization field.

## Shared value and reference contracts

### Reference

Typed immutable record reference. A reference never grants authority by itself.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| object_type | ObjectType | Yes | Expected domain object class. |
| object_id | ID | Yes | Record ID (event_id for AuditEvent). |
| revision | PositiveInt | Yes | Exact immutable revision (event_version for AuditEvent). |

### DocumentVersionRef

Binary-bound document identity. version_id resolves to DocumentVersion.id, whose document_id and binary_hash must match.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| document_id | ID | Yes | DocumentArtifact.id. |
| version_id | ID | Yes | DocumentVersion.id, never a latest-version alias. |
| binary_hash | SHA256 | Yes | Exact immutable binary SHA-256. |

### SemanticReference

Semantic identity in one perception snapshot, not a native execution address.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| snapshot_ref | Ref<PerceptionSnapshot> | Yes | Exact perception snapshot. |
| semantic_id | Text | Yes | Engine representation ID such as #/texts/137. |

### ContentRef

Immutable artifact reference with SHA-256 and media type. The URI alone is never proof of content or authority.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| uri | URI | Yes | Immutable artifact address; governed storage, not arbitrary retrieval authorization. |
| sha256 | SHA256 | Yes | SHA-256 of artifact bytes. |
| media_type | Text | Yes | Content media type. |

### Actor

Authenticated or attested actor; request bodies cannot impersonate actor authority.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| actor_type | ActorType | Yes | Human, system, AI, replay engine or independent validator. |
| actor_id | ID | Yes | Stable identity within the chosen identity system. |

### BusinessValue

Reviewable value. DECIMAL uses an exact decimal string; PERCENT 6.08 means 6.08%, not 0.0608.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| kind | ValueKind | Yes | TEXT or DECIMAL. |
| value | Text | Yes | Exact string value. |
| unit | ValueUnit | Yes | NONE or PERCENT. |

### ApprovedPayload

Exact text authorized for replacement. It is not code, a prompt, or a template to expand at replay time.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| replacement_text | Text | Yes | Exact final replacement string. |

### CapabilityResult

Operation- and engine-specific capability observation. SUPPORTED requires a qualification artifact and a Transitional mutation profile.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| operation | MutationOperation | Yes | Specific native operation. |
| structure | Text | Yes | Native structure tested. |
| conformance | ConformanceClass | Yes | Document conformance class. |
| status | CapabilityStatus | Yes | Supported, protected, unsupported or unknown. |
| engine | Text | Yes | Candidate engine. |
| engine_version | Text | Yes | Exact tested version. |
| qualification_ref | ContentRef | No | Qualification evidence, required for SUPPORTED. |
| reason | Text | Yes | Scope and limitations. |

### NativeAddress

Closed tagged union. CONTENT_CONTROL: kind, sdt_id. BOOKMARK: kind, bookmark_name. PART_PATH: kind, exact_path. SHEET_CELL: kind, sheet_name, cell_address. Every variant includes only its named fields. Paths are exact; no fuzzy or nearest-match syntax.

### Condition

Declarative deterministic pre/postcondition. No scripts, prompts or arbitrary expressions. Unknown or unevaluable conditions block execution or release.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| condition_id | ID | Yes | Unique within the authorization. |
| kind | ConditionKind | Yes | Registered evaluator obligation. |
| scope_ref | Reference | Yes | Exact object to evaluate. |
| expected | Text | Yes | Literal expected hash, text, value or named preservation obligation. |

### ProtectedScope

Required preservation scope. Everything outside approved changes is preserved. An explicit serialization allowance must itself be qualified and approved.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| document_version_ref | DocumentVersionRef | Yes | Protected input version. |
| protected_locator_refs | Ref<NativeLocator>[] | Yes | Explicit protected native objects. |
| preserve_outside_approved_changes | Bool | Yes | MUST be true. |
| serialization_allowance_ref | ContentRef | No | Pinned narrowly qualified allowance; absent means none. |

### ValidationRequirement

One validation obligation in a pinned plan; no engine-chosen optional downgrade.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| requirement_id | ID | Yes | Unique in the ValidationPlan. |
| kind | ValidationCheckKind | Yes | Independent check class. |
| mandatory | Bool | Yes | True for required release checks. |
| business_target_ids | BusinessTargetID[] | Yes | Empty for whole-package preservation checks. |
| description | Text | Yes | What must be observed and preserved. |

### AuthorizationBinding

Sealed content covered by authorization_digest. No lifecycle change may alter these fields.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| target_document_version_ref | DocumentVersionRef | Yes | Exact target version and binary hash. |
| source_document_version_refs | DocumentVersionRef[+] | Yes | Pinned source binaries. |
| target_contract_ref | Ref<TargetContract> | Yes | Exact TargetContract version. |
| rule_pack_ref | Ref<RulePack> | Yes | Exact RulePack version. |
| source_assessment_refs | Ref<SourceAssessment>[+] | Yes | All required sufficiency assessments. |
| evidence_assessment_refs | Ref<EvidenceAssessment>[+] | Yes | All required VERIFIED evidence assessments. |
| review_decision_refs | Ref<ReviewDecision>[+] | Yes | Explicit human approvals. |
| approved_changes | ApprovedChange[+] | Yes | Exact native locators, operations, payloads, evidence and per-change conditions. |
| preconditions | Condition[+] | Yes | Set-wide deterministic preflight checks. |
| postconditions | Condition[+] | Yes | Set-wide deterministic result checks. |
| protected_scope | ProtectedScope | Yes | Preservation outside approved scope. |
| validation_plan_ref | Ref<ValidationPlan> | Yes | Pinned independent validation obligations. |
| mutation_profile | ConformanceClass | Yes | MUST be TRANSITIONAL in v2. |
| qualification_refs | ContentRef[+] | Yes | Evidence qualifying every operation/profile/engine combination. |

### DocumentRole

DocumentRole is a closed enum, not a separate mutable document identity. DocumentArtifact.role assigns a document to one task. The same bytes can have different roles in different task registrations. CURRENT_SOURCE still requires policy-based authority and sufficiency; HISTORICAL_SOURCE and TEMPLATE do not automatically satisfy current-period requirements. EVALUATION_ONLY cannot authorize production changes.

## A. Task and Document

### FoundationTask

One governed business workflow; aggregate progress never grants mutation authority.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| title | Text | Yes | Human-readable task name. |
| business_case | Text | Yes | Use-case identifier; not executable policy. |
| current_period | Text | Yes | Explicit assessed period, e.g. FY2025. |
| status | TaskStatus | Yes | Governed lifecycle projection. |
| document_refs | Ref<DocumentArtifact>[] | Yes | Registered task documents. |
| target_contract_ref | Ref<TargetContract> | Yes | Pinned contract revision. |
| rule_pack_ref | Ref<RulePack> | Yes | Pinned RulePack revision. |
| required_business_target_ids | BusinessTargetID[+] | Yes | All targets required for task completion. |
| exception_refs | Ref<ExceptionRecord>[] | Yes | Open and resolved exception records. |
| release_status | ReleaseStatus | Yes | Whole-task output release state. |

COMPLETED requires every required target to pass its evidence and validation gates. A validated partial change does not imply task completion.

### DocumentArtifact

Logical document registered in one task; source role is not evidence sufficiency.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| file_name | Text | Yes | Display filename, never native identity. |
| role | DocumentRole | Yes | Role in this task. |
| status | DocumentStatus | Yes | Document lifecycle, separate from immutable binary versions. |
| version_refs | DocumentVersionRef[+] | Yes | Known immutable versions. |
| current_version_ref | DocumentVersionRef | Yes | Current selected version; changing it triggers stale-binding checks. |

A role or current-version change is a new artifact revision and audit event. Binary reuse across tasks does not confer source authority.

### DocumentVersion

Exactly one immutable binary, identified by its SHA-256 binary_hash and scoped under a DocumentArtifact.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| document_id | ID | Yes | Owning DocumentArtifact ID. |
| binary_hash | SHA256 | Yes | Lowercase SHA-256 of exact binary bytes; no prefix. |
| byte_length | NonNegativeInt | Yes | Length of the exact binary. |
| format | DocumentFormat | Yes | Detected format, not filename inference. |
| conformance | ConformanceClass | Yes | Detected OOXML conformance or explicit unknown/not applicable. |
| content_ref | ContentRef | Yes | Immutable binary storage reference; sha256 MUST equal binary_hash. |
| capability_results | CapabilityResult[] | Yes | Qualification evidence scoped to structure, operation, profile and engine. |
| derived_from | DocumentVersionRef | No | Input version for generated output. |

Its envelope revision is always 1. Bytes, hash and classification observations in this record are immutable; corrected observations are separate records or a new registration, never rewritten binary history.

## B. Perception and Native Identity

### PerceptionSnapshot

Immutable semantic perception run output for exactly one document version.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| document_version_ref | DocumentVersionRef | Yes | Exact perceived binary. |
| analysis_run_ref | Ref<AnalysisRun> | Yes | Run that produced the snapshot. |
| engine | Text | Yes | Perception engine name, provisionally Docling-slim. |
| engine_version | Text | Yes | Exact engine version used. |
| configuration_ref | ContentRef | Yes | Pinned configuration and digest. |
| semantic_object_refs | Ref<SemanticObject>[] | Yes | Objects belonging to this snapshot. |
| limitations | Text[] | Yes | Detected omissions and unsupported constructs. |

### SemanticObject

Object in a semantic snapshot; never a native execution address.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| semantic_reference | SemanticReference | Yes | Snapshot identity plus engine-local semantic ID. |
| object_kind | Text | Yes | Perception type such as paragraph or table cell; not capability authority. |
| value | BusinessValue | Yes | Perceived value. |
| parent_ref | Ref<SemanticObject> | No | Optional semantic parent in the same snapshot. |
| native_binding_refs | Ref<NativeBinding>[] | Yes | Associations to native objects. |

### NativeLocator

Exact version-scoped native execution address for one native object.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| document_version_ref | DocumentVersionRef | Yes | Exactly one immutable DocumentVersion, including its SHA-256. |
| part_uri | Text | Yes | Exact package part URI. |
| locator_type | LocatorType | Yes | Qualified deterministic address kind. |
| address | NativeAddress | Yes | Typed address matching locator_type. |
| expected_object_type | Text | Yes | Native structure expected at resolution. |
| capture_engine | Text | Yes | Native reader/engine identity and version used to capture this locator. |

The locator and address are immutable. Exact resolution must return one object in the bound binary. Zero/multiple matches refuse execution. No fuzzy repair at replay.

### NativeBinding

Semantic-to-native association, separate from the exact native address.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| semantic_object_ref | Ref<SemanticObject> | Yes | Semantic side of the association. |
| native_locator_refs | Ref<NativeLocator>[] | Yes | Native candidates or resolved objects. |
| status | BindingStatus | Yes | Association result; no execution authority. |
| method | Text | Yes | Deterministic capture or discovery method. |
| reason | Text | Yes | Explain association and ambiguity without claiming authorization. |

RESOLVED requires explicit proven associations to the same document version. A semantic object may span several native objects; each ApprovedChange still selects exactly one uniquely resolving NativeLocator.

## C. Business Governance

### TargetContract

Versioned business target contract defining scope and preservation requirements.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| name | Text | Yes | Contract name. |
| business_target_ids | BusinessTargetID[+] | Yes | Stable logical targets. |
| target_region_refs | Ref<TargetRegion>[+] | Yes | Version-specific target instances. |
| source_requirement_refs | Ref<SourceRequirement>[] | Yes | Required evidence inputs. |
| validation_plan_ref | Ref<ValidationPlan> | Yes | Required independent checks. |
| protected_scope | ProtectedScope | Yes | Preservation policy. |

The reference revision is the TargetContract version. Defining a contract is not implementing business rules.

### TargetRegion

Business target occurrence mapped to a concrete target document version.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_target_id | BusinessTargetID | Yes | Business identity, distinct from semantic/native identity. |
| document_version_ref | DocumentVersionRef | Yes | Target binary. |
| semantic_object_refs | Ref<SemanticObject>[] | Yes | Semantic context. |
| native_binding_refs | Ref<NativeBinding>[] | Yes | Native associations. |
| verification_status | TargetVerificationStatus | Yes | Deterministic evidence state. |
| capability_status | CapabilityStatus | Yes | Capability for contemplated operations. |
| source_requirement_refs | Ref<SourceRequirement>[] | Yes | Requirements relevant to this target. |

AI output cannot independently set verification_status to VERIFIED. Verification is not approval.

### RulePack

Versioned collection of deterministic policy declarations where business policy is known.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| name | Text | Yes | Rule Pack name. |
| business_rule_refs | Ref<BusinessRule>[+] | Yes | Pinned rule declarations. |
| policy_document_ref | ContentRef | Yes | Authoritative policy definition and digest. |

No executable business rules or production thresholds are defined by the illustrative fixtures.

### BusinessRule

Referenceable rule declaration, not executable code.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_target_ids | BusinessTargetID[+] | Yes | Applicable business targets. |
| source_requirement_refs | Ref<SourceRequirement>[] | Yes | Required sources. |
| policy_ref | ContentRef | Yes | Versioned policy definition. |
| description | Text | Yes | Plain-language purpose and input/output obligations. |

Known policy is evaluated deterministically. Unknown policy produces an exception, not invented policy.

### RuleEvaluation

Deterministic evaluation record preserving inputs and outcome.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_rule_ref | Ref<BusinessRule> | Yes | Exact evaluated rule revision. |
| business_target_id | BusinessTargetID | Yes | Evaluated target. |
| input_refs | Reference[] | Yes | Pinned inputs. |
| outcome | CheckOutcome | Yes | Recorded deterministic outcome. |
| proposed_value | BusinessValue | No | Value proposed by a successful evaluation. |
| error_codes | ErrorCode[] | Yes | Catalog codes explaining a block or failure. |

## D. Source, Evidence and Mapping

### SourceRequirement

Policy-level source requirements for a target and period.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_target_id | BusinessTargetID | Yes | Target whose evidence is required. |
| current_period | Text | Yes | Required source period. |
| required_fields | Text[+] | Yes | Business information required; no invented values. |
| permitted_roles | DocumentRole[+] | Yes | Roles allowed by the pinned policy. |
| required_authority | SourceAuthority | Yes | Minimum authority classification. |
| blocking | Bool | Yes | Whether unsatisfied requirements block the target. |
| policy_ref | ContentRef | Yes | Authority for these requirements. |

### SourceAssessment

Deterministic sufficiency assessment; human acceptance cannot manufacture missing evidence.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| source_requirement_ref | Ref<SourceRequirement> | Yes | Requirement evaluated. |
| business_target_id | BusinessTargetID | Yes | Assessed target. |
| document_version_refs | DocumentVersionRef[] | Yes | Sources examined; empty is explicit when missing. |
| status | SourceAssessmentStatus | Yes | Sufficiency lifecycle. |
| method | AssessmentMethod | Yes | DETERMINISTIC only. |
| authority | SourceAuthority | Yes | Authority supported by policy and provenance. |
| satisfied_fields | Text[] | Yes | Fields actually supported. |
| missing_fields | Text[] | Yes | Required fields not supported. |
| evidence_refs | Ref<EvidenceRecord>[] | Yes | Observed supporting evidence. |
| error_codes | ErrorCode[] | Yes | Blocking/diagnostic catalog codes. |

SUFFICIENT requires all blocking fields, authoritative permitted sources, correct period and resolved conflicts. A new source creates a new assessment revision or assessment; prior results remain immutable.

### EvidenceRecord

Immutable observed source fact with provenance, not an AI assertion.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| kind | EvidenceKind | Yes | Native value, formula identity, source excerpt or validation output. |
| document_version_ref | DocumentVersionRef | Yes | Exact source binary. |
| semantic_object_ref | Ref<SemanticObject> | No | Semantic context if available. |
| native_locator_ref | Ref<NativeLocator> | No | Native source identity if applicable. |
| content_ref | ContentRef | Yes | Preserved extracted observation and digest. |
| value | BusinessValue | Yes | Observed business value. |
| formula_text | Text | No | Native formula text, kept distinct from calculated value. |
| authority | SourceAuthority | Yes | Source authority established by policy. |
| current_period | Text | Yes | Period that the evidence can support. |

XLSX observations that depend on formulas require native cell/formula identity, not only a calculated value. AI output is held in AIInteractionRecord and cannot become an authoritative EvidenceRecord by renaming it.

### EvidenceCheck

One deterministic evidence test with replayable inputs and a policy reference.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_target_id | BusinessTargetID | Yes | Checked target. |
| source_assessment_refs | Ref<SourceAssessment>[+] | Yes | Sufficiency inputs. |
| evidence_refs | Ref<EvidenceRecord>[] | Yes | Evidence tested; empty allowed for missing-source checks. |
| policy_ref | ContentRef | Yes | Check policy. |
| method | AssessmentMethod | Yes | DETERMINISTIC only. |
| outcome | CheckOutcome | Yes | Explicit result. |
| error_codes | ErrorCode[] | Yes | Catalog diagnostics. |

### EvidenceAssessment

Aggregate evidence verdict for one target, never a model confidence score.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_target_id | BusinessTargetID | Yes | Target assessed. |
| source_assessment_refs | Ref<SourceAssessment>[+] | Yes | Pinned sufficiency records. |
| evidence_check_refs | Ref<EvidenceCheck>[+] | Yes | Deterministic checks. |
| status | EvidenceStatus | Yes | VERIFIED only if every required check passes. |
| method | AssessmentMethod | Yes | DETERMINISTIC only. |
| error_codes | ErrorCode[] | Yes | Reasons for insufficient, conflicting or stale evidence. |

### MappingProposal

Suggested association of source information to a business target; acceptance is not write authority.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_target_id | BusinessTargetID | Yes | Proposed target. |
| target_region_ref | Ref<TargetRegion> | Yes | Concrete target occurrence. |
| evidence_refs | Ref<EvidenceRecord>[] | Yes | Source observations. |
| rule_evaluation_refs | Ref<RuleEvaluation>[] | Yes | Deterministic inputs. |
| ai_interaction_refs | Ref<AIInteractionRecord>[] | Yes | Optional bounded assistance; may be empty. |
| proposed_value | BusinessValue | Yes | Candidate value. |
| status | MappingProposalStatus | Yes | Review lifecycle. |
| rationale | Text | Yes | Reviewable explanation. |
| error_codes | ErrorCode[] | Yes | Blocking diagnostics. |

### AIInteractionRecord

Bounded AI interaction with zero execution authority.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| actor | Actor | Yes | AI service identity; actor_type must be AI. |
| provider | Text | Yes | Provider identity. |
| model | Text | Yes | Model identity. |
| model_version | NullableText | Yes | Version if exposed, otherwise null. |
| instruction_ref | ContentRef | Yes | Instruction/version artifact and digest. |
| context_refs | ContentRef[+] | Yes | Actual supplied context artifacts and digests. |
| input_refs | Reference[] | Yes | Governed source/context objects. |
| output_ref | ContentRef | Yes | Preserved structured output, subject to data policy. |
| output_summary | Text | Yes | Concise observable result, not hidden reasoning. |
| verification_refs | Ref<EvidenceAssessment>[] | Yes | Subsequent independent evidence outcomes. |
| untrusted_content_detected | Bool | Yes | Whether document content was flagged as untrusted instructions. |

No hidden chain-of-thought field or dependency is permitted. Model confidence, probability, similarity and self-assessment never create execution authority.

## E. Review and Authorization

### ChangeProposal

Concrete proposed native change with zero execution authority, including after review status APPROVED.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_target_id | BusinessTargetID | Yes | One proposed business target. |
| target_document_version_ref | DocumentVersionRef | Yes | Exact proposed target version. |
| target_contract_ref | Ref<TargetContract> | Yes | Pinned contract. |
| rule_pack_ref | Ref<RulePack> | Yes | Pinned RulePack. |
| mapping_proposal_ref | Ref<MappingProposal> | Yes | Mapping reviewed. |
| source_assessment_refs | Ref<SourceAssessment>[+] | Yes | Sufficiency inputs. |
| evidence_assessment_refs | Ref<EvidenceAssessment>[+] | Yes | Evidence verdicts. |
| native_locator_ref | Ref<NativeLocator> | Yes | Proposed exact native target. |
| operation | MutationOperation | Yes | Candidate operation, never an immediate command. |
| current_value | BusinessValue | Yes | Observed current value. |
| proposed_value | BusinessValue | Yes | Proposed current-year value. |
| payload | ApprovedPayload | Yes | Exact replacement text proposed for review. |
| status | ChangeProposalStatus | Yes | Proposal lifecycle. |
| error_codes | ErrorCode[] | Yes | Blocking reasons. |

Editing a proposal creates a new revision and invalidates decisions referring to an earlier payload. Blocked conclusions cannot enter an ApprovedChangeSet.

### ReviewDecision

Explicit immutable human decision on a pinned proposal revision.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| change_proposal_ref | Ref<ChangeProposal> | Yes | Exact proposal reviewed. |
| reviewer | Actor | Yes | Authenticated HUMAN identity, set by the service. |
| outcome | ReviewOutcome | Yes | APPROVE, REJECT or DEFER. |
| reason | Text | Yes | Reviewable reason. |
| reviewed_evidence_refs | Reference[] | Yes | Pinned evidence and sufficiency records actually reviewed. |
| supersedes_decision_ref | Ref<ReviewDecision> | No | Prior decision superseded by this new record. |

Review records never rewrite earlier machine/AI evidence. An APPROVE outcome with blocking gates cannot yield an ApprovedChangeSet.

### ApprovedChange

One sealed operation inside an ApprovedChangeSet; not independently dispatchable.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| business_target_id | BusinessTargetID | Yes | Approved business target. |
| change_proposal_ref | Ref<ChangeProposal> | Yes | Exact approved proposal. |
| native_locator_ref | Ref<NativeLocator> | Yes | Immutable exact execution address. |
| operation | MutationOperation | Yes | Approved native operation. |
| payload | ApprovedPayload | Yes | Exact approved payload. |
| evidence_refs | Ref<EvidenceRecord>[+] | Yes | Evidence supporting this change. |
| review_decision_ref | Ref<ReviewDecision> | Yes | Explicit APPROVE decision. |
| preconditions | Condition[+] | Yes | Required deterministic checks before mutation. |
| postconditions | Condition[+] | Yes | Required deterministic result checks. |

Stored inline in authorization.approved_changes; references to its id/revision resolve within that sealed set. The parent binds contract, RulePack, binary, protected scope and validation.

### ApprovedChangeSet

Sealed authorization assembled by governance from explicit decisions and passing deterministic gates.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| status | ApprovedChangeSetStatus | Yes | Lifecycle; clients cannot set it. |
| authorization | AuthorizationBinding | Yes | Exact frozen execution authorization. |
| authorization_digest | SHA256 | Yes | SHA-256 of canonical authorization only; excludes lifecycle envelope. |

Creation starts at APPROVED. Subsequent lifecycle revisions cannot alter authorization or its digest. Content changes require a new set ID and approval. Eligibility also checks latest revocation/invalidation events, not just the pinned historical snapshot.

## F. Execution and Validation

### ReplayRequest

Internal dispatch request derived only from an eligible ApprovedChangeSet.

No common record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| execution_id | ID | Yes | Orchestrator-assigned execution/idempotency identity. |
| approved_change_set_ref | Ref<ApprovedChangeSet> | Yes | Exact sealed authorization snapshot. |

Exactly these two properties are allowed. No envelope fields, task fields, free-form locator, operation, payload, profile or validation override is accepted. Contract version and correlation travel in trusted transport metadata. Frontend never calls this internal boundary.

### ExecutionResult

Mechanical replay attempt result, independent of validation and release.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| approved_change_set_ref | Ref<ApprovedChangeSet> | Yes | Authorization used. |
| input_document_version_ref | DocumentVersionRef | Yes | Actual execution input. |
| status | ExecutionStatus | Yes | Attempt lifecycle. |
| engine | Text | Yes | Engine identity. |
| engine_version | Text | Yes | Exact version. |
| change_result_refs | Ref<ChangeExecutionResult>[] | Yes | Per-change results. |
| output_document_version_ref | DocumentVersionRef | No | Staged output; absent for refusal before mutation. |
| error_codes | ErrorCode[] | Yes | Attempt diagnostics. |
| release_status | ReleaseStatus | Yes | WITHHELD until independent validation and release gates succeed. |

Its id equals ReplayRequest.execution_id. SUCCEEDED means mechanical completion only; it does not authorize release. Failed staging is quarantined.

### ChangeExecutionResult

Result for one ApprovedChange in one execution attempt.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| execution_ref | Ref<ExecutionResult> | Yes | Parent attempt. |
| approved_change_ref | Ref<ApprovedChange> | Yes | Exact change in the sealed set. |
| status | ChangeExecutionStatus | Yes | Applied, refused, failed or not attempted. |
| observed_before | BusinessValue | No | Observed value before the operation. |
| observed_after | BusinessValue | No | Observed value after the operation. |
| error_codes | ErrorCode[] | Yes | Per-change diagnostics. |

### ValidationPlan

Pinned independent validation obligations approved before execution.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| name | Text | Yes | Plan identifier. |
| required_checks | ValidationRequirement[+] | Yes | Explicit scope and checks, all mandatory checks must pass. |
| validator_policy_ref | ContentRef | Yes | Independent validator qualification and separation policy. |
| release_requires_all_targets | Bool | Yes | True requires every task-required target before whole-document release. |

Plan changes require new approval for affected sets. A replay engine cannot waive checks or assert their success.

### ValidationReport

Independent validation record against an exact execution and output binary.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| execution_ref | Ref<ExecutionResult> | Yes | Exact attempt assessed. |
| approved_change_set_ref | Ref<ApprovedChangeSet> | Yes | Approved changes and scope. |
| validation_plan_ref | Ref<ValidationPlan> | Yes | Required checks. |
| input_document_version_ref | DocumentVersionRef | Yes | Preserved pre-mutation input. |
| output_document_version_ref | DocumentVersionRef | Yes | Exact staged output assessed. |
| validator | Actor | Yes | Independent VALIDATOR identity; distinct from replay engine. |
| status | ValidationStatus | Yes | Independent outcome. |
| check_result_refs | Ref<ValidationCheckResult>[] | Yes | Check evidence. |
| release_status | ReleaseStatus | Yes | May remain WITHHELD even when in-scope validation passes. |
| blocking_exception_refs | Ref<ExceptionRecord>[] | Yes | Unresolved task/target blockers. |
| error_codes | ErrorCode[] | Yes | Validation and release diagnostics. |

PASSED requires all mandatory checks and preservation checks to PASS; engine self-report is insufficient. Any unauthorized change prevents successful release.

### ValidationCheckResult

One independent validation result with preserved observations.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| validation_report_ref | Ref<ValidationReport> | Yes | Report membership. |
| requirement_id | ID | Yes | Matches a ValidationRequirement in the pinned plan. |
| kind | ValidationCheckKind | Yes | Required check type. |
| outcome | CheckOutcome | Yes | Explicit observed outcome. |
| observation_ref | ContentRef | Yes | Independent evidence artifact and digest. |
| error_codes | ErrorCode[] | Yes | Catalog diagnostics. |

### ExceptionRecord

Traceable blocking or nonblocking exception and its remediation history.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| error_code | ErrorCode | Yes | Catalog definition supplies blocking and recovery semantics. |
| status | ExceptionStatus | Yes | Exception lifecycle. |
| business_target_id | BusinessTargetID | No | Affected target, if any. |
| related_refs | Reference[] | Yes | Affected immutable records. |
| detected_by | Actor | Yes | Originating actor. |
| details | Text | Yes | Safe, reviewable facts. |
| resolution_refs | Reference[] | Yes | New evidence/decisions proving resolution; never old-record edits. |

### AnalysisRun

Governed orchestration resource for perception, enrichment and assessment; no mutation authority.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| document_version_refs | DocumentVersionRef[+] | Yes | Pinned inputs. |
| target_contract_ref | Ref<TargetContract> | Yes | Pinned target definition. |
| rule_pack_ref | Ref<RulePack> | Yes | Pinned business policy. |
| status | AnalysisStatus | Yes | Analysis lifecycle. |
| output_refs | Reference[] | Yes | Perception, source, evidence and proposal records. |
| error_codes | ErrorCode[] | Yes | Explicit analysis gaps. |

### AuditEvent references

All governance, execution, validation and exception operations emit AuditEvent records as defined in [event-model.md](event-model.md). An event reference uses object_type AuditEvent, object_id equal to event_id and revision equal to event_version. Events refer to exact record revisions, document hashes and business targets; an event is evidence of a recorded action, not replacement authorization.

## Association and cardinality requirements

- A DocumentArtifact has one or more DocumentVersions; each DocumentVersion belongs to exactly one DocumentArtifact. A task may have several source artifacts, but each ApprovedChangeSet has exactly one target version.
- A PerceptionSnapshot describes one DocumentVersion. SemanticObject.semantic_reference points to its containing snapshot. NativeBinding may associate one semantic object with several locators; every associated locator must belong to that snapshot's version.
- A TargetRegion connects one BusinessTargetID to a target version. Repeated target occurrences require explicit regions and locators, never implicit global replacement.
- A SourceAssessment evaluates one SourceRequirement. EvidenceAssessment aggregates checks for the same target; passing source sufficiency is necessary but not sufficient for VERIFIED.
- Each ChangeProposal concerns one target and one operation. Each approved operation has an explicit ReviewDecision and evidence. A set groups one or more compatible changes on the same binary.
- Conditions, protected scope and validation plan are mandatory authorization content. The authorization must cover all referenced objects and their exact revisions. Missing, revoked or cross-task references block admission.
- One ApprovedChangeSet may have several refused attempts, but at most one committed transformation of its approved input. Retry identity and double-application rules are in status-model.md.
- ExecutionResult and ValidationReport are independent resources. Successful execution produces a staged DocumentVersion; only a release gate can make it available as a released artifact.
- Task completion and whole-document release require all required business targets. A factual NCP edit does not verify an arm's-length conclusion.

## Versioning and authority checks

A request that changes an expected input version fails with STALE_DOCUMENT_VERSION. An unknown reference fails with REFERENCE_NOT_FOUND. A changed authorization digest fails with APPROVAL_CONTENT_MISMATCH. Reusing historical approval after evidence, policy, locator or approved payload changes is prohibited.

Caller-supplied status, reviewer identity, evidence verdict, source authority, qualification or audit hashes cannot establish authority. Services must authenticate actors and deterministically validate those claims. These are architecture obligations; no runtime validators, database models or business rules are supplied here.
