# Local File Roll-Forward Source Intake & Region Model Reconciliation (Phase F)

**Date**: 2026-08-23  
**Mode**: source intake + evidence infrastructure — no mutation capability added  
**Ground Truth**: quarantined; ingestion refused by `GroundTruthGuard`  

---

## A. Region Model Reconciliation (§2)

**Question**: Is 61 the count of semantic Sections and 81 the count of executable Regions?

**Answer**: NO. Neither figure is correct, and they are not two layers of one hierarchy.

| Claim | Claimed by | Produced by | Verdict |
| ---: | :--- | :--- | :--- |
| **61** | Phase E source-completeness audit | heading-delimited segmentation over Heading 1-4 / Title / Subtitle | **UNDERCOUNT — correct method, incomplete style set** |
| **81** | Phase B template profile report (markdown prose) | nothing — no code path produces 81 | **UNSUPPORTED — contradicted by its own run's JSON** |
| **104** | Phase B/C manifest and template profile JSON | TemplateRegionSegmenter element-block segmentation | **OVERCOUNT — table-of-contents lines counted as sections** |

- **61** — It matched the 60 main-outline headings but not the 17 `Appendix Heading` / `Appendix Heading 2` / `Appendix Heading 3` paragraphs, which are real headings in this template. 60 + 1 preamble = 61.
- **81** — The same profiling run wrote 104 into `LocalFile_RollForward_Template_Profile_2026-08-21.json` (`statistics.total_regions`). The figure 81 appears only in the report prose, in a document already marked INVALIDATED_FOR_PLANNING_CONTAMINATION.
- **104** — Its heading test accepted `toc 1` / `toc 2` paragraphs such as 'PART A. TAXPAYER INFORMATION<tab>4', which are contents entries carrying a page number. This template holds 38 such paragraphs. It also emitted several regions per section.

### Evidence: paragraph styles in the template

| Style | Paragraphs | Role in the model |
| :--- | ---: | :--- |
| `Heading 3` | 24 | opens a SECTION (main outline) |
| `Heading 2` | 20 | opens a SECTION (main outline) |
| `Heading 1` | 11 | opens a SECTION (main outline) |
| `Appendix Heading 2` | 8 | opens a SECTION (appendix outline) |
| `Appendix Heading` | 6 | opens a SECTION (appendix outline) |
| `Heading 4` | 5 | opens a SECTION (main outline) |
| `Appendix Heading 3` | 3 | opens a SECTION (appendix outline) |
| `toc 1` / `toc 2` | 38 | **never opens a section** — contents lines |

The main outline carries **60** headings and the appendix band **17**. Phase E saw only the first group, which is exactly the 61 − 78 gap.

### The canonical hierarchy

| Layer | Count | Rule |
| :--- | ---: | :--- |
| DOCUMENT | 1 | the template |
| SECTION | **78** | Heading 1-4, Title, Subtitle, Appendix Heading 1-3; never toc 1 / toc 2 (table-of-contents lines) |
| REGION | **94** | one narrative-body region per section, plus one region per contained table |
| SUBREGION | 54 | tables and figures |
| ELEMENT | 848 | Foundation perception blocks |

The section and region layers are an **exact partition** of the document body (`is_exact_partition = True`): every one of 314 paragraphs and 16 tables belongs to exactly one section and exactly one region.

> No region was renamed or merged. The historical counts are recorded above with the code that produced them; the canonical model is stated separately.

## B. Source Package V1 (§4)

- **Package**: `LOCALFILE-ROLLFORWARD-SOURCES` version **5** (status `DRAFT`)
- **Package hash**: `6f000a1fec049a028ed56b494f9446a54df1e76a7ab2c7786b39f21ea10547a9`
- **Artifacts**: 4

| Artifact | Scope | Format | Size | SHA256 | Dataset roles |
| :--- | :--- | :--- | ---: | :--- | :--- |
| `HMV-24-Final-Local File for FY2023-EN-R0303K` | HISTORICAL | DOCX | 2,764,267 | `8b51f941e106…` | COMPARABLE_COMPANIES, IQR_RESULTS, SCREENING_RESULTS, INDEPENDENCE_CODES, BENCHMARKING_DATA, FAR, GROUP_NARRATIVE, BUSINESS_NARRATIVE, CONTRACTUAL_DATA, ORGANIZATIONAL_DATA, OWNERSHIP_STRUCTURE, TAX_SCHEDULE, RPT, INTEREST_EXPENSE, FINANCIAL_STATEMENTS, FINANCIAL_ANALYSIS, APPENDIX_DISCLOSURE, FIGURE_SOURCE |
| `Client-25-Template-Local File for FY20XX-Man` | TEMPLATE | DOCX | 2,819,648 | `5fdf55e4e600…` | COMPARABLE_COMPANIES, IQR_RESULTS, SCREENING_RESULTS, BENCHMARKING_DATA, FAR, GROUP_NARRATIVE, BUSINESS_NARRATIVE, CONTRACTUAL_DATA, OWNERSHIP_STRUCTURE, TAXPAYER_PROFILE, RPT, INTEREST_EXPENSE, FINANCIAL_STATEMENTS, FINANCIAL_ANALYSIS, SEGMENTED_DATA, APPENDIX_DISCLOSURE |
| `HMV-FA&RPT FY2024.xlsx` | CURRENT_FINANCIAL | XLSX | 404,891 | `9574dcc037af…` | RPT, FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS, INTEREST_EXPENSE, APPENDIX_DISCLOSURE |
| `HMV-25-Appendix I under D20 for FY2024-Final` | CURRENT_TAX | XLSX | 3,004,377 | `80e0b0deb594…` | RPT, APPENDIX_DISCLOSURE, SEGMENTED_DATA, INTEREST_EXPENSE, FINANCIAL_STATEMENTS, FINANCIAL_ANALYSIS, FIXED_ASSETS |

