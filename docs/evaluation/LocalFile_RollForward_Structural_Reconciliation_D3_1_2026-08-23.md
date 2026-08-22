# Local File Roll-Forward Structural Reconciliation Audit (Phase D3.1)

**Audit ID**: `AUDIT-LF-ROLLFORWARD-STRUCTURAL-D3.1-20260823`  
**Date**: 2026-08-23  
**Mode**: **AUDIT_ONLY** — no production code modified, no mutation capability added, no historical report altered.  

---

## A. Executive Summary

The conflicting row counts have a single root cause, and it is provable to the digit.

**Phase C correlated the FY2023 Local File, the Master Template and the FY2024 Ground Truth by *positional table index*.** Those three documents contain 22, 16 and 19 tables respectively, so table *i* in one is a different table in the others. Every "growth case" is an artifact of that misalignment.

The proof is exact — 12 of 12 predicted values match:

| Template table | Phase C "historical" | `HIST.tables[i]` | Phase C "target" | `GT.tables[i]` | Phase C `insert_count` | `GT[i] − HIST[i]` |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 2 | **2** | 11 | **11** | 9 | **9** |
| 13 | 4 | **4** | 6 | **6** | 2 | **2** |
| 14 | 6 | **6** | 10 | **10** | 4 | **4** |
| 15 | 10 | **10** | 16 | **16** | 6 | **6** |

The tables being paired are not related:

| Index | FY2023 table | Master Template table | FY2024 Ground Truth table |
| ---: | :--- | :--- | :--- |
| 10 | NCP \| = \| EBIT | Item \| FY20xx \| WA (FY20ww-20xx) | No \| Company \| Country \| Ticker |
| 13 | NAICS Code \| Description | Database used \| Bureau van Dijk’s TP Catalyst… | Code \| Description |
| 14 | Code \| Description | No \| Company \| Province \| Tax code \| VN SI… | Step \| Search criteria \| Search criteria \|… |
| 15 | Step \| Search criteria \| Search criteria \|… | No \| Company \| Country \| Ticker symbol/ / T… | Screening criteria \| Eliminated \| Retained |

### The three consequences

1. **The "earlier" numbers are phantom deltas.** `2 → 11`, `4 → 6`, `6 → 10`, `10 → 16` are `HIST.tables[i].rows → GT.tables[i].rows`. None describes a real roll-forward.
2. **The Ground Truth determined a planning artifact.** `target_rows == GT.tables[i].rows` in all four cases. This contradicts the evaluation-only rule that Phases B/C/D1/D2/D3 otherwise enforce. The values are hardcoded literals in the Phase C planner, so the leak happened at authoring time rather than at runtime — but the dependency is real.
3. **One `StructuralDelta` carries three documents' numbers.** No two of its fields describe the same document, which is why target_rows - template_rows != insert_count in all four cases.

### What is sound, and what is not

| Layer | Verdict |
| :--- | :--- |
| Phase B profiler | **SOUND** — not a source of the discrepancy |
| Phase C structural deltas | **UNSOUND** — origin of the discrepancy |
| D1 mutation mechanics | **SOUND** — the engine does what it claims |
| D1 golden-case *targets* | **UNSOUND** — synthetic reproductions of phantom deltas |
| D2 comparison mathematics | **SOUND** |
| D2 "4/4 tables" headline | **MISLEADING** — 3 real + 1 synthetic |
| D3 governance / transaction / validation | **SOUND** |
| D3 published artifact | **NOT USABLE** — correct execution of an incorrect plan |

> D3 did exactly what it was designed to do — it executed an approved plan atomically, reconciled every declared cell, passed every registered structural gate and published a reproducible artifact. The artifact is nevertheless not a usable FY2024 Local File, because the plan it executed targeted the wrong tables with the wrong row counts.

## B. Authoritative Reconciliation Matrix

Every number below is either MEASURED live from the named artifact or QUOTED verbatim from a prior artifact. The four row-count concepts are kept strictly separate, as required.

