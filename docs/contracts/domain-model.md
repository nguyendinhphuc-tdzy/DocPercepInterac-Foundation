# Foundation v2 Domain Model

**Foundation architecture generation:** v2

**Contract schema version:** 0.1.0

**Date:** 2026-09-07

**Status:** Pre-freeze architecture contract; no runtime implementation.

The [current baseline](../CURRENT_BASELINE.md) and active [ADRs](../adr/README.md) govern this technology-neutral contract. Architecture generation v2 is distinct from schema version 0.1.0. The first stable contract freeze has not occurred.

## Reading and identity conventions

Lifecycle and enumeration definitions are in [status-model.md](status-model.md). The C2 [invariants](invariants.md), [error catalog](error-catalog.md), [event model](event-model.md) and [behavioral examples](examples/) use these definitions. The future OpenAPI must align with them and cannot weaken the invariants preserved below.

Each top-level record has the following required envelope unless explicitly excluded:

| Field | Type | Meaning |
| --- | --- | --- |
| schema_version | SchemaVersion | 0.1.0, version of this contract. |
| object_type | ObjectType | Exact top-level domain class name. |
| id | ID | Stable logical record identity. |
| revision | PositiveInt | Immutable snapshot revision. |
| created_at | Timestamp | UTC time this snapshot was recorded. |
| task_id | ID | Required for task-owned records; absent on FoundationTask and reusable policy definitions. |

All recorded revisions are immutable. Lifecycle transitions append an event and a new snapshot; they do not edit prior snapshots. Reads without a revision return the latest projection. A reference always pins a revision. New evidence or human override creates a new record/revision and event, preserving earlier machine/AI results. ApprovedChangeSet authorization content is sealed separately from its authorization validity state.

DocumentVersion has revision 1 forever; its id is the version_id used in DocumentVersionRef. ApprovedChange is sealed inline content with an approved_change_id unique inside its parent set; it has no global record envelope or generic reference type. ReplayRequest has exactly its two specified fields and no envelope. AuditEvent uses a dedicated event envelope whose details remain in the event-model workstream.

| Primitive | Constraint |
| --- | --- |
| ID | Nonempty opaque string matching `^[A-Za-z0-9][A-Za-z0-9._:-]*$`; never a native address. |
| BusinessTargetID | Logical business key matching `^[A-Z][A-Z0-9_.]*$`; stable across document versions. |
| SHA256 | Exactly 64 lowercase hexadecimal characters, SHA-256 of exact bytes. |
| Text / NullableText | Nonempty string / nonempty string or null. |
| ExactText | Exact string, including an intentionally empty string; never interpolated or evaluated. |
| DecimalString | Exact base-10 decimal string without exponent notation, NaN or Infinity; preserve precision. |
| IntegerString | Exact signed base-10 integer string without decimal point or exponent. |
| LocalDate | Valid calendar date in YYYY-MM-DD form. |
| CurrencyCode | Explicit three-letter uppercase currency code validated by the pinned business policy. |
| Timestamp | RFC 3339 UTC timestamp with Z suffix. |
| URI | Absolute artifact URI; does not authorize fetching arbitrary locations. |
| EvaluatorKey | Opaque deterministic implementation identifier using the ID character set. Resolved only through an approved versioned registry; never interpreted as executable code, script, module path, query or prompt. |
| PositiveInt / NonNegativeInt | Integer >= 1 / integer >= 0, within interoperable JSON integer range. |
| Bool | Boolean, never a string. |
| CellAddress | One uppercase native A1 address without sheet prefix, range, query or wildcard; native workbook limits apply. |
| RangeAddress | Explicit bounded rectangle, such as A1:D12, in one worksheet; no formulas, names, unions or open-ended ranges. |
| StructuredData | Data-only JSON conforming to the pinned declarative schema; no executable object semantics. |
| Ref<T> | Reference with object_type fixed to a top-level record type T. |
| Nullable<T> | T or null, subject to the field's conditional rules. |
| T[] / T[+] | Array of T, permitting empty / requiring at least one. No duplicate record references. |

NativeLocator addresses and semantic IDs are not interchangeable with BusinessTargetID. Confidence is not a verification or authorization field.

## Shared value and reference contracts

### Reference

Typed immutable top-level record reference. A reference never grants authority. ObjectType deliberately excludes inline ApprovedChange and internal ReplayRequest.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `object_type` | `ObjectType` | Yes | Expected domain object class. |
| `object_id` | `ID` | Yes | Record ID (event_id for AuditEvent). |
| `revision` | `PositiveInt` | Yes | Exact immutable revision (event_version for AuditEvent). |

### DocumentVersionRef

Binary-bound document identity. version_id resolves to DocumentVersion.id, whose document_id and binary_hash must match.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `document_id` | `ID` | Yes | DocumentArtifact.id. |
| `version_id` | `ID` | Yes | DocumentVersion.id, never a latest-version alias. |
| `binary_hash` | `SHA256` | Yes | Exact immutable binary SHA-256. |

### SemanticReference

Semantic identity in one perception snapshot, not a native execution address.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `snapshot_ref` | `Ref<PerceptionSnapshot>` | Yes | Exact perception snapshot. |
| `semantic_id` | `Text` | Yes | Engine representation ID such as #/texts/137. |

### ContentRef

Immutable artifact reference with SHA-256 and media type. The URI alone is never proof of content or authority.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `uri` | `URI` | Yes | Immutable artifact address; governed storage, not arbitrary retrieval authorization. |
| `sha256` | `SHA256` | Yes | SHA-256 of artifact bytes. |
| `media_type` | `Text` | Yes | Content media type. |

### EvaluatorBinding

Exact deterministic evaluator execution identity. This inline value is data, not executable content.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `evaluator_key` | `EvaluatorKey` | Yes | Registered deterministic implementation identifier. |
| `evaluator_version` | `Text` | Yes | Exact immutable implementation version used for this evaluation. |
| `configuration_ref` | `ContentRef` | Yes | Pinned declarative configuration and digest used by that implementation. |

The binding must resolve in the approved evaluator registry. It cannot contain or resolve caller-supplied source code, scripts, queries, expressions or prompts. Changing any binding field produces a new evaluation and can invalidate dependent authorization; historical evaluation records remain unchanged.

### Actor

Authenticated or attested actor; request bodies cannot impersonate actor authority.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `actor_type` | `ActorType` | Yes | Human, system, AI, replay engine or independent validator. |
| `actor_id` | `ID` | Yes | Stable identity within the chosen identity system. |

### BusinessValue

Closed tagged value union with an exact reviewable representation. Every BusinessValue formally contains the following common fields, serialized directly alongside the kind-specific fields. They are mandatory for every variant, not an optional presentation wrapper. Normalized typed values and the original review_text are preserved together; no silent rounding or normalization.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `kind` | `BusinessValueKind` | Yes | Discriminator selecting exactly one kind-specific shape below. |
| `review_text` | `ExactText` | Yes | Exact human-reviewable representation, including an intentionally empty text value. |

Each variant contains these two common fields plus only its declared kind-specific fields. A missing common field, unknown kind or incompatible field is a contract failure.

| kind | Additional required fields | Constraints |
| --- | --- | --- |
| TEXT | value: ExactText | Literal text, including an intentionally empty value. |
| DECIMAL | value: DecimalString | Exact decimal string; no binary floating-point conversion. |
| INTEGER | value: IntegerString | Exact integer string, including values beyond interoperable JSON integer range. |
| DATE | value: LocalDate | ISO calendar date YYYY-MM-DD; no implied timezone. |
| BOOLEAN | value: Bool | True/false value; review_text preserves the displayed representation. |
| CURRENCY | amount: DecimalString; currency_code: CurrencyCode | Explicit amount and currency; never infer currency from a symbol. |
| PERCENT | percentage: DecimalString | 6.08 represents 6.08%, not the fractional ratio 0.0608; review_text may be 6.08%. |
| STRUCTURED | schema_ref: ContentRef; value: StructuredData | Pinned, allowlisted declarative data schema; preserve the complete reviewable structure. |

StructuredData permits JSON data only: strings, finite JSON numbers, booleans, null, arrays and plain string-keyed objects validated against schema_ref. Exact decimal quantities use decimal strings. It cannot contain executable object instances, code handles, deserialization hooks or instructions to evaluate scripts, expressions or templates. Strings remain untrusted data, never executable authority. Unregistered value kinds or schemas fail closed.

### CapabilityResult

Operation-specific capability observation. The complete tuple is operation + native structure + exact document version + engine + engine version + conformance + qualification evidence. No single target-level capability flag substitutes for it. SUPPORTED requires qualified evidence and Transitional OOXML; a recognized address does not prove mutation support.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `capability_result_id` | `ID` | Yes | Identifier unique within one DocumentPreflightAssessment revision; not a global record ID. |
| `operation` | `MutationOperation` | Yes | Specific proposed native operation. |
| `native_structure` | `LocatorType` | Yes | Concrete native structure/address class assessed. |
| `document_version_ref` | `DocumentVersionRef` | Yes | Exact native input context; must match the containing preflight assessment. |
| `native_locator_refs` | `Ref<NativeLocator>[]` | Yes | Exact native objects covered by this entry; nonempty for SUPPORTED. All must match the assessed version and native_structure. |
| `engine` | `Text` | Yes | Engine identity. |
| `engine_version` | `Text` | Yes | Exact assessed engine version. |
| `conformance` | `ConformanceClass` | Yes | Detected conformance class. |
| `qualification_evidence_refs` | `ContentRef[]` | Yes | Pinned operation/profile-specific qualification evidence; nonempty for SUPPORTED. |
| `status` | `CapabilityStatus` | Yes | SUPPORTED, PROTECTED, UNSUPPORTED or UNKNOWN. |
| `reason` | `Text` | Yes | Scope, restrictions and detected limitations. |

