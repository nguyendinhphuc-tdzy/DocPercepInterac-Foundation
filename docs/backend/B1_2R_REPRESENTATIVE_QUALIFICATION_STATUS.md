# B1.2R REMAINS OPEN — SME REVIEW REQUIRED

## Run-003 mechanical execution — 2026-09-16

RUN003_CODE_BASELINE: `ff479464a117992d628b066631bb3770c19b7c1f`.
The preparation commit was pushed to `qualification/backend-b1-representative-run2`
and the working tree was clean before execution.

The Business Owner / qualification reviewer explicitly accepted reuse of
`b1-representative-core-v1`: **ACCEPTED_FOR_CORRECTED_RUN003_CORPUS**.
Acceptance is qualification-only, bounded to the exact corrected five-case
corpus, and non-production. All five inputs completed preflight within existing
finite limits; no numeric limits, general defaults or dependency pins changed.
The corrected historical reference was verified. This acceptance is not general
Local File capacity, semantic fidelity, replay or future corpus authorization.

The new immutable private Run-003 report uses representative evaluation schema
1.2.0 and the approved pinned Docling environment. Its separate
[sanitized Run-003 summary](../../qualification/b1/representative/reports/representative-run-003-summary.json)
is the exact harness projection. Run-002 reports, original manifest, provenance
audit, review pack and viewer remain byte-for-byte unchanged.

| Evidence | Run-003 result |
| --- | --- |
| Cases | Five evaluated: three DOCX and two XLSX |
| Preflight | COMPLETED, 5/5 |
| Semantic conversion | PASS, 15/15 (three per case) |
| Input integrity | PASS, 5/5 |
| Repeatability | PASS for conversion, content, structure, tables, ordering and references |
| Human review | REVIEW_REQUIRED for all five cases; no completed SME judgments |
| Coverage review | PENDING; bound to the corrected scope, including business roles |
| Decision | INSUFFICIENT_EVIDENCE |
| Technology status | PROVISIONAL_CONTINUE |
| production_qualified | false |

| Case | Document role | Business role |
| --- | --- | --- |
| LF-DOCX-001 | TARGET | TARGET_TEMPLATE |
| LF-DOCX-003 | REFERENCE | GOLDEN_EVALUATION_ONLY |
| LF-DOCX-004 | REFERENCE | HISTORICAL_REFERENCE |
| LF-XLSX-001 | SOURCE | HISTORICAL_SOURCE |
| LF-XLSX-002 | SOURCE | CURRENT_SOURCE |

A new private review pack contains five worksheets bound to the exact input,
observation, evaluation version, business role and feature profile. Its separate
read-only viewer displays retained semantic observations, original-document
links, role-specific guidance and the Golden evaluation-only warning. No source
information was reconstructed to repair perception. Human identity, time,
judgments and coverage approval remain unfilled. Evaluation admission does not
constitute human fidelity review.

Post-run validation: 119 representative/privacy tests, 340 backend/Golden tests,
23 contract tests and all eight contract fixtures passed; OpenAPI validation,
private boundary guard and diff whitespace check passed. Frozen Contract remains
unchanged and no private files are tracked. Static viewer checks cover retained
text, tables, sheet groups, picture placeholders, role guidance and original
link targets. Browser visual rendering and native Office launch were not verified.

Next: authentic SME fidelity and coverage review against Run-003, followed by a
separately authorized immutable follow-up run using a reviewed manifest revision.
No Replay or GTPS mapping was started. Mechanical success, presence and
repeatability do not establish correctness or complete B1.2R.

## Historical preparation state before acceptance — 2026-09-16

The non-contract representative evaluation schema is now 1.2.0 for new runs.
It requires the closed business_role field, enforces its document_role pairing,
binds business_role into coverage scope, and allowlists both categories in new
public projections. This follows clarified workflow semantics, not a Frozen
Foundation Contract gap. Historical Run-002 remains 1.1.0 and is preserved.

The corrected five-case pending private manifest uses the Business Owner's
verified FY2023 historical reference. The Golden case is REFERENCE /
GOLDEN_EVALUATION_ONLY and must never serve as execution input or authority.
The original manifest, Run-002 report, public summary, provenance audit and
SME review pack have not been overwritten.

All five corrected binaries fit the existing finite b1-representative-core-v1
limits and complete preflight. Status: **PROFILE_REUSE_CANDIDATE** only.
Profile acceptance for this scope is still pending; no general defaults changed.
Run-003 semantic execution is **NOT AUTHORIZED / NOT EXECUTED** while this gate
is open. A new viewer will be generated only from actual Run-003 observations.
Human review and coverage remain pending; production_qualified remains false.

Validation: 119 representative/privacy tests passed (including 25 new role,
scope and projection checks); 340 backend/Golden tests passed; 23 contract
tests and all eight contract fixtures passed. Private boundary and pinned
dependency checks passed. No representative semantic run was performed.

## Preserved Run-002 status

