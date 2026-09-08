# B1.2A Docling-slim Qualification Report

Evaluation date: 2026-09-08. Architecture: Foundation v2. Frozen contract: 0.1.0.
This report covers the isolated B1.2A spike, alongside B1.0 and B1.1.

## 1. Executive conclusion

**PROVISIONAL_CONTINUE.** Three successful synthetic Office cases preserve useful
text and table structure across three identical-input conversions each. A fourth,
malformed case fails explicitly on all three runs. The tested outputs support
further qualification; they do not establish production Local File suitability.

Synthetic qualification evidence only; representative Local File corpus gate remains open.

Docling-slim technology qualification = PROVISIONAL. B1.2A cannot promote Docling
to production qualification by itself. B1.2B requires a later explicit instruction.

## 2. Candidate evaluated

The published `docling-slim` package, using its public Word and Excel declarative
backend APIs. No source was cloned, copied, patched or vendored. The package
profile is described by the [official release](https://pypi.org/project/docling-slim/2.126.0/).
The locally installed package and the actual conversions are the evidence for
the findings below; upstream support claims are not qualification evidence.

## 3. Candidate exact version

`importlib.metadata.version("docling-slim")` returned **2.126.0**.
`docling-core` resolved to **2.95.0**. Local Python was **3.12.14**, Windows.
The report records all installed package versions. A mismatched or missing
candidate is an infrastructure failure, not a passing negative conversion case.

## 4. Installation profile

An isolated `.venv/b1` contains:

```text
docling-slim[format-docx,format-xlsx]==2.126.0
pypdfium2==5.13.0
```

The requested Office extras installed successfully but their imports failed with
missing `pypdfium2`. Both the high-level `DocumentConverter` and direct Office
backend imports encountered this dependency. The explicitly pinned supplement
enabled the tested public Office backends. It does not qualify PDF processing.
The high-level converter was not subsequently qualified.

Direct and transitive package pins are in
`tools/backend/requirements-b1-docling-spike.txt` and
`tools/backend/constraints-b1-docling-spike.txt`. `pip check` passes.
B0 dependencies and its existing workflow remain independent of this profile.

## 5. Corpus description

No approved representative Local File corpus was established. Client-labelled
repository documents were excluded from committed evidence. The fixture builder
creates fixed-date, sorted-part ZIP packages with inspectable synthetic content.

| Case | Features | Conversion results |
| --- | --- | --- |
| docx-basic | Heading, paragraph with multiple runs, bold value, simple table | 3/3 PASS |
| docx-native-edge | Basic features plus locked control, bookmark, field, hyperlink, revision and header | 3/3 PASS |
| xlsx-basic | Two sheets, cached formula value, defined name, table, merged cells | 3/3 PASS |
| malformed | Deliberately truncated ZIP package | 3/3 structured refusal; expected behavior PASS |

Fixture regeneration is byte-for-byte tested. Synthetic NCP values 14.18% and
6.08% are test content; no benchmark, source sufficiency or business conclusion
is inferred from conversion.

## 6. Input SHA256 values

| Case | SHA-256 |
| --- | --- |
| docx-basic | `6f7992a5e7e5d7ec0fa0dbc07582010689f6c4cf182dbf17a725f84114418d17` |
| docx-native-edge | `4d3c2217e17ead4a5cf84427c4dcd1596d8659211928e4003d4807cd87097882` |
| xlsx-basic | `557800163587088d774863c814dbb988a7d2f0b7dd67cd2df1096c34e455aabc` |
| malformed | `66273ca1bf690574cdd18c04d3a7101436a8302db2ff371ced6dedb693a3f7ab` |

The manifest is `tests/golden/cases/b1/manifest.json`. Every actual byte hash is
checked against DocumentVersion.binary_hash and ContentRef.sha256 before
conversion, and checked again afterwards. Registered byte length is checked.

## 7. Configuration

Probe version 1.0.0 uses public `InputDocument`, `MsWordDocumentBackend` or
`MsExcelDocumentBackend`, `convert()` and `DoclingDocument.export_to_dict()`.
Remote fetch, local fetch and chart-image rendering are disabled. Excel options
are `parse_charts=true`, `treat_singleton_as_text=false`, `gap_tolerance=0`.
Charts themselves were not evaluated. No AI or legacy parser fallback exists.

The public constructor path registers one backend and explicitly constructs
another for conversion using separate scoped byte streams. This avoids access
to the private InputDocument backend but parses twice. The explicit conversion
backend is unloaded. Resource/performance qualification of this approach remains
open; it is not a production adapter design decision.

The JSON report embeds configuration and its hashed ContentRef. Inputs are
explicit local corpus paths, never implicit ContentRef downloads.

## 8. Repeatability method

Each immutable binary is converted three times. A Golden test then generates a
second complete three-run report and compares its stable payload digest. Full
exports, counts, text, table cells, hierarchy and literal semantic references
are retained. Timing is observational and excluded from comparison.

Separate signatures compare content, semantic hierarchy, table structure,
traversal ordering and literal references. Hierarchy may map links to collection
indexes for its own comparison; the reference signature preserves the actual
IDs, parents, children and roots. No reference differences are normalized away.

Evaluation digests use sorted, compact UTF-8 JSON, reject NaN and preserve exact
integer values. They intentionally are not frozen authorization/event JCS hashes:
Docling's exported origin hash can exceed JCS's safe integer range. Frozen RFC
8785 validation remains unchanged. The stable payload excludes installed-package
inventory and elapsed times; those remain in the full observational report.

## 9. Semantic content findings

DOCX basic produced three text objects: a section heading and two inline pieces
for the NCP paragraph. The bold property on `14.18%` survives. The first run's
trailing space is normalized out of the text object. Table text preserves Metric,
Value, NCP and `6.08%`. Native-edge produces nine text objects including all six
construct sentinels. XLSX values reside in table cells, with no standalone texts.

Question A: useful text/structure for this synthetic downstream mapping example
is present. Sufficiency for representative Local File mapping is NOT_EVALUATED.
No business mapping or evidence verification was performed.

## 10. Hierarchy findings

DOCX basic has two groups, including a section and an inline group. Native-edge
has four groups. The header appears in a group named `page header` with furniture
content layer, linked from the body; it is not simply a native header part address.
XLSX has two sheet groups named Financial and Notes, each linked to its table.
These links are useful for semantic navigation (question F) within this export.
Pagination, layout fidelity and cross-version hierarchy stability are NOT_EVALUATED.

## 11. Table findings

Both DOCX cases preserve a 2-by-2 table with the four expected cell strings.
XLSX produces a 3-by-2 Financial table and a 1-by-2 Notes table; the latter has
one text cell spanning two columns. All five repeatability dimensions pass for
the three successful cases.

Question D: tested shapes, cells and merge span are sufficient to interpret these
synthetic tables. Complex/nested tables, styles, units and real business table
semantics are NOT_EVALUATED. Shape fidelity is not exact native identity.

## 12. Semantic-reference stability findings

Question E: content, structure, tables, ordering and literal references are stable
in all three identical-input runs for all three successful cases (15/15 dimension
results PASS). Malformed-case stability is NOT_EVALUATED, not a fabricated pass.
The repeated complete report has the same stable payload hash:

```text
236dae3459fe6cd73d34077502879836aaefa8b7e173e78aa2965ff2d80655e0
```

This is evidence about this package/configuration/corpus only. Semantic references
remain perception-scoped and cannot become execution addresses.

## 13. DOCX findings

Questions B and C: the heading, inline text, bold property, table text and all
control/bookmark/field/hyperlink/revision/header sentinel text are preserved.
The hyperlink URI is also present. The tested control tag `synthetic-control`,
bookmark name `syntheticBookmark`, lock token `sdtContentLocked` and field
instruction `DATE` are absent from the full semantic export. Revision text
survives as ordinary text; native change-tracking identity is not qualified.
Preserved text must not be read as permission to edit a locked control or field.

## 14. XLSX findings

Financial and Notes sheet labels and cell text survive. The formula cell exports
cached `0.0608`, while the tested native formula `6.08/100` is absent. The tested
defined-name target `Financial!$B$2` and table name `FinancialTable` are also absent
from the semantic export. Native enrichment remains necessary. No recalculation,
cached-value freshness, formula correctness or current-period sufficiency was
evaluated. B1.1 observes formula/name/table structures separately.

## 15. Omissions / unsupported constructs

Native control, bookmark, field, formula, defined-name and table identities above
are observed limitations. Whitespace and paragraph grouping are normalized.
No unclassified top-level export fields appeared in this corpus; the probe would
record such fields rather than discard their presence silently.

The malformed case returns `PERCEPTION_FAILED` with exception type, pinned input
hash and no semantic document. Missing dependencies are infrastructure errors.
Strict perception, drawings, charts, equations, embedded objects, encrypted
documents, complex revisions and large files are NOT_EVALUATED by this spike.
Strict mutation remains unsupported independently of any future reading result.

## 16. Implications for Native Identity

Question G: B1.3 still needs separately qualified, version/hash-bound native
addresses, structural fingerprints, protection scope and native formula/name/
table identity. B1.4 must associate semantic observations with those identities
without assigning execution meaning to Docling self_refs. Neither stage is
implemented here. No NativeLocator, NativeBinding or authorization is fabricated.

## 17. Risks

Packaging requires an explicit supplemental dependency. The public backend path
and duplicate parsing need production lifecycle review. Three reruns do not
establish cross-platform, cross-version or large-corpus stability. Semantic
normalization could mislead later mapping unless limitations remain explicit.
The full synthetic export includes test text and hyperlink; this evidence policy
must not be reused for confidential documents without an approved retention plan.

## 18. Evidence limitations

Only generated fixtures were evaluated. No production accuracy rate, confidence
score, latency SLO, rendering comparison or mutation qualification is claimed.
Machine evidence is `tests/golden/reports/b1/docling-qualification.json`;
preflight evidence is `tests/golden/reports/b1/preflight.json`. Tests independently
check known content, table shapes, repeated output, input hashes and failures.

Previous hosted CI run (GitHub Actions run ID 34213137801) completed with SUCCESS:
- Platform: Ubuntu 24.04
- Python: 3.12.14
- Docling candidate: 2.126.0
- Contract scenarios: 8/8 PASS
- Contract regression tests: 23 PASS
- Backend tests: 112 PASS
- Golden tests: 5 PASS
- Docling stable payload SHA256: `236dae3459fe6cd73d34077502879836aaefa8b7e173e78aa2965ff2d80655e0`

This hosted Linux stable payload matched the Windows qualification result for the same
candidate, configuration, and synthetic corpus.
This provides cross-platform repeatability evidence for the tested synthetic corpus.
It is NOT:
- production determinism
- production accuracy
- Local File qualification
- NativeLocator stability

Observed defect in prior run:
The prior hosted run generated qualification reports in `.b1-ci-reports/`. Because
`actions/upload-artifact@v7` runs with default `include-hidden-files: false`, only
`contract-validation-report.json` was retained in the workflow artifact, omitting
`preflight.json` and `docling-qualification.json`.
This micro-hardening pass updates report generation to non-hidden `b1-ci-reports/`,
configures explicit upload paths for all three evidence files, adds pre-upload existence
and format verification via `tools/b1/verify_ci_artifacts.py`, and adds unit tests in
`tests/backend/b1/test_ci_artifacts.py`.

## 19. B1.2B recommendation

Question H: before production adapter work, obtain an approved representative
Local File corpus; decide the supported public API and packaging profile; specify
semantic mapping/loss handling; define resource, audit and lifecycle integration;
and independently review this evidence. Broader corpus cases must cover formulas,
protections, header grouping and native constructs omitted here.

Question I: no tested evidence requires rejecting Docling as the provisional
semantic baseline. The observed native omissions reinforce the accepted separation
of perception and execution identity. Continue qualification conditionally; do
not silently advance to B1.2B or close its gates.

## 20. Qualification status

**PROVISIONAL_CONTINUE**, with the representative-corpus, packaging/API,
production-adapter, native-identity, binding and replay evidence gates still open.