| # | Concept | T10 | T13 | T14 | T15 |
| ---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `region_id` | `rfr-071` | `rfr-093` | `rfr-098` | `rfr-101` |
| | **template table index** | 10 | 13 | 14 | 15 |
| | **semantic identity** | Standard arm's-length range summary (3… | Search & screening strategy matrix (De… | Vietnamese comparable companies (No /… | Comparable companies list (No / Compan… |
| | | | | | |
| 2 | **HISTORICAL ROWS (FY2023)** | | | | |
| | **↳ positional `HIST[i]` (used by Phase C)** | 2 | 4 | 6 | 10 |
| | **↳ positional table is related?** | **NO** | **NO** | **NO** | **NO** |
| | **↳ *semantic* counterpart rows** | **none exists** | [10, 15] | **none exists** | [14, 14] |
| | | | | | |
| 3 | **TEMPLATE ROWS** | | | | |
| | **↳ measured live** | **6** | **23** | **8** | **7** |
| | **↳ Phase B recorded** | 6 | 23 | 8 | 7 |
| | **↳ Phase C recorded** | 6 | 23 | 8 | 7 |
| | **↳ all three agree** | ✅ | ✅ | ✅ | ✅ |
| | | | | | |
| 4 | **CURRENT SOURCE RECORDS** | | | | |
| | **↳ records available in bound workbooks** | **1** | **0** | **0** | **0** |
| | | | | | |
| 5 | **PLANNED TARGET ROWS** | | | | |
| | **↳ Phase C `target_rows`** | 11 | 6 | 10 | 16 |
| | **↳ Phase C `insert_count`** | 9 | 2 | 4 | 6 |
| | **↳ target − template == insert?** | ❌ | ❌ | ❌ | ❌ |
| | | | | | |
| 6 | **D1** | | | | |
| | **↳ synthetic case** | 2 rows -> 11 rows (+9) | 4 rows -> 6 rows (+2) | 6 rows -> 10 rows (+4) | 10 rows -> 16 rows (+6) |
| | **↳ present in real-fixture test** | ✅ | **❌ ABSENT** | ✅ | ✅ |
| | **↳ real precondition rows** | 6 | — | 8 | 7 |
| | **↳ real `expected_postcondition_hash`** | "dummy" (literal placeholder string) | — | "dummy" (literal placeholder string) | "dummy" (literal placeholder string) |
| | | | | | |
| 7 | **D2** | | | | |
| | **↳ fixture kind** | **REAL_FIXTURE** | **SYNTHETIC** | **REAL_FIXTURE** | **REAL_FIXTURE** |
| | **↳ cells reconciled** | 15 | 4 | 12 | 45 |
| | **↳ rows before → after** | 6 → 11 | 3 → 3 | 8 → 10 | 7 → 16 |
| | | | | | |
| 8 | **D3 (real execution)** | | | | |
| | **↳ actual before** | 6 | — | 8 | 7 |
| | **↳ actual after** | 11 | — | 10 | 16 |
| | **↳ measured in published output** | 11 | 23 | 10 | 16 |
| | **↳ status** | EXECUTED | EXCLUDED: UNSUPPORTED_OPERATION | EXECUTED | EXECUTED |
| | | | | | |
| 9 | **GROUND TRUTH (FY2024)** | | | | |
| | **↳ positional `GT[i]` (used by Phase C)** | 11 | 6 | 10 | 16 |
| | **↳ positional table is related?** | **NO** | **NO** | **NO** | **NO** |
| | **↳ *semantic* counterpart rows** | **none exists** | [10, 16] | **none exists** | [11, 11] |

### Structural status

- **Table 10** (`rfr-071`): MISCLASSIFIED. Template T10 is a fixed 6-row arm's-length-range summary whose value cells are 'xx%' placeholders. It is an UPDATE / placeholder-activation region, not REPEATABLE. Its planned target of 11 rows has no basis in any document.
- **Table 13** (`rfr-093`): MISCLASSIFIED AND FORMAT-SHIFTED. Template T13 is a complete 23-row screening narrative with 'zz/yy/xx companies' placeholders. FY2023 and FY2024 express the same content as two differently-shaped tables. This is a format transformation requiring placeholder activation and possibly row removal — not insertion. It was correctly left unexecuted, though for a reason that does not hold up.
- **Table 14** (`rfr-098`): MISCLASSIFIED. No FY2023 or FY2024 table uses this column schema; the FY2024 engagement used the T15 schema for its all-Vietnamese set. Requires a human decision on which presentation applies. Its planned target of 10 rows has no basis.
- **Table 15** (`rfr-101`): PARTIALLY CORRECT CONCEPT, WRONG NUMBERS. This is the only golden table with a genuine counterpart. The real roll-forward is 13 FY2023 comparables -> 10 FY2024 comparables, i.e. a target of 11 rows (header + 10) achieved by REPLACING 6 placeholder rows — a net +4. The planned target of 16 is a positional artifact.

### Provenance of every number

| Number | Source | Artifact | Confidence |
| :--- | :--- | :--- | :--- |
| historical rows | Phase C hardcoded literal == HIST.tables[i].rows (positional) | `HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx` | MEASURED |
| template rows | Measured live from Master Template; corroborated by Phase B table_signatures | `Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx` + Phase B profile | MEASURED |
| current source records | Measured: enumerated all 5 FA&RPT sheets and all 18 Appendix I sheets | FA&RPT + Appendix I workbooks | MEASURED |
| planned target rows | Hardcoded literal | `foundation/tests/evaluation/rollforward_source_binding.py :: StructuralPlanningEngine.plan_manifest` | QUOTED |
| D1 pre/postconditions | Test source | `foundation/tests/test_structural_writeback.py` | QUOTED |
| D2 coverage | Test source | `foundation/tests/test_rollforward_data_reconciliation.py` | QUOTED |
| D3 actuals | Execution report + live output | D3 report JSON + published `.docx` | MEASURED |
| ground truth rows | Measured live | `HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx` | MEASURED |

## C. Table 10 Analysis

**Disputed figures**: `2 → 11` vs `6 → 11`

**Template identity** (measured): `Item \| FY20xx \| WA (FY20ww-20xx)` — 6 rows × 3 columns.

**Semantic identity**: Standard arm's-length range summary (35th / Median / 75th percentile + tested party PLI)

| Concept | Value | Evidence |
| :--- | :--- | :--- |
| FY2023 rows — *positional* `HIST[10]` | 2 | `NCP \| = \| EBIT` — **unrelated table** |
| FY2023 rows — *semantic* | **no counterpart exists** | — |
| Template rows | **6** | measured; Phase B agrees (6) |
| Current source records | **1** | Of the four values template T10 requires (35th percentile, median, 75th percentile, tested-party PLI), only the tested-party PLI exists in a bound sou |
| Planned target rows | 11 (insert 9) | Phase C literal; arithmetic **inconsistent** |
| D1 synthetic fixture | 2 rows -> 11 rows (+9) | `test_golden_case_table_10_growth_2_to_11` on clean_test_doc.tables[1] (3 cols) |
| D1 real-fixture spec | present | 6 → 11 |
| D2 coverage | **REAL_FIXTURE** (15 cells) | `test_four_golden_tables_real_fixture_reconciliation_and_lineage` |
| D3 actual | 6 → 11 | EXECUTED |
| FY2024 rows — *positional* `GT[10]` | 11 | `No \| Company \| Country \| Ticker` — **unrelated table** |
| FY2024 rows — *semantic* | **no counterpart exists** | — |