CapabilityResult is immutable inline content owned by a DocumentPreflightAssessment revision. It does not live on DocumentVersion and is not a standalone ObjectType. Its qualified scope is explicit: an entry for one native object or structure cannot establish support for all objects in the document.

### CapabilityResultRef

Pinned identity of one operation-specific capability result inside its preflight assessment.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `preflight_assessment_ref` | `Ref<DocumentPreflightAssessment>` | Yes | Exact immutable assessment revision. |
| `capability_result_id` | `ID` | Yes | Resolves to exactly one inline CapabilityResult in that assessment revision. |

An eligibility check resolves the complete tuple and qualification evidence, checks the exact native scope and current supersession/qualification validity, and refuses incomplete or incompatible entries. The reference cannot grant mutation authority.

### PreflightFinding

One preserved protection or native-structure observation. Its category is determined by the containing protection_findings or native_structure_findings collection; it is not a target-level capability verdict.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `finding_id` | `ID` | Yes | Unique within the containing preflight assessment revision. |
| `native_object_type` | `Text` | Yes | Observed construct or document-level protection; descriptive data, not an execution address. |
| `part_uri` | `NullableText` | Yes | Exact package part when known; null for a document-wide finding or an unlocatable construct. |
| `native_locator_refs` | `Ref<NativeLocator>[]` | Yes | Exact captured objects when available; may be empty if the structure cannot be safely located. |
| `observation_ref` | `ContentRef` | Yes | Immutable inspection evidence and digest. |
| `description` | `Text` | Yes | Reviewable observation and limits. |

An unlocatable protection/structure finding cannot be silently ignored. Any affected operation whose preservation or support cannot be established remains blocked. This helper is inline assessment content, not a reusable policy definition or independently addressable record.

### NativeAddress

Closed tagged union. All address variants have kind: LocatorType and only their declared fields. NativeLocator.part_uri scopes the package part. Paths and ordinals are valid only within its immutable DocumentVersion.

| kind | Required address fields | Exact identity and limits |
| --- | --- | --- |
| DOCX_CONTENT_CONTROL | sdt_id: Text; element_path: NativeElementPath | Exact content-control element and w:sdtPr/w:id; both must agree. |
| DOCX_BOOKMARK | bookmark_id: Text; bookmark_name: Text; start_path: NativeElementPath; end_path: NativeElementPath | Exact paired bookmark markers in the scoped part; malformed pairs are unsupported. |
| DOCX_PARAGRAPH | paragraph_path: NativeElementPath | Exact w:p element in body, table or other qualified part. |
| DOCX_RUN | run_path: NativeElementPath | Exact w:r element; the qualified operation must validate its text/content structure. |
| DOCX_TABLE_CELL | table_path: NativeElementPath; row_ordinal: PositiveInt; cell_ordinal: PositiveInt; cell_path: NativeElementPath | Exact native w:tr/w:tc child positions and cell path must agree; merged/complex cells are not automatically supported. |
| DOCX_RELATIONSHIP | relationship_id: Text; owner_part_uri: Text | Exact relationship entry in NativeLocator.part_uri, which is the relationships part; no target-URI approximation. |
| XLSX_CELL | sheet_id: Text; cell_address: CellAddress | Exact worksheet part and single native A1 cell. |
| XLSX_DEFINED_NAME | name: Text; scope: DefinedNameScope; scope_sheet_id: Text only for WORKSHEET | Exact workbook or worksheet-scoped name definition; its formula is data, not locator fallback. |
| XLSX_TABLE_RANGE | range_kind: XlsxRangeKind; sheet_id: Text; range_address: RangeAddress; table_id: Text and table_part_uri: Text only for TABLE | Exact bounded native range; TABLE additionally binds the specific table definition. |

The addressed native structure must match expected_object_type and structural_fingerprint. Names, IDs, paths, part URIs and ordinals are conjunctive exact constraints. There is no PART_PATH free-form query variant, nearest-match search, fuzzy address or fingerprint search fallback.

### Condition

Closed discriminated union of deterministic pre/postconditions. Every instance contains condition_id and kind plus exactly the fields declared for that kind. There is no generic scope_ref/expected pair, extension bag or executable condition body.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `condition_id` | `ID` | Yes | Unique within the containing authorization, including its inline changes. |
| `kind` | `ConditionKind` | Yes | Selects exactly one typed condition shape below. |

#### BINARY_HASH_EQUALS

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `document_version_ref` | `DocumentVersionRef` | Yes | Exact registered binary being checked. |
| `expected_binary_hash` | `SHA256` | Yes | Must equal the hash pinned in document_version_ref; compare with the actual bytes. |

Mismatch produces STALE_DOCUMENT_VERSION and execution refusal. This shape cannot predict an unknown future output hash; post-execution checks use the separately registered output identity and independent validation.

#### TEXT_EQUALS

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `target` | `ConditionValueTarget` | Yes | Exact input native object or the approved output change being validated. |
| `expected_text` | `ExactText` | Yes | Literal expected text; no interpolation, normalization or fuzzy comparison. |

#### VALUE_EQUALS

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `target` | `ConditionValueTarget` | Yes | Exact input native object or approved output change being validated. |
| `expected_value` | `BusinessValue` | Yes | Complete typed expected value, including kind, review_text and kind-specific fields. |
| `value_reader_policy_ref` | `ContentRef` | Yes | Pinned deterministic observation/extraction profile, not an executable expression. |

Compare the complete typed value under the declared representation. No implicit type/unit conversion, rounding or tolerance is introduced by this condition. Unsupported extraction blocks the check.

#### CAPABILITY_SUPPORTED

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `native_locator_ref` | `Ref<NativeLocator>` | Yes | Exact input object that the approved operation will address. |
| `capability_result_ref` | `CapabilityResultRef` | Yes | Pinned operation-specific assessment entry covering this locator. |
| `operation` | `MutationOperation` | Yes | Exact approved operation. |
| `engine` | `Text` | Yes | Exact approved replay-engine identity. |
| `engine_version` | `Text` | Yes | Exact qualified replay-engine version. |
| `conformance` | `ConformanceClass` | Yes | Must be TRANSITIONAL for the current mutation profile. |

The referenced assessment must be COMPLETED and still applicable; the entry must be SUPPORTED, cover the exact locator/version/native structure, match this complete operation/engine/version/conformance tuple, and retain valid qualification evidence. This kind cannot ask for a different expected status to weaken the gate.

#### EVIDENCE_VERIFIED

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `evidence_assessment_ref` | `Ref<EvidenceAssessment>` | Yes | Exact deterministic evidence assessment. |
| `business_target_id` | `BusinessTargetID` | Yes | Must match the assessment and approved target. |

Requires VERIFIED with all referenced source/evidence gates still applicable, including freshness under the pinned policy. A historical VERIFIED label or AI statement cannot satisfy this condition after its inputs have expired or been superseded.

#### PRESERVE_SCOPE

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `protected_scope` | `ProtectedScope` | Yes | Exact protected scope from the containing authorization, including its input version and any qualified serialization allowance. |

The scope must equal authorization.protected_scope; a condition cannot supply a weaker replacement. Preflight checks operation ownership against this scope. Independent post-execution validation checks the output against the preserved input and approved changes. The output version comes from the identified ExecutionResult, not a caller override.

All six variants are closed. Arbitrary expressions, queries, scripts, prompts, generic executable payloads, extra fields and unknown variants are forbidden. A new condition kind requires an explicit versioned typed shape and qualified deterministic evaluation. Unknown or unevaluable conditions fail closed.

### ConditionValueTarget

Closed validation-subject union. Every variant contains kind and only its listed fields.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `kind` | `ConditionValueTargetKind` | Yes | INPUT_NATIVE_OBJECT or OUTPUT_APPROVED_CHANGE. |

#### INPUT_NATIVE_OBJECT

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `native_locator_ref` | `Ref<NativeLocator>` | Yes | Exact uniquely resolving address in the pinned input binary. |

#### OUTPUT_APPROVED_CHANGE

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `approved_change_id` | `ID` | Yes | Inline change in the containing ApprovedChangeSet, resolved with that set and its identified execution. |

OUTPUT_APPROVED_CHANGE is a validation subject, not a native execution address or a global ApprovedChange reference. Independent validation must associate the observed output object with that inline change using qualified evidence and a newly captured output-version NativeLocator. It must not execute or resolve an input locator against a different output hash. If the association cannot be established exactly, validation fails closed; no fuzzy fallback.

Text/value postconditions on a mutation result MUST use OUTPUT_APPROVED_CHANGE, not merely re-read the unchanged input. This permits approval of exact postconditions before the output binary exists without inventing an output hash or weakening NativeLocator version scope.

### FreshnessEvaluation

Immutable task-context result of applying one pinned reusable FreshnessPolicy. It is inline assessment/check content, not a reusable definition.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `freshness_policy_ref` | `Ref<FreshnessPolicy>` | Yes | Exact policy revision applied. |
| `document_version_refs` | `DocumentVersionRef[]` | Yes | Sources evaluated; empty only for a blocked evaluation with missing source input. |
| `as_of` | `Timestamp` | Yes | Trusted time/context at which freshness was evaluated; preserved for reproducibility. |
| `input_refs` | `ContentRef[+]` | Yes | Immutable timing, version, publication, supersession or revocation observations required by policy. |
| `evaluator_key` | `EvaluatorKey` | Yes | Must match the pinned policy's deterministic evaluator identifier. |
| `evaluator_version` | `Text` | Yes | Exact registered evaluator implementation version used. |
| `outcome` | `CheckOutcome` | Yes | PASS, FAIL or BLOCKED; NOT_APPLICABLE cannot satisfy this gate. |
| `valid_until` | `Nullable<Timestamp>` | Yes | Expiry derived from the pinned policy if determinable; null never means indefinitely fresh. |
| `reason` | `Text` | Yes | Reviewable policy result and limitations. |
| `error_codes` | `ErrorCode[]` | Yes | Recorded evaluation failures or unavailable inputs. |

