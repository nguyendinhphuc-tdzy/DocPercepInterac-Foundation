# Foundation v2 Backend B0 Implementation Report

**Architecture generation:** Foundation v2  
**Frozen contract schema:** 0.1.0  
**Implementation branch:** `build/backend-foundation-v2`  
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
| `python -m pytest tests/backend -q` | PASS: 38 tests. |
| `python -m pytest tests/golden -q` | PASS: 2 tests. |
| `python -m foundation.evaluation.golden tests/golden/corpus_manifest.yaml tests/golden/reports/b0-synthetic-report.json` | PASS: 1/1 synthetic cases; no qualification claim. |
| `python -m compileall -q foundation/governance foundation/audit foundation/ports foundation/evaluation tests/backend tests/golden` | PASS. |
| `git diff --check` | PASS. |

The ambient Python environment did not contain the contract validator's pinned `openapi-spec-validator` package. Contract validation and contract unit tests therefore use the repository's `.venv-contracts` environment, matching the established contract-tooling dependency set. Backend runtime tests use the dependencies pinned in `foundation/requirements.txt`.

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