**Why the two figures disagree.** The left-hand figure (`2 → 11`) is `HIST.tables[10].rows → GT.tables[10].rows`: two unrelated tables paired by index. The right-hand figure (`6 → 11`) keeps the real template row count on the left but retains the same positional Ground-Truth number on the right. **Neither figure describes a real roll-forward of this table.**

**Cross-document note.** Neither FY2023 nor FY2024 expresses this as a table; the range definition appears in body prose (HIST p282 / GT p274). The template introduces it as a 6-row placeholder table.

**Structural status.** MISCLASSIFIED. Template T10 is a fixed 6-row arm's-length-range summary whose value cells are 'xx%' placeholders. It is an UPDATE / placeholder-activation region, not REPEATABLE. Its planned target of 11 rows has no basis in any document.

## D. Table 13 Analysis

> **Highest-priority issue.**

**Disputed figures**: `4 → 6` vs `23 → 6`

**Template identity** (measured): `Database used \| Bureau van Dijk’s TP Catalyst (“TP Cat”) database` — 23 rows × 2 columns.

**Semantic identity**: Search & screening strategy matrix (Decree 20-2025 key/value format)

| Concept | Value | Evidence |
| :--- | :--- | :--- |
| FY2023 rows — *positional* `HIST[13]` | 4 | `NAICS Code \| Description` — **unrelated table** |
| FY2023 rows — *semantic* | [10, 15] | HIST T15 (10r), HIST T16 (15r) |
| Template rows | **23** | measured; Phase B agrees (23) |
| Current source records | **0** | No screening/search-strategy data exists in either bound workbook. FA&RPT has 5 sheets (Related parties, FS, RPTs, Financial Analysis, Summary-RPTs);  |
| Planned target rows | 6 (insert 2) | Phase C literal; arithmetic **inconsistent** |
| D1 synthetic fixture | 4 rows -> 6 rows (+2) | `test_golden_case_table_13_growth_4_to_6` on clean_test_doc.tables[1] (3 cols, 2 rows added at runtime) |
| D1 real-fixture spec | **ABSENT** | — → — |
| D2 coverage | **SYNTHETIC** (4 cells) | `test_exact_source_to_output_mapping_table_13` |
| D3 actual | — → — | EXCLUDED: UNSUPPORTED_OPERATION |
| FY2024 rows — *positional* `GT[13]` | 6 | `Code \| Description` — **unrelated table** |
| FY2024 rows — *semantic* | [10, 16] | GT T14 (10r), GT T15 (16r) |

**Why the two figures disagree.** The left-hand figure (`4 → 6`) is `HIST.tables[13].rows → GT.tables[13].rows`: two unrelated tables paired by index. The right-hand figure (`23 → 6`) keeps the real template row count on the left but retains the same positional Ground-Truth number on the right. **Neither figure describes a real roll-forward of this table.**

**Cross-document note.** FY2023 and FY2024 express the same information as TWO tables (Step matrix 4 cols + Screening criteria 3 cols). The template replaces both with one 23-row key/value table. This is a FORMAT REDESIGN, not a row-count delta.

**Structural status.** MISCLASSIFIED AND FORMAT-SHIFTED. Template T13 is a complete 23-row screening narrative with 'zz/yy/xx companies' placeholders. FY2023 and FY2024 express the same content as two differently-shaped tables. This is a format transformation requiring placeholder activation and possibly row removal — not insertion. It was correctly left unexecuted, though for a reason that does not hold up.

### Was `4 → 6` only a synthetic benchmark case?

**YES. Explicitly: '4 -> 6' never described the real Master Template's Table 13 (23 rows). It is HIST.tables[13] (NAICS codes, 4 rows) -> GT.tables[13] (BVD independence codes, 6 rows) — two unrelated tables paired by index. D1 reproduced it on a purpose-built 4-row fixture and D2's Table 13 test used a different synthetic 3-row fixture that does not grow at all.**

Three different "Table 13"s exist across the codebase, under three different region ids:

| Where | Region id | Shape | Grows? |
| :--- | :--- | :--- | :--- |
| Real Master Template | `rfr-093` | 23 rows × 2 cols, screening matrix | not executed |
| D1 synthetic golden case | `rfr-target-1` | 4 rows × 3 cols, built in-test | 4 → 6 |
| D2 synthetic unit test | `rfr-096` | 3 rows × 2 cols, BVD codes | no (`insert_count=0`) |

### What the real Master Template's Table 13 actually needs

Placeholder activation and selective row removal, not insertion. Its 23 rows are a complete screening narrative containing 'zz companies selected', 'yy companies remained' and 'xx companies selected' counters plus per-screen criteria text. NOT IMPLEMENTED IN THIS PHASE.

The evidence is in the template rows themselves — the table is already complete in shape and carries unfilled counters:

```
  r00: Database used            || Bureau van Dijk's TP Catalyst ('TP Cat') dat…
  r02: Status screen            || Selected active
  r03: Geographic screen        || Selected companies operating in Vietnam
  r08: zz companies selected    || zz companies selected      <-- placeholder counter
  r09: Quantitative screens     || Rejected companies having less than three co…
  r16: yy companies remained    || yy companies remained      <-- placeholder counter
  r17: Qualitative screens      || Rejected companies for non-comparable functi…
  r22: xx companies selected    || xx companies selected      <-- placeholder counter
```

Required strategy, in order of confidence:

1. **ACTIVATE_PLACEHOLDER / UPDATE_CELLS** (high confidence) — fill `zz`, `yy`, `xx` and the per-screen criteria text.
2. **DELETE_ROWS** (medium confidence) — remove screen rows not applied in FY2024.
3. **INSERT_ROWS** (low confidence) — only if FY2024 applied a screen the template does not list.

**None of these is implemented, and this audit does not implement any of them.**

### D3's exclusion of this region

The right outcome, reached from a premise that does not hold. D3 refused because target_rows(6) < initial_rows(23) implies deletion. But the '6' was never a target for that table — it is GT.tables[13].rows, the FY2024 BVD independence-code table. The correct reason to exclude template T13 is that it has no bound current source and requires placeholder activation, not row insertion.

## E. Table 14 Analysis

**Disputed figures**: `6 → 10` vs `8 → 10`

**Template identity** (measured): `No \| Company \| Province \| Tax code \| VN SIC Code \| Business description` — 8 rows × 6 columns.

**Semantic identity**: Vietnamese comparable companies (No / Company / Province / Tax code / VN SIC / Business description)

| Concept | Value | Evidence |
| :--- | :--- | :--- |
| FY2023 rows — *positional* `HIST[14]` | 6 | `Code \| Description` — **unrelated table** |
| FY2023 rows — *semantic* | **no counterpart exists** | — |
| Template rows | **8** | measured; Phase B agrees (8) |
| Current source records | **0** | No Vietnamese comparable-company records exist in either bound workbook. |
| Planned target rows | 10 (insert 4) | Phase C literal; arithmetic **inconsistent** |
| D1 synthetic fixture | 6 rows -> 10 rows (+4) | `test_golden_case_table_14_growth_6_to_10` on clean_test_doc.tables[1] |
| D1 real-fixture spec | present | 8 → 10 |
| D2 coverage | **REAL_FIXTURE** (12 cells) | `test_four_golden_tables_real_fixture_reconciliation_and_lineage` |
| D3 actual | 8 → 10 | EXECUTED |
| FY2024 rows — *positional* `GT[14]` | 10 | `Step \| Search criteria \| Search criteria \| Passed` — **unrelated table** |
| FY2024 rows — *semantic* | **no counterpart exists** | — |

**Why the two figures disagree.** The left-hand figure (`6 → 10`) is `HIST.tables[14].rows → GT.tables[14].rows`: two unrelated tables paired by index. The right-hand figure (`8 → 10`) keeps the real template row count on the left but retains the same positional Ground-Truth number on the right. **Neither figure describes a real roll-forward of this table.**

**Cross-document note.** No FY2023 or FY2024 table uses the Province / VN SIC column schema. The FY2024 engagement presented its (all-Vietnamese) comparable set using the template T15 schema instead.

**Structural status.** MISCLASSIFIED. No FY2023 or FY2024 table uses this column schema; the FY2024 engagement used the T15 schema for its all-Vietnamese set. Requires a human decision on which presentation applies. Its planned target of 10 rows has no basis.

## F. Table 15 Analysis

**Disputed figures**: `10 → 16` vs `7 → 16`

**Template identity** (measured): `No \| Company \| Country \| Ticker symbol/ / Tax code \| Business description` — 7 rows × 5 columns.

**Semantic identity**: Comparable companies list (No / Company / Country / Ticker / Business description)

| Concept | Value | Evidence |
| :--- | :--- | :--- |
| FY2023 rows — *positional* `HIST[15]` | 10 | `Step \| Search criteria \| Search criteria \| Passed` — **unrelated table** |
| FY2023 rows — *semantic* | [14, 14] | HIST T11 (14r), HIST T19 (14r) |
| Template rows | **7** | measured; Phase B agrees (7) |
| Current source records | **0** | No comparable-company records exist in either bound workbook. |
| Planned target rows | 16 (insert 6) | Phase C literal; arithmetic **inconsistent** |
| D1 synthetic fixture | 10 rows -> 16 rows (+6) | `test_golden_case_table_15_growth_10_to_16` on clean_test_doc.tables[1] |
| D1 real-fixture spec | present | 7 → 16 |
| D2 coverage | **REAL_FIXTURE** (45 cells) | `test_four_golden_tables_real_fixture_reconciliation_and_lineage` |
| D3 actual | 7 → 16 | EXECUTED |
| FY2024 rows — *positional* `GT[15]` | 16 | `Screening criteria \| Eliminated \| Retained` — **unrelated table** |
| FY2024 rows — *semantic* | [11, 11] | GT T10 (11r), GT T16 (11r) |

**Why the two figures disagree.** The left-hand figure (`10 → 16`) is `HIST.tables[15].rows → GT.tables[15].rows`: two unrelated tables paired by index. The right-hand figure (`7 → 16`) keeps the real template row count on the left but retains the same positional Ground-Truth number on the right. **Neither figure describes a real roll-forward of this table.**

**Cross-document note.** The only golden table with a genuine cross-document counterpart. FY2023 carried 13 comparables (mixed Vietnam + India); FY2024 carried 10 (Vietnam only). GT drops the Business description column.

**Structural status.** PARTIALLY CORRECT CONCEPT, WRONG NUMBERS. This is the only golden table with a genuine counterpart. The real roll-forward is 13 FY2023 comparables -> 10 FY2024 comparables, i.e. a target of 11 rows (header + 10) achieved by REPLACING 6 placeholder rows — a net +4. The planned target of 16 is a positional artifact.

## G. Phase B Reconciliation

**Verdict: CORRECT — not a source of the discrepancy.**