No duration, age limit, renewal window or other business threshold is defined here. Policy/configuration changes and new source validity observations require new assessment/check records. A prior PASS is not a perpetual freshness guarantee; governance rechecks applicability at approval and execution. An explicit policy with no age-based restriction must still be evaluated and recorded, not inferred from PERIOD_INDEPENDENT.

### ProtectedScope

Required preservation scope. Everything outside approved changes is preserved. An explicit serialization allowance must itself be qualified and approved.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `document_version_ref` | `DocumentVersionRef` | Yes | Protected input version. |
| `protected_locator_refs` | `Ref<NativeLocator>[]` | Yes | Explicit protected native objects. |
| `preserve_outside_approved_changes` | `Bool` | Yes | MUST be true. |
| `serialization_allowance_ref` | `ContentRef` | No | Pinned narrowly qualified allowance; absent means none. |

### ValidationRequirement

One validation obligation in a pinned plan; no engine-chosen optional downgrade.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `requirement_id` | `ID` | Yes | Unique in the ValidationPlan. |
| `kind` | `ValidationCheckKind` | Yes | Independent check class. |
| `mandatory` | `Bool` | Yes | True for required release checks. |
| `business_target_ids` | `BusinessTargetID[]` | Yes | Empty for whole-package preservation checks. |
| `description` | `Text` | Yes | What must be observed and preserved. |

### AuthorizationBinding

Sealed content covered by authorization_digest. No lifecycle change may alter these fields.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `target_document_version_ref` | `DocumentVersionRef` | Yes | Exact target version and binary hash. |
| `source_document_version_refs` | `DocumentVersionRef[+]` | Yes | Pinned source binaries. |
| `target_contract_definition_ref` | `Ref<TargetContractDefinition>` | Yes | Pinned reusable contract definition revision. |
| `target_contract_instance_ref` | `Ref<TargetContractInstance>` | Yes | Pinned task/document-specific contract instance revision. |
| `rule_pack_ref` | `Ref<RulePack>` | Yes | Exact RulePack version. |
| `source_assessment_refs` | `Ref<SourceAssessment>[+]` | Yes | All required assessments: lifecycle COMPLETED with outcome SUFFICIENT. |
| `evidence_assessment_refs` | `Ref<EvidenceAssessment>[+]` | Yes | All required VERIFIED evidence assessments. |
| `review_decision_refs` | `Ref<ReviewDecision>[+]` | Yes | Explicit human approvals. |
| `approved_changes` | `ApprovedChange[+]` | Yes | Sealed inline typed changes, each uniquely identified by approved_change_id within this set. |
| `preconditions` | `Condition[+]` | Yes | Set-wide deterministic preflight checks. |
| `postconditions` | `Condition[+]` | Yes | Set-wide deterministic result checks. |
| `protected_scope` | `ProtectedScope` | Yes | Preservation outside approved scope. |
| `validation_plan_ref` | `Ref<ValidationPlan>` | Yes | Pinned independent validation obligations. |
| `mutation_profile` | `ConformanceClass` | Yes | MUST be TRANSITIONAL in v2. |
| `qualification_refs` | `ContentRef[+]` | Yes | Evidence qualifying every operation/profile/engine combination. |

### Period

Explicit business period independent of storage identity; no implicit fiscal calendar conversion.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `label` | `Text` | Yes | Reviewable period label. |
| `start_date` | `LocalDate` | Yes | Inclusive start date. |
| `end_date` | `LocalDate` | Yes | Inclusive end date; not earlier than start. |

### MutationPayload

Closed discriminated union for current operations. Every variant has kind and exact replacement_text; kind selects a specific typed contract, not an arbitrary operation body.

| kind (MutationPayloadType) | Compatible operation | Required payload fields |
| --- | --- | --- |
| RUN_TEXT_REPLACEMENT | REPLACE_RUN_TEXT | kind; replacement_text: ExactText |
| SDT_TEXT_REPLACEMENT | REPLACE_SDT_TEXT | kind; replacement_text: ExactText |
| SIMPLE_TABLE_CELL_TEXT_REPLACEMENT | REPLACE_SIMPLE_TABLE_CELL_TEXT | kind; replacement_text: ExactText |

The enclosing operation and payload kind MUST agree. replacement_text is already the final approved string; replay never interpolates prompts, expressions or templates. Replacement preserves all structure outside the qualified operation profile. Future operations add explicitly versioned typed union members, compatible address shapes and qualification evidence. There is no arbitrary-object fallback or generic patch member; unknown variants are refused.

### NativePathStep

One exact native XML child-element step; no query language or fuzzy predicate.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `namespace_uri` | `URI` | Yes | Expanded XML namespace URI. |
| `local_name` | `Text` | Yes | Exact element local name. |
| `ordinal` | `PositiveInt` | Yes | One-based ordinal among direct child elements having this expanded name. |

### NativeElementPath

Nonempty ordered array of NativePathStep from the package part's document element to the addressed element, including the root as step 1 with ordinal 1. Each step is exact; missing or mismatched structure refuses execution.

### DocumentRole

DocumentRole is a closed enum, not a separate mutable document identity. DocumentArtifact.role assigns a document to one task. The same bytes can have different roles in different task registrations. CURRENT_SOURCE still requires policy-based authority and sufficiency; HISTORICAL_SOURCE and TEMPLATE do not automatically satisfy current-period requirements. EVALUATION_ONLY cannot authorize production changes.

## A. Task and Document

### FoundationTask

One governed business workflow; aggregate progress never grants mutation authority.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `title` | `Text` | Yes | Human-readable task name. |
| `business_case` | `Text` | Yes | Use-case identifier; not executable policy. |
| `current_period` | `Period` | Yes | Explicit assessed period, e.g. FY2025. |
| `status` | `TaskStatus` | Yes | Governed lifecycle projection. |
| `document_refs` | `Ref<DocumentArtifact>[]` | Yes | Registered task documents; may be empty while CREATED. |
| `target_contract_definition_ref` | `Ref<TargetContractDefinition>` | No | Pinned reusable contract definition revision. |
| `target_contract_instance_ref` | `Ref<TargetContractInstance>` | No | Pinned task/document-specific contract instance revision. |
| `rule_pack_ref` | `Ref<RulePack>` | No | Pinned RulePack revision. |
| `required_business_target_ids` | `BusinessTargetID[]` | Yes | May be empty while CREATED; before ANALYZING, populate a nonempty required target set from the pinned definition. |
| `exception_refs` | `Ref<ExceptionRecord>[]` | Yes | Open and resolved exception records. |
| `release_status` | `ReleaseStatus` | Yes | Whole-task output release state. |
| `prior_period` | `Period` | No | Explicit prior-period context when a selected requirement uses PRIOR_PERIOD. |

CREATED may exist before documents, the TargetContractDefinition, TargetContractInstance or RulePack are pinned. Before ANALYZING, pin the definition, a registered instance for the exact target DocumentVersion and the RulePack; the instance may still await perception and native binding. Before review/authorization, every selected target must have complete task-specific binding and passing gates. COMPLETED requires every required target to pass evidence, validation and release gates.

### DocumentArtifact

Logical document registered in one task; source role is not evidence sufficiency.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `file_name` | `Text` | Yes | Display filename, never native identity. |
| `role` | `DocumentRole` | Yes | Role in this task. |
| `status` | `DocumentStatus` | Yes | Document lifecycle, separate from immutable binary versions. |
| `version_refs` | `DocumentVersionRef[+]` | Yes | Known immutable versions. |
| `current_version_ref` | `DocumentVersionRef` | Yes | Current selected version; changing it triggers stale-binding checks. |

A role or current-version change is a new artifact revision and audit event. Binary reuse across tasks does not confer source authority.

### DocumentVersion

Exactly one immutable binary, identified by its SHA-256 binary_hash and scoped under a DocumentArtifact.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `document_id` | `ID` | Yes | Owning DocumentArtifact ID. |
| `binary_hash` | `SHA256` | Yes | Lowercase SHA-256 of exact binary bytes; no prefix. |
| `byte_length` | `NonNegativeInt` | Yes | Length of the exact binary. |
| `content_ref` | `ContentRef` | Yes | Immutable binary storage reference; sha256 MUST equal binary_hash. |
| `derived_from` | `DocumentVersionRef` | No | Input version for generated output. |

Its envelope revision is always 1. It records immutable binary identity, storage and derivation only. Detected format/conformance, protection/native-structure findings and operation/engine capability observations belong to DocumentPreflightAssessment. New observations or engine qualifications do not create a new binary identity or rewrite this record.

### DocumentPreflightAssessment

