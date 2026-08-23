# Local File Roll-Forward Source Completeness & Readiness Audit (Phase E)

**Date**: 2026-08-23  
**Mode**: AUDIT / READINESS MAP — no mutation planned, no production behaviour changed  
**Ground Truth**: quarantined during readiness; opened only for §17 evaluation  

---

## Executive Summary

The Master Template contains **61 heading-delimited semantic regions**, **16 tables** and **38 drawing constructs**. The two current-source workbooks contribute **23 sheets**.

**Segmentation is an exact partition of the document body**: 314 paragraph assignments over 314 body paragraphs and 16 table assignments over 16 tables, with no duplicates (`is_exact_partition = True`). Nothing is unclassified.

> Phase E derives 61 regions from the template's own heading structure. This is not the 104 regions in the contaminated Phase C manifest, which came from a different segmenter that has since been invalidated. The count is reported as measured; no target count was assumed.

### What can be automated with the files we actually have

| Readiness | Regions |
| :--- | ---: |
| `AUTO_NOOP_READY` | 2 |
| `HUMAN_REVIEW_READY` | 26 |
| `BLOCKED_MISSING_SOURCE` | 29 |
| `NOT_APPLICABLE` | 4 |

| Source coverage | Regions |
| :--- | ---: |
| `MISSING_SOURCE` | 29 |
| `FULLY_SUPPORTED` | 18 |
| `HUMAN_REVIEW` | 7 |
| `NOT_APPLICABLE` | 6 |
| `PARTIALLY_SUPPORTED` | 1 |

**No region is `AUTO_MUTATION_READY`.** (0 regions.) That is the honest answer: the current source set supports the *financial and related-party* domains well, supports the *benchmarking* domain not at all, and the mutation engine implements only row insertion, which is the wrong operation for almost every region that does have a source.

## A. Current Source Dataset Profiling (§3)

Every sheet profiled from content. Sheet names were never used to assign a role.

### `HMV-FA&RPT FY2024.xlsx`

| Sheet | Rows × Cols | Records | Domain | Pattern | Units | Formulas | Dataset roles |
| :--- | :--- | ---: | :--- | :--- | :--- | ---: | :--- |
| I. Related parties | 18 × 19 | 8 | ENTITY | TABULAR_TEXT | %, eur | 0 | UNKNOWN |
| FS | 66 × 9 | 45 | MIXED | TABULAR_WITH_NARRATIVE | vnd, usd | 30 | FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS, INTEREST_EXPENSE |
| RPTs | 17 × 7 | 12 | MIXED | TABULAR_TEXT | vnd, % | 27 | RELATED_PARTY_TRANSACTIONS |
| Financial Analysis | 71 × 7 | 51 | MIXED | TABULAR_NUMERIC | vnd | 47 | FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS |
| III. Summary-RPTs | 64 × 27 | 37 | MIXED | TABULAR_WITH_NARRATIVE | vnd, % | 64 | INTEREST_EXPENSE, RELATED_PARTY_TRANSACTIONS, APPENDIX_DISCLOSURE |

### `HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx`