| Table | Phase B `row_count` | Measured template rows | Agrees | `col_count` | `table_hash` | `safe_to_clone` |
| ---: | ---: | ---: | :---: | ---: | :--- | :---: |
| 10 | 6 | 6 | ✅ | 3 | `2bd8b27f` | True |
| 13 | 23 | 23 | ✅ | 2 | `b1384e4e` | True |
| 14 | 8 | 8 | ✅ | 6 | `515cf63c` | True |
| 15 | 7 | 7 | ✅ | 5 | `d7c319bd` | True |

- **StructuralDelta**: Phase B does not emit StructuralDelta at all. Its table_signatures record only template-side facts (row_count, col_count, table_hash, header_signature, gridspan/vmerge topology, prototype_row_idx, safe_to_clone), and every one of them matches the live template exactly.
- **RowTemplate**: RowTemplate.prototype_row_idx = 1 is structurally defensible for T14/T15 (row 1 is a real placeholder data row). It is semantically wrong for T10, whose row 1 is '35th Percentile' — a unique statistical label, not a repeatable record — and for T13, whose row 1 is blank.
- **safe_to_clone**: safe_to_clone=True is TRUE AS SPECIFIED: the field means the row's OOXML topology can be deep-copied without corrupting the package, and that holds for all four. It does NOT mean the table is semantically repeatable, and nothing downstream distinguishes the two. This is a naming/contract hazard rather than an incorrect value.

**DOMAIN MODEL GAP recorded.** Phase B has no field for historical_rows, current_source_rows or target_rows — correctly, since it profiles only the template. The gap is that no LATER phase introduced a structure to hold them either, so Phase C had to overload StructuralDelta.

## H. Phase C Reconciliation

**Verdict: INCORRECT — this is the origin of the discrepancy.**

StructuralDelta exposes exactly two row-count fields, template_rows and target_rows, plus insert_count/delete_count. Phase C needed four distinct concepts and had two slots, so it put template_rows in the template slot, Ground-Truth rows in the target slot, and buried the FY2023 count in the untyped observation_context dict.

| Region | Table | `template_rows` | `target_rows` | target − template | declared `insert_count` | Consistent |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: |
| `rfr-071` | 10 | 6 | 11 | 5 | 9 | **❌** |
| `rfr-093` | 13 | 23 | 6 | -17 | 2 | **❌** |
| `rfr-098` | 14 | 8 | 10 | 2 | 4 | **❌** |
| `rfr-101` | 15 | 7 | 16 | 9 | 6 | **❌** |

Not one of the four is arithmetically self-consistent, because `insert_count` is `GT[i] − HIST[i]` while `target_rows − template_rows` is `GT[i] − TEMPLATE[i]`.

**Derivation method.** The values are HARDCODED LITERALS in the planning engine, not measurements. No code path in Phase C opens the FY2023 document or counts source records; source_binding only verifies that named Excel ranges exist.

**No silent normalization.** The existing manifest JSON has been left byte-for-byte as produced. This audit records the discrepancy; it does not rewrite it.

Phase C should have preserved four separately-provenanced numbers. Recorded as **GAP-01** and **GAP-02**.

## I. D1 Reconciliation

**Verdict: SYNTHETIC GOLDEN CASES; REAL-FIXTURE RUN COVERED ONLY 3 OF 4 TABLES.**

| Table | Case label | Synthetic growth | Equals `HIST[i] → GT[i]`? | Real-fixture case |
| ---: | :--- | :--- | :---: | :--- |
| 10 | SYNTHETIC | 2 -> 11 | ✅ | TEMPLATE-TO-GROUND-TRUTH: 6 -> 11 |
| 13 | SYNTHETIC | 4 -> 6 | ✅ | ABSENT from the real-fixture test |
| 14 | SYNTHETIC | 6 -> 10 | ✅ | TEMPLATE-TO-GROUND-TRUTH: 8 -> 10 |
| 15 | SYNTHETIC | 10 -> 16 | ✅ | TEMPLATE-TO-GROUND-TRUTH: 7 -> 16 |

Every D1 golden case is a **synthetic** reproduction of a phantom positional delta, executed on a purpose-built fixture table that is neither the template's table nor any real document's table.

### Overclaim — CONFIRMED

- **Artifact**: `docs\evaluation\LocalFile_RollForward_Structural_Writeback_D1_2026-08-21.md`
- **Claim**: 'The four golden table-growth cases ... were verified end-to-end against the real Master Template', with Table 13 listed as APPLIED & VERIFIED.
- **Reality**: foundation/tests/test_structural_writeback.py::test_real_fixture_end_to_end_all_4_tables builds exactly three TableMutationSpec objects (tables 10, 14, 15). No Table 13 spec exists in it. The test name says 'all_4_tables'; the body executes three.

### Region id drift

| Table | D1 report says | Phase C anchor says |
| ---: | :--- | :--- |
| 13 | `rfr-096` | `rfr-093` |
| 14 | `rfr-097` | `rfr-098` |
| 15 | `rfr-098` | `rfr-101` |

The D1 report and the D1/D2 real-fixture tests use region ids that disagree with the row-template anchors Phase C actually emitted. rfr-098 denotes Table 15 in the D1 report but Table 14 in the manifest.

### Idempotence gap

Every real-fixture MutationPlan sets expected_postcondition_hash='dummy'. StructuralWritebackEngine's NOOP check compares a live fingerprint against that field, so it can never trigger on a real-fixture run. D1's idempotence test passes only because it patches the field with a real fingerprint before the second call.

## J. D2 Reconciliation

**Verdict: THE '4 / 4 GOLDEN TABLES' HEADLINE MIXES 3 REAL-FIXTURE TABLES WITH 1 SYNTHETIC UNIT TEST.**

