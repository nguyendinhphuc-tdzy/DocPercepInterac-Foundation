# Local File Roll-Forward Planning Integrity Remediation (Phase C2 / D3.2)

**Audit ID**: `REMEDIATION-LF-ROLLFORWARD-PLANNING-INTEGRITY-C2-D3.2-20260823`  
**Date**: 2026-08-23  
**Scope**: planning and evaluation integrity only; no mutation behaviour changed  

---

## Executive Summary

Six Phase D3.1 findings are closed. The repair is a general invariant in each case, not a per-table patch.

| Finding | Defect | Remediation | Enforced by |
| :--- | :--- | :--- | :--- |
| **P0-1** | Positional table identity across documents | Multi-factor position-free identity + correspondence resolver blind to `ordinal` | `table_identity.py`; `assert_no_positional_input()` |
| **P0-2** | Ground Truth determined planning targets | Active quarantine that raises if planning opens the oracle | `GroundTruthQuarantine` |
| **P0-3** | Structural validity treated as semantic validity | Pre-D1 gate on table anatomy, row semantics and column domain | `MutationPreconditionValidator` |
| **P0-4** | 72/72 MATCH with 0/72 source addresses | Addressability hard gate; value verdict and source verdict separated | `LineageAddressabilityGate` |
| **P0-5** | Source existence treated as compatibility | Content-derived dataset-role profiling + required-role binding | `source_capability.py`, `semantic_binding.py` |
| **P0-6** | `expected_postcondition_hash = "dummy"` | Real, projectable semantic postcondition hash | `PostconditionHasher` |

### The clean benchmark

Replanning all 16 template tables from independent evidence (FY2023 + Template + FY2024 sources, no Ground Truth) yields:

| Readiness | Cases |
| :--- | ---: |
| **READY** | 1 |
| **BLOCKED** | 11 |
| **MANUAL_REVIEW** | 4 |

The contaminated manifest reported **27 REPEATABLE regions with VERIFIED bindings**. The clean benchmark reports **1 READY**. That collapse is the finding, not a regression: the earlier readiness rested on positional pairings and Ground-Truth-derived targets.

> It is better to have 1 trustworthy READY region than 27 built on contaminated assumptions.

## A. Positional Identity Audit (P0-1)

FY2023 holds **22** tables, the Template **16**, the FY2024 oracle **19**. Index *i* denotes a different table in each, so positional correspondence is invalid by construction.

**Replacement** (`applications/rollforward/table_identity.py`) scores correspondence on these factors and no others:

- section context
- heading context
- header signature
- column schema
- row label schema
- merge topology
- neighbouring paragraphs
- semantic labels

`ordinal` is retained as **display and intra-document locator only**. The resolver cannot read it: `assert_no_positional_input()` = **True**, and a test renumbers every table in both documents and requires identical verdicts.

### The four contaminated golden tables, re-resolved

| Template table | Identity | Contaminated positional pairing | Old delta | Position-free verdict | Score |
| ---: | :--- | :--- | :--- | :--- | ---: |
| 10 | arm's-length range | `HIST.tables[10] (2r) -> GT.tables[10] (11r)` | `2 -> 11` | **UNCORRELATED** | 0.0164 |
| 13 | screening strategy | `HIST.tables[13] (4r) -> GT.tables[13] (6r)` | `4 -> 6` | **UNCORRELATED** | 0.03 |
| 14 | VN comparables | `HIST.tables[14] (6r) -> GT.tables[14] (10r)` | `6 -> 10` | **UNCORRELATED** | 0.262 |
| 15 | comparables | `HIST.tables[15] (10r) -> GT.tables[15] (16r)` | `10 -> 16` | **UNCORRELATED** | 0.2858 |

Every one resolves to **UNCORRELATED**: no FY2023 table is that table. The old deltas were arithmetic on unrelated pairs.

### Residual `.tables[...]` uses, classified

