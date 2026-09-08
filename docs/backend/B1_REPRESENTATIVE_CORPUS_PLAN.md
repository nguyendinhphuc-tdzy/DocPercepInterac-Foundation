# B1.2R Representative Local File Corpus Plan

Architecture: Foundation v2. Frozen contract: 0.1.0, unchanged.
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

Absent profiles stay NOT_EVALUATED. `required_profiles` defines the intended
scope before evaluation; a completed private coverage review is necessary for
any forward recommendation. Approval for evaluation is distinct from fidelity
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

All seven human dimensions must be evaluated. Status vocabulary is PASS,
PARTIAL, FAIL, UNSUPPORTED, NOT_EVALUATED and REVIEW_REQUIRED. The latter two
prevent completion. Narrative notes and loss descriptions remain private.
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

The JSON manifest is a non-contract evaluation schema. Frozen models are reused
for DocumentVersion and DocumentPreflightAssessment, without new fields. Public
CI tests only synthetic harness inputs and never invokes private evaluation.

## 10. Decision rules

No weighted score or confidence threshold is used.

- INSUFFICIENT_EVIDENCE: absent corpus, incomplete/stale reviews, incomplete
  coverage, changed input, unresolved critical loss, unknown/semantic-required
  losses, failed conversion or unresolved repeatability differences.
- RECONSIDER_DOCLING_BASELINE: complete bound reviews establish critical semantic
  losses on at least two distinct input hashes. Two IDs for one binary do not
  prove repeated representative failures. This is a conservative operational
  interpretation of repeated cases, not a production accuracy threshold.
- PROVISIONAL_COORDINATE_B1_2B_AND_B1_3: successful stable perception, complete
  coverage/reviews and adequate semantic dimensions, with classified native gaps.
- PROVISIONAL_CONTINUE_TO_B1_2B: successful stable perception, complete
  coverage/reviews, PASS fidelity dimensions and no unresolved material gaps.

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
