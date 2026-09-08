# Foundation v2 B1.0 + B1.1 + B1.2A Implementation Report

Date: 2026-09-08. Branch: `build/backend-b1-foundation-v2`.
Accepted starting commit: `b0f028e0b3de53debf99b38b898fbd7a9f7b9503` (B0 PR #4).
The starting commit equals the inspected origin/master and is an ancestor of
this work. This report records the working tree committed with this report;
it does not claim hosted CI success or completion of all B1 stages.

## Scope and phase

PROJECT_PHASE now records B0 as ACCEPTED and B1 as the current backend workstream.
This iteration is explicitly B1.0 + B1.1 + B1.2A. Frontend remains U0.
The qualification plan records open gates. B1.2B production adapter, B1.3 native
identity, B1.4 binding and B1.5 integration remain deferred.

There is no contract contradiction requiring a schema change. Frozen contracts,
ADRs, CURRENT_BASELINE, domain/governance implementation, frontend, B0 tests and
existing B0/contract workflows are unchanged. Prototype parsers remain reference
material. No AI, business mapping, replay or Office writeback was added.

## Content and preflight boundary

The minimal non-contract `DocumentContentResolverPort` returns immutable bytes.
`verified_bytes` checks actual SHA-256 against both frozen document/content
hashes before any ZIP/XML or Docling processing. A mismatch raises
`STALE_DOCUMENT_VERSION`; length/type disagreement raises `INVALID_CONTRACT`.
The caller resolves content and persists results; no URI is fetched implicitly.

`foundation-ooxml-preflight` version 1.0.0 consumes a pinned ASSESSING assessment
and returns an immutable successor with frozen DocumentPreflightAssessment fields.
It also returns small RFC 8785 evidence artifacts and their SHA-256 ContentRefs.
It checks package bounds, names, CRC/decompression, content types, main part,
relationships, XML and used element/attribute namespace evidence. DTDs are refused.
Namespace classification is bounded observation, not full OOXML schema validation.

| Input/boundary | Observed behavior |
| --- | --- |
| DOCX basic | COMPLETED, DOCX, TRANSITIONAL; run/paragraph/table/cell and relationship findings |
| DOCX native-edge | Additional control/lock, bookmark, field, hyperlink, revision and header findings |
| XLSX | COMPLETED, XLSX, TRANSITIONAL; sheets, cells, formula, name, table and merge findings |
| Truncated package / damaged DEFLATE | FAILED with CORRUPTED_DOCUMENT; no capability grant |
| Wrong MIME or extension | Actual package evidence determines format |
| Mixed or unrecognized namespace | UNKNOWN; includes used attribute namespaces |
| Strict OOXML | STRICT_OOXML_MUTATION_UNQUALIFIED; DOCX operations UNSUPPORTED |
| Enforced Word document protection | Present DOCX operation structures PROTECTED |
| Local control lock | Explicit protection finding; unrelated scope is not declared protected |
| Excel workbook/sheet protection | Explicit scoped findings |
| Unknown element / binary part | Explicit unknown/uninspected finding; no support inferred |

Each capability pins the exact input DocumentVersionRef, operation, structure,
candidate engine OpenXmlSdk 3.5.1 and conformance. This candidate is distinct from
the assessor. The baseline's open replay gate and observed structure determine
UNKNOWN, PROTECTED or UNSUPPORTED. No result is SUPPORTED, no NativeLocator is
fabricated, and no qualification evidence is invented. The frozen operation
vocabulary contains no XLSX mutation; its empty capability list is accompanied
by explicit EXECUTION_UNSUPPORTED rather than a fabricated operation.

The new negative tests first reproduced two implementation defects: uncaught
`zlib.error` for a damaged DEFLATE stream and incorrectly Transitional detection
when an attribute used an unknown/Strict namespace. Both now produce the required
structured refusal or UNKNOWN result. These corrections did not change contracts.

## Docling qualification

Exact candidate: `docling-slim[format-docx,format-xlsx]==2.126.0`, with the observed
Office-import dependency explicitly supplemented by `pypdfium2==5.13.0`.
All resolved Python package versions are constrained. B0 does not depend on
this installation. The spike uses public Office backend APIs and no private
backend access, vendoring or fallback parser.

Four synthetic cases are each run three times. Both DOCX cases and the XLSX case
convert successfully. Malformed input returns structured failure without a fake
semantic document. Content, hierarchy, table structure, traversal order and
literal references are stable in the successful cases. A second whole report
reproduces the stable payload hash. Timing and installed-package inventory are
retained as observational data outside that stable payload.

The DOCX 2-by-2 tables and XLSX 3-by-2 / 1-by-2 tables retain tested text and merge
span. XLSX exports cached 0.0608 without the tested formula expression; native
control/bookmark/field/name/table identity remains incomplete. The detailed
findings, all input hashes, limitations and answers to questions A-I are in
[B1_2A_DOCLING_QUALIFICATION_REPORT.md](B1_2A_DOCLING_QUALIFICATION_REPORT.md).

Synthetic qualification evidence only; representative Local File corpus gate remains open.
Recommendation: PROVISIONAL_CONTINUE. Docling remains PROVISIONAL.

## Validation evidence

Local B1 executable: `.venv/b1/Scripts/python.exe` (Python 3.12.14).
The commands below use that interpreter as `python`, with
`FOUNDATION_B1_REQUIRE_DOCLING=1` for pytest. No B1 dependency skip is allowed.

| Command | Result |
| --- | --- |
| `python tools/contracts/validate_contract_fixtures.py --report contract-validation-report.json` | OpenAPI PASS; 8/8 scenarios PASS in every dimension |
| `python -m unittest discover -s tests/contracts -v` | 23 passed |
| `python -m pytest tests/backend -q` | 112 passed, 0 skipped |
| `python -m pytest tests/golden -q` | 5 passed, 0 skipped |
| `python tools/b1/preflight_probe.py` | Three COMPLETED assessments; malformed FAILED; artifacts generated |
| `python tools/b1/docling_probe.py` | Four expected behaviors PASS, three runs each; PROVISIONAL_CONTINUE |
| `python -m pip check` | No broken requirements |
| `python -m compileall -q foundation/domain foundation/governance foundation/audit foundation/ports foundation/evaluation foundation/adapters/preflight tools/b1 tests/backend tests/golden` | PASS |
| `git diff --check` | PASS |

The aggregate includes 35 new B1 tests (25 preflight, 7 perception, 3 Golden).
All 82 original B0 backend/Golden tests also passed under the independent
`.venv-contracts/Scripts/python.exe` using:

```text
python -m pytest tests/backend tests/golden --ignore=tests/backend/b1 --ignore=tests/golden/b1 -q
```

The final full B0-environment run passed 113 tests and explicitly skipped four
optional Docling cases. This is separate from the B1 environment's mandatory-
candidate, zero-skip results.
Generated preflight histories pass strict frozen OpenAPI schema validation.
All evidence artifact hashes, corpus hashes and repeatability signatures pass
their checks. Changed Markdown fences and new workflow YAML are checked locally.

## CI and publication

New workflow: `.github/workflows/backend-b1.yml`, job
`Foundation Backend B1 qualification`, Python 3.12, actions v7. It installs pinned
B0 and isolated B1 tooling, requires the candidate, runs contract/B0/B1/Golden
checks, compiles the new boundaries and uploads fresh reports. Existing required
check names, triggers and behavior are unchanged.

Hosted GitHub Actions result: NOT_RUN for this unpublished work. Local steps
passed; this does not prove Linux runner compatibility. No push or merge is
authorized by this task. The branch is retained locally for review.

## File inventory and remaining gates

Modified: `docs/PROJECT_PHASE.md` only.

Created:

- This report, the B1 qualification plan and B1.2A findings report in `docs/backend/`.
- `foundation/ports/content.py` and three files under `foundation/adapters/preflight/`.
- Two evaluation files under `foundation/evaluation/perception/`.
- Three CLI/fixture builder files under `tools/b1/` and two pinned dependency files.
- B1 preflight/perception tests, Golden tests and their README.
- Four synthetic binaries, corpus manifest and two machine report snapshots.
- `.github/workflows/backend-b1.yml`.

Before B1.2B: representative approved corpus, public API/packaging decision,
semantic loss policy, resource handling and audit/lifecycle integration design.
Before B1.3: qualified native structure/address profiles, formula versus cached
value capture, scoped protection and exact version/fingerprint negative tests.
Production thresholds, complex OOXML, rendering, encrypted OLE and performance
qualification remain open. No execution engine or mutation is qualified here.