| File | Uses | Classification |
| :--- | ---: | :--- |
| `foundation/applications/rollforward/data_reconciliation.py` | 1 | INTRA-DOCUMENT LOCATOR — addresses a table inside one document |
| `foundation/applications/rollforward/mutation_precondition.py` | 2 | INTRA-DOCUMENT LOCATOR — addresses a table inside one document |
| `foundation/applications/rollforward/orchestrator.py` | 4 | INTRA-DOCUMENT LOCATOR — addresses a table inside one document |
| `foundation/applications/rollforward/structural_writeback.py` | 4 | INTRA-DOCUMENT LOCATOR — addresses a table inside one document |
| `foundation/tests/evaluation/rollforward_clean_planner_c2.py` | 1 | INTRA-DOCUMENT LOCATOR — addresses a table inside one document |
| `foundation/tests/evaluation/rollforward_d3_execution.py` | 1 | INTRA-DOCUMENT LOCATOR — addresses a table inside one document |
| `foundation/tests/evaluation/rollforward_planning_integrity_audit.py` | 14 | INTRA-DOCUMENT LOCATOR — addresses a table inside one document |
| `foundation/tests/evaluation/rollforward_profiler.py` | 3 | CONTAMINATED (marked INVALIDATED_FOR_PLANNING_CONTAMINATION, retained) |
| `foundation/tests/evaluation/rollforward_source_binding.py` | 3 | CONTAMINATED (marked INVALIDATED_FOR_PLANNING_CONTAMINATION, retained) |
| `foundation/tests/evaluation/rollforward_structural_audit_d3_1.py` | 18 | AUDIT_EVIDENCE — demonstrates the defect, does not plan |

No remaining use is cross-document semantic identity. Addressing a table inside one document by index is a locator and remains correct.

## B. Ground Truth Contamination Audit (P0-2)

| Template table | Contaminated `target_rows` | `GT.tables[i].rows` | Equal? | Contaminated `insert_count` | `GT[i] − HIST[i]` | Equal? |
| ---: | ---: | ---: | :---: | ---: | ---: | :---: |
| 10 | 11 | 11 | ✅ | 9 | 9 | ✅ |
| 13 | 6 | 6 | ✅ | 2 | 2 | ✅ |
| 14 | 10 | 10 | ✅ | 4 | 4 | ✅ |
| 15 | 16 | 16 | ✅ | 6 | 6 | ✅ |

**Enforcement.** GroundTruthQuarantine (rollforward_clean_planner_c2.py) is armed for the whole planning run; opening the Ground Truth raises GroundTruthContaminationError. Covered by `test_ground_truth_quarantine_raises_when_planning_opens_it`.

### Historical artifacts — marked, never deleted

| Artifact | Status | Deleted |
| :--- | :--- | :---: |
| `foundation/tests/evaluation/rollforward_source_binding.py` | `INVALIDATED_FOR_PLANNING_CONTAMINATION` | no |
| `foundation/tests/evaluation/rollforward_profiler.py` | `INVALIDATED_FOR_PLANNING_CONTAMINATION` | no |
| `docs/evaluation/LocalFile_RollForward_Structural_Writeback_D1_2026-08-21.md` | `INVALIDATED_FOR_PLANNING_CONTAMINATION` | no |
| `docs/evaluation/LocalFile_RollForward_Data_Reconciliation_D2_2026-08-21.md` | `INVALIDATED_FOR_PLANNING_CONTAMINATION` | no |
| `docs/evaluation/LocalFile_RollForward_D3_Execution_Report.md` | `INVALIDATED_FOR_PLANNING_CONTAMINATION` | no |
| `docs/evaluation/LocalFile_RollForward_Source_Binding_2026-08-21.md` | `INVALIDATED_FOR_PLANNING_CONTAMINATION` | no |
| `docs/evaluation/LocalFile_RollForward_Template_Profile_2026-08-21.md` | `INVALIDATED_FOR_PLANNING_CONTAMINATION` | no |

The contaminated planner still exists and still runs, so the Phase A–D3 suites keep exercising the engine mechanics they were written for. Only its **row-count targets and readiness claims** are withdrawn.

## C. Source Dataset Audit (P0-5)

**Method**: content-derived dataset roles; sheet names are never consulted.

### `HMV-FA&RPT FY2024.xlsx` — 5 sheets

Roles present: `FINANCIAL_ANALYSIS`, `FINANCIAL_STATEMENTS`, `INTEREST_EXPENSE`, `RPT_DATA`  
Benchmarking family present: **NONE**

| Sheet | Records | Domain | Roles | Formula cells |
| :--- | ---: | :--- | :--- | ---: |
| I. Related parties | 8 | ENTITY | UNKNOWN | 0 |
| FS | 45 | MIXED | FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS, INTEREST_EXPENSE | 30 |
| RPTs | 12 | MIXED | RPT_DATA | 27 |
| Financial Analysis | 51 | MIXED | FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS | 47 |
| III. Summary-RPTs | 37 | MIXED | INTEREST_EXPENSE, RPT_DATA | 64 |

