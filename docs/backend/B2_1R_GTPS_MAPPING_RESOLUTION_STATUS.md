# B2.1R representative mapping resolution

Status: **IMPLEMENTED — mapping evidence review pending**.
Production qualified: **false**. Replay qualified/authorized: **false**.

## Baseline and isolation

`B21_BASELINE_SHA = 43945769c77841498af10b13d278740a3c53ad48`

The clean exact baseline was pushed to `build/gtps-first-draft-vslice-01` before
representative implementation. B1 native identity commit
`ad87422b47b7881bd1926f0f81a085326e38a520` was selectively reused as `73d97c0`.
The qualification branch/evidence were not merged or modified. No frontend
changes or dependency upgrades.

The existing Business Owner progression waiver remains the authority to proceed.
This milestone supplies no missing human-review fields, does not execute Run-004,
and does not promote B1.2R or authorize approval/Replay.

## Implemented behavior

- Transaction matching uses transaction concept plus an engagement-scoped
  canonical party identity. Alias entries retain canonical name, known aliases
  and exact version/digest/pointer evidence. Unknown aliases require review;
  no fuzzy party matching. Historical counterparties remain distinct, including
  removals within the bounded inventory. Country/relationship changes stay visible.
- Section 4 is a generic container. Five current transactions occupy existing
  slots: Transaction under Review first, then descending materiality, with Template
  guidance pinned as configuration evidence. No Golden ordering or label-match
  prerequisite, discretionary grouping or row insertion.
- One BusinessTarget can have explicitly grouped occurrences, each with its own
  region, native identity, current content, proposal and projection. Duplicate or
  overlapping targets fail closed.
- Historical financial images are not reconstructed. Observed historical business
  context, explicit Template metrics and current-source values support bounded
  financial mappings. No historical numbers are fabricated.
- A replaceable native provider reuses B1 preflight, verified bytes, external
  python-docx loading, QName addresses, C14N fingerprints and exact re-resolution.
  Whole-table identity precedes native cell coordinates; multiple matches refuse.
- A separate formatted-text **review-only** profile permits observed formatting
  and retains UNKNOWN package conformance. It addresses Transitional main-body
  objects only and refuses fields, bookmarks, nested/merged tables, protection,
  revisions and unknown text constructs. B1's original stricter profile retains
  its behavior. Neither profile grants mutation capability.
- Concrete proposals validate against frozen `ChangeProposal`, status DRAFT.
  Viewer projections expose native refs, exact content, source/history lineage,
  rationale, classifications and warnings. No Word highlighting, approval,
  ApprovedChangeSet, mutation or document output.

## Sanitized representative evidence

Evaluation reuses Run-003 observations and only the three configured business
roles. Office content, selectors, private hashes and review notes remain private.
Golden is not a mapping input. Optional Golden comparison was not performed.

| Target | Concrete DRAFT proposals | Scope/limitation |
| --- | ---: | --- |
| Reporting period | 1 | Section 7 fiscal year; cover field unsupported |
| Processing services | 4 | Label, party, relationship, amount |
| Raw-material purchase | 4 | Label, party, relationship, amount |
| Raw-material sale | 4 | Correct party; separate historical removal retained |
| Interest expense | 4 | RPT-specific authority; no global FS reconciliation |
| Other business expense | 4 | New transaction; narrative review required |
| Current NCP | 1 | Exact ratio; display/cache freshness unqualified |
| Section 7 financial metrics | 3 | Net sales, cost of goods sold, EBIT |
| **Total** | **25** | **All non-executable** |

26 target intents: 25 exact candidates, 0 ambiguous, 0 not found, 1 unsupported.
25 exact proposed-target highlight projections; 1 unresolved projection.
Separate detailed-heading navigation: 3 resolved, 1 unsupported, 1 not found.
Those navigation candidates are not narrative ChangeProposals; summary-container
proposals are independently bound.

Seven existing rows cover five current transactions:
`ROW_GROWTH_NOT_REQUIRED_FOR_REPRESENTATIVE_CASE`. Unused rows remain untouched.
Historical financial image limitation: `NON_BLOCKING_FOR_BOUNDED_MAPPING`.

General Office fidelity, source cache freshness, absent historical relationship
fields, complete occurrence inventory, narrative wording and execution preservation
remain unqualified. Sales-heading bookmarks and embedded drawing/text structures
are outside this profile. No best-effort fallback.

## Validation

Existing pinned environment: Python 3.12.14; docling-slim 2.126.0.
`FOUNDATION_B1_REQUIRE_DOCLING=1` for pytest.

| Check | Result |
| --- | --- |
| Focused B2/native identity/representative/privacy tests | 188 passed before final additional refusal test |
| `pytest tests/backend tests/golden -q` | 410 passed, including final refusal test |
| `unittest discover -s tests/contracts -q` | 23 passed |
| Contract fixture validator | OpenAPI PASS; 8/8 fixtures |
| Private tracked/index boundary | PASS |
| Frozen Contract/domain diff from B2.1 | Empty |
| Prior private evidence/review preservation | 58 recorded files unchanged |
| Run-003 report and all source input integrity | Unchanged |
| Representative rerun with inaccessible unselected/Golden content | Identical |

The architecture guard covers core mapping and native adapters: no legacy
WritebackEngine, action executor, rollforward or Replay dependency. Existing
assertions were retained. No Frozen Contract gap was identified.

## Next gate

Review private `MAPPING_EVIDENCE_REVIEW_v2.md` and its bound immutable result/config.
Confirm aliases, ordering, source authority, occurrences and proposed payloads.
Machine repeatability is not business correctness. Human Approval implementation
remains gated on mapping evidence review and explicit next-phase authorization.
DOCX Replay and First Draft output remain unauthorized.