### Evidence quality per role

| Artifact | Role | Quality | Records | Located in | Rationale |
| :--- | :--- | :--- | ---: | :--- | :--- |
| `HMV-24-Final-Local File fo` | COMPARABLE_COMPANIES | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 7 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | IQR_RESULTS | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 3 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | SCREENING_RESULTS | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 9 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | INDEPENDENCE_CODES | **STRONGLY_SUPPORTED** | 559 | 22 table(s), 493 paragraph(s) | 2 content signal(s) over 559 record(s). |
| `HMV-24-Final-Local File fo` | BENCHMARKING_DATA | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 3 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | FAR | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 6 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | GROUP_NARRATIVE | **STRONGLY_SUPPORTED** | 559 | 22 table(s), 493 paragraph(s) | 2 content signal(s) over 559 record(s). |
| `HMV-24-Final-Local File fo` | BUSINESS_NARRATIVE | **STRONGLY_SUPPORTED** | 559 | 22 table(s), 493 paragraph(s) | 2 content signal(s) over 559 record(s). |
| `HMV-24-Final-Local File fo` | CONTRACTUAL_DATA | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 4 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | ORGANIZATIONAL_DATA | **STRONGLY_SUPPORTED** | 559 | 22 table(s), 493 paragraph(s) | 2 content signal(s) over 559 record(s). |
| `HMV-24-Final-Local File fo` | OWNERSHIP_STRUCTURE | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 3 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | TAX_SCHEDULE | **STRONGLY_SUPPORTED** | 559 | 22 table(s), 493 paragraph(s) | 2 content signal(s) over 559 record(s). |
| `HMV-24-Final-Local File fo` | RPT | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 4 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | INTEREST_EXPENSE | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 4 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | FINANCIAL_STATEMENTS | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 4 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | FINANCIAL_ANALYSIS | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 6 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | APPENDIX_DISCLOSURE | **VERIFIED** | 559 | 22 table(s), 493 paragraph(s) | 3 schema signals over 559 structured records. |
| `HMV-24-Final-Local File fo` | FIGURE_SOURCE | **STRONGLY_SUPPORTED** | 559 | 22 table(s), 493 paragraph(s) | 2 content signal(s) over 559 record(s). |
| `Client-25-Template-Local F` | COMPARABLE_COMPANIES | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 7 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | IQR_RESULTS | **STRONGLY_SUPPORTED** | 132 | 16 table(s), 269 paragraph(s) | 2 content signal(s) over 132 record(s). |
| `Client-25-Template-Local F` | SCREENING_RESULTS | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 3 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | BENCHMARKING_DATA | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 3 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | FAR | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 5 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | GROUP_NARRATIVE | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 3 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | BUSINESS_NARRATIVE | **STRONGLY_SUPPORTED** | 132 | 16 table(s), 269 paragraph(s) | 2 content signal(s) over 132 record(s). |
| `Client-25-Template-Local F` | CONTRACTUAL_DATA | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 3 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | OWNERSHIP_STRUCTURE | **STRONGLY_SUPPORTED** | 132 | 16 table(s), 269 paragraph(s) | 2 content signal(s) over 132 record(s). |
| `Client-25-Template-Local F` | TAXPAYER_PROFILE | **STRONGLY_SUPPORTED** | 132 | 16 table(s), 269 paragraph(s) | 2 content signal(s) over 132 record(s). |
| `Client-25-Template-Local F` | RPT | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 6 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | INTEREST_EXPENSE | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 4 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | FINANCIAL_STATEMENTS | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 4 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | FINANCIAL_ANALYSIS | **VERIFIED** | 132 | 16 table(s), 269 paragraph(s) | 6 schema signals over 132 structured records. |
| `Client-25-Template-Local F` | SEGMENTED_DATA | **STRONGLY_SUPPORTED** | 132 | 16 table(s), 269 paragraph(s) | 2 content signal(s) over 132 record(s). |
| `Client-25-Template-Local F` | APPENDIX_DISCLOSURE | **STRONGLY_SUPPORTED** | 132 | 16 table(s), 269 paragraph(s) | 2 content signal(s) over 132 record(s). |
| `HMV-FA&RPT FY2024.xlsx` | RPT | **STRONGLY_SUPPORTED** | 8 | I. Related parties, RPTs | 2 content signal(s) over 8 record(s). |
| `HMV-FA&RPT FY2024.xlsx` | FINANCIAL_ANALYSIS | **STRONGLY_SUPPORTED** | 45 | FS | content profiler credited FINANCIAL_ANALYSIS on this sheet. |
| `HMV-FA&RPT FY2024.xlsx` | FINANCIAL_STATEMENTS | **STRONGLY_SUPPORTED** | 45 | FS | content profiler credited FINANCIAL_STATEMENTS on this sheet. |
| `HMV-FA&RPT FY2024.xlsx` | INTEREST_EXPENSE | **STRONGLY_SUPPORTED** | 45 | FS | content profiler credited INTEREST_EXPENSE on this sheet. |
| `HMV-FA&RPT FY2024.xlsx` | APPENDIX_DISCLOSURE | **STRONGLY_SUPPORTED** | 37 | III. Summary-RPTs | 2 content signal(s) over 37 record(s). |
| `HMV-25-Appendix I under D2` | RPT | **STRONGLY_SUPPORTED** | 68 | Checklist, I. Related parties | content profiler credited RPT_DATA on this sheet. |
| `HMV-25-Appendix I under D2` | APPENDIX_DISCLOSURE | **STRONGLY_SUPPORTED** | 68 | Checklist, III. Summary-RPTs | content profiler credited REFERENCE_LIST on this sheet. |
| `HMV-25-Appendix I under D2` | SEGMENTED_DATA | **STRONGLY_SUPPORTED** | 68 | Checklist, Interest expenses | content profiler credited SEGMENTED_DATA on this sheet. |
| `HMV-25-Appendix I under D2` | INTEREST_EXPENSE | **STRONGLY_SUPPORTED** | 37 | III. Summary-RPTs | content profiler credited INTEREST_EXPENSE on this sheet. |
| `HMV-25-Appendix I under D2` | FINANCIAL_STATEMENTS | **STRONGLY_SUPPORTED** | 28 | IV. Segmented data | content profiler credited FINANCIAL_STATEMENTS on this sheet. |
| `HMV-25-Appendix I under D2` | FINANCIAL_ANALYSIS | **STRONGLY_SUPPORTED** | 45 | FS | content profiler credited FINANCIAL_ANALYSIS on this sheet. |
| `HMV-25-Appendix I under D2` | FIXED_ASSETS | **STRONGLY_SUPPORTED** | 46 | CF | content profiler credited FIXED_ASSETS on this sheet. |