### `HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx` — 18 sheets

Roles present: `RPT_DATA`, `REFERENCE_LIST`, `SEGMENTED_DATA`, `INTEREST_EXPENSE`, `FINANCIAL_STATEMENTS`, `FINANCIAL_ANALYSIS`, `FIXED_ASSETS`  
Benchmarking family present: **NONE**

| Sheet | Records | Domain | Roles | Formula cells |
| :--- | ---: | :--- | :--- | ---: |
| Checklist | 68 | ENTITY | RPT_DATA, REFERENCE_LIST, SEGMENTED_DATA | 0 |
| Full Appendix I | 152 | MIXED | RPT_DATA | 314 |
| I. Related parties | 8 | ENTITY | UNKNOWN | 0 |
| Country list | 274 | ENTITY | UNKNOWN | 0 |
| III. Summary-RPTs | 37 | MIXED | INTEREST_EXPENSE, RPT_DATA | 77 |
| IV. Segmented data | 28 | MONETARY | FINANCIAL_STATEMENTS, INTEREST_EXPENSE | 75 |
| FS | 45 | MIXED | FINANCIAL_ANALYSIS, FINANCIAL_STATEMENTS, INTEREST_EXPENSE | 47 |
| Interest expenses | 37 | MIXED | SEGMENTED_DATA | 69 |
| Types of relationship | 13 | NARRATIVE | UNKNOWN | 0 |
| Transfer pricing method | 11 | NARRATIVE | UNKNOWN | 0 |
| Note FS | 344 | MONETARY | UNKNOWN | 889 |
| P&L | 14 | MIXED | UNKNOWN | 104 |
| CF | 46 | MONETARY | FIXED_ASSETS, INTEREST_EXPENSE | 166 |
| Exchange rate calculation | 21 | MONETARY | UNKNOWN | 14 |
| TỶ giá ngày TCB | 371 | MONETARY | UNKNOWN | 1480 |
| Lãi vay vốn hóa - PBC | 118 | MIXED | UNKNOWN | 2 |
| IV. Segmented data_banking | 34 | MIXED | UNKNOWN | 30 |
| IV. Segmented data_securities | 76 | MIXED | INTEREST_EXPENSE | 67 |

**Conclusion.** Neither bound workbook contains BENCHMARKING_DATA, COMPARABLE_COMPANIES, IQR_RESULTS or SCREENING_RESULTS. Every benchmarking target region is therefore MISSING_CURRENT_SOURCE and BLOCKED.

## D. Semantic Binding Audit (P0-5 / P0-7)

**Rule**: a binding is VERIFIED only when the source proves it carries the dataset role the target domain requires.

Verified bindings: **3 / 16** regions.

| Table | Domain | Required dataset roles | Verdict | Roles found |
| ---: | :--- | :--- | :--- | :--- |
| 0 | COVER_BLOCK | — | **INSUFFICIENT_EVIDENCE** | — |
| 1 | COVER_BLOCK | — | **INSUFFICIENT_EVIDENCE** | — |
| 2 | UNKNOWN | — | **INSUFFICIENT_EVIDENCE** | — |
| 3 | RELATED_PARTY_TRANSACTIONS | `RPT_DATA` | **VERIFIED** | RPT_DATA |
| 4 | INTEREST_SCHEDULE | `INTEREST_EXPENSE` | **VERIFIED** | INTEREST_EXPENSE |
| 5 | FUNCTIONAL_ANALYSIS | — | **INSUFFICIENT_EVIDENCE** | — |
| 6 | PLI_FORMULA | — | **INSUFFICIENT_EVIDENCE** | — |
| 7 | PLI_FORMULA | — | **INSUFFICIENT_EVIDENCE** | — |
| 8 | PLI_FORMULA | — | **INSUFFICIENT_EVIDENCE** | — |
| 9 | UNKNOWN | — | **INSUFFICIENT_EVIDENCE** | — |
| 10 | ARMS_LENGTH_RANGE | `IQR_RESULTS`, `BENCHMARKING_DATA` | **MISSING_CURRENT_SOURCE** | — |
| 11 | FINANCIAL_INDICATORS | `FINANCIAL_STATEMENTS`, `FINANCIAL_ANALYSIS` | **VERIFIED** | FINANCIAL_STATEMENTS, FINANCIAL_ANALYSIS |
| 12 | DOCUMENT_CHECKLIST | — | **INSUFFICIENT_EVIDENCE** | — |
| 13 | SCREENING_STRATEGY | `SCREENING_RESULTS`, `BENCHMARKING_DATA` | **MISSING_CURRENT_SOURCE** | — |
| 14 | COMPARABLE_COMPANIES | `COMPARABLE_COMPANIES`, `BENCHMARKING_DATA` | **MISSING_CURRENT_SOURCE** | — |
| 15 | COMPARABLE_COMPANIES | `COMPARABLE_COMPANIES`, `BENCHMARKING_DATA` | **MISSING_CURRENT_SOURCE** | — |

