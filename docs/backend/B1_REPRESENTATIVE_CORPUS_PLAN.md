# B1.2R Representative Local File Corpus Plan

Architecture: Foundation v2. Frozen contract: 0.1.0, unchanged.
Non-contract representative evaluation schema: 1.1.0.
Accepted B1 baseline: `14d9121848c3abca447d6f910cdb5f032ef45b97` (PR #5).
Work branch: `qualification/backend-b1-representative`.

## 1. Objective

Determine what the accepted provisional perception candidate preserves,
normalizes, loses or cannot interpret in approved representative Local File
documents. This phase supplies evidence for the next decision; it does not
implement a production adapter, native identity, binding, mapping or replay.

## 2. Business reason

Downstream interpretation requires meaningful narrative, distinguishable
sections, accurate table content and explicit limitations. A successful
conversion or repeatable signature cannot establish that business information
survives. Required fidelity judgments therefore belong to the human/SME review.

## 3. What B1.2A established

The pinned `docling-slim[format-docx,format-xlsx]==2.126.0` profile, including the
accepted explicit `pypdfium2==5.13.0` supplement, processes the accepted synthetic
corpus. Three-run observations and Windows/Ubuntu evidence exist. B1.1 provides
exact-byte preflight, explicit protections and unqualified capabilities. B1.2R
reuses these mechanisms and does not upgrade their dependencies.

## 4. What B1.2A did not establish

Representative content fidelity, Local File business accuracy, production
determinism and operational readiness remain open. Semantic references are not
NativeLocators. Readable native structures and stable semantic IDs do not grant
execution authority. Docling technology status remains PROVISIONAL_CONTINUE.

## 5. Corpus selection strategy

Aim initially for 5–10 approved cases selected for meaningful feature coverage,
not to satisfy a count. A smaller collection cannot silently claim broader
coverage: an identified reviewer must document the chosen scope and its limits
in the private coverage review. No business acceptance threshold is invented.

| Desired profile | Questions / private review focus |
| --- | --- |
| Narrative-heavy DOCX | Required narrative, headings, sections and repeated regions |
| Table-heavy DOCX | Boundaries, shape, content and interpretation |
| DOCX controls and document furniture | Headers/footers, fields, hyperlinks, bookmarks, content controls |
| DOCX visual structures | Images, drawings and organisation-chart meaning |
| Multi-sheet XLSX | Sheet context, cells, displayed/cached values and cross-sheet context |
| Formula-heavy XLSX | Formula versus cached value; information required by native enrichment |
| XLSX native structures | Tables, names, merges, hidden rows/columns and protection |
| XLSX visual structures | Charts, images, drawings and their business relevance |

Absent profiles stay NOT_EVALUATED. `required_profiles` defines intended scope,
not evidence. A required profile is evaluated only when an EVALUATED case has a
valid, current, bound review and explicit feature evidence other than
NOT_EVALUATED. FAIL, PARTIAL and UNSUPPORTED mean evaluated coverage with adverse
quality; they cannot create a forward recommendation merely by closing coverage.
A completed scope-bound private coverage review is also necessary.
Approval for evaluation is distinct from fidelity
review and never authorizes mutation. Synthetic test inputs are not corpus cases.

## 6. Privacy model

The repository is public. Corpus binaries remain outside it, under the explicitly
configured `FOUNDATION_B1_PRIVATE_CORPUS_DIR`. Corpus roots inside the repository
or containing the repository are rejected; resolved input paths must stay inside
that external root. No recursive corpus discovery/copy is performed.

Only the exact `.foundation-private/` ignore rule is added. Local manifest and
full reports live there, separate from the external binaries. The CLI verifies
Git ignores and the index boundary before reading a manifest. Symlink escapes,
private/public output swaps and reuse of an existing private report filename
are refused. Private evidence is never uploaded by CI.

The bounded Git guard rejects tracked/staged paths under `.foundation-private/`,
`private-corpus/`, `b1-private-corpus/`, and a configured private path inside the
repository. It does not inspect document contents or print filenames. It cannot
detect confidential material deliberately renamed to an unrelated public path;
manual index review before every commit remains necessary. It is not a DLP system.

## 7. Evaluation dimensions

| Dimension | Automated observation | Required reviewer judgment |
| --- | --- | --- |
| CONTENT_FIDELITY | Text/table output retained privately | Required content retained accurately? |
| STRUCTURE_FIDELITY | Hierarchy and ordering | Sections distinguishable and correctly grouped? |
| TABLE_FIDELITY | Tables/cells/shapes | Boundaries and business meaning preserved? |
| BUSINESS_RELEVANT_STRUCTURE | Expected profile presence | Required business regions distinguishable? |
| SEMANTIC_LOSS | Raw output and explicit missing checks | Meaning-bearing omissions/normalization? |
| NATIVE_IDENTITY_LOSS | Preflight versus perception observations | Native-required or semantic-required loss? |
| FAILURE_TRANSPARENCY | Conversion errors, preflight outcomes and unknown checks | Limitations sufficiently explicit? |
| REPEATABILITY | Three runs: conversion, content, hierarchy, tables, ordering, literal refs | Interpret significance of observed differences |

Automated feature presence uses existing B1.1 findings and Docling collections.
OBSERVED is presence only. NOT_OBSERVED is not proof of native absence.
Unimplemented comparisons remain NOT_EVALUATED. No additional semantic parser,
fuzzy matching or LLM fills gaps. In particular, hidden ranges, chart meaning,
formula/cached-value correctness, cross-sheet context, repeated sections and
organisation charts require private review or later qualified native inspection.

## 8. Reviewer process

Use the public inert review template only as a template; complete it privately
after reading the actual input and private evidence. Every completed case review
records reviewer identity, timestamp, exact input SHA-256 and observation digest.
The digest pins engine/configuration and stable observations, excluding elapsed
time. A changed input or observation invalidates review reuse.

All seven human dimensions must have truthful statuses. Status vocabulary is
PASS, PARTIAL, FAIL, UNSUPPORTED, NOT_EVALUATED, REVIEW_REQUIRED and NOT_APPLICABLE.
TABLE_FIDELITY is applicable exactly when TABLES is declared for the case. When
TABLES is absent it must be NOT_APPLICABLE; even PASS is rejected. All other
dimensions remain applicable. An applicable dimension cannot be NOT_EVALUATED,
REVIEW_REQUIRED or NOT_APPLICABLE in a valid completed review. Qualification
quality checks evaluate only applicable dimensions.

Every declared feature must appear exactly once in `review.feature_evidence`,
with no undeclared keys. Each entry has status PASS, PARTIAL, FAIL, UNSUPPORTED
or NOT_EVALUATED and evidence_basis AUTOMATED, HUMAN or BOTH. A human's bound
review may record evaluated fidelity even when automation is NOT_EVALUATED.
AUTOMATED currently means presence/structural observation only; it is not
independent fidelity authority. An AUTOMATED basis may only record NOT_EVALUATED
for fidelity status until an automated fidelity mechanism is separately qualified;
no such mechanism exists in B1.2R today. BOTH means human fidelity judgment
supported by an actual automated presence observation (OBSERVED or NOT_OBSERVED);
NOT_EVALUATED alone is not sufficient automated support for a BOTH claim.
Presence alone never supplies fidelity. Missing/stale/invalid
feature review grants no evaluated coverage; explicit NOT_EVALUATED remains an
honest unevaluated result even in an otherwise valid review.

Narrative notes and loss descriptions remain private.
Classifications are SEMANTIC_REQUIRED, NATIVE_REQUIRED, OPTIONAL or UNKNOWN.

CRITICAL_SEMANTIC_LOSS requires reviewer evidence that business-required meaning
is absent/materially corrupted and cannot reasonably be recovered by the planned
Native Identity layer. A native tag or cell address alone is not such a loss.
The manifest rejects inconsistent critical/native-recoverable classifications
from completed decision eligibility. Review files are local SME assertions;
this harness is not an authenticated review or approval service.

## 9. Evidence model

Private reports retain manifest, hashes, before/after integrity, preflight and
artifact bytes, three raw semantic exports, repeatability, feature observations,
review data and diagnostics separately. Input binaries are never saved by the
harness. Each private report uses a new filename; prior evidence is preserved.

Public projection constructs only allowlisted enums, opaque case IDs and safe
boolean/status results. It never copies paths, filenames, document hashes,
content, financial values, raw exports, reviewer identity or notes. Third-party
Python diagnostic output is captured privately; logging and native stdout/stderr
are suppressed during the serial engine call. Do not use this global output
suppression in a concurrent application server.

The JSON manifest is non-contract evaluation schema 1.1.0. The scope digest hashes
compact, sorted-key UTF-8 JSON with SHA-256 lowercase hex. It includes only
evaluation_version, sorted required_profiles and cases sorted by case_id, each
with case_id, format, document_role and sorted expected_feature_profile.
Ordering changes do not affect it. It excludes paths, input hashes, reviewer
identity/notes and source content. Case reviews still bind actual input hashes
and observation digests separately.

Completed coverage review must contain `scope_digest` matching the current scope.
Changing required profiles, selection, IDs, formats, roles or expected profiles
invalidates the old approval. Result scope must also match reviewed scope. The
helper never updates a review or silently replaces an approved digest. Reviewers
must approve a new digest after scope changes. This digest is not published in
the public summary. Public `unevaluated_profiles` uses actual feature-review
coverage, preserving failed quality as evaluated but unqualified evidence.

Frozen models are reused
for DocumentVersion and DocumentPreflightAssessment, without new fields. Public
CI tests only synthetic harness inputs and never invokes private evaluation.

## 10. Decision rules

No weighted score or confidence threshold is used.

- INSUFFICIENT_EVIDENCE: absent corpus, incomplete/stale reviews, incomplete
  feature evidence, stale scope approval, incomplete coverage, changed input,
  unresolved critical loss, unknown/semantic-required losses, adverse feature
  quality, failed conversion or unresolved repeatability differences.
- RECONSIDER_DOCLING_BASELINE: complete bound reviews establish critical semantic
  losses on at least two distinct input hashes. Two IDs for one binary do not
  prove repeated representative failures. This is a conservative operational
  interpretation of repeated cases, not a production accuracy threshold.
- PROVISIONAL_COORDINATE_B1_2B_AND_B1_3: successful stable perception, complete
  coverage/reviews and adequate semantic dimensions, with classified native gaps.
- PROVISIONAL_CONTINUE_TO_B1_2B: successful stable perception, complete
  scope-bound coverage/reviews, PASS feature quality and applicable fidelity
  dimensions, and no unresolved material gaps.

These are recommendations for a later explicit decision. They do not promote
the engine or start deferred implementation. A changed recommendation does not
edit the accepted technology status automatically.

## 11. Known limitations

Actual corpus approval, storage access controls and SME expertise are supplied
externally. No authentic representative corpus or review has been provided in
this session. Existing preflight coverage remains bounded; full ECMA conformance,
rendering, formula recalculation and production resource handling remain open.
The private directory is Git-ignored, not encrypted by this tooling. Run locally
in an approved environment, without concurrent editing of corpus files.

## 12. Next decision gate

Complete harness validation now. Then supply the external corpus location and
approved private manifest, run read-only evaluation, complete the private SME
reviews and coverage rationale, rerun into a new private report path, and review
the sanitized summary before public publication. Until then the corpus status is
CORPUS_NOT_PROVIDED and the decision remains INSUFFICIENT_EVIDENCE.

Evaluation 1.0.0 manifests/reviews are not accepted as 1.1.0 evidence. Migration
requires explicit feature evidence, truthful applicability, a freshly approved
scope digest and case reviews bound to the new evaluation observation digest.
Do not relabel an old completed review automatically. Historical private reports
remain unchanged. Foundation Contract v0.1.0 and the B1.2A evaluation profile are
unaffected by this non-contract schema change.