Top-level task-owned preflight assessment of exactly one immutable DocumentVersion. It records observations and operation-specific capability evidence separately from binary identity.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `document_version_ref` | `DocumentVersionRef` | Yes | Exact assessed document/version/SHA-256 identity. |
| `status` | `DocumentPreflightStatus` | Yes | Assessment lifecycle only; COMPLETED does not mean all operations are supported. |
| `detected_format` | `Nullable<DocumentFormat>` | Yes | Observed recognized format; null when detection is pending, unknown or outside the vocabulary. |
| `detected_conformance` | `ConformanceClass` | Yes | Observed class; UNKNOWN when unresolved, NOT_APPLICABLE only when established. |
| `format_observation_refs` | `ContentRef[]` | Yes | Preserved format/conformance observations; nonempty for COMPLETED, including unsupported/unknown findings. |
| `protection_findings` | `PreflightFinding[]` | Yes | Document/native-object protections with evidence and exact scope where available. |
| `native_structure_findings` | `PreflightFinding[]` | Yes | Native structures encountered, including unsupported or unlocatable constructs. |
| `capability_results` | `CapabilityResult[]` | Yes | Inline operation/native-structure/engine/version/conformance/qualification entries. |
| `assessor` | `Actor` | Yes | Authenticated deterministic assessment service; actor_type SYSTEM. |
| `engine` | `Text` | Yes | Inspection/assessment engine identity, distinct from the replay engine assessed in each capability entry. |
| `engine_version` | `Text` | Yes | Exact inspection/assessment engine version. |
| `configuration_ref` | `ContentRef` | Yes | Pinned deterministic inspection configuration and coverage requirements. |
| `assessed_at` | `Nullable<Timestamp>` | Yes | Completion time; required non-null at COMPLETED and preserved on supersession. |
| `error_codes` | `ErrorCode[]` | Yes | Detection, protection, native-structure or qualification diagnostics. |
| `supersedes_assessment_ref` | `Ref<DocumentPreflightAssessment>` | No | Explicit prior assessment replaced by this new assessment; historical observations remain intact. |

All findings and capability entries belong to the pinned binary; every captured locator must match it. Each capability_result_id is unique within this assessment revision. Empty findings are meaningful only with coverage evidence showing no applicable findings; incomplete coverage cannot establish support.

A completed assessment may explicitly contain PROTECTED, UNSUPPORTED or UNKNOWN capabilities. FAILED represents technical inability to complete the assessment. New inspection engines, configurations, qualification evidence or corrected observations produce new assessments and explicit supersession where applicable, never evolving fields on DocumentVersion. Unrelated assessments for other engine/operation profiles do not automatically supersede each other. Affected approval is invalidated when changed evidence undermines its pinned capability assumptions.

## B. Perception and Native Identity

### PerceptionSnapshot

Immutable semantic perception run output for exactly one document version.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `document_version_ref` | `DocumentVersionRef` | Yes | Exact perceived binary. |
| `analysis_run_ref` | `Ref<AnalysisRun>` | Yes | Run that produced the snapshot. |
| `engine` | `Text` | Yes | Perception engine name, provisionally Docling-slim. |
| `engine_version` | `Text` | Yes | Exact engine version used. |
| `configuration_ref` | `ContentRef` | Yes | Pinned configuration and digest. |
| `semantic_object_refs` | `Ref<SemanticObject>[]` | Yes | Objects belonging to this snapshot. |
| `limitations` | `Text[]` | Yes | Detected omissions and unsupported constructs. |

### SemanticObject

Object in a semantic snapshot; never a native execution address.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `semantic_reference` | `SemanticReference` | Yes | Snapshot identity plus engine-local semantic ID. |
| `object_kind` | `Text` | Yes | Perception type such as paragraph or table cell; not capability authority. |
| `value` | `BusinessValue` | Yes | Perceived value. |
| `parent_ref` | `Ref<SemanticObject>` | No | Optional semantic parent in the same snapshot. |
| `native_binding_refs` | `Ref<NativeBinding>[]` | Yes | Associations to native objects. |

### NativeLocator

Exact version-scoped native execution address for one native object.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `document_version_ref` | `DocumentVersionRef` | Yes | Exactly one immutable DocumentVersion, including its SHA-256. |
| `part_uri` | `Text` | Yes | Exact package part URI. |
| `locator_type` | `LocatorType` | Yes | Qualified deterministic address kind. |
| `address` | `NativeAddress` | Yes | Typed address matching locator_type. |
| `expected_object_type` | `Text` | Yes | Native structure expected at resolution. |
| `capture_engine` | `Text` | Yes | Native reader/engine identity and version used to capture this locator. |
| `structural_fingerprint` | `SHA256` | Yes | Exact digest of the captured native structure under the pinned fingerprint profile. |
| `fingerprint_profile_ref` | `ContentRef` | Yes | Versioned deterministic structural fingerprint rules and digest. |

The locator, binary binding and structural fingerprint are immutable. Resolve its exact typed address first, require exactly one native object, then verify structural_fingerprint using the pinned profile. A mismatch fails closed with PRECONDITION_FAILED. Never search by fingerprint, nearest text, similarity or fuzzy matching. More address variants do not expand the qualified mutation vocabulary.

### NativeBinding

Semantic-to-native association, separate from the exact native address.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `semantic_object_ref` | `Ref<SemanticObject>` | Yes | Semantic side of the association. |
| `native_locator_refs` | `Ref<NativeLocator>[]` | Yes | Native candidates or resolved objects. |
| `status` | `BindingStatus` | Yes | Association result; no execution authority. |
| `method` | `Text` | Yes | Deterministic capture or discovery method. |
| `reason` | `Text` | Yes | Explain association and ambiguity without claiming authorization. |

RESOLVED requires explicit proven associations to the same document version. A semantic object may span several native objects; each ApprovedChange still selects exactly one uniquely resolving NativeLocator.

## C. Business Governance

### TargetContractDefinition

Reusable versioned business contract definition; contains no task/document-specific bindings.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `name` | `Text` | Yes | Reusable contract name. |
| `business_target_ids` | `BusinessTargetID[+]` | Yes | Logical business targets. |
| `target_region_definition_refs` | `Ref<TargetRegionDefinition>[+]` | Yes | Reusable region declarations. |
| `source_requirement_refs` | `Ref<SourceRequirement>[]` | Yes | Reusable source policies. |
| `validation_plan_ref` | `Ref<ValidationPlan>` | Yes | Reusable validation requirements without task-owned object references. |
| `protection_policy_ref` | `ContentRef` | Yes | Reusable preservation policy, never a captured ProtectedScope. |

No direct or transitive reference to a task-owned DocumentVersion, SemanticObject, NativeBinding, NativeLocator, TargetRegion, TargetContractInstance or ProtectedScope instance is permitted. ContentRef must not disguise such a reference. Its revision is the reusable TargetContract definition version.

### TargetRegionDefinition

Reusable definition of a business target region without a concrete document address.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `business_target_id` | `BusinessTargetID` | Yes | Stable logical business identity. |
| `description` | `Text` | Yes | Business meaning and expected occurrence policy. |
| `allowed_value_kinds` | `BusinessValueKind[+]` | Yes | Accepted typed business value kinds. |
| `value_schema_ref` | `ContentRef` | Yes | Pinned declarative value constraints. |
| `permitted_operations` | `MutationOperation[]` | Yes | Candidate operation vocabulary; permission does not prove qualification. |
| `source_requirement_refs` | `Ref<SourceRequirement>[]` | Yes | Reusable required source definitions. |
| `protection_policy_ref` | `ContentRef` | Yes | Reusable preservation requirements. |

Definitions describe meaning and policy only. They never hold DocumentVersionRef, semantic/native object references, task-owned scopes, or captured locators.

### TargetContractInstance

Task/document-specific binding of one reusable contract definition.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `definition_ref` | `Ref<TargetContractDefinition>` | Yes | Exact reusable definition version. |
| `target_document_version_ref` | `DocumentVersionRef` | Yes | Exactly one task-owned target version and hash. |
| `target_region_refs` | `Ref<TargetRegion>[]` | Yes | Bound occurrences; empty at registration, completed by analysis. |
| `protected_scope` | `ProtectedScope` | Yes | Concrete preservation scope for this exact document version. |
| `validation_plan_ref` | `Ref<ValidationPlan>` | Yes | Pinned reusable plan applied to this instance. |

An instance can be registered before perception without claiming resolved targets. Analysis creates new instance revisions with explicit region bindings. Proposal, review and authorization pin the completed instance revision. Rebinding after a binary or definition change requires a new instance/revision and renewed affected approval.

### TargetRegion

Business target occurrence mapped to a concrete target document version.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `region_definition_ref` | `Ref<TargetRegionDefinition>` | Yes | Exact reusable region definition. |
| `target_contract_instance_ref` | `Ref<TargetContractInstance>` | Yes | Owning task/document instance. |
| `business_target_id` | `BusinessTargetID` | Yes | Business identity, distinct from semantic/native identity. |
| `document_version_ref` | `DocumentVersionRef` | Yes | Target binary. |
| `semantic_object_refs` | `Ref<SemanticObject>[]` | Yes | Semantic context. |
| `native_binding_refs` | `Ref<NativeBinding>[]` | Yes | Native associations. |
| `verification_status` | `TargetVerificationStatus` | Yes | Deterministic evidence state. |
| `source_requirement_refs` | `Ref<SourceRequirement>[]` | Yes | Requirements relevant to this target. |
| `preflight_assessment_refs` | `Ref<DocumentPreflightAssessment>[]` | Yes | Pinned relevant assessments for this region's exact document version. |
| `capability_result_refs` | `CapabilityResultRef[]` | Yes | Selected operation-specific entries from those assessment revisions; no copied or flattened region capability verdict. |

AI output cannot independently set verification_status to VERIFIED. Verification is not approval. Every occurrence and referenced assessment must match its instance's target version. Each capability reference must cover the exact contemplated native locator and belong to preflight_assessment_refs. Support for one operation/structure/engine combination says nothing about another.

### RulePack

Versioned collection of deterministic policy declarations where business policy is known.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `name` | `Text` | Yes | Rule Pack name. |
| `business_rule_refs` | `Ref<BusinessRule>[+]` | Yes | Pinned rule declarations. |
| `policy_document_ref` | `ContentRef` | Yes | Authoritative policy definition and digest. |