**Why D2 said 4/4 while D3 excluded Table 13.** D2 reported 4/4 because the report author counted four table-level unit tests, three of which ran against the real Master Template output and one of which ran against an in-test synthetic document. The real-fixture reconciliation itself asserts three tables.

| | Real-fixture run | Table 13 |
| :--- | :--- | :--- |
| Test | `test_four_golden_tables_real_fixture_reconciliation_and_lineage` | `test_exact_source_to_output_mapping_table_13` |
| Kind | REAL_FIXTURE | **SYNTHETIC** |
| Tables | [10, 14, 15] | in-test document |
| In-test assertion | `assert summary.total_tables == 3` | `insert_count=0` |
| Cells | 72 | 4 |

**Explicitly recorded: D2's Table 13 is a synthetic fixture.** tmp_path/t13_doc.docx built in-test: 3 rows x 2 cols, BVD independence codes A/B. Relation to the real template's Table 13: **NONE — template T13 is a 23-row x 2-col screening matrix**. Relation to the `4 → 6` claim: NONE — the synthetic fixture is 3 rows and does not grow. The report's '4 template rows -> 6 expanded rows' line for Table 13 is not produced by any executed test.

### What "72 / 72 cells matched" does and does not prove

- ✅ **Proves**: Every cell value the approved MutationPlan declared was written into the generated document exactly as declared, with unit-aware semantic and display comparison.
- ❌ **Does not prove**: That those values came from the FY2024 sources. Measured from the D3 lineage: 0 of 72 cells carry a source cell address. 15 cells (Table 10) name a workbook and sheet; 57 cells (Tables 14 and 15) name only a workbook and carry harness-generated placeholder values.

*The D2 report file is unmodified.*

## K. D3 Reconciliation

**Verdict: MECHANICALLY SOUND, SEMANTICALLY WRONG TARGETS — D3 faithfully executed an incorrect plan.**

| Region | Table | Before | After | Inserted |
| :--- | ---: | ---: | ---: | ---: |
| `rfr-071` | 10 | 6 | 11 | +5 |
| `rfr-098` | 14 | 8 | 10 | +2 |
| `rfr-101` | 15 | 7 | 16 | +9 |

### Semantic defects in the published artifact

All 34 registered hard validation rules passed. The output is still not usable:

**Table 10 — `WRONG_TABLE`**  
Five FY2024 P&L line items (Net Sales, COGS, Gross Profit, EBIT, NCP) were appended to the arm's-length-range table, below rows '35th Percentile', 'Median', '75th Percentile' and "ABC's PLI in FY20xx". The values are real and correctly traced to FA&RPT, but they belong to a different table. The 'xx%' placeholders they were meant to inform remain unfilled.  
*Evidence*: `docs/evaluation/output/Generated_LocalFile_FY2024_PhaseD3.docx table 10 rows 6-10`

**Table 14 — `INSERTED_AFTER_FOOTER_ROW`**  
Template T14 row 7 is a full-width footer ("ABC's VN SIC Code: xxx"). The engine appends after the last row, so both new data rows landed BELOW the footer. Placeholder rows 'Company 1'-'Company 5' and the ellipsis row remain above it.  
*Evidence*: `docs/evaluation/output/Generated_LocalFile_FY2024_PhaseD3.docx table 14 rows 8-9`

**Table 15 — `PLACEHOLDERS_RETAINED_AND_COLUMN_MISMATCH`**  
Nine rows were appended after the ellipsis placeholder row; 'Company 1'-'Company 5' and the ellipsis remain. Column 4 is 'Business description' but received a percentage ('4.20%'), because the harness row template was written for a benchmarking-margin table.  
*Evidence*: `docs/evaluation/output/Generated_LocalFile_FY2024_PhaseD3.docx table 15 rows 7-15`

### Why validation did not catch this

- **Covered**: Package integrity, perception, element inventory, declared target row/column/header invariants, non-target semantic drift, merge topology, media and relationships, headers/footers, sections, headings, body reading order.
- **Not covered**: Whether an inserted row belongs in that table at all; whether the insertion position respects a table's footer or placeholder rows; whether the column semantics of the value match the column header. No registered rule expresses table-level semantic fit, so all 34 passed on a semantically incoherent output.

## L. Ground Truth Comparison

> Ground Truth is evaluation-only. This section diagnoses; it changes no planning artifact.

**Inventory mismatch**: FY2023 has 22 tables, the Template 16, FY2024 19. The three documents cannot be correlated by table index. Any correlation must be by header schema and content.

### Template Table 10 — Arm's-length range summary (6r x 3c)

- **FY2023 counterpart**: NONE (range defined in prose, HIST paragraph 282)
- **FY2024 counterpart**: NONE (range defined in prose, GT paragraph 274)
- **True delta**: No table-level delta exists. Placeholder activation only.
- **D3 produced**: 11 rows containing 5 P&L line items that belong elsewhere
- **Verdict**: **CONTRADICTED**

### Template Table 13 — Screening matrix, key/value (23r x 2c)

- **FY2023 counterpart**: HIST T15 Step matrix (10r x 4c) + HIST T16 Screening criteria (15r x 3c)
- **FY2024 counterpart**: GT T14 Step matrix (10r x 4c) + GT T15 Screening criteria (16r x 3c)
- **True delta**: Format redesign: two tables in FY2023/FY2024 collapse into one 23-row key/value table in the Decree 20-2025 template. Row counts are not comparable.
- **D3 produced**: Not executed (excluded)
- **Verdict**: **INFERRED — exclusion was correct, stated reason was not**

### Template Table 14 — VN comparables, Province/VN SIC schema (8r x 6c)

