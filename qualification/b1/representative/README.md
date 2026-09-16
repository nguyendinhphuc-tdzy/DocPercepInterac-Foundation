# Representative B1 qualification — public specification only

## Evaluation v1.2.0 migration and Run-003 gate

Run-002 remains immutable historical evidence under evaluation schema 1.1.0.
Its private report, original manifest, provenance audit, review pack and public
summary are not migrated in place. The public summary remains Run-002 until a
separately authorized new immutable run completes.

New manifests and case reviews use evaluation schema 1.2.0. Each case requires:

| business_role | document_role |
| --- | --- |
| TARGET_TEMPLATE | TARGET |
| HISTORICAL_REFERENCE | REFERENCE |
| GOLDEN_EVALUATION_ONLY | REFERENCE |
| CURRENT_SOURCE | SOURCE |
| HISTORICAL_SOURCE | SOURCE |

Other combinations fail closed. These are qualification metadata, not execution
permissions. GOLDEN_EVALUATION_ONLY is an evaluation benchmark: never an
execution target, authoritative source, or historical mapping source.

The v1.2.0 coverage scope digest includes business_role alongside case ID,
format, document_role and expected_feature_profile. Paths, filenames, input
hashes and content remain excluded. Changing a role invalidates old coverage.
Public v1.2.0 output allowlists document_role_category and business_role_category.

Run-003 uses a NEW private manifest with the verified corrected FY2023 reference
and the Business Owner's five role mappings. Human reviews and coverage remain
PENDING; no old digest or review is approval for the corrected scope. Case
review_status is the distinct approval-for-evaluation gate; preparation leaves
it PENDING too until all run gates are accepted.

Measure and reassess all corrected inputs with the qualification-only profile.
Admission under existing limits yields PROFILE_REUSE_CANDIDATE, not acceptance.
Record profile acceptance separately before semantic execution. General preflight
defaults remain unchanged. Only after all gates pass may immutable Run-003 and
its own review pack/viewer be generated. Mechanical success never completes
SME or coverage review and never qualifies production.

This non-contract evolution follows clarified business workflow semantics, not
a Frozen Foundation Contract gap. No contract semantics change.

`corpus.schema.json` is evaluation version **1.2.0**, a closed Draft 2020-12
evaluation manifest schema, not a
Foundation domain contract. `corpus.example.json` and `review.example.json` are
inert templates containing no actual corpus values. Never fill them with private
information in this directory. The only versioned binaries remain synthetic.

## Qualification-only preflight profile

The B1.2R evaluator explicitly supplies the non-contract profile
`b1-representative-core-v1` to `OoxmlPreflight`. It uses these exact finite
limits:

| Limit | Value |
| --- | ---: |
| `max_package_bytes` | 3,004,377 |
| `max_uncompressed_bytes` | 22,302,224 |
| `max_part_bytes` | 17,856,208 |
| `max_parts` | 132 |
| `max_xml_elements` | 796,703 |

The general Foundation defaults are unchanged. Only the part and XML-element
limits exceed those defaults; the other three values deliberately narrow the
qualification envelope. The profile has zero numeric headroom and was calibrated
for the approved immutable CORE corpus. Any corpus binary or reviewed-scope
change requires recalibration.

The profile does not establish production capacity, general Office support,
semantic fidelity, native identity, mutation capability or business sufficiency.
Its numeric values are not a cryptographic corpus binding. Private evidence
records the profile ID and exact preflight `configuration_ref`, and both
participate in the observation digest bound by review. Input hashes and the
coverage scope digest retain their separate identity roles. The public summary
does not expose the profile ID or configuration reference.

Approved actual binaries must be outside the Git repository. Set
`FOUNDATION_B1_PRIVATE_CORPUS_DIR` to that existing private directory in your local
environment. Do not echo its value to public logs. Resolve filenames privately
in `.foundation-private/b1-representative/manifest.local.json`. Paths in the
manifest are relative to the external root, or absolute inside it. The root may
not be the repository or an ancestor of it.

Use the already pinned B1 Python 3.12 environment. Do not upgrade dependencies.
From the repository root, the exact private run command is:

```powershell
python tools/b1/representative_probe.py `
  --manifest .foundation-private/b1-representative/manifest.local.json `
  --private-report .foundation-private/b1-representative/reports/run-001/full.json `
  --public-summary qualification/b1/representative/reports/representative-summary.json