No executable business rules or production thresholds are defined by the illustrative fixtures.

### BusinessRule

Referenceable rule declaration, not executable code.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `rule_type` | `RuleType` | Yes | Explicit Local File rule taxonomy; required for every BusinessRule. |
| `evaluator_key` | `EvaluatorKey` | Yes | Registered deterministic implementation identifier, not executable code or a script. |
| `business_target_ids` | `BusinessTargetID[+]` | Yes | Applicable business targets. |
| `source_requirement_refs` | `Ref<SourceRequirement>[]` | Yes | Required sources. |
| `policy_ref` | `ContentRef` | Yes | Versioned policy definition. |
| `description` | `Text` | Yes | Plain-language purpose and input/output obligations. |

Known policy is evaluated deterministically. evaluator_key is resolved only through the approved registry and pinned policy/configuration binding; it is never dynamically executed as source text, a module path, query or prompt. Unknown policy or an unregistered/incompatible evaluator produces a blocking exception, not invented behavior.

| RuleType | Contract meaning |
| --- | --- |
| ALWAYS_UPDATE | Require a governed current-task update assessment under the pinned policy; the name does not bypass evidence, review or authorization. |
| UPDATE_IF_CHANGED | Propose an update when the registered deterministic comparison establishes a relevant change. |
| DERIVED_UPDATE | Propose a value derived by the registered deterministic evaluator from required authoritative inputs. |
| CARRY_FORWARD | Preserve prior content only when the pinned policy and evidence permit carrying it forward; historical presence alone is insufficient. |
| TEMPLATE_CONTROLLED | Govern the target according to the pinned template/contract policy, without granting the template independent mutation authority. |
| PROTECTED | Preserve the governed target; do not authorize native mutation that violates its protected scope. |

RuleType classifies business policy, not native operations or authorization states. Every type retains source/evidence gates, human review where applicable, exact native identity, controlled replay and independent validation. This taxonomy defines contracts only; no business evaluator or current threshold is implemented.

### RuleEvaluation

Deterministic evaluation record preserving inputs and outcome.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `business_rule_ref` | `Ref<BusinessRule>` | Yes | Exact evaluated rule revision. |
| `business_target_id` | `BusinessTargetID` | Yes | Evaluated target. |
| `evaluator_binding` | `EvaluatorBinding` | Yes | Exact deterministic implementation/version/configuration used; evaluator_key must match the BusinessRule declaration. |
| `input_refs` | `Reference[]` | Yes | Pinned inputs. |
| `outcome` | `CheckOutcome` | Yes | Recorded deterministic outcome. |
| `proposed_value` | `BusinessValue` | No | Value proposed by a successful evaluation. |
| `error_codes` | `ErrorCode[]` | Yes | Catalog codes explaining a block or failure. |

## D. Source, Evidence and Mapping

### FreshnessPolicy

Reusable versioned deterministic source-freshness policy definition. It is separate from PeriodPolicy and contains no task-owned document, timestamp observation or assessment reference.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `name` | `Text` | Yes | Reusable freshness policy name. |
| `evaluator_key` | `EvaluatorKey` | Yes | Registered deterministic freshness evaluator identifier, never executable policy text. |
| `policy_ref` | `ContentRef` | Yes | Authoritative policy definition and digest, including the governing freshness criteria. |
| `configuration_ref` | `ContentRef` | Yes | Pinned approved declarative configuration/schema and any policy-authorized parameters. |
| `required_input_keys` | `Text[+]` | Yes | Named timing/version/validity observations required for deterministic evaluation; task values are supplied by assessment, not stored here. |
| `description` | `Text` | Yes | Reviewable policy purpose and applicability, without implicit defaults. |

The record revision is the FreshnessPolicy version. Evaluator binding and configuration must be reproducible. Configuration is declarative data, never a script, query, prompt or arbitrary expression. Approved business policy may later supply age/version/validity parameters; this contract sets no current threshold or default.

PeriodPolicy answers which business period evidence must concern. FreshnessPolicy answers whether that evidence remains current and usable at the trusted evaluation context, considering the policy's required timing/version/validity facts. PERIOD_INDEPENDENT never means freshness-independent. Missing policy, configuration, evaluator registration or required observations fails closed rather than treating evidence as fresh.

### SourceRequirement

Policy-level source requirements for a target and period.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `business_target_id` | `BusinessTargetID` | Yes | Target whose evidence is required. |
| `period_policy` | `PeriodPolicy` | Yes | Reusable business-period requirement; resolved in task context. |
| `freshness_policy_ref` | `Ref<FreshnessPolicy>` | Yes | Independently pinned deterministic freshness policy revision; required even for PERIOD_INDEPENDENT. |
| `specific_period` | `Period` | No | Required only for SPECIFIC_PERIOD; forbidden for the other policies. |
| `required_fields` | `Text[+]` | Yes | Business information required; no invented values. |
| `permitted_roles` | `DocumentRole[+]` | Yes | Roles allowed by the pinned policy. |
| `required_authority` | `SourceAuthority` | Yes | Minimum authority classification. |
| `blocking` | `Bool` | Yes | Whether unsatisfied requirements block the target. |
| `policy_ref` | `ContentRef` | Yes | Authority for these requirements. |

Reusable and task-independent. CURRENT_PERIOD resolves to FoundationTask.current_period; PRIOR_PERIOD resolves to its explicit prior_period; SPECIFIC_PERIOD uses this definition's specific_period; PERIOD_INDEPENDENT has no resolved source period. No assumed calendar subtraction. Missing period context blocks assessment and cannot be guessed. Resolving that period does not establish freshness: the separate freshness_policy_ref must also be evaluated on current task/source observations.

### SourceAssessment

Deterministic sufficiency assessment; human acceptance cannot manufacture missing evidence.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `source_requirement_ref` | `Ref<SourceRequirement>` | Yes | Requirement evaluated. |
| `business_target_id` | `BusinessTargetID` | Yes | Assessed target. |
| `document_version_refs` | `DocumentVersionRef[]` | Yes | Sources examined; empty is explicit when missing. |
| `outcome` | `Nullable<SourceSufficiencyOutcome>` | Yes | Always present. Non-null at COMPLETED and retained when a completed assessment is SUPERSEDED; null for pending/in-progress/technical failure. |
| `resolved_task_period` | `Period` | Yes | Current task period used as assessment context. |
| `resolved_source_period` | `Nullable<Period>` | Yes | Period resolved from the requirement; null only for PERIOD_INDEPENDENT on a completed assessment. |
| `freshness_policy_ref` | `Ref<FreshnessPolicy>` | Yes | Exact policy revision from source_requirement_ref; independent of resolved period. |
| `freshness_evaluation` | `Nullable<FreshnessEvaluation>` | Yes | Recorded deterministic freshness result; non-null with outcome PASS is required for COMPLETED/SUFFICIENT. |
| `evaluator_binding` | `EvaluatorBinding` | Yes | Exact deterministic sufficiency evaluator implementation/version/configuration used. This is separate from the nested freshness evaluator identity. |
| `status` | `SourceAssessmentStatus` | Yes | Lifecycle only: PENDING, ASSESSING, COMPLETED, SUPERSEDED or FAILED. |
| `method` | `AssessmentMethod` | Yes | DETERMINISTIC only. |
| `authority` | `SourceAuthority` | Yes | Authority supported by policy and provenance. |
| `satisfied_fields` | `Text[]` | Yes | Fields actually supported. |
| `missing_fields` | `Text[]` | Yes | Required fields not supported. |
| `evidence_refs` | `Ref<EvidenceRecord>[]` | Yes | Observed supporting evidence. |
| `error_codes` | `ErrorCode[]` | Yes | Blocking/diagnostic catalog codes. |

COMPLETED means the deterministic assessment finished, not that sources are sufficient. Only outcome SUFFICIENT can pass a blocking source gate. MISSING covers absent sources or required fields; STALE covers inapplicable versions/period or failed freshness applicability; CONFLICTING covers contradictory facts; NOT_AUTHORITATIVE rejects source authority; AMBIGUOUS means unresolved identification or interpretation. FAILED is a technical assessment failure and has no business verdict. Preserve every finding in error_codes; deterministic policy chooses the primary outcome when several apply. A completed finding is immutable; new evidence produces a new assessment, and supersession preserves the original outcome. A period match alone cannot yield SUFFICIENT. The freshness evaluation must use the pinned policy and assessed source versions, record its as_of and provenance, and pass independently. Missing inputs may leave freshness_evaluation null or BLOCKED but can never produce SUFFICIENT.

### EvidenceRecord

Immutable observed source fact with provenance, not an AI assertion.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `kind` | `EvidenceKind` | Yes | Native value, formula identity, source excerpt or validation output. |
| `document_version_ref` | `DocumentVersionRef` | Yes | Exact source binary. |
| `semantic_object_ref` | `Ref<SemanticObject>` | No | Semantic context if available. |
| `native_locator_ref` | `Ref<NativeLocator>` | No | Native source identity if applicable. |
| `content_ref` | `ContentRef` | Yes | Preserved extracted observation and digest. |
| `observed_value` | `Nullable<BusinessValue>` | Yes | Optional-in-value typed observation: scalar, structured or null when evidence is represented only by content_ref. |
| `formula_text` | `Text` | No | Native formula text, kept distinct from calculated value. |
| `authority` | `SourceAuthority` | Yes | Source authority established by policy. |
| `period_scope` | `EvidencePeriodScope` | Yes | SPECIFIC_PERIOD, PERIOD_INDEPENDENT or explicitly UNKNOWN. |
| `period` | `Nullable<Period>` | Yes | Required period when SPECIFIC_PERIOD; null otherwise. |