- **FY2023 counterpart**: NONE with this schema
- **FY2024 counterpart**: NONE with this schema; GT used the T15 schema for its Vietnam-only set
- **True delta**: Undetermined — requires a human decision on presentation.
- **D3 produced**: 10 rows, 2 appended below the footer row
- **Verdict**: **CONTRADICTED**

### Template Table 15 — Comparables, Country/Ticker schema (7r x 5c)

- **FY2023 counterpart**: HIST T11 and T19 (14r x 4c) = 13 comparables, Vietnam + India
- **FY2024 counterpart**: GT T10 and T16 (11r x 4c) = 10 comparables, Vietnam only
- **True delta**: 13 FY2023 comparables -> 10 FY2024 comparables (a DECREASE of 3). Target shape is 11 rows. GT also drops the Business description column (5 template cols -> 4).
- **D3 produced**: 16 rows of placeholder peers
- **Verdict**: **CONTRADICTED**

**Summary.** Of the four golden tables, exactly one (T15) has a genuine cross-document counterpart, and its real delta is negative. None of the four 'growth' figures used by Phases C, D1, D2 or D3 is supported by the Ground Truth.

## M. Domain Model Gaps

| ID | Severity | Gap | Location |
| :--- | :--- | :--- | :--- |
| `GAP-01` | **CRITICAL** | StructuralDelta cannot express four distinct row-count concepts | `foundation/applications/rollforward/models.py :: StructuralDelta` |
| `GAP-02` | **CRITICAL** | No provenance on any row count | `StructuralDelta.observation_source / observation_context (free-form str and untyped dict)` |
| `GAP-03` | **HIGH** | safe_to_clone conflates OOXML safety with semantic repeatability | `foundation/applications/rollforward/models.py :: RowTemplate.safe_to_clone` |
| `GAP-04` | **HIGH** | No table anatomy: header / data region / placeholder rows / footer | `RowTemplate and TableMutationSpec` |
| `GAP-05` | **HIGH** | mutation_strategy is a free-form string, not a typed operation | `RollForwardRegion.mutation_strategy (str) and TableMutationSpec.operation (str)` |
| `GAP-06` | **MEDIUM** | Region-to-table binding is carried in a parsed anchor string | `RowTemplate.row_anchor, parsed with str.split in the D3 scope resolver` |
| `GAP-07` | **MEDIUM** | No column-schema delta concept | `StructuralDelta.column_delta (int only)` |
| `GAP-08` | **MEDIUM** | Reconciliation cannot distinguish a bound source value from a plan-authored literal | `CellMutationSpec (source_cell_address is Optional and unenforced)` |

### `GAP-01` — StructuralDelta cannot express four distinct row-count concepts (CRITICAL)

- **Location**: `foundation/applications/rollforward/models.py :: StructuralDelta`
- **Current fields**: `template_rows`, `target_rows`, `insert_count`, `delete_count`, `column_delta`
- **Missing concepts**: `historical_rows`, `current_source_record_count`, `placeholder_row_count`, `data_region_start_idx`, `data_region_end_idx`, `footer_row_count`
- **Consequence**: Phase C had two slots for four concepts and silently mixed three documents into one object. Every downstream consumer then read those fields as if they described a single document.

### `GAP-02` — No provenance on any row count (CRITICAL)

- **Location**: `StructuralDelta.observation_source / observation_context (free-form str and untyped dict)`
- **Consequence**: There is no typed way to say which document a number was measured from, so a Ground-Truth-derived figure is indistinguishable from a template measurement. This is what let Ground Truth reach a planning artifact undetected.

### `GAP-03` — safe_to_clone conflates OOXML safety with semantic repeatability (HIGH)

- **Location**: `foundation/applications/rollforward/models.py :: RowTemplate.safe_to_clone`
- **Consequence**: The docstring correctly limits it to XML topology, but no separate field records whether a table is semantically row-repeatable. All four golden tables report safe_to_clone=True, including a fixed statistical summary and a screening narrative.

### `GAP-04` — No table anatomy: header / data region / placeholder rows / footer (HIGH)

- **Location**: `RowTemplate and TableMutationSpec`
- **Consequence**: StructuralWritebackEngine always appends after the last row, so rows land below footers (observed in template T14), and placeholder rows are never replaced.

### `GAP-05` — mutation_strategy is a free-form string, not a typed operation (HIGH)

- **Location**: `RollForwardRegion.mutation_strategy (str) and TableMutationSpec.operation (str)`
- **Consequence**: Only INSERT_ROWS is implemented, so any region that needs UPDATE, placeholder activation, or removal is either misrepresented as an insertion or blocked with a misleading reason.

### `GAP-06` — Region-to-table binding is carried in a parsed anchor string (MEDIUM)

- **Location**: `RowTemplate.row_anchor, parsed with str.split in the D3 scope resolver`
- **Consequence**: There is no typed target_table_index, which is how the D1 report and the D1/D2 tests came to use region ids that disagree with the manifest anchors.

### `GAP-07` — No column-schema delta concept (MEDIUM)

- **Location**: `StructuralDelta.column_delta (int only)`
- **Consequence**: Template T15 has 5 columns and its FY2024 counterpart has 4. An integer delta cannot say which column was dropped, so no validation can catch a value written into a column whose header does not match it.

### `GAP-08` — Reconciliation cannot distinguish a bound source value from a plan-authored literal (MEDIUM)

- **Location**: `CellMutationSpec (source_cell_address is Optional and unenforced)`
- **Consequence**: 0 of 72 reconciled cells in the D3 run carry a source cell address, yet the run reports 100% source-to-output match. The metric measures plan-to-output fidelity and is titled source-to-output.