Date: 2026-09-14. Foundation v2; Frozen Contract **0.1.0 unchanged**.
Run: **run-002**. Accepted repository baseline:
`f29e218976b597100eb8e056055df647f3ab7305`.

## Automated evidence

The existing harness ran without modification using pinned docling-slim 2.126.0,
non-contract evaluation schema 1.1.0 and the accepted representative-only
preflight profile. The approved manifest selection was not changed. Run-002 did
not exist before this run; the new private report is retained as immutable
evidence. Existing private reports and the original manifest were preserved.

| Evidence | Observed result |
| --- | --- |
| Corpus | AVAILABLE; five manifest cases, five approved, five evaluated |
| Format scope | Three DOCX; two XLSX |
| Preflight | COMPLETED for 5/5 |
| Conversion | PASS for 15/15; three per case |
| Input integrity | PASS for 5/5; before/after input hashes equal |
| Repeatability | PASS for conversion, content, structure, tables, ordering and references on all five cases |
| Required profiles | 18 declared; none has completed bound fidelity coverage |
| Human review | 0/5 valid completed reviews |
| Coverage review | PENDING; existing pending digest does not match current scope |
| Decision | INSUFFICIENT_EVIDENCE |
| Technology status | PROVISIONAL_CONTINUE |
| production_qualified | false |

The [sanitized harness summary](../../qualification/b1/representative/reports/representative-summary.json)
contains opaque case IDs and closed statuses only. It is generated by the
harness, not edited to improve outcomes. Scope declarations are not coverage.

Semantic presence observes narrative/tables in selected DOCX, hyperlinks in
the two cases declaring them, images in the cases declaring them, and multiple
sheets in both XLSX. Other semantic presence checks remain NOT_EVALUATED.
Organisation-chart meaning, cached values and cross-sheet context have no
implemented presence comparison on either side. Native presence findings do
not prove that their business meaning survived conversion. No reported
NOT_EVALUATED is interpreted as absence or loss.

## Human gate and next action

An inert private review package binds each of the five case IDs to its exact
input hash and stable observation digest, and supplies a freshly calculated
coverage-scope candidate. It leaves reviewer identity, review time and judgments
unfilled. The candidate digest is not coverage approval; the existing manifest
and report are not rewritten.

An actual SME must inspect the source and retained semantic exports, complete
CONTENT_FIDELITY, STRUCTURE_FIDELITY, TABLE_FIDELITY where applicable,
BUSINESS_RELEVANT_STRUCTURE, SEMANTIC_LOSS, NATIVE_IDENTITY_LOSS and
FAILURE_TRANSPARENCY, and record every declared feature's fidelity evidence.
Per harness, TABLE_FIDELITY applies to the three cases declaring TABLES; XLSX
cell/table business meaning still requires its other dimensions and profiles.

The SME must classify losses as SEMANTIC_REQUIRED, NATIVE_REQUIRED, OPTIONAL or
UNKNOWN and approve current coverage scope with actual identity and rationale.
Critical semantic loss and native-required loss counts are **UNASSESSED, not
zero**. Presence and repeatability are not correctness or business accuracy.

After authentic reviews, preserve the original manifest, create a reviewed
private manifest revision, and run the existing CLI into the first unused
immutable report path (prefer run-003). The harness must validate input,
observation and scope bindings before a scoped recommendation can close B1.2R.

B1.2B and B1.3 remain separate, explicitly authorized engineering gates. This
run does not start either, implement binding/replay, qualify production, or
complete B1. P0 synchronization and the five-target learning scope may proceed
without pretending the SME gate is closed.

## P0 handoff

See [project phase](../PROJECT_PHASE.md),
[working logic](../decisions/P0_BUSINESS_WORKING_LOGIC_2026-09-14.md), and
[vertical-slice scope](../implementation/FOUNDATION_VERTICAL_SLICE_SCOPE_v0.1.md).
All five targets are locked for learning; source authority, mandatory policy,
qualified operations and exact bindings remain open. No Frozen Contract, ADR,
runtime source, dependency pin or corpus binary changed.

## Local regression evidence

Pinned B1 Python 3.12 environment, `FOUNDATION_B1_REQUIRE_DOCLING=1` for B1 tests.
Synthetic tests below verify engineering behavior, not representative fidelity.

| Check | Result |
| --- | --- |
| Representative/privacy pytest suites | 94 passed, no skips |
| B1 preflight pytest suite | 117 passed |
| Full backend pytest suite | 310 passed, no skips |
| Golden pytest suite | 5 passed |
| OpenAPI command from contract CI | OpenAPI 3.1 PASS |
| Contract fixture validator | 8/8 PASS in all dimensions |
| Contract unittest suite | 23 passed |
| B1 boundary compilation | PASS |

The local contract validation report is retained privately; platform checkout
line endings change its input-byte hashes, so it does not replace the committed
historical report. Its runtime freeze field does not reopen the formal contract
freeze. Hosted CI is a separate publication check, not human fidelity review.
