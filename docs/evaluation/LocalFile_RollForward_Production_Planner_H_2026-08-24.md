# Local File Roll-Forward — Production Planner (Phase H)

Generated 2026-08-24T02:49:06.887413+00:00 from a real planning run. Machine-readable twin: `LocalFile_RollForward_Production_Planner_H_2026-08-24.json`.

## Inputs

| Role | Document | Document id |
|---|---|---|
| Historical Local File | HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx | doc-hist-fy2023 |
| Master Template | Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx | doc-tmpl-decree20 |
| Current-year source | HMV-FA&RPT FY2024.xlsx | doc-farpt-fy2024 |
| Current-year source | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | doc-appendix1-fy2024 |

Periods: **FY2023 → FY2024**, both read from document content.

## Planning decisions

- Regions planned: **16**
- READY: **0** · HUMAN_REVIEW: **3** · BLOCKED: **13**
- Mutation plan: 0 table(s), 0 row(s), 0 cell(s) (digest `e3b0c44298fc1c14`)
- Manifest status: **REVIEW_REQUIRED** — not approved, not executed

### Ready regions

None. No region reached a verified binding **and** a structurally safe prototype row, so nothing is executable on these inputs. Readiness was not manufactured to make the fixture pass.

### Human-review regions

| Region | Section | Why |
|---|---|---|
| `rfr-e6ca100094cac4f3` | Overview | Historical correspondence is weak (score 0.38, matched on semantic_label(RELATED_PARTY_TRANSACTIONS), column_schema_alignment, header_token_overlap, section_context). |
| `rfr-2b942dc4774b8484` | Payment of interest on intercompany loan(s) | No corresponding table in the historical Local File; the region has no prior-year basis to roll forward from. |
| `rfr-8fb821ad2a482245` | Allocation method used in the calculation of ABC’s operating result for each business segment | No corresponding table in the historical Local File; the region has no prior-year basis to roll forward from. |

### Blocked regions

| Region | Section | Why |
|---|---|---|
| `rfr-d46c200d26f19ff0` | Untitled region | Historical correspondence is weak (score 0.51, matched on semantic_label(COVER_BLOCK), column_schema_alignment, header_token_overlap, merge_topology). |
| `rfr-4d3280f73b63728f` | Untitled region | No current-year evidence supports this region. |
| `rfr-4ece458761d2fdec` | Executive Summary | No corresponding table in the historical Local File; the region has no prior-year basis to roll forward from. |
| `rfr-886c68a9cbaee49a` | Analysis of functions, assets and risks | Historical correspondence is weak (score 0.41, matched on semantic_label(FUNCTIONAL_ANALYSIS), section_context). |
| `rfr-d530d5963267f6b2` | Selection of profit level indicator (“PLI”) | No current-year evidence supports this region. |
| `rfr-1428592fc8d46ebd` | Selection of profit level indicator (“PLI”) | Historical correspondence is weak (score 0.48, matched on semantic_label(PLI_FORMULA), header_token_overlap, section_context, merge_topology). |
| `rfr-faf9f50139bee705` | Selection of profit level indicator (“PLI”) | Historical correspondence is weak (score 0.41, matched on semantic_label(PLI_FORMULA), merge_topology). |
| `rfr-851d9e27f3a0b81b` | The standard arm’s length range | No corresponding table in the historical Local File; the region has no prior-year basis to roll forward from. |
| `rfr-d64bd1292a678a2c` | The standard arm’s length range | No corresponding table in the historical Local File; the region has no prior-year basis to roll forward from. |
| `rfr-cbfc855f1ed1946c` | Summary of reasons and explanation for the causes, business plans, investment and development strategy of taxpayers which have been in loss position for three years or more | Historical correspondence is weak (score 0.36, matched on semantic_label(DOCUMENT_CHECKLIST)). |
| `rfr-268c5ad2bd7fe689` | Summary of reasons and explanation for the causes, business plans, investment and development strategy of taxpayers which have been in loss position for three years or more | No corresponding table in the historical Local File; the region has no prior-year basis to roll forward from. |
| `rfr-4b8dca9dd20e953d` | Summary of reasons and explanation for the causes, business plans, investment and development strategy of taxpayers which have been in loss position for three years or more | No corresponding table in the historical Local File; the region has no prior-year basis to roll forward from. |
| `rfr-4df4dedcf13b6fd2` | Summary of reasons and explanation for the causes, business plans, investment and development strategy of taxpayers which have been in loss position for three years or more | No corresponding table in the historical Local File; the region has no prior-year basis to roll forward from. |