```

Private output paths must be Git-ignored and must not already exist. Use run-002
for a subsequent run; do not overwrite a prior full report. The public summary
contains only safe status/profile information and may replace its previous
snapshot. An exit code of zero means a report was produced, not qualification
approval. Read `corpus_status` and `decision`.

When the environment variable is absent, the runner does not read the manifest
or create fake case evidence. It writes a public summary with no cases,
CORPUS_NOT_PROVIDED and INSUFFICIENT_EVIDENCE. A configured but missing corpus
directory, unsafe path or invalid manifest produces a fixed safe refusal and
nonzero exit; no exception text or input filename is printed.

## Private review workflow

1. Select approximately 5–10 approved representative cases where available. Use
   LF-DOCX-001 / LF-XLSX-001 style opaque IDs, unrelated to client identity.
2. Declare required profiles and set each approved case to
   APPROVED_FOR_EVALUATION. A PENDING case is not read. Missing inputs stay
   NOT_EVALUATED and block a forward recommendation.
3. Run to create private preflight, semantic output and three-run observations.
4. Compare input and output privately. Copy the review template into each private
   case's optional `review` field. Bind the exact input_sha256 and
   observation_digest from that case's full report. Record actual reviewer/time,
   dimensions and loss descriptions. No raw excerpt is required in public output.
5. Complete coverage_review with reviewer identity, rationale and scope_digest
   for the selected scope. Compute the candidate scope digest locally using
   `coverage_scope_digest(manifest)` from
   `foundation.evaluation.perception.representative`; copy it only when the
   reviewer approves that exact scope. The helper does not update approval.
   Required profiles without valid feature-level evidence block a forward
   recommendation even if their names are declared in the manifest.
6. Rerun into a new private path. The stable observation digest excludes elapsed
   time; changed evidence cannot reuse a completed review. Review the allowlisted
   public summary before staging it.

Human dimensions: CONTENT_FIDELITY, STRUCTURE_FIDELITY, TABLE_FIDELITY,
BUSINESS_RELEVANT_STRUCTURE, SEMANTIC_LOSS, NATIVE_IDENTITY_LOSS and
FAILURE_TRANSPARENCY. Values: PASS, PARTIAL, FAIL, UNSUPPORTED, NOT_EVALUATED,
REVIEW_REQUIRED, NOT_APPLICABLE. TABLE_FIDELITY is applicable exactly when TABLES
is in expected_feature_profile. Otherwise it must be NOT_APPLICABLE, never a
placeholder PASS. All other dimensions remain applicable. Applicable dimensions
cannot be NOT_APPLICABLE, NOT_EVALUATED or REVIEW_REQUIRED in a completed review.
Loss classes: SEMANTIC_REQUIRED, NATIVE_REQUIRED, OPTIONAL,
UNKNOWN. A critical loss must be semantic-required and not recoverable through
Native Identity. Reviews are local SME evidence, not authenticated authorization.

Automatic feature-presence values: OBSERVED, NOT_OBSERVED, NOT_EVALUATED.
They do not establish fidelity. Case execution values: EVALUATED, FAILED,
NOT_EVALUATED. Repeatability compares conversion, content, structure, tables,
ordering and references separately: PASS, OBSERVED_LIMITATION, NOT_EVALUATED.
All values describe qualification observations, never native execution support.

## Feature evidence and scope binding (1.2.0)

Every declared profile must have a corresponding `review.feature_evidence` entry;
undeclared keys are rejected. The inert review template corresponds to the
NARRATIVE/TABLES example scope. Adjust it privately for the actual declared scope.

```json
{
  "CHARTS": {
    "status": "NOT_EVALUATED",
    "evidence_basis": "HUMAN"
  }
}
```

Feature statuses are closed: PASS, PARTIAL, FAIL, UNSUPPORTED, NOT_EVALUATED.
Basis is AUTOMATED, HUMAN or BOTH. HUMAN means the reviewer actually compared
private source and output; automation need not implement the feature. AUTOMATED
currently means presence/structural observation only; it is NOT independent
fidelity authority. An AUTOMATED basis may only record NOT_EVALUATED for fidelity
status until an automated fidelity mechanism is separately qualified. No such
mechanism exists in B1.2R today. BOTH means human fidelity judgment supported
by an actual automated presence observation (OBSERVED or NOT_OBSERVED);
NOT_EVALUATED alone is not sufficient automated support for a BOTH claim.
Presence is not fidelity. A FAIL result supplies evaluated coverage but fails
quality. Public feature evidence is projected only from valid bound reviews;
private notes, identifiers and hashes are never included.

Coverage uses EVALUATED cases with current valid reviews and feature statuses
other than NOT_EVALUATED. `unevaluated_profiles` uses the same rule across the
feature vocabulary; declarations alone cannot remove profiles from that list.
All declared feature qualities must PASS for a forward recommendation; unresolved
PARTIAL, FAIL, UNSUPPORTED or NOT_EVALUATED results remain conservative blockers.

`coverage_review.scope_digest` is SHA-256 lowercase hex over compact sorted-key
UTF-8 JSON containing evaluation_version, sorted required_profiles, and cases
sorted by case_id. Each case includes only case_id, format, document_role, business_role and
sorted expected_feature_profile. Array ordering has no scope meaning. Paths,
filenames, reviewer notes, actual input hashes and source text are excluded.
Input and observation integrity remain separate case-review bindings.

Changing any included field requires renewed scope review. An old approved
digest is never recalculated automatically, and result case scope must match
the reviewed manifest scope. The public summary does not expose this digest.

Historical migration from 1.0.0 to 1.1.0 used versioned templates to populate
feature evidence, apply the dimension rules, approve the scope digest and bind
the case review to that evaluation observation digest. Preserve old private
reports. This does not change Foundation Contract v0.1.0, Docling's version or
the accepted synthetic B1.2A evaluation schema.

## Engineering tests and public CI

```powershell
$env:FOUNDATION_B1_REQUIRE_DOCLING = '1'
python -m pytest tests/backend/b1/representative tests/backend/b1/privacy -q
python tools/b1/verify_private_corpus_boundary.py
```

These tests use synthetic temporary inputs only. CI does not require a private
corpus or run the representative CLI. Its existing upload allowlist contains
only synthetic B1 and contract reports, never `.foundation-private/` or these
private run outputs. The Git guard checks tracked/index paths, including forced
staging of ignored content, without reading or printing document contents.

Before committing, run the guard and privately inspect `git status`,
`git diff --cached --name-only` and `git ls-files`. The guard cannot recognize
confidential material renamed into arbitrary unrelated directories. If private
content is staged, stop and unstage it; do not commit or rewrite Git history.

See `docs/backend/B1_REPRESENTATIVE_CORPUS_PLAN.md` for decision rules, coverage
questions and deferred B1.2B/B1.3 boundaries. Synthetic test results cannot be
published as representative Local File qualification evidence.