| Sheet | Rows × Cols | Records | Domain | Pattern | Units | Formulas | Dataset roles |
| :--- | :--- | ---: | :--- | :--- | :--- | ---: | :--- |
| Checklist | 123 × 14 | 68 | ENTITY | TABULAR_WITH_NARRATIVE | — | 0 | RELATED_PARTY_TRANSACTIONS, APPENDIX_DISCLOSURE, SEGMENTED_DATA, TAXPAYER_PROFILE |
| Full Appendix I | 184 × 35 | 152 | MIXED | TABULAR_WITH_NARRATIVE | — | 314 | RELATED_PARTY_TRANSACTIONS |
| I. Related parties | 18 × 19 | 8 | ENTITY | TABULAR_TEXT | %, eur | 0 | UNKNOWN |
| Country list | 275 × 2 | 274 | ENTITY | TABULAR_TEXT | — | 0 | UNKNOWN |
| III. Summary-RPTs | 64 × 27 | 37 | MIXED | TABULAR_WITH_NARRATIVE | vnd, % | 77 | INTEREST_EXPENSE, RELATED_PARTY_TRANSACTIONS, APPENDIX_DISCLOSURE |
| IV. Segmented data | 40 × 20 | 28 | MONETARY | TABULAR_NUMERIC | % | 75 | FINANCIAL_STATEMENTS, INTEREST_EXPENSE |
| FS | 66 × 9 | 45 | MIXED | TABULAR_WITH_NARRATIVE | vnd, usd | 47 | FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS, INTEREST_EXPENSE |
| Interest expenses | 63 × 14 | 37 | MIXED | TABULAR_NUMERIC | vnd, % | 69 | SEGMENTED_DATA |
| Types of relationship | 18 × 5 | 13 | NARRATIVE | TABULAR_WITH_NARRATIVE | % | 0 | APPENDIX_DISCLOSURE |
| Transfer pricing method | 24 × 6 | 11 | NARRATIVE | TABULAR_WITH_NARRATIVE | — | 0 | UNKNOWN |
| Note FS | 427 × 19 | 344 | MONETARY | TABULAR_NUMERIC | vnd, usd | 889 | UNKNOWN |
| P&L | 35 × 11 | 14 | MIXED | TABULAR_NUMERIC | — | 104 | UNKNOWN |
| CF | 65536 × 11 | 46 | MONETARY | TABULAR_NUMERIC | vnd, usd | 166 | FIXED_ASSETS, INTEREST_EXPENSE |
| Exchange rate calculation | 29 × 8 | 21 | MONETARY | TABULAR_NUMERIC | vnd, usd | 14 | UNKNOWN |
| TỶ giá ngày TCB | 440 × 12 | 371 | MONETARY | TABULAR_NUMERIC | — | 1480 | UNKNOWN |
| Lãi vay vốn hóa - PBC | 125 × 14 | 118 | MIXED | TABULAR_NUMERIC | usd | 2 | UNKNOWN |
| IV. Segmented data_banking | 39 × 9 | 34 | MIXED | TABULAR_WITH_NARRATIVE | vnd | 30 | UNKNOWN |
| IV. Segmented data_securities | 82 × 9 | 76 | MIXED | TABULAR_NUMERIC | vnd | 67 | INTEREST_EXPENSE |

**Dataset roles present across the whole current source set**: `APPENDIX_DISCLOSURE`, `FINANCIAL_ANALYSIS`, `FINANCIAL_STATEMENTS`, `FIXED_ASSETS`, `INTEREST_EXPENSE`, `RELATED_PARTY_TRANSACTIONS`, `SEGMENTED_DATA`, `TAXPAYER_PROFILE`

## B. Benchmarking Domain Audit (§9) — PRIORITY

| Required benchmarking dataset | Role | Present | Sheets |
| :--- | :--- | :---: | :--- |
| comparable-company data | `COMPARABLE_COMPANIES` | ❌ **ABSENT** | — |
| search database / benchmarking output | `BENCHMARKING_DATA` | ❌ **ABSENT** | — |
| screening criteria & results | `SCREENING_RESULTS` | ❌ **ABSENT** | — |
| IQR / percentile results | `IQR_RESULTS` | ❌ **ABSENT** | — |

- BvD independence codes present: **False**
- Accepted/rejected comparables present: **False**
- Any benchmarking source at all: **False**

**Verdict.** NO benchmarking source of any kind exists in the current set; every dependent region is BLOCKED_MISSING_SOURCE. 5 region(s) depend on it: `rgn-046`, `rgn-051`, `rgn-052`, `rgn-055`, `rgn-061`.

**Minimum required artifact** (`BENCHMARKING_REPORT`):
- accepted comparable-company set with identifiers
- rejected companies with rejection reason
- search strategy and screening steps with pass counts
- BvD independence codes
- per-company PLI values for the tested period
- quartile / interquartile range statistics

## C. Source Requirement Matrix (§5)

