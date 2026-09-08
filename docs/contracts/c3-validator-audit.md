# C3 validator infrastructure audit

**Audited commit:** `447d6e2bc813bf6efdf2bdc2816c2566981fd1ee`

**Contract schema:** 0.1.0. **Architecture:** Foundation v2.

**Freeze status:** NOT FROZEN; corrected-commit GitHub Actions evidence is pending.

The original workflow commands were reproduced with Python 3.12 and the pinned
tooling dependencies. OpenAPI validation passed. Fixture validation raised
`referencing.exceptions.PointerToNowhere` before completing the first fixture.
That exception did not establish that a fixture violated the contract.

## Root-cause evidence and corrections

| Affected file/scenario | Assertion and expected result | Observed result | Contract authority | Classification | Correction owner |
| --- | --- | --- | --- | --- | --- |
| Validator / first record in C2-01 | Resolve RecordEnvelope from the complete machine root; finish all fixtures. | Detached component root cannot resolve `/components/schemas/RecordEnvelope`; report is not written. | OpenAPI component references and Draft 2020-12 schema composition. | VALIDATOR_IMPLEMENTATION_ERROR | Validator: one `$defs` root, no deprecated RefResolver. |
| Validator / all scenarios | Keep dimension results independent and report exceptions. | Overall status copied into all result columns; uncaught exceptions abort processing. | C3 machine-validation and reporting requirements. | VALIDATOR_IMPLEMENTATION_ERROR | Validator: categorized stage errors, per-fixture isolation and mandatory report. |
| Validator / valid primitive values | Accept IDs, URIs and SHA-256 values matching OpenAPI. | Valid values fall through handwritten primitive dispatch to “unhandled contract type”. | domain-model.md reference/value contracts and matching OpenAPI schemas. | VALIDATOR_IMPLEMENTATION_ERROR | Validator: validate shapes through OpenAPI and retain separate reference resolution. |
| Validator / ordinary actions in C2-01–08 | Require no fuzzy replay; governance actions need no replay observations. | Actions without replay requests fail “fuzzy fallback must be explicitly false”. | FND-INV-LOC-002 and FND-INV-REPLAY-001. | VALIDATOR_IMPLEMENTATION_ERROR | Validator: require explicit false at replay dispatch and reject explicit fallback/overrides. |
| OpenAPI / C2-06 audit_events[35].metadata | Accept typed first_material_failure_event_id while retaining closed validation metadata. | OpenAPI rejects a field explicitly permitted by event-model.md. | event-model.md VALIDATION and REPLAY metadata tables. | OPENAPI_PROJECTION_ERROR | OpenAPI: project the existing optional ID on both metadata variants; keep additionalProperties false. |
| Validator / RFC 8785 numeric regression | Canonicalize 1.0 as 1 and 0.000001 in decimal notation. | Handwritten routine emits 1.0 and 1e-06. | domain-model.md Authorization digest canonicalization; event-model.md integrity rule. | HASH_CANONICALIZATION_ERROR | Tooling: pinned RFC 8785 library, tested numeric and UTF-16 ordering vectors. |
| Validator / corrupted temporary fixture copies | Reject duplicate immutable identities, AI dispatch, unreviewed payloads despite recomputed digests, and release with blocked required targets. | Those negative cases passed the previous checks. | FND-INV-AUD-001, AI-001, AUTH-002 and REL-001. | VALIDATOR_IMPLEMENTATION_ERROR | Validator: enforce those existing semantic invariants; retain negative regression tests. |

No `FIXTURE_ERROR` or `SEMANTIC_CONTRACT_ERROR` was established. No canonical
fixture, C1/C2 decision, enum vocabulary or mutation scope was changed. The first
completed infrastructure report exposed the projection/validator errors above;
corrections were made in their owning layers.

## Resolution and source authority

OpenAPI is the machine schema authority. The validator builds an ephemeral
Draft 2020-12 bundle without flattening references or removing closure keywords.
Fixture validation reads its enum values from OpenAPI. Markdown parsing is
confined to separate projection-drift/documentation tests.

Handwritten field/primitive dispatch was removed. Remaining checks express
cross-record semantic rules and fixture wrapper assertions, not a competing
schema definition for every domain object. The dependency lock includes direct
and transitive tooling versions; jsonschema remains 4.26.0.

## C2-02

The fixture already records the approved subset path:

```text
AWAITING_REVIEW -> BLOCKED -> READY_FOR_EXECUTION -> EXECUTING -> VALIDATING -> BLOCKED
```

The independent NCP subset executes and validates. The required arm's-length
conclusion stays blocked; whole-task release remains WITHHELD. The validator
also rejects a temporary negative copy that claims completion/release while
leaving that target blocked, even when its expected assertions agree.

## Validation evidence

The root `contract-validation-report.json` contains each scenario's separate
Schema, Refs, State, Governance, Hash, Behavior and Overall results, plus the
VALIDATOR_INTERNAL result, tool versions, environment and input hashes.

All eight unchanged fixtures pass locally. Eight authorization digests and 276
audit-event hashes verify without regeneration. OpenAPI 3.1 passes. Regression
tests exercise schema closure, unresolved references, exception/report handling,
negative governance cases and projection drift.

These are Windows/Python 3.12 local results using the CI dependency lock. The
Ubuntu GitHub Actions run for the corrected commit is still required before
declaring Foundation Contract v0.1 FROZEN. Fixture observations remain
illustrative; this audit does not qualify a native execution engine.