XLSX observations that depend on formulas require native cell/formula identity, not only a calculated value. AI output is held in AIInteractionRecord and cannot become an authoritative EvidenceRecord by renaming it. Evidence can be a table, set of observations, image or narrative rather than a scalar. content_ref preserves the evidence even when observed_value is null. PERIOD_INDEPENDENT does not satisfy a dated requirement unless the pinned policy permits it; UNKNOWN cannot satisfy a period-sensitive gate.

### EvidenceCheck

One deterministic evidence test with replayable inputs and a policy reference.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `check_kind` | `EvidenceCheckKind` | Yes | Explicit deterministic evidence check category; required for every EvidenceCheck. |
| `business_target_id` | `BusinessTargetID` | Yes | Checked target. |
| `source_assessment_refs` | `Ref<SourceAssessment>[+]` | Yes | Sufficiency inputs. |
| `evidence_refs` | `Ref<EvidenceRecord>[]` | Yes | Evidence tested; empty allowed for missing-source checks. |
| `policy_ref` | `ContentRef` | Yes | Check policy. |
| `evaluator_binding` | `EvaluatorBinding` | Yes | Exact deterministic check implementation/version/configuration used. |
| `method` | `AssessmentMethod` | Yes | DETERMINISTIC only. |
| `outcome` | `CheckOutcome` | Yes | Explicit result. |
| `error_codes` | `ErrorCode[]` | Yes | Catalog diagnostics. |
| `freshness_evaluation` | `FreshnessEvaluation` | No | Required only for FRESHNESS; absent for other kinds. Pins the policy, as_of, evaluator version, inputs and outcome. |

For FRESHNESS, the evaluation outcome must equal this check's outcome and its policy must match the referenced source requirement/assessment. One FRESHNESS check covers one pinned policy and evaluation context; split mixed policies into separate checks. A later check may find a prior source assessment no longer applicable, but it never rewrites that earlier result.

| EvidenceCheckKind | Explicit obligation |
| --- | --- |
| SOURCE_PRESENCE | Establish that required source artifacts/observations exist. |
| PERIOD | Check applicability to the resolved required business period. |
| FRESHNESS | Apply the separate versioned deterministic freshness policy at the recorded as_of context. |
| AUTHORITY | Check source authority against governed policy. |
| COMPLETENESS | Check every required field/record requirement. |
| CONSISTENCY | Detect contradictions among relevant source facts. |
| VALUE_TYPE | Check the declared typed business value and structured schema where applicable. |
| UNIT | Check explicit units/currency/percentage representation without implicit conversion. |
| FORMULA | Check required native formula identity and its relation to the observed value; calculated value alone is insufficient. |
| PROVENANCE | Check immutable source versions, locations, artifact hashes and traceable lineage. |

Check categories are not confidence scores or lifecycle states. Each check records a deterministic outcome with evidence. Period and freshness require distinct checks when applicable; neither implies the other.

### EvidenceAssessment

Aggregate evidence verdict for one target, never a model confidence score.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `business_target_id` | `BusinessTargetID` | Yes | Target assessed. |
| `source_assessment_refs` | `Ref<SourceAssessment>[+]` | Yes | Pinned sufficiency records. |
| `evidence_check_refs` | `Ref<EvidenceCheck>[+]` | Yes | Deterministic checks. |
| `evaluator_binding` | `EvaluatorBinding` | Yes | Exact deterministic aggregation implementation/version/configuration used. |
| `status` | `EvidenceStatus` | Yes | VERIFIED only if every required check passes. |
| `method` | `AssessmentMethod` | Yes | DETERMINISTIC only. |
| `error_codes` | `ErrorCode[]` | Yes | Reasons for insufficient, conflicting or stale evidence. |

### MappingProposal

Suggested association of source information to a business target; acceptance is not write authority. A governed SYSTEM service persists and emits MappingProposal. AI participation is recorded separately in AIInteractionRecord and referenced as input/causation; it never authors a governed verification or approval transition.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `business_target_id` | `BusinessTargetID` | Yes | Proposed target. |
| `target_region_ref` | `Ref<TargetRegion>` | Yes | Concrete target occurrence. |
| `evidence_refs` | `Ref<EvidenceRecord>[]` | Yes | Source observations. |
| `rule_evaluation_refs` | `Ref<RuleEvaluation>[]` | Yes | Deterministic inputs. |
| `ai_interaction_refs` | `Ref<AIInteractionRecord>[]` | Yes | Optional bounded assistance; may be empty. |
| `proposed_value` | `BusinessValue` | Yes | Candidate value. |
| `status` | `MappingProposalStatus` | Yes | Review lifecycle. |
| `rationale` | `Text` | Yes | Reviewable explanation. |
| `error_codes` | `ErrorCode[]` | Yes | Blocking diagnostics. |

### AIInteractionRecord

Bounded AI interaction with zero execution authority.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `actor` | `Actor` | Yes | AI service identity; actor_type must be AI. |
| `provider` | `Text` | Yes | Provider identity. |
| `model` | `Text` | Yes | Model identity. |
| `model_version` | `NullableText` | Yes | Version if exposed, otherwise null. |
| `instruction_ref` | `ContentRef` | Yes | Instruction/version artifact and digest. |
| `context_refs` | `ContentRef[+]` | Yes | Actual supplied context artifacts and digests. |
| `input_refs` | `Reference[]` | Yes | Governed source/context objects. |
| `output_ref` | `ContentRef` | Yes | Preserved structured output, subject to data policy. |
| `output_summary` | `Text` | Yes | Concise observable result, not hidden reasoning. |
| `verification_refs` | `Ref<EvidenceAssessment>[]` | Yes | Subsequent independent evidence outcomes. |
| `untrusted_content_detected` | `Bool` | Yes | Whether document content was flagged as untrusted instructions. |

No hidden chain-of-thought field or dependency is permitted. Model confidence, probability, similarity and self-assessment never create execution authority.

## E. Review and Authorization

### ChangeProposal

Concrete proposed native change with zero execution authority, including after review status APPROVED.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `business_target_id` | `BusinessTargetID` | Yes | One proposed business target. |
| `target_document_version_ref` | `DocumentVersionRef` | Yes | Exact proposed target version. |
| `target_contract_definition_ref` | `Ref<TargetContractDefinition>` | Yes | Pinned reusable contract definition revision. |
| `target_contract_instance_ref` | `Ref<TargetContractInstance>` | Yes | Pinned task/document-specific contract instance revision. |
| `rule_pack_ref` | `Ref<RulePack>` | Yes | Pinned RulePack. |
| `mapping_proposal_ref` | `Ref<MappingProposal>` | Yes | Mapping reviewed. |
| `source_assessment_refs` | `Ref<SourceAssessment>[+]` | Yes | Sufficiency inputs. |
| `evidence_assessment_refs` | `Ref<EvidenceAssessment>[+]` | Yes | Evidence verdicts. |
| `native_locator_ref` | `Ref<NativeLocator>` | Yes | Proposed exact native target. |
| `operation` | `MutationOperation` | Yes | Candidate operation, never an immediate command. |
| `current_value` | `BusinessValue` | Yes | Observed current value. |
| `proposed_value` | `BusinessValue` | Yes | Proposed current-year value. |
| `payload` | `MutationPayload` | Yes | Closed typed candidate payload, matching operation; no execution authority. |
| `status` | `ChangeProposalStatus` | Yes | Proposal lifecycle. |
| `error_codes` | `ErrorCode[]` | Yes | Blocking reasons. |

Editing a proposal creates a new revision and invalidates decisions referring to an earlier payload. Blocked conclusions cannot enter an ApprovedChangeSet.

### ReviewDecision

Explicit immutable human decision on a pinned proposal revision.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `change_proposal_ref` | `Ref<ChangeProposal>` | Yes | Exact proposal reviewed. |
| `reviewer` | `Actor` | Yes | Authenticated HUMAN identity, set by the service. |
| `outcome` | `ReviewOutcome` | Yes | APPROVE, REJECT, DEFER or REQUEST_MORE_SOURCE; only APPROVE can support authorization. |
| `reason` | `Text` | Yes | Reviewable reason. |
| `reviewed_evidence_refs` | `Reference[]` | Yes | Pinned evidence and sufficiency records actually reviewed. |
| `supersedes_decision_ref` | `Ref<ReviewDecision>` | No | Prior decision superseded by this new record. |
| `requested_source_requirement_refs` | `Ref<SourceRequirement>[]` | Yes | Nonempty for REQUEST_MORE_SOURCE; otherwise empty. |

Review records never rewrite earlier machine/AI evidence. An APPROVE outcome with blocking gates cannot yield an ApprovedChangeSet. REQUEST_MORE_SOURCE explicitly requests the named requirements and leaves the affected proposal blocked; it never converts missing source evidence into sufficiency.

### ApprovedChange

One sealed operation inside an ApprovedChangeSet; not independently dispatchable.

Sealed inline value; no common record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `approved_change_id` | `ID` | Yes | Unique only within the containing ApprovedChangeSet. |
| `business_target_id` | `BusinessTargetID` | Yes | Approved business target. |
| `change_proposal_ref` | `Ref<ChangeProposal>` | Yes | Exact approved proposal. |
| `native_locator_ref` | `Ref<NativeLocator>` | Yes | Immutable exact execution address. |
| `operation` | `MutationOperation` | Yes | Approved native operation. |
| `payload` | `MutationPayload` | Yes | Exact approved payload. |
| `evidence_refs` | `Ref<EvidenceRecord>[+]` | Yes | Evidence supporting this change. |
| `review_decision_ref` | `Ref<ReviewDecision>` | Yes | Explicit APPROVE decision. |
| `preconditions` | `Condition[+]` | Yes | Required deterministic checks before mutation. |
| `postconditions` | `Condition[+]` | Yes | Required deterministic result checks. |