| Region | Heading | Domain | Required source roles | Current artifact | Coverage | Readiness |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rgn-001` | PREAMBLE (before first heading) | TAXPAYER_PROFILE | TAXPAYER_PROFILE | HMV-25-Appendix I under D20 for FY… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-002` | Glossary | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **HUMAN_REVIEW** | `HUMAN_REVIEW_READY` |
| `rgn-003` | Objective and scope | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **HUMAN_REVIEW** | `HUMAN_REVIEW_READY` |
| `rgn-004` | Executive Summary | EXECUTIVE_SUMMARY | RELATED_PARTY_TRANSACTIONS, IQR_RESULTS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **PARTIALLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-006` | Information on ABC | TAXPAYER_PROFILE | TAXPAYER_PROFILE | HMV-25-Appendix I under D20 for FY… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-007` | Overview of the XYZ Group | GROUP_PROFILE | OWNERSHIP_STRUCTURE, NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-008` | Overview of ABC | BUSINESS_NARRATIVE | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-009` | Background | BUSINESS_NARRATIVE | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-010` | ABC’s organisation and management struct… | ORGANIZATION | ORGANIZATIONAL_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-011` | Business strategy | BUSINESS_NARRATIVE | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-012` | Business restructurings, capital transfe… | GROUP_PROFILE | OWNERSHIP_STRUCTURE, NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-013` | Companies having similar products / Key… | COMPETITOR_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-015` | Related party transactions | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-016` | Overview | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-017` | Details of related party transactions | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-018` | Sales of goods / merchandises / goods | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-019` | Purchases of materials / merchandises /… | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-020` | Provision of services | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-021` | Receipt of technical support services | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-022` | Payment of royalties / licensing fee / t… | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-023` | Payment of interest on intercompany loan… | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-024` | Purchases / sales of fixed assets | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-025` | Other transactions | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-026` | Values of intra-group payments and recei… | RELATED_PARTY_TRANSACTIONS | RELATED_PARTY_TRANSACTIONS | HMV-FA&RPT FY2024.xlsx!RPTs, HMV-F… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-027` | Copies of intercompany agreements | INTERCOMPANY_AGREEMENTS | CONTRACTUAL_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-028` | Analysis of functions, assets and risks | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-029` | Functions performed | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-030` | Research and development (“R&D”) | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-031` | Procurement | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-032` | Production/ Operation | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-033` | Production/ Operation scheduling | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-034` | Production/ Operation process | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-035` | Quality control and inspection | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-036` | Warehousing and Logistics | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-037` | Marketing and Sales | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-038` | After-sales services | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-039` | General Administration | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-040` | Assets used | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-041` | Risks assumed | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-042` | Characterization of ABC | FUNCTIONAL_ANALYSIS | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-043` | Changes from Previous Fiscal Year | BUSINESS_NARRATIVE | NARRATIVE_DATA | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-045` | Transfer pricing methods | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **HUMAN_REVIEW** | `HUMAN_REVIEW_READY` |
| `rgn-046` | Internal and external comparable data | BENCHMARKING | BENCHMARKING_DATA, COMPARABLE_COMPANIES, IQR_RESULTS, SCREENING_RESULTS | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-047` | Selection of the most appropriate transf… | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **HUMAN_REVIEW** | `HUMAN_REVIEW_READY` |
| `rgn-048` | Application of CPM | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **NOT_APPLICABLE** | `AUTO_NOOP_READY` |
| `rgn-049` | Selection of tested party | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **HUMAN_REVIEW** | `HUMAN_REVIEW_READY` |
| `rgn-050` | Selection of profit level indicator (“PL… | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **HUMAN_REVIEW** | `HUMAN_REVIEW_READY` |
| `rgn-051` | Search for comparable companies | BENCHMARKING | BENCHMARKING_DATA, COMPARABLE_COMPANIES, IQR_RESULTS, SCREENING_RESULTS | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-052` | Use of standard arm’s length range | BENCHMARKING | BENCHMARKING_DATA, COMPARABLE_COMPANIES, IQR_RESULTS, SCREENING_RESULTS | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-053` | Use of previous year and multiple year d… | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **HUMAN_REVIEW** | `HUMAN_REVIEW_READY` |
| `rgn-054` | Adjustments | STATUTORY_METHODOLOGY | STATUTORY_TEXT | — | **NOT_APPLICABLE** | `AUTO_NOOP_READY` |
| `rgn-055` | The standard arm’s length range | BENCHMARKING | BENCHMARKING_DATA, COMPARABLE_COMPANIES, IQR_RESULTS, SCREENING_RESULTS | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |
| `rgn-057` | Financial information | FINANCIAL_INFORMATION | FINANCIAL_STATEMENTS, FINANCIAL_ANALYSIS | HMV-FA&RPT FY2024.xlsx!FS, HMV-FA&… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-058` | ABC’s audited financial statements in FY… | FINANCIAL_INFORMATION | FINANCIAL_STATEMENTS, FINANCIAL_ANALYSIS | HMV-FA&RPT FY2024.xlsx!FS, HMV-FA&… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-059` | Allocation method used in the calculatio… | FINANCIAL_INFORMATION | FINANCIAL_STATEMENTS, FINANCIAL_ANALYSIS | HMV-FA&RPT FY2024.xlsx!FS, HMV-FA&… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-060` | Summary of financial data in relation to… | FINANCIAL_INFORMATION | FINANCIAL_STATEMENTS, FINANCIAL_ANALYSIS | HMV-FA&RPT FY2024.xlsx!FS, HMV-FA&… | **FULLY_SUPPORTED** | `HUMAN_REVIEW_READY` |
| `rgn-061` | Summary of reasons and explanation for t… | BENCHMARKING | BENCHMARKING_DATA, COMPARABLE_COMPANIES, IQR_RESULTS, SCREENING_RESULTS | — | **MISSING_SOURCE** | `BLOCKED_MISSING_SOURCE` |