**Answering the question in §12 directly**: yes. The domain model needs explicit, separately provenanced `historical_rows`, `template_rows`, `current_source_rows` and `target_rows`, and future mutation strategies must distinguish `INSERT`, `DELETE`, `ACTIVATE_PLACEHOLDER` and `UPDATE`. **None of this is implemented in D3.1.**

## N. Recommended Corrections

Recommendations only. Nothing below is implemented.

| ID | Priority | Type | Recommendation |
| :--- | :--- | :--- | :--- |
| `REC-01` | **P0** | DOMAIN_MODEL | Replace StructuralDelta's two row-count slots with four explicitly named, separately provenanced measurements: historical_rows, template_rows, current_source_record_count, target_rows — each carrying the document id, artifact hash and measurement method it came from. |
| `REC-02` | **P0** | GOVERNANCE | Add a planning-time assertion that no planning field may be derived from the Ground Truth artifact, and make target_rows require a non-Ground-Truth provenance record. |
| `REC-03` | **P0** | PLANNING | Correlate documents by header schema and content fingerprint, never by positional table index. Emit an explicit UNCORRELATED verdict when no counterpart exists, as is the case for template T10, T13 and T14. |
| `REC-04` | **P1** | DOMAIN_MODEL | Introduce a typed MutationOperation enum — INSERT_ROWS, DELETE_ROWS, UPDATE_CELLS, ACTIVATE_PLACEHOLDER, REPLACE_DATA_REGION — and require every region to declare one. Do not implement the new operations in the same change; land the type first so that unsupported operations are refused by name rather than by arithmetic accident. |
| `REC-05` | **P1** | DOMAIN_MODEL | Add a TableAnatomy value object (header_rows, data_region span, placeholder_row_idxs, footer_rows) so insertion position and placeholder replacement are explicit. |
| `REC-06` | **P1** | VALIDATION | Add a semantic-fit validation family to the D3 FullDocumentValidator: reject an insertion whose row lands outside the declared data region, and reject a value whose type contradicts its column header. |
| `REC-07` | **P1** | RECONCILIATION | Require source_cell_address (or an explicit UNBOUND_LITERAL marker) on every CellMutationSpec, and report bound-cell coverage separately from plan-to-output fidelity so a run can never present 100% match while 0% of cells are source-bound. |
| `REC-08` | **P2** | HYGIENE | Stop using 'dummy' for expected_postcondition_hash in real-fixture plans; compute the true postcondition or leave the field null and let the engine treat null as 'idempotence unavailable' rather than 'never applied'. |
| `REC-09` | **P2** | REPORTING | Label every metric in every evaluation report as REAL_FIXTURE or SYNTHETIC at the point of the number, and never aggregate the two into a single ratio such as '4/4'. |
| `REC-10` | **P2** | TRACEABILITY | Add a typed target_table_index to RollForwardRegion so region-to-table binding stops depending on string parsing and cross-artifact region id drift becomes detectable. |

## O. Final Conclusion

**Single root cause.** Phase C correlated three structurally different documents by positional table index and recorded the result in a StructuralDelta that has no room for the four row-count concepts involved.

### Which numbers are true

| Claim | Verdict |
| :--- | :--- |
| template_rows (6 / 23 / 8 / 7) | TRUE — measured, and independently corroborated by Phase B. |
| '2 -> 11', '4 -> 6', '6 -> 10', '10 -> 16' | FALSE as roll-forward deltas. Each is HIST.tables[i].rows -> GT.tables[i].rows for semantically unrelated tables. |
| '6 -> 11', '23 -> 6', '8 -> 10', '7 -> 16' | HALF TRUE. The left side is the real template row count; the right side is the same positional Ground-Truth artifact. |
| D2 '72 / 72 cells matched' | TRUE as plan-to-output fidelity. NOT true as source-to-output traceability: 0 of 72 cells carry a source cell address. |
| D2 '4 / 4 golden tables' | MISLEADING — 3 real-fixture tables plus 1 synthetic unit test. |
| D1 'four golden cases verified against the real Master Template' | OVERCLAIM — the real-fixture test contains three specs, not four. |
| D3 '34 / 34 validation checks passed' | TRUE for what those checks measure. No registered check expresses semantic fit, so the result is compatible with a semantically incoherent document. |

### The source of truth

| Concept | Authoritative source |
| :--- | :--- |
| `template_rows` | The Master Template itself. Phase B measured it correctly. |
| `historical_rows` | The FY2023 Local File, correlated **by header schema**, never by index. |
| `current_source_rows` | The bound workbooks — which contain **no** benchmarking data at all. |
| `target_rows` | **Currently unknowable from approved inputs** for T10, T13 and T14. For T15 it is 11 (header + 10 comparables), and that figure is only visible in the Ground Truth, which may not feed planning. |

**What is trustworthy.** Phase B is sound. The D1 mutation mechanics, D2 comparison mathematics and D3 governance, transaction and validation machinery are all sound. What is unsound is the planning input they were given: the four golden growth targets.

**Honest status of Phase D3.** D3 did exactly what it was designed to do — it executed an approved plan atomically, reconciled every declared cell, passed every registered structural gate and published a reproducible artifact. The artifact is nevertheless not a usable FY2024 Local File, because the plan it executed targeted the wrong tables with the wrong row counts.

### Constraints honoured

- No production code modified.
- DELETE_ROWS not implemented.
- No mutation capability expanded.
- No historical report altered.
- No prior number rewritten to force agreement.
- Ground Truth used for evaluation and diagnosis only; no planning artifact changed.

---

*Every measured figure in this report can be regenerated with `python foundation/tests/evaluation/rollforward_structural_audit_d3_1.py`.*