## E. Target Schema & Table Anatomy Audit (P0-3)

Anatomy concepts introduced: **header band**, **data region**, **placeholder rows**, **footer band**.

| Table | Rows × Cols | Row semantics | Data region | Footer | Placeholders | Target rows | Target basis |
| ---: | :--- | :--- | :--- | :--- | :--- | ---: | :--- |
| 0 | 3 × 1 | UNKNOWN | [1, 2] | — | — | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 1 | 3 × 1 | UNKNOWN | [1, 2] | — | [2] | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 2 | 4 × 3 | UNKNOWN | [1, 3] | — | — | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 3 | 8 × 4 | ENTITY_RECORD | [1, 7] | — | — | 153 | header + current-source record count + footer |
| 4 | 4 × 5 | ENTITY_RECORD | [1, 3] | — | [1, 2, 3] | 77 | header + current-source record count + footer |
| 5 | 28 × 3 | UNKNOWN | [1, 27] | — | — | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 6 | 2 × 3 | UNKNOWN | [1, 1] | — | — | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 7 | 2 × 3 | UNKNOWN | [1, 1] | — | — | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 8 | 2 × 3 | UNKNOWN | [1, 1] | — | — | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 9 | 14 × 6 | UNKNOWN | [1, 13] | — | [6, 12] | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 10 | 6 × 3 | STATISTIC | [1, 5] | — | [4] | 6 | fixed-shape table; row count does not change u… |
| 11 | 9 × 3 | LINE_ITEM | [1, 8] | — | — | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 12 | 25 × 3 | UNKNOWN | [1, 24] | — | — | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 13 | 23 × 2 | KEY_VALUE | [1, 21] | [22] | [1] | 23 | fixed-shape table; row count does not change u… |
| 14 | 8 × 6 | ENTITY_RECORD | [1, 6] | [7] | [5, 6] | — | UNKNOWABLE_FROM_APPROVED_INPUTS |
| 15 | 7 × 5 | ENTITY_RECORD | [1, 6] | — | [5, 6] | — | UNKNOWABLE_FROM_APPROVED_INPUTS |

### The published Phase D3 plan, replayed through the new gate

**Executable: False** — 10 violations.

| Violation code | Count |
| :--- | ---: |
| `DUMMY_POSTCONDITION_HASH` | 3 |
| `PLACEHOLDER_ROWS_NOT_CONSUMED` | 3 |
| `INSERTION_BELOW_FOOTER` | 2 |
| `ROW_SEMANTICS_MISMATCH` | 1 |
| `COLUMN_DOMAIN_VIOLATION` | 1 |

| Code | Region | Location | Detail |
| :--- | :--- | :--- | :--- |
| `DUMMY_POSTCONDITION_HASH` | `rft-10` | — | expected_postcondition_hash is the placeholder 'dummy'. Idempotence cannot be proven against a placeholder; compute it with Postco… |
| `ROW_SEMANTICS_MISMATCH` | `rft-10` | — | Region row semantics are STATISTIC: each row is a fixed, uniquely-labelled entry, not a repeatable record. Appending 2 rows is not… |
| `PLACEHOLDER_ROWS_NOT_CONSUMED` | `rft-10` | — | Rows [4] are unfilled template placeholders and every new row is appended after them (first new row 6). The published table would… |
| `DUMMY_POSTCONDITION_HASH` | `rft-14` | — | expected_postcondition_hash is the placeholder 'dummy'. Idempotence cannot be proven against a placeholder; compute it with Postco… |
| `INSERTION_BELOW_FOOTER` | `rft-14` | table 14 row 8 | Row 8 would be written below the table's footer band (rows [7]). New records must land inside the data region [1, 6]. |
| `INSERTION_BELOW_FOOTER` | `rft-14` | table 14 row 9 | Row 9 would be written below the table's footer band (rows [7]). New records must land inside the data region [1, 6]. |
| `PLACEHOLDER_ROWS_NOT_CONSUMED` | `rft-14` | — | Rows [5, 6] are unfilled template placeholders and every new row is appended after them (first new row 8). The published table wou… |
| `DUMMY_POSTCONDITION_HASH` | `rft-15` | — | expected_postcondition_hash is the placeholder 'dummy'. Idempotence cannot be proven against a placeholder; compute it with Postco… |
| `COLUMN_DOMAIN_VIOLATION` | `rft-15` | table 15 row 7 col 4 | value shape 'percentage' is not accepted by column 4 ('Business description') whose role is DESCRIPTION (accepts text) |
| `PLACEHOLDER_ROWS_NOT_CONSUMED` | `rft-15` | — | Rows [5, 6] are unfilled template placeholders and every new row is appended after them (first new row 7). The published table wou… |