_4 further regions are structural containers or empty and are classified `NOT_APPLICABLE`._

## D. Source Completeness Scorecard (§13)

Counts of regions per coverage status. No weighting is applied.

| Domain | Regions | Fully | Partial | N/A (static) | Missing | Insufficient | Supported % |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FUNCTIONAL_ANALYSIS | 15 | 0 | 0 | 0 | 15 | 0 | **0.0%** |
| RELATED_PARTY_TRANSACTIONS | 12 | 12 | 0 | 0 | 0 | 0 | **100.0%** |
| STATUTORY_METHODOLOGY | 9 | 0 | 0 | 2 | 0 | 0 | **22.2%** |
| BENCHMARKING | 5 | 0 | 0 | 0 | 5 | 0 | **0.0%** |
| BUSINESS_NARRATIVE | 4 | 0 | 0 | 0 | 4 | 0 | **0.0%** |
| FINANCIAL_INFORMATION | 4 | 4 | 0 | 0 | 0 | 0 | **100.0%** |
| TAXPAYER_PROFILE | 2 | 2 | 0 | 0 | 0 | 0 | **100.0%** |
| GROUP_PROFILE | 2 | 0 | 0 | 0 | 2 | 0 | **0.0%** |
| EXECUTIVE_SUMMARY | 1 | 0 | 1 | 0 | 0 | 0 | **100.0%** |
| ORGANIZATION | 1 | 0 | 0 | 0 | 1 | 0 | **0.0%** |
| COMPETITOR_ANALYSIS | 1 | 0 | 0 | 0 | 1 | 0 | **0.0%** |
| INTERCOMPANY_AGREEMENTS | 1 | 0 | 0 | 0 | 1 | 0 | **0.0%** |

_All percentages are counts of regions per coverage status divided by the number of classified regions in that domain. No weighting is applied._

## E. Figure / Media Readiness (§11)

The template package contains **no raster media and no charts** (`word/media/` is empty, no `word/charts/`). Of 38 drawing constructs, **35 are layout text boxes**, not figures. Only **3** are data-bearing figures, and **0** of them can be automated from the current sources.

| Figure | Para | Kind | Shapes | SmartArt | Raster | Readiness | Required artifact |
| :--- | ---: | :--- | ---: | :---: | :---: | :--- | :--- |
| `fig-p0091` | 91 | **ORGANIZATION_CHART** | 10 | — | — | `HUMAN_REVIEW` | ORGANIZATION_CHART |
| `fig-p0127` | 127 | **TRANSACTION_FLOW** | 1 | — | — | `HUMAN_REVIEW` | MANAGEMENT_INFORMATION |
| `fig-p0179` | 179 | **PROCESS_FLOW** | 1 | ✅ | — | `HUMAN_REVIEW` | FIGURE_CHART_SOURCE |

