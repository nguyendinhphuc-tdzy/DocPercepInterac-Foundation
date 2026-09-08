# Foundation v2 Backend B0 Repository Audit

**Audit date:** 2026-09-08  
**Branch:** `build/backend-foundation-v2`  
**Audited commit:** `dcf092f`  
**Contract baseline:** Foundation Contract v0.1.0

## Purpose and authority

This audit identifies how the existing backend can support Foundation v2. It
does not approve legacy behavior for reuse. The authority order is
`docs/CURRENT_BASELINE.md`, accepted ADRs, the frozen contract under
`docs/contracts/`, and then implementation material.

The required architecture boundaries are:

`Perceive != Understand != Authorize != Locate != Execute`

Business Target ID, Semantic/Docling Reference, and Native Locator remain
separate identities. A Native Locator is exact, version-scoped, and bound to a
binary hash. AI and proposals have no execution authority. Only a sealed
ApprovedChangeSet can authorize replay. Replay, independent validation, and
release are separate responsibilities.

The historical statement **“Docling is removed”** appears in
`foundation/requirements.txt`, `foundation/STATUS.md`, and
`foundation/perception/parser.py`. It is superseded. Docling-slim is the
provisional semantic perception baseline; existing parser and anchor code is
prototype/reference material.

## Classification meanings

| Classification | Meaning |
| --- | --- |
| KEEP | Already conforms to the current boundary and can remain in its role. |
| REFACTOR | Useful responsibility, but its interface or ownership must change before v2 use. |
| ADAPT | Reuse a bounded mechanism behind a new v2 port after qualification. |
| DEPRECATE | Keep isolated for compatibility while replacing its responsibility. |
| REFERENCE_ONLY | Use as research or test material; do not import it into authoritative v2 flow. |
| REMOVE_LATER | Remove after callers and retained evidence have migrated. No removal occurs in B0. |

## Component findings