Sealed inline content at authorization.approved_changes. It has no common record envelope, global id/revision, task_id or standalone resource. Identify it only by the parent approved_change_set_ref plus approved_change_id. The parent binds the definition/instance versions, RulePack, binary, protected scope and validation. Payload kind must match operation and a compatible qualified locator.

### ApprovedChangeSet

Sealed authorization assembled by governance from explicit decisions and passing deterministic gates.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `status` | `ApprovedChangeSetStatus` | Yes | Authorization validity only: APPROVED, INVALIDATED, REVOKED or SUPERSEDED. |
| `authorization` | `AuthorizationBinding` | Yes | Exact frozen execution authorization. |
| `authorization_digest` | `SHA256` | Yes | SHA-256 of canonical authorization only; excludes lifecycle envelope. |

Creation starts at APPROVED after all authorization gates pass. Execution, validation and release do not transition this status. Subsequent authorization lifecycle snapshots cannot alter authorization or its digest. Changed content requires a new set ID and explicit approval; old sets become INVALIDATED, REVOKED or SUPERSEDED by new events. Eligibility checks latest validity events as well as the pinned authorization snapshot.

## F. Execution and Validation

### ReplayRequest

Internal dispatch request derived only from an eligible ApprovedChangeSet.

No common record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `execution_id` | `ID` | Yes | Orchestrator-assigned execution/idempotency identity. |
| `approved_change_set_ref` | `Ref<ApprovedChangeSet>` | Yes | Exact sealed authorization snapshot. |

Exactly these two properties are allowed. No envelope fields, task fields, free-form locator, operation, payload, profile or validation override is accepted. Contract version and correlation travel in trusted transport metadata. Frontend never calls this internal boundary.

### ExecutionResult

Mechanical replay attempt result, independent of validation and release.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `approved_change_set_ref` | `Ref<ApprovedChangeSet>` | Yes | Authorization used. |
| `input_document_version_ref` | `DocumentVersionRef` | Yes | Actual execution input. |
| `status` | `ExecutionStatus` | Yes | Attempt lifecycle. |
| `engine` | `Text` | Yes | Engine identity. |
| `engine_version` | `Text` | Yes | Exact version. |
| `change_result_refs` | `Ref<ChangeExecutionResult>[]` | Yes | Per-change results. |
| `output_document_version_ref` | `DocumentVersionRef` | No | Staged output; absent for refusal before mutation. |
| `error_codes` | `ErrorCode[]` | Yes | Attempt diagnostics. |

Its id equals ReplayRequest.execution_id. SUCCEEDED means mechanical completion only; it does not authorize release. Failed staging is quarantined. Release state belongs to task/document release governance, not this result.

### ChangeExecutionResult

Result for one ApprovedChange in one execution attempt.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `execution_ref` | `Ref<ExecutionResult>` | Yes | Parent attempt. |
| `approved_change_set_ref` | `Ref<ApprovedChangeSet>` | Yes | Parent sealed set used by the referenced execution. |
| `approved_change_id` | `ID` | Yes | Identifier of exactly one inline ApprovedChange in that set. |
| `status` | `ChangeExecutionStatus` | Yes | Applied, refused, failed or not attempted. |
| `observed_before` | `BusinessValue` | No | Observed value before the operation. |
| `observed_after` | `BusinessValue` | No | Observed value after the operation. |
| `error_codes` | `ErrorCode[]` | Yes | Per-change diagnostics. |

The pair approved_change_set_ref + approved_change_id is the only inline-change identity. It must match the parent ExecutionResult's set. Inline changes are not global reference targets.

### ValidationPlan

Pinned independent validation obligations approved before execution.

Uses the record envelope without task_id.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `name` | `Text` | Yes | Plan identifier. |
| `required_checks` | `ValidationRequirement[+]` | Yes | Explicit scope and checks, all mandatory checks must pass. |
| `validator_policy_ref` | `ContentRef` | Yes | Independent validator qualification and separation policy. |
| `release_requires_all_targets` | `Bool` | Yes | True requires every task-required target before whole-document release. |

Plan changes require new approval for affected sets. A replay engine cannot waive checks or assert their success.

### ValidationReport

Independent validation record against an exact execution and output binary.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `execution_ref` | `Ref<ExecutionResult>` | Yes | Exact attempt assessed. |
| `approved_change_set_ref` | `Ref<ApprovedChangeSet>` | Yes | Approved changes and scope. |
| `validation_plan_ref` | `Ref<ValidationPlan>` | Yes | Required checks. |
| `input_document_version_ref` | `DocumentVersionRef` | Yes | Preserved pre-mutation input. |
| `output_document_version_ref` | `DocumentVersionRef` | Yes | Exact staged output assessed. |
| `validator` | `Actor` | Yes | Independent VALIDATOR identity; distinct from replay engine. |
| `status` | `ValidationStatus` | Yes | Independent outcome. |
| `check_result_refs` | `Ref<ValidationCheckResult>[]` | Yes | Check evidence. |
| `blocking_exception_refs` | `Ref<ExceptionRecord>[]` | Yes | Known blocking exceptions; report does not own task release state. |
| `error_codes` | `ErrorCode[]` | Yes | Validation and release diagnostics. |

PASSED requires all mandatory checks and preservation checks to PASS; engine self-report is insufficient. Any unauthorized change prevents successful release. A passing report is input to release governance, not a release decision or authorization state change.

### ValidationCheckResult

One independent validation result with preserved observations.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `validation_report_ref` | `Ref<ValidationReport>` | Yes | Report membership. |
| `requirement_id` | `ID` | Yes | Matches a ValidationRequirement in the pinned plan. |
| `kind` | `ValidationCheckKind` | Yes | Required check type. |
| `outcome` | `CheckOutcome` | Yes | Explicit observed outcome. |
| `observation_ref` | `ContentRef` | Yes | Independent evidence artifact and digest. |
| `error_codes` | `ErrorCode[]` | Yes | Catalog diagnostics. |

### ExceptionRecord

Traceable blocking or nonblocking exception and its remediation history.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `error_code` | `ErrorCode` | Yes | Catalog definition supplies blocking and recovery semantics. |
| `status` | `ExceptionStatus` | Yes | Exception lifecycle. |
| `business_target_id` | `BusinessTargetID` | No | Affected target, if any. |
| `related_refs` | `Reference[]` | Yes | Affected immutable records. |
| `detected_by` | `Actor` | Yes | Originating actor. |
| `details` | `Text` | Yes | Safe, reviewable facts. |
| `resolution_refs` | `Reference[]` | Yes | New evidence/decisions proving resolution; never old-record edits. |

### AnalysisRun

Governed orchestration resource for perception, enrichment and assessment; no mutation authority.

Uses the full task-owned record envelope.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `document_version_refs` | `DocumentVersionRef[+]` | Yes | Pinned inputs. |
| `target_contract_definition_ref` | `Ref<TargetContractDefinition>` | Yes | Pinned reusable contract definition revision. |
| `target_contract_instance_ref` | `Ref<TargetContractInstance>` | Yes | Pinned task/document-specific contract instance revision. |
| `rule_pack_ref` | `Ref<RulePack>` | Yes | Pinned business policy. |
| `status` | `AnalysisStatus` | Yes | Analysis lifecycle. |
| `output_refs` | `Reference[]` | Yes | Perception, source, evidence and proposal records. |
| `error_codes` | `ErrorCode[]` | Yes | Explicit analysis gaps. |

### AuditEvent references

Governance, execution, validation and exception actions emit immutable AuditEvent records defined in event-model.md. The reference convention is object_type AuditEvent, object_id equal to event_id and revision equal to event_version. An event proves a recorded action; it does not replace the ApprovedChangeSet or independent validation.

## Reusability and binding boundary

| Reusable, without task_id | Allowed dependencies |
| --- | --- |
| TargetContractDefinition | TargetRegionDefinition, SourceRequirement, reusable ValidationPlan and reusable policy ContentRefs. |
| TargetRegionDefinition | SourceRequirement, business target identifiers, type/operation declarations and reusable declarative policy/schema artifacts. |
| SourceRequirement | Business target identifiers, reusable period policy, optional fixed specific_period, pinned FreshnessPolicy and reusable policy artifacts. |
| FreshnessPolicy | Reusable deterministic evaluator identifiers and policy/configuration artifacts; never task-specific freshness observations. |
| RulePack and BusinessRule | Other reusable rule/source definitions, business target identifiers and reusable policy artifacts. |
| ValidationPlan | Reusable check definitions, business target identifiers and validator policy artifacts. |

This boundary is transitive. Reusable definitions MUST NOT reference task-owned DocumentVersions, DocumentPreflightAssessments, CapabilityResultRefs, PreflightFindings, FreshnessEvaluations, SemanticObjects, NativeBindings, NativeLocators, TargetRegions, TargetContractInstances or ProtectedScope instances, including through an intermediate reference or an artifact URI used to hide the dependency. A policy describes preservation rules; a ProtectedScope instance identifies actual objects in a particular binary.

TargetContractInstance binds a pinned TargetContractDefinition to exactly one task and one target DocumentVersion. TargetRegion binds a TargetRegionDefinition to an occurrence in that instance. A task can register an instance before perception; unresolved bindings do not confer readiness or authorization.

## Operation, payload and locator compatibility

The current mutation vocabulary remains the three operations below. Each requires its matching payload kind, an exact compatible locator and operation-specific qualification evidence for the engine/version/conformance/native structure.