**Roles available at VERIFIED quality**: _none_

**Roles available at any quality**: `APPENDIX_DISCLOSURE`, `FINANCIAL_ANALYSIS`, `FINANCIAL_STATEMENTS`, `FIXED_ASSETS`, `INTEREST_EXPENSE`, `RPT`, `SEGMENTED_DATA`

### Why the historical file and the template supply nothing

A prior-year Local File and the master template are Local File *documents*: their prose discusses comparables, quartiles, functions and risks at length, so naive content matching credits them with almost every role in the taxonomy. They are the workflow's structural and baseline inputs, never its current-year data sources.

| Artifact | Scope | Roles its content matched | May supply current-year roles |
| :--- | :--- | :--- | :---: |
| `HMV-24-Final-Local File for FY2023-EN-R0` | HISTORICAL | 18 role(s) matched in prose | **NO** |
| `Client-25-Template-Local File for FY20XX` | TEMPLATE | 16 role(s) matched in prose | **NO** |

> Treating a prior-year output as a current-year source is precisely the contamination Phase D3.1 found. `SUPPLYING_SCOPES` makes it structurally impossible rather than a matter of care.

### Divergence from the Phase E role set

| Role | Phase E | Phase F | Why |
| :--- | :---: | :---: | :--- |
| `TAXPAYER_PROFILE` | present | absent | Phase E's signal set is broader (it accepts 'company name' / 'address' / 'taxpayer'); Phase F requires stronger dataset-shaped evidence. |

This divergence is reported rather than reconciled by fiat: two independently authored signal sets disagree on one weakly-evidenced role, and the stricter verdict is the safer one to carry forward.

## C. Source Request Matrix (§9)

7 requests, **7 blocking and still outstanding**.