## Source bindings

| Region | Source | Sheet | Range | Status |
|---|---|---|---|---|
| `rfr-d46c200d26f19ff0` | (none) | — | — | MISSING |
| `rfr-4d3280f73b63728f` | (none) | — | — | MISSING |
| `rfr-4ece458761d2fdec` | (none) | — | — | MISSING |
| `rfr-e6ca100094cac4f3` | HMV-FA&RPT FY2024.xlsx | RPTs | — | AMBIGUOUS |
| `rfr-e6ca100094cac4f3` | HMV-FA&RPT FY2024.xlsx | III. Summary-RPTs | — | AMBIGUOUS |
| `rfr-e6ca100094cac4f3` | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | Checklist | — | AMBIGUOUS |
| `rfr-e6ca100094cac4f3` | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | Full Appendix I | — | AMBIGUOUS |
| `rfr-e6ca100094cac4f3` | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | III. Summary-RPTs | — | AMBIGUOUS |
| `rfr-2b942dc4774b8484` | HMV-FA&RPT FY2024.xlsx | FS | — | AMBIGUOUS |
| `rfr-2b942dc4774b8484` | HMV-FA&RPT FY2024.xlsx | III. Summary-RPTs | — | AMBIGUOUS |
| `rfr-2b942dc4774b8484` | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | III. Summary-RPTs | — | AMBIGUOUS |
| `rfr-2b942dc4774b8484` | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | IV. Segmented data | — | AMBIGUOUS |
| `rfr-2b942dc4774b8484` | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | FS | — | AMBIGUOUS |
| `rfr-2b942dc4774b8484` | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | CF | — | AMBIGUOUS |
| `rfr-2b942dc4774b8484` | HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx | IV. Segmented data_securities | — | AMBIGUOUS |
| `rfr-886c68a9cbaee49a` | (none) | — | — | MISSING |
| `rfr-d530d5963267f6b2` | (none) | — | — | MISSING |
| `rfr-1428592fc8d46ebd` | (none) | — | — | MISSING |
| `rfr-faf9f50139bee705` | (none) | — | — | MISSING |
| `rfr-851d9e27f3a0b81b` | (none) | — | — | MISSING |

## Structural deltas

None: no region reached a safe row-growth decision on these inputs.

## Rejected evidence

Every supplied current-year source was cell-addressable and was profiled.

## Timing

| Stage | ms |
|---|---|
| period_validation_ms | 0.01 |
| template_profile_ms | 391.89 |
| historical_correlation_ms | 875.07 |
| source_profile_ms | 2106.8 |
| region_planning_ms | 1.95 |
| plan_assembly_ms | 0.14 |
| **total planning** | **3375.86** |

No model was called at any point: the planner has no provider import and the roll-forward agent path returns before any model call.

## Proof: Ground Truth was never accessed

Files opened during planning (recorded by patching `docx.Document` and `openpyxl.load_workbook`):

- `Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx`
- `HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx`
- `HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx`
- `HMV-FA&RPT FY2024.xlsx`

Ground Truth (`HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx`) open count: **0**.

Two independent guards enforce this: `InputAccessGuard` refuses any path that is not a declared workflow input, and `GroundTruthGuard` refuses by content hash even if such a file were renamed into a slot.

## Proof: no hardcoded fixture identifiers

`planner.py` was scanned for the identifiers used by the fixture-bound evaluation harnesses (`rfr-071`, `rfr-093`, `rfr-098`, `rfr-101`, `GOLDEN_`, `HMV-`, `FA&RPT`, `Appendix I`, cell literals `D14`/`D8`/`D34`).

Matches found: **none**.

Region ids are derived from each table's own position-free identity key; sheet names and cell addresses come from the profiled source header row.

## Governance

- Manifest status after planning: `REVIEW_REQUIRED`
- Approved: `False`
- The planner cannot approve, cannot execute, and writes no document.
- Execution remains behind `POST /api/agent/rollforward/approve`, which requires a named approver and re-checks that the plan still describes the workflow's documents.
