# B1.1 Resource-Safe OOXML Preflight Evolution

Date: 2026-09-09. Branch: `build/backend-b1-resource-safe-preflight`.
Starting baseline: `a8c91372b9a7b63e806a039abcde569dc4800569`.
Architecture generation: Foundation v2. Frozen contract: **0.1.0, unchanged**.

## Outcome and scope

The adapter now enforces XML capacity incrementally before structural inspection,
without retaining all expanded ZIP members or constructing XML DOMs. Binary
verification, package integrity, namespace/conformance rules, native and unknown
findings, protection observations and operation-specific capabilities are preserved.
Audit remediation 1.1.1 also establishes a deliberately narrow ZIP admission
profile: only stored members with local/central header agreement and contiguous
physical member layout are qualified. DEFLATE, BZIP2, LZMA and data-descriptor
layouts fail closed before member decompression.

This implements the approved HYBRID C+D direction: sequential phases and shared
streaming reducers. Optional control-part DOMs proved unnecessary: existing
control semantics need only roots and direct-child metadata. Both BULK_XML and
CONTROL_XML therefore use the same event parser and observation reducer. There
is no size-based parser switching or fallback and no new DOM capacity knob.

This is implementation evidence, not production qualification or broader scale
support. The private representative Run-001 remains gated. No NativeLocator,
NativeBinding, replay, mutation, production Docling integration or contract change
is included.

## Acceptance audit remediation

- **F01 closed:** Expat errors and parser-originated ValueError/LookupError codec
  failures now return FAILED / CORRUPTED_DOCUMENT with a fixed reason in either
  pass. Observation-reducer exceptions are re-raised as implementation failures.
- **F02 closed for the admitted profile:** the ineffective request for one byte
  beyond ZipExtFile's declared view was removed. Stored-member local and central
  fields, local extra data and physical boundaries are validated before reads;
  an understated member with a hidden suffix fails as CORRUPTED_DOCUMENT.
- **F03 closed:** STORED is the only qualified compression method. DEFLATE,
  BZIP2, LZMA and data-descriptor layouts fail before member decompression.
- **F04 closed:** finding occurrence identity is deterministic and distinct from
  observation content identity. Duplicate semantic observations may share their
  observation_ref, while every finding_id remains unique within the assessment.

## Allocation lifecycle and phases

Previously the adapter read every expanded ZIP member into `parts`, built every
XML tree into `xml`, then counted elements. Its XML capacity gate was a
POST_PARSE_FAIL_CLOSED_GATE and could not prevent the allocations it measured.

The new phases are:

1. **A — Verify immutable binary.** The unchanged content port returns bytes;
   `verified_bytes` checks the exact DocumentVersion, ContentRef hash and length
   before package inspection. No alternate unverified input path exists.
2. **B — ZIP metadata safety.** Retain ZipInfo/name indexes; enforce package,
   part-count, expanded-total and per-part limits, canonical names, uniqueness
   and encryption refusal before decompression. Then enforce the stored-only
   compression policy and verify local/central CRC, size, method, flags and name
   agreement plus exact physical adjacency through the central-directory start.
3. **C — Streaming safety/capacity.** Visit all members in sorted name order.
   XML/rels use start/end events, incremental aggregate element counting and
   explicit DTD/external-entity refusal. Non-XML members are drained for read/CRC
   parity. Stored-member reads request at most 64 KiB. Count bytes exposed by
   ZipExtFile against the already validated physical layout; stop immediately at
   the first hard refusal and close the stream.
4. **D — Sequential inspection.** Reopen admitted XML/rels one at a time against
   the same verified immutable bytes. Shared reducers retain QName counters,
   namespace signals, root identity, ordered protection observations and the
   selected direct-child control metadata. Document text, formula contents,
   passwords and cell values are not retained. Every parser/member is released.
5. **E — Cross-part validation.** Resolve content-type overrides and root/main
   identity using member indexes. Preserve relationship source/target existence,
   canonical target resolution, modes, types and per-part duplicate-ID checks.
6. **F — Deterministic reduction.** Preserve sorted parts/QNames/errors, ordered
   protection occurrences and relationship records, exact unknown counts and
   current capability order. Build existing findings, artifacts and assessment.

CONTROL_XML means exactly `[Content_Types].xml` or a `.rels` member. Other `.xml`
members are BULK_XML. This internal classification changes control metadata
collection, not common QName, namespace or protection interpretation. The
case-sensitive `.xml`/`.rels` inspection coverage remains unchanged.