| Request | Type | Required dataset roles | Regions | Status | Missing roles |
| :--- | :--- | :--- | ---: | :--- | :--- |
| `REQ-001` | MANAGEMENT_INFORMATION | FAR, BUSINESS_NARRATIVE | 15 | **OUTSTANDING** | FAR, BUSINESS_NARRATIVE |
| `REQ-002` | BENCHMARKING_REPORT | COMPARABLE_COMPANIES, SCREENING_RESULTS, IQR_RESULTS, INDEPENDENCE_CODES | 5 | **OUTSTANDING** | COMPARABLE_COMPANIES, SCREENING_RESULTS, IQR_RESULTS, INDEPENDENCE_CODES |
| `REQ-003` | MANAGEMENT_INFORMATION | FAR, BUSINESS_NARRATIVE | 4 | **OUTSTANDING** | FAR, BUSINESS_NARRATIVE |
| `REQ-004` | NARRATIVE_DOCUMENT | GROUP_NARRATIVE | 2 | **OUTSTANDING** | GROUP_NARRATIVE |
| `REQ-005` | CONTRACTUAL_DOCUMENT | CONTRACTUAL_DATA | 1 | **OUTSTANDING** | CONTRACTUAL_DATA |
| `REQ-006` | MANAGEMENT_INFORMATION | FAR, BUSINESS_NARRATIVE | 1 | **OUTSTANDING** | FAR, BUSINESS_NARRATIVE |
| `REQ-007` | ORGANIZATION_CHART | ORGANIZATIONAL_DATA | 1 | **OUTSTANDING** | ORGANIZATIONAL_DATA |

Every request is `OUTSTANDING`: the current package supplies none of the required roles. No request was marked satisfied by a filename, a placeholder, or public content.

## D. Re-binding — what new evidence would change (§6)

These are **dry runs**. No artifact was created, none was added to the package, and nothing was executed. They answer only: *if these roles arrived, which regions would become eligible for human review?*

| Scenario | Hypothetical roles | Regions that would unblock |
| :--- | :--- | ---: |
| benchmarking dataset arrives | `BENCHMARKING_DATA`, `COMPARABLE_COMPANIES`, `INDEPENDENCE_CODES`, `IQR_RESULTS`, `SCREENING_RESULTS` | **5** |
| management information (FAR + business narrative) arrives | `BUSINESS_NARRATIVE`, `FAR` | **20** |
| organisation chart arrives | `ORGANIZATIONAL_DATA` | **1** |
| intercompany agreements arrive | `CONTRACTUAL_DATA` | **1** |
| group narrative arrives | `GROUP_NARRATIVE`, `OWNERSHIP_STRUCTURE` | **0** |

**benchmarking dataset arrives** — 5 region(s) would move to `HUMAN_REVIEW_READY`:

| Region | From | To |
| :--- | :--- | :--- |
| `rgn-046` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-051` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-052` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-055` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-061` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |

**management information (FAR + business narrative) arrives** — 20 region(s) would move to `HUMAN_REVIEW_READY`:

| Region | From | To |
| :--- | :--- | :--- |
| `rgn-008` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-009` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-011` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-013` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-028` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-029` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-030` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-031` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-032` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-033` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-034` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| `rgn-035` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |
| … | | _8 more_ |

**organisation chart arrives** — 1 region(s) would move to `HUMAN_REVIEW_READY`:

| Region | From | To |
| :--- | :--- | :--- |
| `rgn-010` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |

**intercompany agreements arrive** — 1 region(s) would move to `HUMAN_REVIEW_READY`:

| Region | From | To |
| :--- | :--- | :--- |
| `rgn-027` | BLOCKED_MISSING_SOURCE | **HUMAN_REVIEW_READY** |

### Governance

- `execution_authorized` = **False**
- `requires_human_approval` = **True**
- Readiness values intake is structurally forbidden to emit: `APPROVED`, `EXECUTING`, `AUTO_MUTATION_READY`, `COMPLETED`, `FINAL_VALIDATED`

> Recalculated readiness changes what a human MAY review. It does not approve anything, does not transition any manifest to APPROVED or EXECUTING, and triggers no mutation. Human approval remains the only execution authorization.

## E. Constraints Honoured (§15, §11, §12)

| Constraint | Status |
| :--- | :--- |
| No DOCX/XLSX mutated | ✅ intake reads only |
| StructuralWritebackEngine unchanged | ✅ untouched |
| DataReconciliationEngine unchanged | ✅ untouched |
| Agent / providers / frontend unchanged | ✅ untouched |
| No new mutation capability | ✅ none added |
| Ground Truth cannot be ingested | ✅ `GroundTruthGuard` refuses by name **and** by hash |
| No fabricated source | ✅ only the four real artifacts were ingested |
| No public-internet substitution | ✅ no network access; gaps are reported, not filled |

---

*Regenerate with `python foundation/tests/evaluation/rollforward_source_intake_report.py`.*
