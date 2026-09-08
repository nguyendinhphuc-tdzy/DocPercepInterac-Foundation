# Foundation v2 B1 Qualification Plan

Date: 2026-09-08. Iteration: B1.0 + B1.1 + B1.2A.
Accepted B0: `b0f028e0b3de53debf99b38b898fbd7a9f7b9503` (PR #4).
Frozen contract: 0.1.0. Implementation branch: `build/backend-b1-foundation-v2`.

## Business objective

Establish observable document boundaries before Local File governance can
interpret sources or authorize changes. Inspect exact binaries and evaluate
semantic perception without claiming evidence sufficiency, execution identity,
or mutation support.

## B1 problem statement

An Office file opening successfully says little about native protections,
semantic omissions, conformance, or safe mutation. B1 must preserve explicit
observations and unknowns rather than letting parser success close those gates.

## B1 architecture boundary

Perceive != Understand != Authorize != Locate != Execute.
BusinessTargetID != SemanticReference != NativeLocator.

`DocumentContentResolverPort` materializes immutable bytes. `verified_bytes`
compares actual SHA-256, DocumentVersion.binary_hash and ContentRef.sha256
before inspection/conversion, and checks registered length. A mismatch raises
the frozen `STALE_DOCUMENT_VERSION`; content lookup and persistence are
application-owned. No adapter downloads a ContentRef URI.

`OoxmlPreflight` consumes an ASSESSING DocumentPreflightAssessment pinned to the
same task/version/engine/configuration. It returns a validated immutable
successor plus content-addressed evidence bytes. The application owns saving
that result and emitting causal AuditEvents. This iteration does not implement
an orchestration or persistence service.

The spike calls public Docling Office backend constructors and `convert()`;
`export_to_dict()` supplies semantic observations. It does not translate output
to production Foundation SemanticObjects or NativeLocators. No legacy parser
or AI fallback exists.

## Current assumptions

- Docling-slim technology qualification = PROVISIONAL.
- B1.2A cannot promote Docling to production qualification by itself.
- No accepted operation/profile-specific replay qualification exists.
- The frozen mutation vocabulary contains three DOCX operations and no XLSX
  operation; XLSX preflight explicitly records that boundary without fabricating
  capability tuples for nonexistent operations.
- Client-labelled repository documents are excluded from committed evidence.
  Newly generated synthetic cases have inspectable provenance and fixed bytes.
- Technical package/XML limits are versioned evaluation defaults, not approved
  production intake policy or business thresholds.

## What are we trying to learn?

Can real DOCX/XLSX package evidence establish format, conformance and native
findings deterministically? Can Docling preserve text, table shape and useful
hierarchy for a constrained Local File example? Which native semantics remain
missing? Do repeated conversions preserve content and literal semantic IDs?
What evidence remains necessary before production adapter work?

## B1.0 scope

Record accepted B0 and this B1 iteration in PROJECT_PHASE; preserve U0.
Document qualification questions, measurable tests, boundaries and open gates.

## B1.1 scope

Inspect ZIP validity/CRC, safe package names, content types, root/internal
relationships, expected main roots and namespaces. Do not use filename or MIME
as format authority. Reject malformed packages, unsafe relationships, encrypted
ZIP members, DTDs and configured resource-limit violations. A non-ZIP input is
outside this bounded profile; OLE encryption diagnosis is not implemented.

Detect Transitional or Strict from used namespace/relationship evidence;
mixed or unresolved evidence gives UNKNOWN. This is namespace classification,
not ECMA schema validation or a claim that every conformance constraint holds.

Inventory all inspected XML element names and relationship types. Explicit
findings cover Word controls/locks, bookmarks, fields, revisions, tables,
paragraphs/runs, headers/footers, drawings/text boxes and enforced document
protection. Excel findings cover sheets/cells, formulas, names, tables, merges,
drawings, workbook protection and worksheet protection. Unrecognized elements
and uninspected binary parts remain visible and blocked for mutation.

Whole-document enforced protection can establish PROTECTED for present DOCX
operation structures. A local control lock is a scope-specific finding; without
qualified locators it does not mark unrelated document content protected.
Absent structures and Strict mutation give UNSUPPORTED. Present unqualified
structures give UNKNOWN. SUPPORTED is never generated. Candidate execution
engine is OpenXmlSdk 3.5.1, while the assessor identifies itself separately as
foundation-ooxml-preflight 1.0.0. Every tuple pins the input DocumentVersionRef.

Evidence uses UTF-8 RFC 8785 bytes, SHA-256 ContentRefs and small facts rather
than document text, passwords or raw XML. Returned artifacts include the exact
configuration. Preflight creates no execution locators.

## B1.2A scope

Evaluate `docling-slim[format-docx,format-xlsx]==2.126.0` in `.venv/b1`, isolated
from B0 and broad legacy requirements. The requested extras install but their
Office imports require undeclared `pypdfium2`; preserve this failure and pin
`pypdfium2==5.13.0` as an explicit supplement. The resolved Python dependencies
are constrained in `tools/backend/constraints-b1-docling-spike.txt`.

The high-level DocumentConverter eagerly imports unrelated PDF backends and
does not import under the requested Office-only profile. Evaluate the public
declarative Office backend API explicitly, without patching or cloning Docling,
and leave high-level converter qualification open. Registration and conversion
use separately scoped byte streams; the public constructor path currently
parses twice to avoid depending on InputDocument's private backend attribute.

Four deterministic cases: DOCX basic, DOCX native-edge, XLSX and malformed DOCX.
Three runs each, plus a second complete report in regression tests. Capture
full semantic exports, counts, text digests, hierarchy, table cells/shapes,
ordering, literal refs, structured failures and observational elapsed time.
Compare those five stability dimensions separately. Reference differences must
not be normalized away. Empty or failed output cannot count as successful
perception. Missing dependencies are infrastructure failures, never a passing
malformed-input test.

## B1.2B/B1.3/B1.4 deferred scope

Production Docling mapping/lifecycle integration, native Office locators,
semantic-to-native binding and integrated B1 qualification need later explicit
authorization. Replay, business mapping, AI and production services remain
outside this iteration.

## Technology qualification rules

Keep exact engine/configuration/dependency versions and input hashes. Use PASS,
FAIL, OBSERVED_LIMITATION and NOT_EVALUATED rather than confidence scores.
Only PROVISIONAL_CONTINUE, PROVISIONAL_BLOCK or INSUFFICIENT_EVIDENCE may describe
the spike recommendation. Synthetic repeatability cannot establish production
accuracy or stable native identity. No new operation or contract field is added.

## Acceptance evidence

- Frozen contract validator and 23 existing contract regression tests.
- Existing B0 backend and Golden tests, unchanged.
- Negative preflight tests and strict OpenAPI validation of generated records.
- Mandatory installed-candidate tests in B1 CI; B0 may skip only optional
  Docling-dependent cases and must report the skips.
- Deterministic fixture regeneration and same-input report comparison.
- JSON evidence under `tests/golden/reports/b1/` and the B1.2A findings report.
- Existing B0/contract workflows remain unchanged; a separate B1 workflow
  installs exact spike dependencies, tests and uploads fresh evidence.

## Known risks

Namespace classification is not full OOXML schema validation. The native
inventory is intentionally bounded and may classify ordinary untested objects
as unknown. Unknowns never grant support. Main-part detection does not qualify
all Office structures or encrypted/OLE files. The Docling dependency supplement
and public backend path require independent review before adapter promotion.
Synthetic tests do not measure layout, pagination, complex nested tables,
headers in real templates, charts, equations, external content or performance
SLOs. Audit service integration and production resource limits remain open.

## B1 decision gates

1. B1.1: repeatable exact-byte preflight, frozen-schema conformance, explicit
   unknowns/protection, zero fabricated locators and zero SUPPORTED results.
2. B1.2A: exact candidate, actual conversions and failures, three-run stability
   measurements and reproducible evidence with explicit limitations.
3. Before B1.2B: representative approved Local File corpus; packaging/API profile
   decision; tested semantic mapping/loss policy; bounded resource behavior and
   lifecycle/audit integration design.
4. Before B1.3/B1.4: operation-specific native capture/resolution profiles,
   formula/cached-value distinction, protection coverage, version/fingerprint
   negative tests and independently reviewed semantic/native association rules.
5. Replay qualification remains a separate Golden A/B and validation gate.