The two passes intentionally repeat admitted member reads/XML parsing. The second pass
also enforces its own safety counters. No parser or member survives into the
next part; only reduced observations remain for final validation and evidence.

## Versions and capacities

| Item | Accepted baseline | PR before remediation | Remediated |
| --- | --- | --- | --- |
| OoxmlPreflight engine version | 1.0.0 | 1.1.0 | 1.1.1 |
| PreflightConfig profile version | 1.0.0 | 1.1.0 | 1.1.1 |
| Streaming parser strategy version | N/A | 1.0.0 | 1.1.0 |
| max_package_bytes | 33,554,432 | 33,554,432 | 33,554,432 |
| max_uncompressed_bytes | 134,217,728 | 134,217,728 | 134,217,728 |
| max_part_bytes | 16,777,216 | 16,777,216 | 16,777,216 |
| max_parts | 4,096 | 4,096 | 4,096 |
| max_xml_elements | 500,000 | 500,000 | 500,000 |

Configuration evidence now pins the parser strategy, chunk size, DOM absence,
entity/DTD refusal, actual Expat version, stored-only compression method, refusal
of data descriptors and physical-layout rule. Canonical EvidenceArtifact encoding
remains RFC 8785 plus SHA-256. Engine/configuration provenance changes necessarily
change dependent artifact/finding hashes; identical runs in the same pinned
environment produce identical evidence.

The ZIP trust boundary is explicit. Python ZipFile supplies parsed central-directory
metadata and CRC verification for admitted reads. Foundation does not claim that
ZipExtFile can reveal bytes beyond its declared expanded size. Before opening any
member, Foundation instead compares the admitted stored member's central metadata
with its local header and requires its physical data end to equal the next local
header or central-directory start. This closes hidden physical suffixes for the
qualified stored-only profile without adding a general ZIP decompressor. Other
compression/layout profiles remain unsupported pending separate qualification.

Old profile versions are not silently relabeled. Historical assessments, artifacts
and reviews remain intact. New engine/configuration observations require new
assessments and applicable review bindings, with explicit scoped supersession.
The representative harness already binds the adapter engine/configuration in its
observation digest; no harness/schema or profile-selection plumbing was changed.

## Failure precedence and authority

Request/hash checks precede package checks. Metadata capacity checks precede
duplicate/path/encryption checks, matching the existing order. In the safety pass,
the first encountered read/CRC, XML syntax, DTD/entity or element-capacity refusal
wins in sorted package-part order. No later member or structural inspection runs
after a hard safety refusal. This can change the first error for a package with
multiple defects compared with loading all members before parsing.

After safety admission, deterministic control validation retains the previous
content-type/main-part/relationship ordering. Existing fixed refusal reasons and
frozen ErrorCodes remain in use. Invalid admitted physical layouts produce
CORRUPTED_DOCUMENT. Unqualified compression or data-descriptor layouts produce
UNSUPPORTED_FILE_FORMAT before decompression. Expected Expat encoding ValueError,
LookupError and ExpatError paths produce deterministic structured failures; errors
raised by the observation reducer remain programmer failures and are not relabeled.

Conformance still uses element namespaces, attribute namespaces and relationship
type signals with the accepted exclusions. Unknown constructs remain observable.
Protection occurrence order/multiplicity is preserved. Readability never grants
SUPPORTED; Strict mutation stays unqualified and frozen XLSX mutation remains
unsupported. A FAILED assessment returns no supported capability or locator.

## Semantic-equivalence and structural tests

`tests/backend/b1/preflight/accepted_v1.py` is a test-only oracle copied from the
accepted starting commit. Only its evidence import was relocated. Foundation
runtime never imports it. It preserves a reproducible comparison without relying
on Git history availability in shallow CI checkouts.

Equivalence compares eight existing-style DOCX/XLSX cases plus dominant and
distributed generated workbooks. Decoded assessment, native/protection findings,
observation payloads, format/conformance, capabilities, errors and all nonconfig
artifacts are compared, preserving list order and multiplicity. Only engine
version/configuration provenance and digest-derived references are normalized;
each referenced semantic payload is compared. Document identity is not normalized.

The original test-first run against old code had four expected failures: new
versioning, two early-refusal cases, and DOM-free admitted inspection. The 1.1.1
remediation test-first run then exposed nine expected failures covering F01-F04.
All focused checks now pass.
An instrumentation test was corrected to observe inspection reads rather than
fixture-construction ZIP writes; its early-stop assertion was retained.

