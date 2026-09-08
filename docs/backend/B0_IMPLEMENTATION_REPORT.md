# Foundation v2 Backend B0 Implementation Report

**Architecture generation:** Foundation v2  
**Frozen contract schema:** 0.1.0  
**Implementation branch:** `hardening/backend-b0-final`
**Baseline implementation commit:** `3bd26dd` (`Backendd B0.1 and 0.2`)  
**Status:** Complete; awaiting independent audit

## Authority and Scope

Backend B0 establishes contract-conforming domain, governance, audit, port, and qualification-harness boundaries. It does not integrate legacy APIs, Docling, an AI provider, a replay engine, an independent validation engine, or production persistence. No frozen contract, ADR, current baseline, project-phase, frontend, or contract tag was changed.

## Milestone Status

| Milestone | Status | Result |
| --- | --- | --- |
| B0.1 Repository Audit | Complete | Current and legacy boundaries, dependencies, risks, and the B0 implementation path are recorded in `B0_REPOSITORY_AUDIT.md`. |
| B0.2 Frozen Contract Typed Domain Models | Complete | Strict Pydantic projections cover the frozen OpenAPI component schemas and all eight behavioral fixtures. |
| B0.3 State Machine Enforcement | Complete | The frozen lifecycle edges are represented by a new v2 transition engine with revision, actor, guard, audit-hook, and idempotency controls. |
| B0.4 Runtime Invariant Enforcement | Complete | A registry enforces the fifteen required B0 invariant IDs with structured, fail-closed results. |
| B0.5 Audit Foundation | Complete | RFC 8785/SHA-256 event integrity, immutable event creation, task-scoped causation, and chain validation are implemented. |
| B0.6 Architecture Ports / Legacy Boundary | Complete | Typed protocols define the external boundaries; architecture tests reject imports from legacy mutation, API, and frontend layers. |
| B0.7 Golden Corpus Harness | Complete | An engine-neutral manifest, runner, comparator, JSON report, dummy adapter, and synthetic self-test are operational. |

## Implemented Architecture

The B0 implementation adds these v2 boundaries:

- `foundation.domain`: frozen typed records, references, enums, and discriminated unions.
- `foundation.governance.state`: canonical transition definitions and append-only transition decisions.
- `foundation.governance.invariants`: the invariant registry, external observation inputs, and structured outcomes.
- `foundation.governance.authorization`: ApprovedChangeSet RFC 8785 authorization-digest computation and verification.
- `foundation.audit`: immutable event creation, RFC 8785 event hashing, hash verification, and causation-chain validation.
- `foundation.ports`: perception, native identity, bounded AI, replay, independent validation, and append-only persistence protocols.
- `foundation.evaluation.golden`: engine-neutral document-engine qualification models and runner.

The new core does not import the historical writeback, action-executor, or structural-writeback implementations. Status changes are domain decisions that produce new revisions; the implementation exposes no client status patch or direct document mutation path.

## B0.3 State Machine Coverage

The canonical matrix covers eleven frozen lifecycles: FoundationTask, DocumentArtifact, DocumentPreflightAssessment, SourceAssessment, MappingProposal, ChangeProposal, ApprovedChangeSet, ExecutionResult, ValidationReport, ExceptionRecord, and AnalysisRun.

The matrix contains 103 allowed directed edges. Generated enum cross-product tests reject all other 375 pairs, including self-transitions and terminal-state exits unless the frozen status model explicitly permits an edge. The transition engine also checks:

- exact expected revision and creates a new revision rather than mutating history;
- an authenticated actor context;
- a required audit hook before a transition decision is returned;
- optional deterministic guards with structured failure;
- request idempotency without emitting a duplicate audit decision;
- SourceAssessment lifecycle and sufficiency outcome separation;
- ApprovedChangeSet authorization state independence from execution and validation;
- Scenario C2-02 partial processing through `AWAITING_REVIEW -> BLOCKED -> READY_FOR_EXECUTION -> EXECUTING -> VALIDATING -> BLOCKED`.

Illegal edges and guard failures map to `INVALID_STATE_TRANSITION` and fail closed.

## B0.4 Invariant Coverage

