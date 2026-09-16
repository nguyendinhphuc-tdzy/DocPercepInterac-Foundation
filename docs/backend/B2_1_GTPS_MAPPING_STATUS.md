# B2.1 GTPS governed mapping plan

## Business Owner progression decision

The Business Owner explicitly authorized B2.1 in the current task and stated
that the SME check had occurred. The formal Run-003 records remain incomplete.
This document records progression authorization, not completed human review.

| Governance field | Recorded state |
| --- | --- |
| FORMAL_SME_RECORD_COMPLETENESS | INCOMPLETE / WAIVED_AS_PROGRESSION_BLOCKER_BY_BUSINESS_OWNER |
| BUSINESS_PROGRESSION_DECISION | APPROVED_TO_PROCEED_TO_BOUNDED_GTPS_VERTICAL_SLICE |
| GENERAL_OFFICE_FIDELITY | PROVISIONAL_CONTINUE |
| PRODUCTION_QUALIFIED | FALSE |
| REPLAY_QUALIFIED | FALSE |

B1 Run-003 mechanical evidence is complete and preserved. Reviewer identity,
review time, case judgments, feature fidelity and losses have not been invented
or rewritten. Formal review completion remains documentation/audit debt. No
Run-004 was created and no existing qualification verdict was promoted.

## Implementation authority and isolation

Branch: `build/gtps-first-draft-vslice-01`.
Starting master: `fa1a4433b6ea8b724abdaac3e0596fc320793f41`.
The qualification branch and prior B1 provisional implementation branches were
not merged into this runtime branch.

Business interpretation follows
[GTPS Workflow Profile v0.2](../business/GTPS_LOCAL_FILE_WORKFLOW_PROFILE_v0.2.md)
and the First Draft Vertical Slice specification read from
`docs/gtps-first-draft-vertical-slice-v0.1` at
`87a15cf060997d4d06bbc65c245ded7eaab02a07` (PR #17 branch).
Frozen Contract v0.1.0 remains unchanged.

## Implemented boundary

The GTPS application planner consumes already perceived, version-bound views.
It does not parse Office files, call AI, fetch arbitrary URIs, approve changes,
persist contract records, or mutate documents.

1. Versioned engagement selectors identify current facts and their period,
   relationship fields, calculation context and semantic evidence pointers.
   Numeric parsing uses decimal strings with an explicit grouping convention;
   missing values, ambiguous years and unsupported forms are refused.
2. Historical selections must include exact supporting context. Configured
   business concepts and historical meaning resolve BusinessTargetID before a
   target region is considered. Confidence/fuzzy similarity is not a fallback.
3. Authority is configured per target and source key. Conflicting duplicate
   current facts are blocked, including equal-value duplicates with distinct
   lineage; there is no newest-wins rule.
4. Template regions are explicit, pinned evaluation/configuration hypotheses.
   Missing, ambiguous, stale, protected or overlapping regions are blocked.
5. A replaceable native-candidate interface checks the exact target version,
   region, operation, observed content and structural fingerprint. Unavailable,
   multiple or mismatched candidates remain structured refusals.
6. Successful fixture cases produce the existing frozen `EvidenceRecord`,
   `MappingProposal` and **DRAFT** `ChangeProposal` models. All outputs have zero
   execution authority. Missing native identity produces a non-contract mapping
   intent with a blocked projection; it never creates a fake NativeLocator ref.
7. The projection includes Business Target, pinned semantic region, native ref
   when available, old/new value, source and historical evidence, rationale,
   change types, warnings and review status. No frontend or Word-highlight change
   is included.

Supported bounded target families: reporting period, configured entity identity,
Section 4 RPT relationships, current-client NCP and Section 7 financial metrics.
The representative configuration does not enable entity identity without
approved current evidence. Full benchmarking is out of scope.

RPT comparison exposes changed amount, new/removed category, changed party,
changed relationship and narrative-review conditions. New/removed means absence
within the supplied bounded selection, not an authorized insertion or deletion.
Short historical party labels are not silently equated to current legal names.
An ambiguous party match requires review.

## Representative evidence

An ignored local evaluation consumes the existing Run-003 report and exact
private input/observation bindings. It selects only current source, historical
reference and target template. Golden content is never passed to mapping.
The report itself, all Office inputs and prior reviews remain unchanged.

| Evidence | Observed result |
| --- | --- |
| Current fact selections | 8 |
| Normalization refusals | 0 |
| Reviewable mapping intents | 5 |
| Representative contract ChangeProposals | 0: native candidates unresolved |
| Representative native refusals | 5 |
| Unresolved business mappings | 3 |
| Executable mappings | 0 |

The five intents cover reporting period, current NCP, raw-material purchase,
interest expense and a new other-expense category. Template mappings are
review hypotheses, not business-approved bindings. All remain non-executable.

The three distinct business refusals are:

- processing services: no configured exact target slot in the selected template;
- raw-material sales: multiple historical counterparty contexts;
- Section 7 net sales: historical financial-table image does not provide the
  selected metric's semantic context.

Other visible limitations include missing historical country/relationship fields,
party-name representation differences, narrative review, inventory completeness,
unsupported row growth and unresolved native identity. Current NCP retains the
source decimal-ratio representation; Word display formatting and cache freshness
are not qualified. FS and RPT interest-expense contexts have not been reconciled
into a global authority decision; authority remains target-specific.

## Validation

The tests use synthetic non-customer fixtures; representative inputs, selectors,
mapping results and review notes stay private. Tests cover all requested business
scenarios, genuine conflicting source rows, historical/template ambiguity, stale
versions and content, missing evidence, native candidate failures, protection,
target collisions, deterministic results, role collision and Golden isolation.
The import/call guard prohibits legacy writeback and Replay in the mapping lane.

Final checks in the existing pinned B1 environment:

| Command/check | Result |
| --- | --- |
| `pytest tests/backend/b2 tests/backend/b1/representative tests/backend/b1/privacy -q` | 148 passed (54 B2.1 tests) |
| `pytest tests/backend tests/golden -q` | 369 passed |
| `unittest discover -s tests/contracts -q` | 23 passed |
| `tools/contracts/validate_contract_fixtures.py` | OpenAPI and 8/8 fixtures passed |
| Private boundary guard, staged diff whitespace, frozen-contract diff | Clean |
| Re-evaluation of private mapping evidence with final code | Identical |
| Prior private qualification/review preservation checks | Unchanged |

`FOUNDATION_B1_REQUIRE_DOCLING=1` was set for pytest; no dependency changes.
No frozen-domain/OpenAPI changes, dependency upgrades, historical qualification
rewrites or tracked private artifacts are required.

## Next gate

**Mapping evidence review.** Review the private proposals and refusals, resolve
business meaning and template-region hypotheses, and provide exact native
identity behind the interface before promoting concrete representative proposals.
Registered target/policy definitions and source/evidence assessments remain
separate application integration work; the evaluation references are not a
production registry. No public HTTP API was added to the frozen OpenAPI surface.

B2.2 approval/sealing and B2.3 Replay remain unauthorized. A future First Draft
must be a real DOCX derived from a governed copy of the approved TARGET Template,
with only ApprovedChangeSet changes and independently validated preservation of
non-target content. Historical Reference and Golden can never be output bases.