The three semantic defects Phase D3.1 found in the published artifact — P&L rows in the arm's-length table, rows below the footer, a percentage in a description column — are each refused before D1 is called.

## F. D2 Lineage Audit (P0-4)

**Rule**: a cell may be MATCH only with document + sheet/element + cell address or range; otherwise binding_status=UNVERIFIED and reconciliation_status=BLOCKED.

The two questions are now answered separately:

- `value_semantic_status` — did the planned value land in the cell
- `status` — is this cell traceable to a located source

| Case | Value semantics | Addressability | Binding | Reconciliation |
| :--- | :--- | :--- | :--- | :--- |
| no source at all | MATCH | **UNADDRESSED** | UNVERIFIED | **BLOCKED** |
| workbook named, no cell address (the D3 shape) | MATCH | **PARTIAL** | UNVERIFIED | **BLOCKED** |
| fully addressed | MATCH | **ADDRESSED** | VERIFIED | **MATCH** |

Applied to the published Phase D3 lineage: **0 / 72** cells carry a source cell address. Under the gate that run reports **BLOCKED**, not `MATCH`. The `72 / 72` figure is withdrawn as source-correctness evidence; it remains valid as plan-to-output fidelity.

## G. Idempotence Audit (P0-6)

**Algorithm**: `rollforward-postcondition-v1` over target table, target rows, target cells, row schema, merge topology, shading and paragraph-style signatures.

Because the hash is computed from a logical cell model rather than from a saved document, it can be **projected before execution**: for template table 15, current `dceb31b336bd7263f91dd92a03e6a248` vs projected `fca808f4a59ee4fbd2bc4395badfd463` (differs: True). A test asserts a projected hash equals the hash of the document after the production cloner actually applies the same rows.

Placeholders now rejected: `dummy`, `none`, `null`, `post`, `post-dummy`, `tbd`, `todo` (and empty). MutationPreconditionValidator raises DUMMY_POSTCONDITION_HASH for placeholders.

> D1's NOOP check compares a live fingerprint against expected_postcondition_hash. With 'dummy' it could never match, so real-fixture idempotence was inert.

## H. Clean REAL_TARGET_BENCHMARK

Artifact: `docs/evaluation/LocalFile_RollForward_Real_Target_Benchmark_v1_2026-08-23.json`

| Table | Domain | Template | Historical (position-free) | Source records | Strategy | Implemented | Readiness |
| ---: | :--- | ---: | :--- | ---: | :--- | :---: | :--- |
| 0 | COVER_BLOCK | 3 | WEAK (T0, 3r) | — | UPDATE_CELLS | ❌ | **BLOCKED** |
| 1 | COVER_BLOCK | 3 | EXACT (T1, 3r) | — | UPDATE_CELLS | ❌ | **BLOCKED** |
| 2 | UNKNOWN | 4 | UNCORRELATED | — | NO_STRATEGY_DETERMINABLE | ❌ | **BLOCKED** |
| 3 | RELATED_PARTY_TRANSACTIONS | 8 | WEAK (T6, 2r) | 152 | INSERT_ROWS | ✅ | **MANUAL_REVIEW** |
| 4 | INTEREST_SCHEDULE | 4 | UNCORRELATED | 76 | REPLACE_DATA_REGION | ❌ | **BLOCKED** |
| 5 | FUNCTIONAL_ANALYSIS | 28 | WEAK (T9, 27r) | — | CARRY_FORWARD_STATIC | ✅ | **MANUAL_REVIEW** |
| 6 | PLI_FORMULA | 2 | EXACT (T10, 2r) | — | CARRY_FORWARD_STATIC | ✅ | **READY** |
| 7 | PLI_FORMULA | 2 | WEAK (T10, 2r) | — | CARRY_FORWARD_STATIC | ✅ | **MANUAL_REVIEW** |
| 8 | PLI_FORMULA | 2 | WEAK (T10, 2r) | — | CARRY_FORWARD_STATIC | ✅ | **MANUAL_REVIEW** |
| 9 | UNKNOWN | 14 | UNCORRELATED | — | NO_STRATEGY_DETERMINABLE | ❌ | **BLOCKED** |
| 10 | ARMS_LENGTH_RANGE | 6 | UNCORRELATED | — | ACTIVATE_PLACEHOLDER | ❌ | **BLOCKED** |
| 11 | FINANCIAL_INDICATORS | 9 | UNCORRELATED | 51 | UPDATE_CELLS | ❌ | **BLOCKED** |
| 12 | DOCUMENT_CHECKLIST | 25 | WEAK (T2, 25r) | — | UPDATE_CELLS | ❌ | **BLOCKED** |
| 13 | SCREENING_STRATEGY | 23 | UNCORRELATED | — | ACTIVATE_PLACEHOLDER | ❌ | **BLOCKED** |
| 14 | COMPARABLE_COMPANIES | 8 | UNCORRELATED | — | REPLACE_DATA_REGION | ❌ | **BLOCKED** |
| 15 | COMPARABLE_COMPANIES | 7 | UNCORRELATED | — | REPLACE_DATA_REGION | ❌ | **BLOCKED** |