| Frozen invariant ID | B0 enforcement | External observation boundary |
| --- | --- | --- |
| FND-INV-DOC-001 | Verifies immutable DocumentVersion reference and binary-hash consistency across authorized changes. | None |
| FND-INV-ID-001 | Verifies Business Target ID, Semantic Reference, and Native Locator remain separate identities. | None |
| FND-INV-ID-002 | Verifies NativeBinding expresses semantic-to-native association without replacing either identity. | None |
| FND-INV-LOC-001 | Requires exact, single native resolution, matching structural fingerprint, and no fuzzy fallback. | `LocatorResolutionObservation` from a future native adapter is mandatory. |
| FND-INV-CAP-001 | Verifies operation-specific capability binding and matching supported preconditions. | Capability result supplied by preflight records. |
| FND-INV-EVAL-001 | Requires evaluator key, version, and configuration reference for critical deterministic evaluations. | None |
| FND-INV-SRC-001 | Blocks authorization when SourceAssessment is absent, incomplete, or insufficient. | None |
| FND-INV-EVD-001 | Requires deterministic verified evidence for authorization. | None |
| FND-INV-FRESH-001 | Requires a deterministic freshness policy and passing freshness evidence. | None |
| FND-INV-AI-001 | Prevents AI output or AI actors from establishing verified evidence or authorization. | None |
| FND-INV-AUTH-001 | Requires an approved proposal and qualifying human ReviewDecision. | None |
| FND-INV-AUTH-002 | Recomputes and verifies the sealed authorization digest. | None |
| FND-INV-AUTH-003 | Keeps authorization validity independent of execution, validation, and release states. | None |
| FND-INV-REPLAY-001 | Requires ReplayRequest to contain only execution identity and an approved ApprovedChangeSet reference. | Future replay adapter executes only this sealed request. |
| FND-INV-REL-001 | Blocks whole-task release when any mandatory target remains blocked, while preserving independent subset eligibility. | None |

Each result carries the invariant ID, pass/fail outcome, frozen ErrorCode where applicable, affected references, blocking flag, and reason. Missing required external evidence fails closed. The positive C2-01 scenario passes all fifteen registered invariants, and focused negative tests cover stale identity, missing locator resolution, AI authority, insufficient source, invalid digest, and blocked release.

## Authorization and Audit Evidence

Authorization digests and AuditEvent integrity hashes use the pinned `rfc8785==0.1.4` implementation, UTF-8 RFC 8785 JSON Canonicalization Scheme output, SHA-256, and lowercase hexadecimal output. Serialization preserves the frozen fixture's distinction between omitted optional properties and explicit nulls.

All eight frozen ApprovedChangeSet authorization revisions recompute to their recorded digests. Tests detect changes to content, operation, payload, locator, policy, evidence, and references.

All 276 frozen AuditEvents recompute to their recorded integrity hashes. Causation validation requires exactly one `TASK_CREATED` root per task, requires every later event to cite an earlier event from the same task, rejects cycles and cross-task causes, and keeps the first material failure traceable even when later processing proceeds on an independent causal branch. Tests also reject content tampering, null causation on later events, missing causes, and invalid causal order.

AI audit metadata remains the frozen closed union. It records provider, model, version, instruction, context, and output references and provides no field for hidden chain-of-thought.

## B0.6 Ports

The following Protocol interfaces exchange frozen domain records and references:

- `PerceptionPort`
- `NativeIdentityPort`
- `AIInterpretationPort`
- `ReplayPort`
- `ValidationPort`
- `DomainRecordRepository`
- `AuditRepository`

`ReplayPort` accepts only the frozen `ReplayRequest`; no free-form operation, locator, or payload override is available. Persistence protocols expose append and revision-aware retrieval boundaries suitable for immutable history. No concrete external adapters are included in B0.

## B0.7 Golden Corpus Harness

The harness defines strict `GoldenCase`, `GoldenManifest`, `GoldenObservation`, `GoldenResult`, and `GoldenReport` models. It validates manifest input hashes, invokes an engine-neutral adapter protocol, compares capability, preservation, and expected-failure observations deterministically, and writes a machine-readable JSON report.

The synthetic harness self-test passes one of one cases. Its qualification scope is `HARNESS_SELF_TEST_ONLY`, and `qualification_claimed` is `false`. This result does not qualify Docling, Open XML SDK, docx4j, Strict OOXML, or any production engine.

## Validation Evidence

| Command | Result |
| --- | --- |
| `.venv-contracts\\Scripts\\python.exe tools/contracts/validate_contract_fixtures.py --report contract-validation-report.json` | PASS: OpenAPI valid; 8/8 scenarios passed every validation dimension; 8/8 authorization digests and 276/276 event hashes verified. |
| `.venv-contracts\\Scripts\\python.exe -m unittest discover -s tests/contracts -v` | PASS: 23 tests. |
| `python -m pytest tests/backend -q` | PASS: 71 tests. |
| `python -m pytest tests/golden -q` | PASS: 2 tests. |
| `python -m foundation.evaluation.golden tests/golden/corpus_manifest.yaml tests/golden/reports/b0-synthetic-report.json` | PASS: 1/1 synthetic cases; no qualification claim. |
| `python -m compileall -q foundation/governance foundation/audit foundation/ports foundation/evaluation tests/backend tests/golden` | PASS. |
| `git diff --check` | PASS. |

The ambient Python environment does not contain the contract validator's pinned `openapi-spec-validator` package. Contract validation and contract unit tests therefore use the repository's `.venv-contracts` environment, matching the established contract-tooling dependency set. Backend runtime tests use the dependencies pinned in `foundation/requirements.txt`.

## Final Hardening

The independent B0 audit identified four P0 governance gaps: authorization validated only records already listed in the authorization, capability checks did not compare the full execution tuple, review binding did not establish proposal revision lineage, and graph resolution could select records by stable business identity without task scope. The hardening pass closes each gap without changing Contract v0.1.0, ADRs, fixtures, or the baseline.