- **`fig-p0091` (ORGANIZATION_CHART)** — Shape-and-connector organisation chart; requires a current-year org chart.
- **`fig-p0127` (TRANSACTION_FLOW)** — Drawing canvas holding a related-party transaction flow; its node labels are client-specific and no current source enumerates them.
- **`fig-p0179` (PROCESS_FLOW)** — SmartArt diagram (word/diagrams/*). Editing requires the SmartArt data model, which no current source supplies.

| Figure readiness | Count |
| :--- | ---: |
| `STATIC_PRESERVE` | 35 |
| `HUMAN_REVIEW` | 3 |

## F. Historical Text as a Source (§12)

FY2023 text is never promoted to current-year verified merely because it existed.

| Historical reuse class | Regions | Meaning |
| :--- | ---: | :--- |
| `REQUIRES_CURRENT_YEAR_SOURCE` | 26 | Year-specific facts (amounts, comparables, headcount, agreements) — reuse is unsafe. |
| `REUSABLE_WITH_VERIFICATION` | 22 | Narrative that is probably still true but must be confirmed against current facts. |
| `REUSABLE_BASELINE` | 9 | Statutory / methodological text that does not change year on year. |

## G. Required Additional Artifacts (§14)

| ID | Type | Priority | Blocking | Regions | Title |
| :--- | :--- | :--- | :---: | ---: | :--- |
| `ART-001` | MANAGEMENT_INFORMATION | **BLOCKING** | ✅ | 15 | Management information / client questionnaire — FUNC… |
| `ART-002` | BENCHMARKING_REPORT | **BLOCKING** | ✅ | 5 | Benchmarking / comparable-company dataset — BENCHMAR… |
| `ART-003` | MANAGEMENT_INFORMATION | **BLOCKING** | ✅ | 4 | Management information / client questionnaire — BUSI… |
| `ART-004` | NARRATIVE_DOCUMENT | **BLOCKING** | ✅ | 2 | Current-year narrative source document — GROUP_PROFI… |
| `ART-005` | BENCHMARKING_REPORT | **LOW** | — | 1 | Benchmarking / comparable-company dataset — EXECUTIV… |
| `ART-006` | CONTRACTUAL_DOCUMENT | **BLOCKING** | ✅ | 1 | Executed intercompany agreements — INTERCOMPANY_AGRE… |
| `ART-007` | MANAGEMENT_INFORMATION | **BLOCKING** | ✅ | 1 | Management information / client questionnaire — COMP… |
| `ART-008` | ORGANIZATION_CHART | **BLOCKING** | ✅ | 1 | Current-year organisation / ownership chart — ORGANI… |

### `ART-001` — Management information / client questionnaire — FUNCTIONAL_ANALYSIS

- **Type**: `MANAGEMENT_INFORMATION`
- **Priority**: **BLOCKING**
- **Reason required**: 15 region(s) in domain FUNCTIONAL_ANALYSIS cannot be completed from the current source set; their required dataset roles are absent or only partially present.
- **Affected regions** (15): `rgn-028`, `rgn-029`, `rgn-030`, `rgn-031`, `rgn-032`, `rgn-033`, `rgn-034`, `rgn-035`, `rgn-036`, `rgn-037`, `rgn-038`, `rgn-039`, `rgn-040`, `rgn-041` …
- **Required content**:
  - current-year functional profile
  - assets deployed
  - risks borne
  - entity characterisation

### `ART-002` — Benchmarking / comparable-company dataset — BENCHMARKING

- **Type**: `BENCHMARKING_REPORT`
- **Priority**: **BLOCKING**
- **Reason required**: 5 region(s) in domain BENCHMARKING cannot be completed from the current source set; their required dataset roles are absent or only partially present.
- **Affected regions** (5): `rgn-046`, `rgn-051`, `rgn-052`, `rgn-055`, `rgn-061`
- **Required content**:
  - comparable company set
  - screening criteria
  - independence codes
  - accepted/rejected comparables
  - PLI values
  - quartile / IQR results

### `ART-003` — Management information / client questionnaire — BUSINESS_NARRATIVE

- **Type**: `MANAGEMENT_INFORMATION`
- **Priority**: **BLOCKING**
- **Reason required**: 4 region(s) in domain BUSINESS_NARRATIVE cannot be completed from the current source set; their required dataset roles are absent or only partially present.
- **Affected regions** (4): `rgn-008`, `rgn-009`, `rgn-011`, `rgn-043`
- **Required content**:
  - current-year business facts
  - strategy statement
  - restructuring events

### `ART-004` — Current-year narrative source document — GROUP_PROFILE

- **Type**: `NARRATIVE_DOCUMENT`
- **Priority**: **BLOCKING**
- **Reason required**: 2 region(s) in domain GROUP_PROFILE cannot be completed from the current source set; their required dataset roles are absent or only partially present.
- **Affected regions** (2): `rgn-007`, `rgn-012`
- **Required content**:
  - group structure
  - ultimate parent
  - group activities

### `ART-005` — Benchmarking / comparable-company dataset — EXECUTIVE_SUMMARY

- **Type**: `BENCHMARKING_REPORT`
- **Priority**: **LOW**  (not blocking: the affected regions are partially supported)
- **Reason required**: 1 region(s) in domain EXECUTIVE_SUMMARY cannot be completed from the current source set; their required dataset roles are absent or only partially present.
- **Affected regions** (1): `rgn-004`
- **Required content**:
  - transaction summary
  - method selected
  - arm's-length conclusion

### `ART-006` — Executed intercompany agreements — INTERCOMPANY_AGREEMENTS

- **Type**: `CONTRACTUAL_DOCUMENT`
- **Priority**: **BLOCKING**
- **Reason required**: 1 region(s) in domain INTERCOMPANY_AGREEMENTS cannot be completed from the current source set; their required dataset roles are absent or only partially present.
- **Affected regions** (1): `rgn-027`
- **Required content**:
  - agreement inventory
  - counterparties
  - effective dates
  - pricing terms

### `ART-007` — Management information / client questionnaire — COMPETITOR_ANALYSIS

- **Type**: `MANAGEMENT_INFORMATION`
- **Priority**: **BLOCKING**
- **Reason required**: 1 region(s) in domain COMPETITOR_ANALYSIS cannot be completed from the current source set; their required dataset roles are absent or only partially present.
- **Affected regions** (1): `rgn-013`
- **Required content**:
  - competitor identities
  - market position
  - product overlap

### `ART-008` — Current-year organisation / ownership chart — ORGANIZATION

- **Type**: `ORGANIZATION_CHART`
- **Priority**: **BLOCKING**
- **Reason required**: 1 region(s) in domain ORGANIZATION cannot be completed from the current source set; their required dataset roles are absent or only partially present.
- **Affected regions** (1): `rgn-010`
- **Required content**:
  - current organisation chart
  - reporting lines
  - headcount

## H. Human Review Work Queue (§16)

55 items, of which **29 are blocking**.

| Region | Heading | Blocking | Issue | Human evidence request |
| :--- | :--- | :---: | :--- | :--- |
| `rgn-001` | PREAMBLE (before first heading) | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-002` | Glossary | — | Region contains 2 template placeholder token(s) (ABC / XYZ / FY20xx); these mu… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-003` | Objective and scope | — | Region contains 4 template placeholder token(s) (ABC / XYZ / FY20xx); these mu… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-004` | Executive Summary | — | Partially supported: ['RELATED_PARTY_TRANSACTIONS'] available, ['IQR_RESULTS']… | Obtain a BENCHMARKING_REPORT covering transaction summary, method selected, ar… |
| `rgn-006` | Information on ABC | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-007` | Overview of the XYZ Group | ✅ | None of the required dataset roles ['OWNERSHIP_STRUCTURE', 'NARRATIVE_DATA'] i… | Obtain a NARRATIVE_DOCUMENT covering group structure, ultimate parent, group a… |
| `rgn-008` | Overview of ABC | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year business facts, strategy… |
| `rgn-009` | Background | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year business facts, strategy… |
| `rgn-010` | ABC’s organisation and managemen… | ✅ | None of the required dataset roles ['ORGANIZATIONAL_DATA'] is present in the c… | Obtain a ORGANIZATION_CHART covering current organisation chart, reporting lin… |
| `rgn-011` | Business strategy | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year business facts, strategy… |
| `rgn-012` | Business restructurings, capital… | ✅ | None of the required dataset roles ['OWNERSHIP_STRUCTURE', 'NARRATIVE_DATA'] i… | Obtain a NARRATIVE_DOCUMENT covering group structure, ultimate parent, group a… |
| `rgn-013` | Companies having similar product… | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering competitor identities, market positio… |
| `rgn-015` | Related party transactions | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-016` | Overview | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-017` | Details of related party transac… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-018` | Sales of goods / merchandises /… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-019` | Purchases of materials / merchan… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-020` | Provision of services | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-021` | Receipt of technical support ser… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-022` | Payment of royalties / licensing… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-023` | Payment of interest on intercomp… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-024` | Purchases / sales of fixed asset… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-025` | Other transactions | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-026` | Values of intra-group payments a… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-027` | Copies of intercompany agreement… | ✅ | None of the required dataset roles ['CONTRACTUAL_DATA'] is present in the curr… | Obtain a CONTRACTUAL_DOCUMENT covering agreement inventory, counterparties, ef… |
| `rgn-028` | Analysis of functions, assets an… | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-029` | Functions performed | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-030` | Research and development (“R&D”) | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-031` | Procurement | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-032` | Production/ Operation | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-033` | Production/ Operation scheduling | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-034` | Production/ Operation process | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-035` | Quality control and inspection | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-036` | Warehousing and Logistics | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-037` | Marketing and Sales | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-038` | After-sales services | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-039` | General Administration | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-040` | Assets used | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-041` | Risks assumed | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-042` | Characterization of ABC | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year functional profile, asse… |
| `rgn-043` | Changes from Previous Fiscal Yea… | ✅ | None of the required dataset roles ['NARRATIVE_DATA'] is present in the curren… | Obtain a MANAGEMENT_INFORMATION covering current-year business facts, strategy… |
| `rgn-045` | Transfer pricing methods | — | Region contains 1 template placeholder token(s) (ABC / XYZ / FY20xx); these mu… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-046` | Internal and external comparable… | ✅ | None of the required dataset roles ['BENCHMARKING_DATA', 'COMPARABLE_COMPANIES… | Obtain a BENCHMARKING_REPORT covering comparable company set, screening criter… |
| `rgn-047` | Selection of the most appropriat… | — | Region contains 4 template placeholder token(s) (ABC / XYZ / FY20xx); these mu… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-049` | Selection of tested party | — | Region contains 1 template placeholder token(s) (ABC / XYZ / FY20xx); these mu… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-050` | Selection of profit level indica… | — | Region contains 4 template placeholder token(s) (ABC / XYZ / FY20xx); these mu… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-051` | Search for comparable companies | ✅ | None of the required dataset roles ['BENCHMARKING_DATA', 'COMPARABLE_COMPANIES… | Obtain a BENCHMARKING_REPORT covering comparable company set, screening criter… |
| `rgn-052` | Use of standard arm’s length ran… | ✅ | None of the required dataset roles ['BENCHMARKING_DATA', 'COMPARABLE_COMPANIES… | Obtain a BENCHMARKING_REPORT covering comparable company set, screening criter… |
| `rgn-053` | Use of previous year and multipl… | — | Region contains 6 template placeholder token(s) (ABC / XYZ / FY20xx); these mu… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-055` | The standard arm’s length range | ✅ | None of the required dataset roles ['BENCHMARKING_DATA', 'COMPARABLE_COMPANIES… | Obtain a BENCHMARKING_REPORT covering comparable company set, screening criter… |
| `rgn-057` | Financial information | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-058` | ABC’s audited financial statemen… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-059` | Allocation method used in the ca… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-060` | Summary of financial data in rel… | — | All required dataset roles are present, but no implemented mutation strategy c… | Confirm the carried-forward content still applies to the current fiscal year a… |
| `rgn-061` | Summary of reasons and explanati… | ✅ | None of the required dataset roles ['BENCHMARKING_DATA', 'COMPARABLE_COMPANIES… | Obtain a BENCHMARKING_REPORT covering comparable company set, screening criter… |

## I. Currently Available vs Required-but-Missing (§18)

### Currently available

| Workbook | Sheets | Dataset roles supplied |
| :--- | ---: | :--- |
| `HMV-FA&RPT FY2024.xlsx` | 5 | APPENDIX_DISCLOSURE, FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS, INTEREST_EXPENSE, RELATED_PARTY_TRANSACTIONS |
| `HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx` | 18 | APPENDIX_DISCLOSURE, FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS, FIXED_ASSETS, INTEREST_EXPENSE, RELATED_PARTY_TRANSACTIONS, SEGMENTED_DATA, TAXPAYER_PROFILE |

### Required but missing

| Dataset role | Needed by | Supplied by any current source |
| :--- | ---: | :---: |
| `NARRATIVE_DATA` | 22 region(s) | ❌ |
| `STATUTORY_TEXT` | 9 region(s) | ❌ |
| `IQR_RESULTS` | 6 region(s) | ❌ |
| `BENCHMARKING_DATA` | 5 region(s) | ❌ |
| `COMPARABLE_COMPANIES` | 5 region(s) | ❌ |
| `SCREENING_RESULTS` | 5 region(s) | ❌ |
| `OWNERSHIP_STRUCTURE` | 2 region(s) | ❌ |
| `ORGANIZATIONAL_DATA` | 1 region(s) | ❌ |
| `CONTRACTUAL_DATA` | 1 region(s) | ❌ |

> No binding was created to satisfy any of the above. Absence is reported as absence.

## J. Ground Truth Evaluation (§17) — post-freeze, evaluation-only

Readiness altered by this section: **False**.

| Gap | Status | Detail |
| :--- | :--- | :--- |
| Benchmarking / comparable-company data absent from current s… | **VERIFIED** | FY2024 contains 2 comparable-company table(s) and 2 screening table(s); FY2023 contained 2 comparable-company table(s). The FY2024 file therefore required benchmarking content that no suppli… |
| FY2023 benchmarking text cannot be reused as current-year ve… | **VERIFIED** | Comparable-set size changed from [14, 14] (FY2023) to [11, 11] (FY2024). |
| Corporate narrative requires current-year management informa… | **STRONGLY_SUPPORTED** | FY2024 carries 514 body paragraphs against FY2023's 538. The narrative was rewritten rather than copied, supporting the finding that these regions need current-year evidence rather than hist… |
| Template table set is not a positional match to either year | **VERIFIED** | FY2023 has 22 tables, the template 16, FY2024 19. The audit correlated by content and never by index. |

> Evaluation-only. Ground Truth was opened after the readiness map was frozen and was not used to discover, invent or bind any source artifact.

## K. The Two Questions

### What can we safely automate with the files we actually have?

- **2 region(s)** are `AUTO_NOOP_READY`: statutory methodology text that carries forward unchanged and needs no current source.
- **0 regions** are `AUTO_MUTATION_READY`. Two independent reasons: the benchmarking domain has no source at all, and for the domains that *do* have a source the required operation is cell update or data-region replacement, neither of which is implemented.

### What exact additional files or human evidence are required?

- **ART-001** (`MANAGEMENT_INFORMATION`, BLOCKING) — Management information / client questionnaire — FUNCTIONAL_ANALYSIS; unblocks 15 region(s).
- **ART-002** (`BENCHMARKING_REPORT`, BLOCKING) — Benchmarking / comparable-company dataset — BENCHMARKING; unblocks 5 region(s).
- **ART-003** (`MANAGEMENT_INFORMATION`, BLOCKING) — Management information / client questionnaire — BUSINESS_NARRATIVE; unblocks 4 region(s).
- **ART-004** (`NARRATIVE_DOCUMENT`, BLOCKING) — Current-year narrative source document — GROUP_PROFILE; unblocks 2 region(s).
- **ART-006** (`CONTRACTUAL_DOCUMENT`, BLOCKING) — Executed intercompany agreements — INTERCOMPANY_AGREEMENTS; unblocks 1 region(s).
- **ART-007** (`MANAGEMENT_INFORMATION`, BLOCKING) — Management information / client questionnaire — COMPETITOR_ANALYSIS; unblocks 1 region(s).
- **ART-008** (`ORGANIZATION_CHART`, BLOCKING) — Current-year organisation / ownership chart — ORGANIZATION; unblocks 1 region(s).
- ART-005 (`BENCHMARKING_REPORT`, LOW) — Benchmarking / comparable-company dataset — EXECUTIVE_SUMMARY; affects 1 region(s).

---

*Regenerate with `python foundation/tests/evaluation/source_completeness_audit.py`.*