Structural tests prohibit `ElementTree.fromstring`, prohibit inspection after
capacity refusal, prove later malformed members remain unopened, verify stream
closure, and refuse large controls before reducer allocation. Boundary tests cover
exact aggregate XML and per-part byte limits; dominant and distributed workloads
exercise aggregate accounting. Unknown counts and sensitive-value exclusion,
CRC, compression refusal, encryption, malformed/control relationships, protection, immutable
identity and deterministic evidence remain covered.

Remediation regressions cover UTF-7, Shift-JIS and unknown codec declarations in
the shared parser, including explicit inspection-pass coverage; observer programmer
errors remain visible. They reproduce understated stored-member metadata with a
hidden malformed suffix and require structural refusal. DEFLATE, BZIP2 and LZMA
are refused before ZipFile.open, while stored packages remain admitted. Repeated
identical protection observations preserve a shared observation_ref but receive
unique deterministic finding IDs. Each finding ID combines the stable traversal
occurrence ordinal with its evidence digest; IDs are unique within the assessment,
repeatable across identical runs and do not create native execution identity.

## Local validation evidence

Python 3.12.14, accepted B1 environment. Synthetic Docling regressions were
explicitly authorized; no private Docling or representative Run-001 was invoked.

| Check | Result |
| --- | --- |
| Contract fixture validator | OpenAPI PASS; 8/8 scenarios PASS |
| Contract unittest suite | 23 passed |
| Focused preflight tests | 72 passed: 25 original-module + 47 resource-safe/remediation |
| Representative/privacy tests | 83 passed |
| Full backend tests | 254 passed |
| Golden tests | 5 passed |
| Private corpus boundary | PASS |
| pip check | No broken requirements |
| Compile preflight, tests and changed tooling | PASS |
| git diff --check | PASS |

No skipped tests or reduced invariants were used. Frozen contracts, domain models,
ADRs, representative schema/harness, Docling pins and workflows have no changes.

## Synthetic resource observations

`tools/b1/preflight_resource_probe.py` generates synthetic workbooks and runs each
engine/case in a fresh process. It accepts no private input path. The large fixture
builder generates rows, cells, formulas and sheet distribution deterministically;
no large binary is committed. Existing Golden fixture bytes remain reproducible.

| Synthetic case | Old / new result | Old peak working set | New peak working set |
| --- | --- | --- | --- |
| Dominant worksheet | COMPLETED / COMPLETED | 114.90 MiB | 49.54 MiB |
| Distributed worksheets | COMPLETED / COMPLETED | 115.80 MiB | 49.26 MiB |
| Above default element limit | FAILED / FAILED | 129.82 MiB | 56.97 MiB |

These are single local lifetime peaks, including imports/input generation, not
portable pass thresholds. The new runs did not exceed their pre-assessment peak.
Elapsed times were approximately 0.73/0.92 seconds, 0.71/0.94 seconds and 0.34/0.29
seconds respectively. Two-pass overhead remains observable; production performance
or security qualification is not implied.

Reproduce locally with a new output path:

```powershell
python tools/b1/preflight_resource_probe.py --report <new-synthetic-report.json>
```

## Private default-profile observation and next gate

After all required regressions passed, the existing external LF-XLSX-003 mirror
was checked against prior private identity evidence. Engine/profile 1.1.1 with
unchanged defaults returned FAILED / DOCUMENT_TOO_LARGE / "Configured expanded
package limits exceeded". Before/after identity checks passed. No member/XML
inspection or Docling was needed beyond that metadata refusal, and representative
Run-001 was not invoked.

This private result remains local and ignored; source names, source hashes and
content are not published. The case is not declared supported. Its representative
qualification still requires separately approved, bounded profile review and later
explicit harness plumbing, followed by fresh preflight and SME/scope review.

## Remaining bounds

The content port still materializes compressed bytes before the package-size
check, and ZIP directory parsing precedes the part-count gate. Only the stored,
contiguous, no-data-descriptor layout is qualified; ordinary DEFLATE Office
packages therefore fail closed until an independently bounded decompression path
is qualified. Streaming parsers may allocate token/attribute/depth state; chunk
size alone is not a process-memory guarantee. Exact unknown-QName inventories,
relationship metadata, protection occurrences and returned evidence can grow with
admitted XML. The adapter retains reduced observations across parts, not
constant-size state. No new depth, token, CPU or output-memory thresholds are
claimed. Those require separate evidence and architecture decisions. This
implementation neither widens capacity nor replaces independent validation,
native identity or governance.