### SourceRequirement completeness

`FND-INV-SRC-001` now derives applicable requirements from the pinned TargetContractDefinition, matching TargetRegion and TargetRegionDefinition, and RulePack/BusinessRule relationships. It filters by the approved change's BusinessTargetID and blocking flag, then requires every applicable requirement to have a task-owned authorization SourceAssessment with `COMPLETED` + `SUFFICIENT` outcome and passing deterministic freshness evidence. Missing, stale, conflicting, ambiguous, non-authoritative, cross-target, cross-task, and unresolved replacement assessments fail closed with the corresponding frozen source error. Non-blocking requirements may remain absent.

### Exact capability tuple

`FND-INV-CAP-001` now verifies preflight completion and equality of DocumentVersion, NativeLocator scope, operation, engine, engine version, conformance, supported status, locator coverage, and non-empty qualification evidence. Capability observations from another task or another document version cannot satisfy an approval. No new engine or conformance class was added or qualified.

### Exact review/proposal/change binding

`FND-INV-AUTH-001` follows the frozen immutable-snapshot interpretation: the human ReviewDecision must approve an `IN_REVIEW` proposal revision, and the ApprovedChange must reference the immediate next `APPROVED` revision of the same logical task-owned proposal. A closed-model comparison permits only `revision`, `created_at`, and `status` to differ. Business target, document, contract, rule, mapping, source, evidence, locator, operation, values, payload, and error content must remain identical. The sealed ApprovedChange then must match the approved proposal and contain its source/evidence references.

### Task-scoped governance isolation

`GovernanceGraph` resolves immutable refs with explicit task ownership, rejects ambiguous duplicate identities, and groups latest records by `(record_id, task_id)`. Release evaluation now resolves TargetRegion by task and business target. Source, evidence, proposal, review, locator, binding, document, preflight, and authorization lookups reject cross-task records.

### State-machine review

The frozen lifecycle matrix remains unchanged. `StateTransitionEngine` still requires an optimistic revision, an authenticated actor, an audit hook, immutable successor revisions, and idempotent request handling. A `TransitionGuardRegistry` now binds each exact source/target edge to the guard instance used for the decision; an unregistered or substituted caller guard fails with `INVALID_STATE_TRANSITION`. The test factory is explicitly test-only and no Local File rule is embedded in the state machine.

### Port boundary decision

The perception and native-identity ports now return explicit non-contract `PerceptionResult` and `NativeIdentityResult` DTOs. They carry contract records for application persistence without implying that an adapter may persist snapshots, semantic objects, locators, or bindings as a hidden side effect. No frozen domain schema was changed and no adapter was implemented.

### Requirements authority cleanup

`foundation/requirements.txt` now identifies itself as a dependency artifact, points architecture authority to `docs/CURRENT_BASELINE.md` and the frozen contract, preserves legacy packages for reference compatibility, identifies Docling-slim as the provisional B1 semantic candidate, and states that python-docx/openpyxl presence does not qualify universal replay. No Docling dependency was added.

### Backend CI

`.github/workflows/backend-b0.yml` adds a reproducible backend gate for Foundation and B0 tests. It installs `tools/backend/requirements.txt`, which reuses pinned contract dependencies and pins pytest, then runs frozen contract validation, contract unit tests, backend tests, Golden tests, compilation, and report upload. The existing `Validate Foundation Contract v0.1` workflow remains unchanged.

### Final evidence

The hardening suite adds 31 focused negative and regression tests. Final local results are:

- frozen contract validation: 8/8 scenarios PASS, 8/8 authorization digests PASS, 276/276 AuditEvent hashes PASS, OpenAPI PASS;
- contract unit tests: 23 passed;
- backend tests: 71 passed;
- Golden harness tests: 2 passed;
- synthetic Golden run: 1/1 passed with `qualification_claimed=false`;
- Foundation v2 compilation and `git diff --check`: PASS.

The hardening pass still does not implement Docling, native Office adapters, replay, independent validation adapters, AI providers, production persistence, APIs, frontend integration, business services, or B1 orchestration. It makes no engine qualification claim and does not support Strict OOXML mutation.

## Known Limitations and B1 Boundary

B0 deliberately stops at architecture and deterministic contract enforcement. B1 may implement orchestration and concrete adapters only after this milestone is independently audited and accepted. The following remain outside B0:

- Docling semantic perception and its Golden Corpus qualification;
- native identity enrichment for DOCX and XLSX;
- Open XML SDK 3.5.1 and docx4j 17.0.5 replay adapters and A/B qualification;
- production AI-provider integration;
- independent document validation adapters;
- durable append-only persistence and transaction coordination;
- API routing, authorization infrastructure, and frontend integration;
- business rule packs, production freshness thresholds, and customer document fixtures;
- any claim of Strict OOXML mutation support or production readiness.

The next phase must consume these frozen records, governance decisions, and ports. It must not import legacy mutation behavior as architecture authority or change Contract v0.1.0 semantics to simplify implementation.