| Path | Current responsibility | Embedded assumption | Contract alignment or conflict | Treatment | Main risk | Reusable in B0 |
| --- | --- | --- | --- | --- | --- | --- |
| `foundation/domain/` | Frozen v0.1 typed contract projection introduced by B0.2. | Immutable closed data shapes precede runtime behavior. | Aligns with contract envelopes, unions, identities, and authority limits. | KEEP | Later services may try to add convenience behavior to domain records. | Yes: canonical backend data types only. |
| `foundation/perception/parser.py` | Extracts DOCX, XLSX, and PDF geometry with python-docx, openpyxl, pdfplumber, and raw OOXML reads. | “Docling is removed”; custom geometry is the perception baseline. | Conflicts with provisional Docling-slim baseline and does not produce PerceptionSnapshot/SemanticObject identity. Its XLSX formula/value reads may inform native enrichment. | REFERENCE_ONLY | Treating extracted blocks as governed semantic truth or using them as execution addresses. | No direct import; retain corpus observations and helper research. |
| `foundation/perception/models.py` | Defines Element, capabilities, and DOCX/XLSX/PDF anchor models. | `doc_id + element_id` and generic anchors are sufficient identity; confidence/capability can live on elements. | Conflicts with the three-identity model, operation-specific capability, version-bound NativeLocator, and deterministic evidence gates. | DEPRECATE | Accidental conversion of a semantic element or confidence value into execution authority. | Field names and old fixture data are reference material only. |
| `foundation/perception/anchor_builder.py` | Builds and resolves hash/index/content anchors, including lower-confidence recovery paths. | A changed location can be recovered through fallback matching. | Exact fingerprints are useful observations, but fallback/self-heal and index-only resolution violate the no-fuzzy-execution rule. | REFERENCE_ONLY | Ambiguous or stale targets could be silently redirected. | Hash/fingerprint experiments may inform a future qualified locator capture adapter. |
| `foundation/perception/element_classifier.py` | Assigns generic editable/rendered/selectable capabilities and confidence. | One flattened element capability describes mutation support. | Conflicts with capability tuple: operation, structure, version, engine/version, conformance, and qualification evidence. | REFACTOR | `editable=true` could be mistaken for qualified replay support. | Detection observations may feed DocumentPreflightAssessment after remapping. |
| `foundation/perception/xlsx_visual_inventory.py` | Inventories XLSX drawings and unsupported openpyxl object classes. | openpyxl-visible structures define practical coverage. | Aligns with fail-closed discovery and XLSX native enrichment, but results are not version-bound CapabilityResult entries. | ADAPT | Missing native objects may be reported as absent rather than unsupported. | Inventory probes after binding outputs to exact DocumentVersion and assessor configuration. |
| `foundation/output/writeback.py` | Direct generic DOCX/XLSX writes through python-docx/openpyxl and string/anchor batches. | A request anchor plus value is enough to mutate; fallback resolver output is acceptable. | Conflicts with sealed authorization, typed payloads, exact locators, replay qualification, and independent validation. These libraries are not authoritative universal replay engines. | REMOVE_LATER | Unauthorized, fuzzy, or structure-damaging changes can be saved as successful output. | Only as negative/golden-corpus reference; never in v2 replay flow. |
| `foundation/output/lineage.py` | Logs value-patched records with hashes and confidence. | A simple line log is sufficient audit proof; confidence supports provenance. | Conflicts with immutable typed AuditEvent, actor/correlation/causation, integrity payload hash, and the ban on confidence as verification. | DEPRECATE | Incomplete records may be mistaken for contract audit evidence. | Log formatting is not reusable; stored historical evidence remains preserved. |
| `foundation/api/routes/documents.py` | Upload, inspect, direct element PATCH, download, and visual inventory endpoints. | Frontend may submit an anchor/value and call mutation directly. | The PATCH endpoint is explicitly forbidden by the v2 API boundary; it bypasses ApprovedChangeSet and controlled replay. | REMOVE_LATER | Direct mutation remains reachable and can bypass governance. | Intake/download mechanics may later move behind governed application ports. |
| `foundation/api/routes/agent.py` | Agent chat, proposal execution/rejection, and roll-forward approval endpoints. | A confirmed ProposedAction or manifest approval may directly drive writeback. | Conflicts with AI zero authority and the rule that only ApprovedChangeSet reaches replay. | REFACTOR | Human confirmation of an incomplete proposal may be treated as full authorization. | Provider-neutral chat transport can support bounded assistance after authority is removed. |
| `foundation/api/routes/workflow.py` | Session workflow intake and role assignment. | Mutable session state is the workflow aggregate. | Some role/intake concepts align, but it does not use immutable task records, pinned revisions, or v2 status vocabulary. | ADAPT | Session “latest” state can erase or bypass historical decisions. | Intake UX data after translation to immutable records/events. |
| `foundation/api/routes/gpts.py` and `foundation/applications/gpts/` | Demo mapping and GPT-assisted mapping with WritebackEngine access. | Mapping confidence or demo rules can lead directly to writes. | Conflicts with bounded AI assistance and proposal zero authority. | REMOVE_LATER | AI-generated mappings can cross directly into mutation. | Prompt/evaluation examples only, after removing write paths. |
| `foundation/applications/agent/models.py` | Agent context, citations, intent, ProposedAction, and provider registry. | ProposedAction plus confirmation is an executable unit; confidence is routing evidence. | ProposedAction is not ChangeProposal or ApprovedChangeSet; anchor dicts are not NativeLocator. | DEPRECATE | A competing model vocabulary obscures the frozen authority boundary. | Provider registry and user-visible non-chain-of-thought step concepts may be adapted separately. |
| `foundation/applications/agent/orchestrator.py` | Selects model/provider and generates agent responses/proposals. | Agent orchestration owns intent and proposal flow. | Provider isolation and visible explanations align; downstream proposal authority does not. | REFACTOR | AI output may inherit application authority through existing executor coupling. | Bounded interpretation, drafting, and ambiguity-analysis orchestration only. |
| `foundation/applications/agent/action_executor.py` | Claims a proposal, hashes a document, resolves/falls back to anchors, writes, stores, and logs. | A server-side confirmed proposal is enough to execute; re-perception may recover an address. | Conflicts with ApprovedChangeSet-only replay, exact locator resolution, typed operations, and independent validation. | REMOVE_LATER | This is a direct AI/proposal-to-write path with fuzzy fallback. | Hash-staleness test cases can inform future invariant tests; no runtime reuse. |
| `foundation/applications/agent/proposal_store.py` | Persists mutable proposed actions and statuses. | Proposal lifecycle and execution claim belong in one store record. | Conflicts with immutable revisions and separation of proposal, review, authorization, and execution. | DEPRECATE | Status mutation can rewrite history and blur authorization state. | Storage concurrency lessons only. |
| `foundation/applications/pilot/event_log.py` | Emits sanitized pilot analytics events. | Product telemetry can double as an audit record. | Useful privacy filtering, but event types, envelope, causation, evaluator identity, and integrity hash are noncanonical. | REFERENCE_ONLY | Telemetry could be relied upon as legal/governance audit evidence. | Sanitization cases may inform a separate observability adapter. |
| `foundation/applications/rollforward/models.py` | V1 manifest, region, source binding, diff, validation, and transition models. | One mutable RollForwardManifest owns the full workflow. | Conflicts with frozen top-level records and separated lifecycles. | DEPRECATE | Competing enums and mutable aggregate state can contaminate v2 code. | Domain scenarios and old corpus expectations only. |
| `foundation/applications/rollforward/state_machine.py` | Enforces the V1 manifest state graph and mutates the manifest/history. | Manifest APPROVED is execution authority and validation is one manifest state. | Conflicts with canonical task, authorization, execution, validation, and release state machines. B0.3 must not extend this graph. | REFERENCE_ONLY | Reusing it would duplicate or contradict frozen transitions. | Exception/test patterns only. |
| `foundation/applications/rollforward/evidence_policy.py` | Hard-coded source field policies and evidence corpus evaluation. | Embedded patterns and role schemas are current business authority. | Deterministic evidence intent aligns, but policy is not a pinned RulePack/SourceRequirement/FreshnessPolicy with evaluator binding. | ADAPT | Hidden thresholds or patterns could become unversioned policy. | Evaluation techniques after extracting versioned declarative policy. |
| `foundation/applications/rollforward/source_intake.py`, `source_registry.py`, `workflow_intake.py` | Registers source files, assigns roles, computes hashes, requests missing sources, and derives readiness. | Mutable package/register state is authoritative. | Hashing, explicit source requests, and role separation align; record identity and state vocabulary do not. | ADAPT | Mutable readiness may overwrite prior assessments or conflate period with freshness. | File hashing, intake checks, and missing-source request mechanics behind v2 ports. |
| `foundation/applications/rollforward/source_capability.py` | Profiles spreadsheet datasets and readable source fields. | Reader visibility represents source capability. | Useful for XLSX enrichment/read capability, but not operation-specific native mutation capability. | ADAPT | Reader support may be promoted to replay support. | Source profiling observations only. |
| `foundation/applications/rollforward/data_reconciliation.py` | Reconciles spreadsheet values, formulas, units, and source/target cells. | Cell references and reconciliation records can form the governed model. | Formula provenance and deterministic checks align; identities and policy bindings are not canonical. | ADAPT | Derived values may lack exact evaluator/configuration identity. | Evaluator algorithms after binding key/version/configuration and emitting frozen records. |
| `foundation/applications/rollforward/semantic_binding.py` | Derives target schemas and evaluates table semantics. | Derived table/column roles can serve as target bindings. | Mapping ideas align, but they do not preserve BusinessTargetID, SemanticReference, and NativeLocator as separate identities. | ADAPT | Semantic similarity or derived schema could become an execution locator. | Candidate mapping evidence only. |
| `foundation/applications/rollforward/planner.py` and `mutation_precondition.py` | Builds mutation plans, digests them, and checks preconditions. | MutationPlan/ApprovedScope are the authorization boundary. | Digest and precondition concepts align, but frozen authority is inline ApprovedChange in ApprovedChangeSet with RFC 8785 digest. | REFACTOR | A parallel authorization format can bypass sealed content. | Pure planning observations after output is mapped into ChangeProposal; no execution authority. |
| `foundation/applications/rollforward/structural_writeback.py` | Clones rows and performs structural DOCX writes with in-process checks. | python-docx/custom OOXML is the production execution engine. | Conflicts with provisional replay candidates and current mutation vocabulary; some preservation tests are useful. | REFERENCE_ONLY | Custom serialization may alter unapproved package content. | Golden-corpus challenger cases and failure examples only. |
| `foundation/applications/rollforward/full_validation.py` | Compares package/document structures and produces validation findings. | Validator may share libraries and process assumptions with mutation code. | Package diff, protected scope, and re-perception concepts align, but v2 requires independently qualified validation and canonical reports. | ADAPT | Correlated replay/validator blind spots may produce false assurance. | Individual checks behind an independent validator port after qualification. |
| `foundation/applications/rollforward/orchestrator.py` | Combines approval scope, mutation, reconciliation, validation, lineage, and publication. | One orchestrator may own execution through publication. | Conflicts with separation of authorization, execution, independent validation, and release. | DEPRECATE | Mechanical success may be reported as validated or publishable. | Scenario ordering and failure cases only. |
| `foundation/adapters/storage.py` | Local/cloud binary storage with hashes and temporary paths. | “Original/patched/latest” flags identify document state. | Byte storage and hashing are useful, but aliases are not immutable DocumentVersionRef and cannot authorize reads/writes. | ADAPT | Latest/patched lookup can bypass exact version and binary hash locking. | ContentRef storage mechanism after exact-version interfaces are introduced. |
| `foundation/adapters/repository.py` | Local/Supabase persistence for sessions, documents, versions, proposals, lineage, pilot events, and workflows. | Mutable CRUD rows represent current truth. | Persistence mechanics are reusable, schemas are not v2 records and do not guarantee append-only revisions. | REFACTOR | Updates can rewrite governance history or mix tenant/task identities. | Connection, transaction, and optimistic-concurrency patterns only. |
| `foundation/migrations/001_initial_schema.sql` and `002_workflow_intake.sql` | Persist legacy sessions, documents, versions, proposals, lineage, pilot events, and workflow intake. | Existing relational rows are the long-term domain schema. | They do not project the frozen ObjectType records or immutable revision/audit model. | DEPRECATE | Extending these tables could cement mutable legacy semantics into v2. | Database operational lessons only; future schema work requires a separate approved phase. |
| `foundation/eval/classifier_diff.py` | Compares deterministic and AI-assisted classifier output. | Classifier quality/confidence is the main evaluation boundary. | Comparative evaluation is useful, but confidence cannot establish verification or authorization. | REFERENCE_ONLY | Quality metrics may be misread as governance evidence. | Evaluation harness patterns after outputs use canonical records. |
| `foundation/models/README.md` | Reserves a former model location and points to perception models. | Perception models are the shared canonical domain. | Superseded by `foundation/domain/` for v2 contracts. | REMOVE_LATER | Imports may continue to seek a competing model package. | No code reuse. |
| `foundation/tests/` | Legacy perception, agent, API, roll-forward, writeback, and deployment tests. | Passing existing behavior establishes architecture readiness. | Valuable regression and corpus evidence, but many tests assert superseded behavior. They do not prove v2 contract conformance. | REFERENCE_ONLY | Keeping a green legacy test may preserve a forbidden direct-write path. | Select test documents, negative cases, and engine observations for future Golden Corpus work. |
| `foundation/requirements.txt` | Backend dependency list plus historical architecture commentary. | python-docx/openpyxl geometry and “Docling is removed” are authoritative. | Dependency availability is useful; comments conflict with current baseline. Restricted readers/helpers remain possible, subject to qualification. | DEPRECATE | Engineers may treat comments as current architecture authority. | Existing Pydantic v2 dependency supports B0.2; no dependency change is needed. |
| `foundation/STATUS.md` | Historical implementation status and decisions. | Prototype features and direct writeback represent current Foundation architecture. | Explicitly non-authoritative and contradicted by the current baseline/frozen contract. | REFERENCE_ONLY | Status prose can reactivate superseded design decisions. | Historical evidence only. |

## B0 boundary decision

B0.2 adds only the typed data projection and its conformance tests. It does
not connect the new records to existing API, persistence, AI, perception,
writeback, validation, or roll-forward modules. That separation prevents
prototype imports from silently defining v2 semantics.

The Python/OpenAPI drift check derives the ObjectType registry, fields, required
properties, closure, and enum value coverage from the frozen OpenAPI document.
Semantic fixture validation then loads all eight frozen scenarios through the
Python types. This avoids a third handwritten schema authority.

## Deferred work

- B0.3: canonical lifecycle enforcement and transition evidence.
- B0.4: runtime invariant enforcement, including reference resolution and
  authorization eligibility.
- B0.5: immutable audit persistence and integrity hashing infrastructure.
- B0.6: application ports/adapters that isolate legacy services.
- B0.7: Golden Corpus harness and engine qualification evidence.

No legacy file, endpoint, engine, test, dependency list, or persisted record is
removed or rewritten by this audit.