| MutationOperation | MutationPayloadType | Compatible LocatorType |
| --- | --- | --- |
| REPLACE_RUN_TEXT | RUN_TEXT_REPLACEMENT | DOCX_RUN |
| REPLACE_SDT_TEXT | SDT_TEXT_REPLACEMENT | DOCX_CONTENT_CONTROL |
| REPLACE_SIMPLE_TABLE_CELL_TEXT | SIMPLE_TABLE_CELL_TEXT_REPLACEMENT | DOCX_TABLE_CELL |

DOCX_BOOKMARK, DOCX_PARAGRAPH, DOCX_RELATIONSHIP, XLSX_CELL, XLSX_DEFINED_NAME and XLSX_TABLE_RANGE have defined identity shapes for inspection, enrichment, evidence and binding. They do not introduce additional mutation operations. A paragraph or bookmark cannot silently resolve to a run for execution. New mutation operations require a versioned typed payload, an explicit compatible locator and qualification evidence before support can be claimed.

The current mutation profile is Transitional OOXML only. Strict OOXML mutation remains unsupported until explicitly qualified, regardless of reader/locator support. Zero matches, multiple matches, a fingerprint mismatch, an unknown variant or an unqualified operation all fail closed. Fingerprint verification is an exact precondition, not a confidence estimate.

## Authorization digest canonicalization

The digest input is the complete frozen authorization object, including inline ApprovedChange values, exact typed payloads, pinned definition/instance and RulePack revisions, document hashes, evidence and decision references, pre/postconditions, protected scope, qualification and validation obligations.

1. Reject duplicate JSON keys, invalid Unicode, non-finite numbers and values outside the contract. Exact business decimals and large integers are strings.
2. Canonicalize the authorization object using the RFC 8785 JSON Canonicalization Scheme (JCS).
3. Encode the canonical JSON as UTF-8 without a byte-order mark.
4. Compute SHA-256 over those exact bytes.
5. Store the result as 64 lowercase hexadecimal characters in authorization_digest.

The contract uses JCS for deterministic JSON hashing. See [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785).

```text
authorization_digest = lowercase_hex(SHA-256(UTF-8(JCS(authorization))))
```

Only authorization is hashed by this field. The outer lifecycle envelope and authorization_digest itself are excluded. Reference revision and embedded binary/content digests are included; every referenced record must also resolve immutably and pass integrity/authority checks. Do not reorder authorization arrays or normalize approved text after approval. Authorization validity changes do not rehash or alter the sealed content. A digest provides integrity checking and is not, by itself, permission to execute.

## Preserved invariants and cardinality

1. BusinessTargetID, SemanticReference and NativeLocator are separate identities. NativeBinding represents the association between semantic and native objects, not an execution address.
2. DocumentVersion is an immutable binary identified by SHA-256. Every NativeLocator belongs to exactly one such version and includes structural_fingerprint.
3. PerceptionSnapshot describes one DocumentVersion. Its SemanticObjects and associated NativeLocators must refer to that same version.
4. Reusable definitions never contain task-owned bindings. Instances and regions pin their definitions and exact target version.
5. SourceAssessment lifecycle COMPLETED does not imply sufficiency. Blocking gates require COMPLETED plus outcome SUFFICIENT and current authoritative inputs.
6. ChangeProposal and AIInteractionRecord have zero execution authority. AI output cannot independently set VERIFIED or APPROVED; model confidence/probability/similarity/self-assessment cannot grant authority.
7. Explicit immutable ReviewDecision records support authorization. REQUEST_MORE_SOURCE and human override create new records/events and never rewrite earlier source, machine or AI evidence.
8. Human approval cannot bypass blocking Source Sufficiency, protected objects, ambiguous locators or unsupported capabilities.
9. ApprovedChangeSet binds exactly one target DocumentVersion and binary hash, definition and instance versions, RulePack version, exact approved payloads and locators, evidence, human decisions, preconditions, postconditions, protected scope and required validation.
10. ApprovedChange is sealed inline content, identified only by approved_change_set_ref plus approved_change_id. There is no standalone reference or dispatch route for it.
11. Only an eligible ApprovedChangeSet may create a ReplayRequest. The request contains only execution_id and approved_change_set_ref; free-form locator, operation, payload, profile and validation overrides are forbidden. Frontend never calls the replay service directly.
12. Execution-time binary hash mismatch produces STALE_DOCUMENT_VERSION and execution refusal. Exact locator or fingerprint failures also refuse execution; fuzzy execution fallback is prohibited.
13. Authorization validity, execution progress, independent validation and task/document release are separate state machines. Execution or validation success never changes authorization status into a progress or release state.
14. Replay and independent validation are separate responsibilities. Successful mechanical execution produces only a staged version. Unauthorized changes prevent successful release.
15. Task completion and whole-document release require every required business target. A supported NCP factual change does not verify an arm's-length conclusion when current benchmark evidence is missing.
16. Every recorded revision is immutable and every reference is pinned. Supersession, override, revocation and correction append new records/events. No historical rewriting or silent reuse of obsolete approval is allowed.
17. DocumentVersion owns immutable binary identity; DocumentPreflightAssessment owns evolving observation history through new immutable assessments/revisions. Capability remains specific to its exact native scope, operation, engine/version, conformance and qualification evidence.
18. Every BusinessRule declares RuleType and a deterministic evaluator_key. Every RuleEvaluation, SourceAssessment, EvidenceCheck and EvidenceAssessment records the exact EvaluatorBinding used. Every EvidenceCheck declares EvidenceCheckKind. Neither taxonomy nor binding supplies executable code or authorization.
19. Period policy and freshness policy are separate, independently required governance concerns. A pinned period, unchanged hash or prior PASS never supplies indefinite freshness.
20. Every Condition is one closed typed variant; every BusinessValue includes kind and review_text. No generic executable condition/payload or implicit fallback is allowed.

One set may have several refused attempts, but at most one committed transformation of its approved input. Retry and concurrency guards are defined in status-model.md and remain independent of authorization validity.

## C1 migration consequences and unresolved work

These corrections are breaking changes to the un-frozen draft, not a runtime or data migration implementation:

- The draft TargetContract splits into TargetContractDefinition and TargetContractInstance; TargetRegionDefinition is reusable, while TargetRegion carries document bindings. References must identify which side they pin.
- SourceRequirement.current_period becomes period_policy with conditional specific_period. SourceAssessment records resolved_task_period and resolved_source_period separately.
- SourceAssessment.status no longer contains business outcomes. Old INSUFFICIENT or CONFLICTED drafts cannot be losslessly relabeled without inspecting the underlying findings; preserve old records and re-assess under the new contract.
- Generic address variants are replaced by the nine typed shapes, with exact structural fingerprints and pinned fingerprint profiles. Capture and qualification are still open implementation/evidence work.
- A flattened target capability is replaced by operation-specific CapabilityResult entries.
- BusinessValue now distinguishes all eight kinds and preserves review_text; prior percent-as-decimal-with-unit drafts must retain their exact meaning during explicit migration.
- The draft text-only payload helper is replaced by the MutationPayload union. No executable extension bag is introduced.
- Global inline-change references are removed. Results identify approved_change_set_ref and approved_change_id.
- Execution/validation/release labels are removed from ApprovedChangeSetStatus. Those states cannot be mechanically mapped to new approval without checking approval history, revocation and sealed content.
- Architecture generation stays v2; the pre-freeze wire/persistence schema version is 0.1.0. Do not silently relabel historical 2.0.0 draft records or reuse their digests. A converted authorization requires a newly sealed set and renewed explicit review.

Before freeze, the future OpenAPI and any additional shared-package material must align the domain, status and C2 behavioral contracts. Production fingerprint profiles, native-operation qualification, structured-value schema allowlisting, fiscal period policy and deterministic precedence for multiple source findings still require explicit policy/evidence decisions. None is a reason to weaken the fail-closed boundary or invent runtime behavior in this phase.

## C1.1 migration consequences

- Move DocumentVersion.format, conformance and capability_results observations into new DocumentPreflightAssessment records bound to the same binary identity. Do not rewrite historical DocumentVersion revisions or mint new binary identity merely because an engine assessment changes.
- Replace TargetRegion's copied capability_results with pinned preflight_assessment_refs and capability_result_refs. Assign entry IDs within each immutable assessment revision; no global capability record or broad target capability flag is introduced.
- Add explicit rule_type and evaluator_key to every BusinessRule through new definition revisions. Revalidate affected RulePack/approval references rather than silently defaulting a type or inferring an evaluator from free text.
- Add a reusable FreshnessPolicy and pin it in SourceRequirement. Record the resolved freshness evaluation separately from period resolution; there is no default age threshold or exemption for period-independent evidence.
- Add check_kind to every EvidenceCheck. Historical checks without sufficient provenance cannot be relabeled as passing a new freshness or formula check.
- Convert the generic Condition scope/expected shape into its exact typed variant. Output postconditions use the inline approved-change validation subject, never an input locator reused against a different hash.
- Make BusinessValue.kind and review_text explicit common fields without changing the eight passed C1 kinds or discarding exact representations.

These changes remain within pre-freeze schema version 0.1.0. Existing sealed authorizations are immutable: changed definition/policy/condition/capability bindings require a newly reviewed and sealed set with its RFC 8785 authorization digest. C1 authorization/execution/validation/release separation, inline ApprovedChange identity and restricted ReplayRequest remain unchanged.

Production freshness criteria/configuration, deterministic evaluator bindings and native preflight/qualification coverage still need approved evidence. No business thresholds, runtime implementations, error-catalog definitions, event-envelope changes or OpenAPI changes are supplied by C1.1.
