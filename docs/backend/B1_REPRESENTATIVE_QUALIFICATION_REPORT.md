# B1.2R Representative Qualification Report

Date: 2026-09-08. Branch: `qualification/backend-b1-representative`.
Starting/accepted B1 commit: `14d9121848c3abca447d6f910cdb5f032ef45b97`.
The accepted commit and inspected origin/master are ancestors of this work.

## Current evidence outcome

**CORPUS_NOT_PROVIDED. Decision: INSUFFICIENT_EVIDENCE.**

`FOUNDATION_B1_PRIVATE_CORPUS_DIR` was not configured. The actual representative
CLI was executed and produced zero case results. No representative binary,
manifest, hash, semantic export or reviewer record was supplied or published.
Docling remains **PROVISIONAL_CONTINUE**, candidate **2.126.0** with the unchanged
accepted dependency profile. Foundation Contract v0.1.0 is unchanged.

| Representative evidence | Result |
| --- | --- |
| Real cases evaluated | 0 |
| DOCX workflow coverage | NOT_EVALUATED |
| XLSX workflow coverage | NOT_EVALUATED |
| Narrative, hierarchy and table fidelity | NOT_EVALUATED |
| Business-relevant structure | NOT_EVALUATED |
| Semantic / critical semantic loss | NOT_EVALUATED |
| Native identity loss | NOT_EVALUATED |
| Failure transparency on representative files | NOT_EVALUATED |
| Representative three-run repeatability | NOT_EVALUATED |
| Representative input pre/post hash equality | NOT_EVALUATED |
| Human/SME review | No reviews supplied; required review remains open |

No claim is made about any real client, entity, financial value or document.
All 23 desired feature categories remain unevaluated. Q1–Q6 and Q9 about real
content/structures/failures remain unanswered by actual corpus evidence. For
Q7–Q8, the accepted semantic/native authority separation is preserved, but no
representative loss classification has been made. Q10 yields INSUFFICIENT_EVIDENCE.

## Harness implemented

The runner reuses B1.1 preflight, immutable DocumentVersion content checks and
the B1.2A probe, without changing their behavior. It retains three same-input
runs and compares conversion/content/structure/tables/ordering/references
separately. Automated presence observations, reviewer dimensions, loss
classifications and qualification recommendations remain distinct.

The closed evaluation manifest uses opaque case IDs and versioned fixed enums.
Approval to evaluate a case is separate from completed fidelity review. Reviews
bind to the private input and stable observation hashes. Unreviewed/stale,
uncovered, changed or unresolved evidence cannot produce a forward recommendation.
Native-only loss is not automatically a reason to reject Docling.

No production SemanticObject mapping, NativeLocator, NativeBinding, AI, business
mapping, writeback or replay was added. This is an evaluation harness, not an
orchestration or authenticated approval service.

## Privacy and evidence locations

The external corpus directory must be explicitly configured and remain outside
the repository. Local metadata is confined to the exact ignored
`.foundation-private/` directory. The CLI checks Git ignores/index boundaries,
resolved input/output paths and existing report files. No corpus copy is made.

Private evidence location reserved for a later approved run:
`.foundation-private/b1-representative/reports/<new-run-id>/full.json`.
No private full report was created for the absent-corpus run.

Actual safe public output:
`qualification/b1/representative/reports/representative-summary.json`.
It records no cases, no paths, no source names, no document hashes, no excerpts
and no financial values. Public summaries are built from an allowlist rather
than redacting raw exports. Python prints are captured privately; logging and
native stdout/stderr are suppressed inside serial engine evaluation.

The bounded privacy guard checks Git tracked/index paths, not document contents.
It cannot identify private content renamed outside reserved/configured paths;
manual staged-file inspection is still required. The private directory is not
an encryption or access-control mechanism. No private CI artifact is configured.

## Engineering validation evidence

These are **synthetic harness tests**, not representative qualification cases.
Two accepted synthetic inputs (DOCX basic and XLSX basic) exercise the actual
reused engines, three conversions per input. Temporary malformed/boundary/review
data test failure and privacy paths. They are not counted as real cases.

Local Python: `.venv/b1/Scripts/python.exe`, with
`FOUNDATION_B1_REQUIRE_DOCLING=1` for tests. Candidate versions unchanged.

| Command | Observed result |
| --- | --- |
| `python tools/contracts/validate_contract_fixtures.py --report contract-validation-report.json` | OpenAPI PASS; 8/8 frozen scenarios PASS |
| `python -m unittest discover -s tests/contracts -v` | 23 passed |
| `python -m pytest tests/backend -q` | 158 passed; zero skipped |
| `python -m pytest tests/golden -q` | 5 passed; zero skipped |
| `python -m pytest tests/backend/b1/representative tests/backend/b1/privacy -q` | 34 passed; zero skipped |
| `python -m pip check` | No broken requirements |
| `python tools/b1/verify_private_corpus_boundary.py` | PASS |
| `python -m compileall -q foundation/evaluation/perception/representative.py tools/b1/representative_probe.py tools/b1/verify_private_corpus_boundary.py tests/backend/b1/representative tests/backend/b1/privacy` | PASS |
| `git diff --check` | PASS |

The accepted backend baseline has 124 tests; 34 new harness/privacy tests bring
it to 158. All five Golden tests remain unchanged and pass. There are no reduced
pass counts or skipped B1 Docling cases. Frozen contract/fixtures, ADRs, accepted
preflight/probe logic, domain/governance code and dependency pins have no diff.

Tests prove private/full versus public separation, no public filename/path/text/
hash leakage in tested projections, duplicate/stale review rejection, missing
corpus behavior, exact-byte before/after equality, mutation detection, symlink
boundaries, private report preservation and forced-staging detection. The actual
absence result was generated through the documented CLI rather than hand-filled.

## Files and CI scope

Created: this report and the representative corpus plan; public README, manifest
schema, inert corpus/review examples and absent-corpus JSON summary; representative
evaluation module; representative CLI and Git privacy guard; representative and
privacy tests.

Modified: `.gitignore` with the exact private-directory rule and the B1 workflow
with qualification-branch/schema triggers and the bounded Git privacy check.
The B1 workflow still installs the exact candidate and runs all accepted checks.
Its upload paths still contain only the three accepted synthetic/contract reports.
Public CI never requests a private corpus or executes the representative CLI.
The B0 and frozen-contract workflows are unchanged.

## Remaining risks and next decision

The harness passes its engineering checks. Actual B1.2R qualification has not
occurred. Approved representative files, selection/coverage rationale and complete
SME reviews are required next. Existing bounded preflight coverage, public API/
packaging decisions, production resource handling, complex tables/visuals and
native enrichment remain open. Do not begin B1.2B or B1.3 from these test results.

Run instructions and the exact private CLI are in
`qualification/b1/representative/README.md`. Use a new private report path for
each run and inspect the sanitized summary before publishing it.

**B1.2R harness complete; representative qualification remains
INSUFFICIENT_EVIDENCE pending approved private corpus.**