### Why each golden table is blocked

**Table 10 — ARMS_LENGTH_RANGE** (BLOCKED, needs `ACTIVATE_PLACEHOLDER`)
- MISSING_CURRENT_SOURCE: no bound workbook contains ['IQR_RESULTS', 'BENCHMARKING_DATA']. Content profiling of 23 sheets found no such dataset.
- STRATEGY_NOT_IMPLEMENTED: this region requires ACTIVATE_PLACEHOLDER, which the D1 writeback engine does not provide (it implements INSERT_ROWS only). Not implemented in this phase by instruction.

**Table 13 — SCREENING_STRATEGY** (BLOCKED, needs `ACTIVATE_PLACEHOLDER`)
- MISSING_CURRENT_SOURCE: no bound workbook contains ['SCREENING_RESULTS', 'BENCHMARKING_DATA']. Content profiling of 23 sheets found no such dataset.
- STRATEGY_NOT_IMPLEMENTED: this region requires ACTIVATE_PLACEHOLDER, which the D1 writeback engine does not provide (it implements INSERT_ROWS only). Not implemented in this phase by instruction.

**Table 14 — COMPARABLE_COMPANIES** (BLOCKED, needs `REPLACE_DATA_REGION`)
- MISSING_CURRENT_SOURCE: no bound workbook contains ['COMPARABLE_COMPANIES', 'BENCHMARKING_DATA']. Content profiling of 23 sheets found no such dataset.
- STRATEGY_NOT_IMPLEMENTED: this region requires REPLACE_DATA_REGION, which the D1 writeback engine does not provide (it implements INSERT_ROWS only). Not implemented in this phase by instruction.

**Table 15 — COMPARABLE_COMPANIES** (BLOCKED, needs `REPLACE_DATA_REGION`)
- MISSING_CURRENT_SOURCE: no bound workbook contains ['COMPARABLE_COMPANIES', 'BENCHMARKING_DATA']. Content profiling of 23 sheets found no such dataset.
- STRATEGY_NOT_IMPLEMENTED: this region requires REPLACE_DATA_REGION, which the D1 writeback engine does not provide (it implements INSERT_ROWS only). Not implemented in this phase by instruction.

## I. Constraints Honoured

| Constraint | Status |
| :--- | :--- |
| No new mutation types | ✅ none added |
| `DELETE_ROWS` not implemented | ✅ recommendation vocabulary only; a test asserts it is absent from `structural_writeback.py` |
| No image or narrative mutation | ✅ untouched |
| No Agent / provider / frontend change | ✅ untouched |
| DOCX mutation behaviour unchanged | ✅ `structural_writeback.py` mutation path untouched |
| Historical reports preserved | ✅ marked with a status banner, content intact |
| Failing tests not deleted | ✅ updated with the historical reason recorded |

### What did change, and why

- `data_reconciliation.py` — the P0-4 lineage gate. This is reconciliation *reporting* integrity, explicitly required by the phase, and it changes no document.
- Five evaluation reports and two evaluation modules — status banners only.

---

*Regenerate with `python foundation/tests/evaluation/rollforward_planning_integrity_audit.py`.*
