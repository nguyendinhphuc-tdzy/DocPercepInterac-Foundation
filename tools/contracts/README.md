# Foundation contract tooling

This package validates architecture fixtures; it does not implement Foundation
services, perception, replay or native Office validation. The fixture binaries,
external observations and qualification artifacts remain illustrative.

Use Python 3.12 in an isolated environment. Local validation and GitHub Actions
install the same complete dependency lock:

```shell
python -m pip install --disable-pip-version-check -r tools/contracts/requirements.txt
python tools/contracts/validate_contract_fixtures.py --report contract-validation-report.json
python -m unittest discover -s tests/contracts -v
```

The fixture command also validates OpenAPI 3.1. CI runs that OpenAPI check
separately for diagnosis, then runs the fixture command even if the separate
check failed. Report upload always runs and a missing artifact is an error.

## Authority and schema resolution

The baseline, ADRs and Markdown contracts define semantics. OpenAPI projects
object fields, required properties, types, enums and closed unions. The validator
loads that projection and relocates its component schemas once into an in-memory
Draft 2020-12 `$defs` root. Component selection is a `$ref` on that same root.
Referenced schemas are not inlined or duplicated. All closure keywords, including
`additionalProperties` and `unevaluatedProperties`, are retained. Broken or
unsupported external schema pointers fail closed. No deprecated resolver is used.

Fixture validity does not read Markdown. The separate projection-drift tests
compare semantic registries and union vocabulary with OpenAPI, and check Markdown
fences. A documentation-format failure in those tests does not change a fixture's
machine-validation result.

The validator owns cross-record semantic checks: immutable reference identity,
causation, lifecycle transitions, authorization eligibility, source and evidence
gates, independent validation and aggregate release. Tests corrupt copies in
temporary directories; they never rewrite the eight canonical fixtures.

## Report dimensions

| Category | Result field | Responsibility |
| --- | --- | --- |
| SCHEMA | schema_result | YAML and fixture envelope, canonical fields, required properties, enums and typed unions from OpenAPI. |
| REFERENCE | reference_result | Pinned record/artifact resolution, binary-bound DocumentVersionRef consistency and duplicate identities. |
| STATE_MACHINE | state_machine_result | Immutable revision sequence and legal lifecycle/release edges. |
| GOVERNANCE | governance_result | Actors, causation, material event coverage, sealed approval, replay, evidence and independent validation/release gates. |
| HASH | hash_result | RFC 8785 canonical payloads, UTF-8, SHA-256 and lowercase hexadecimal comparison. |
| BEHAVIOR | behavior_result | Expected scenario assertions checked against actual records/events; expected values cannot waive governance. |
| VALIDATOR_INTERNAL | validator_internal_result | Unexpected tooling exceptions, isolated per stage and fixture. |
| OVERALL | overall_result | PASS only if every dimension passes. |

A dependent dimension is `NOT_EVALUATED` when malformed input prevents a valid
evaluation; it is never reported as PASS. Unexpected exceptions fail the affected
dimension and `VALIDATOR_INTERNAL`, while remaining fixtures still run. The report
is written before the command returns a failure status. Missing expected fixtures
receive failure rows. Failure to write to an inaccessible report destination is
an operating-system error, not successful validation.

The report records tooling versions, environment, input hashes and checked/passed
hash counts. Its local overall PASS is not a freeze declaration: GitHub Actions
must also pass for the corrected commit. No native-engine qualification claim
can be inferred from fixture success.
