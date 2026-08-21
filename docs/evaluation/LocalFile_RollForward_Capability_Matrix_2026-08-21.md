# Local File Roll-Forward Capability & Mapping Matrix

**Date**: 2026-08-21  
**Project**: DocPercepInterac-Foundation  
**Scope**: Capability Matrix & Technical Domain Mapping for Local File Roll-Forward Workflow  

---

## 1. Document Inventory & Role Matrix

| Document Key | Actual Filename | Format | Size | Total Elements | Primary Role | Data Provided | Excluded / Prohibited Usage |
|---|---|---|---|---|---|---|---|
| **A. Historical Source** | `HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx` | DOCX | 2,699 KB | 2,777 | Historical Baseline | • Narrative context & industry profile<br>• Previous-year FAR analysis<br>• Historical search matrix & rejection criteria<br>• Baseline text phrasing | ❌ Do NOT use for FY2024 financial figures<br>❌ Do NOT assume unchanged corporate ownership |
| **B. Target Template** | `Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx` | DOCX | 2,753 KB | 848 | Target Container & Structural Schema | • Master outline & Decree 20-2025 compliance structure<br>• Standardized table column layouts<br>• Placeholder markers (`FY20xx`, `[ABC]`) | ❌ Contains NO client-specific transaction values<br>❌ Table rows are skeleton templates (e.g. 1-4 rows) |
| **C. Current Data 1** | `HMV-FA&RPT FY2024.xlsx` | XLSX | 395 KB | 667 | Financial & RPT Data Source | • Audited FY2024 Balance Sheet & P&L (`FS`)<br>• Related Parties list & categories (`I. Related parties`)<br>• Transaction values & markups (`RPTs`)<br>• Multi-year financial ratios (`Financial Analysis`) | ❌ Does NOT contain full tax declaration checklist<br>❌ Does NOT contain benchmark rejection company list |
| **D. Current Data 2** | `HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx` | XLSX | 2,934 KB | 10,005 | Regulatory Tax Appendix | • Official Decree 20/2025 Appendix I tables<br>• Section III RPT Categorization<br>• Section IV Segmented Data (RPT vs Independent)<br>• 30% EBITDA interest cap calculation (`Interest expenses`) | ❌ Narrative qualitative analysis not present<br>❌ Benchmarking qualitative write-up not present |
| **E. Ground Truth** | `HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx` | DOCX | 2,578 KB | 2,838 | Reference & Evaluation Benchmark ONLY | • Validates expected output structure<br>• Confirms real-world row growth and styling<br>• Verifies company name and RPT changes | ⚠️ **STRICTLY PROHIBITED AS INPUT SOURCE**<br>Used exclusively to measure and validate proposed workflow accuracy |

---

## 2. Foundation Perception vs Mutation Capability Baseline

| Structural Primitive | Extraction / Detection | DOM Rendering & Visualization | Mapped & Addressed | In-Place Scalar Writeback | Structural Mutation (Insert/Delete/Clone) | Current Status |
|---|---|---|---|---|---|---|
| **Paragraph Text** | ✅ Full (`python-docx`) | ✅ Full (`docx-preview`) | ✅ Full (`AnchorDOCX`, `style_id` + fingerprint) | ✅ Full (`WritebackEngine._safe_replace_docx_para`) | ❌ None (Cannot insert/delete paragraph blocks) | **Scalar Editable** |
| **Table Cell Text** | ✅ Full (`extract_cell_visible_text`) | ✅ Full (`td[data-element-id]`) | ✅ Full (`AnchorDOCX`, `table_hash` + row/col) | ✅ Full (`WritebackEngine._safe_replace_docx_cell`) | ❌ None | **Scalar Editable** |
| **DOCX Table Rows** | ✅ Detected as cells | ✅ Rendered in grid | ✅ Mapped by index/hash | ❌ None | ❌ **HARD GAP**: Cannot clone row or mutate table row count | **Immutable Structure** |
| **DOCX Table Formatting** | ✅ Partial (`gridSpan`, `vMerge`) | ✅ Rendered | ❌ Not exposed as mutable anchor | ❌ None | ❌ Cannot copy borders, shading, cell margins | **Read-Only** |
| **XLSX Cell Value** | ✅ Full (`openpyxl`) | ✅ Full (`.xlsx-grid-cell`) | ✅ Full (`AnchorXLSX`, `sheet_name` + `cell_address`) | ✅ Full (`openpyxl` with type coercion & anti-drift) | ❌ Cannot insert/delete worksheet rows/columns | **Scalar Editable** |
| **XLSX Formula** | ✅ Full (`openpyxl`) | ✅ Full (read-only tooltip) | ✅ Full | 🛡️ Protected Read-Only (Throws error on overwrite) | ❌ None | **Protected Read-Only** |
| **Embedded Images** | ✅ Full (Media Manifest) | ✅ Full (`docx-preview` / canvas) | ✅ Full (`docx-rel:rid`, `media_id`) | ❌ None (Cannot replace binary asset) | ❌ Cannot regenerate diagrams or charts | **Asset Read-Only** |
| **Word Drawings / Canvas** | ✅ Full (`kind='drawing'`) | ✅ Rendered | ✅ Stamped with identity | ❌ None | ❌ Cannot mutate internal vector drawing shapes | **Container Read-Only** |
| **Headings & Hierarchy** | ✅ Full (`style_id`, regex) | ✅ Full (outline tree) | ✅ Mapped as paragraphs | ✅ Text editable | ❌ Cannot alter heading levels or renumber | **Scalar Editable** |
| **Footnotes & Endnotes** | ✅ Full | ✅ Rendered | ✅ Mapped | ❌ None | ❌ Cannot create or delete footnotes | **Read-Only** |

---

## 3. Template Table Roll-Forward Classification Matrix

Analysis of all 16 tables in `Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx` against Historical Source, Ground Truth, and Excel Data Sources:

| Table Index | Table Header / Name | Template Rows | Historical FY23 Rows | Ground Truth FY24 Rows | Row Delta Status | Source Data Binding | Roll-Forward Classification | Recommended Mutation Strategy |
|---|---|---|---|---|---|---|---|---|
| **Table 0** | Company Profile & Tax Box | 3 | 3 | 3 | `EQUAL` (3) | `HMV-FA&RPT FY2024.xlsx` → `I. Related parties` | `UPDATE` | In-place scalar update of company name, tax code, address |
| **Table 1** | Report Page Declaration | 3 | 3 | 3 | `EQUAL` (3) | Template metadata / Final render pass | `UPDATE` | In-place update of total page count post-generation |
| **Table 2** | Summary of Transactions & TP Methods | 4 | 25 | 25 | `REPEATABLE` (4 → 25) | `HMV-FA&RPT FY2024.xlsx` → `RPTs` & `III. Summary-RPTs` | `REPEATABLE` | **Row Cloning**: Clone row 1 schema 24 times; populate transaction names, methods, PLIs |
| **Table 3** | Related Party Transactions Summary | 8 | 2 | 2 | `REPEATABLE` (8 → 2) | `HMV-FA&RPT FY2024.xlsx` → `RPTs` (Rows 5-9) | `REPEATABLE` | **Row Shrinking / Truncation**: Keep 2 rows matching active material transactions; clear/remove unused template rows |
| **Table 4** | Related Party Loans & Borrowings | 4 | 1 | 1 | `REPEATABLE` (4 → 1) | `HMV-FA&RPT FY2024.xlsx` → `RPTs` (Interest row) & `Appendix I` → `Interest expenses` | `REPEATABLE` | **Row Truncation**: Keep 1 row for active shareholder loan; populate loan principal, currency, rate |
| **Table 5** | Functional, Asset & Risk (FAR) Profile | 28 | 6 | 6 | `UPDATE` (28 vs 6) | `HMV-24-Final-Local File for FY2023.docx` → Table 9 | `UPDATE` / `MANUAL_REVIEW` | Preserve 6-category entity FAR structure; verify functional role changes with Tax team |
| **Table 6** | Net Cost Plus (NCP) Formula Definition | 2 | 2 | 2 | `EQUAL` (2) | Template Standard Formula | `STATIC` | Preserve verbatim from Template (Decree 20-2025 standard) |
| **Table 7** | Operating Margin (OM) Formula Definition | 2 | 5 | 5 | `EQUAL` (2) | Template Standard Formula | `STATIC` | Preserve verbatim from Template |
| **Table 8** | Return on Assets (ROA) Formula Definition | 2 | 29 | 27 | `STATIC` (2) | Template Standard Formula | `STATIC` | Preserve formula definition; update text values if applicable |
| **Table 9** | Multi-Year Financial Comparatives Summary | 14 | 27 | 2 | `REPEATABLE` (14 → 2) | `HMV-FA&RPT FY2024.xlsx` → `Financial Analysis` | `REPEATABLE` | **Row Expansion**: Populate multi-year revenue, COGS, OP, and profitability ratios from `Financial Analysis` |
| **Table 10** | Financial Indicators & Weighted Averages | 6 | 2 | 11 | `GROWTH` (2 → 11, +9) | `HMV-FA&RPT FY2024.xlsx` → `Financial Analysis` (Rows 4-35) | `REPEATABLE` | **Row Cloning**: Clone ratio row 9 times; bind to audited 3-year weighted average metrics |
| **Table 11** | Key Balance Sheet & P&L Indicators | 9 | 14 | 7 | `REPEATABLE` (9 → 7) | `HMV-FA&RPT FY2024.xlsx` → `FS` (Audited Financials) | `REPEATABLE` | **Row Truncation/Binding**: Map standard lines (Net Sales, COGS, GP, Fin Exp, Admin Exp, EBIT) |
| **Table 12** | Appendix Compliance / Document Reference | 25 | 7 | 4 | `UPDATE` (25) | Local File Section Mapping | `UPDATE` | In-place update of cross-reference page and section numbers |
| **Table 13** | Search Matrix / Screening Steps Summary | 23 | 4 | 6 | `GROWTH` (4 → 6, +2) | Benchmark Study Report / `Draft BM FY24` | `REPEATABLE` | **Row Cloning**: Insert 2 screening steps corresponding to updated database filtering criteria |
| **Table 14** | Primary Comparable Companies List | 8 | 6 | 10 | `GROWTH` (6 → 10, +4) | Benchmark Study Report (`Draft BM FY24-W1203`) | `REPEATABLE` | **Row Cloning**: Clone comparable company row 4 times; populate company name, country, tax code, SIC |
| **Table 15** | Benchmarking Interquartile Range Results | 7 | 10 | 16 | `GROWTH` (10 → 16, +6) | Benchmark Study Report (`Draft BM FY24-W1203`) | `REPEATABLE` | **Row Cloning**: Clone company margin row 6 times; populate 3-year weighted average NCP/OM margins, Min, Q1, Median, Q3, Max |

---

## 4. Template Section & Narrative Region Classification

| Section / Region | Heading Title | Historical FY23 Baseline | Template State | Current Data Source | Classification | Roll-Forward Action |
|---|---|---|---|---|---|---|
| **Section 1** | Executive Summary | Entity overview, summary table of RPTs and findings | Skeleton with `[ABC]` and `FY20xx` | `HMV-FA&RPT FY2024.xlsx` (`FS`, `RPTs`) | `UPDATE` | Roll-forward executive summary text, insert FY2024 transaction figures and conclusion |
| **Section 2** | Organizational Structure | Ownership tree, subsidiary overview, Board of Management | Template narrative + diagram placeholder | `I. Related parties` + Corporate register | `UPDATE` / `REGENERATE` | Update company legal form, share capital, parent ownership percentages; update org chart |
| **Section 3** | Business Operations & Strategy | Manufacturing process, product lines, industry environment | Generic template text with `[PRODUCTS]` | `HMV-24-Final Local File.docx` Section 3 | `STATIC` / `UPDATE` | Carry over business description narrative; update annual production volumes and headcount |
| **Section 4** | Related Party Transactions | Detailed descriptions of purchases, sales, processing, loans | Template sections with `[RELATED PARTY]` | `HMV-FA&RPT FY2024.xlsx` (`RPTs`, `III. Summary-RPTs`) | `UPDATE` & `REPEATABLE` | Populate transaction amounts, pricing terms, contract numbers, and counterparties |
| **Section 5** | Functional Analysis (FAR) | In-depth analysis of manufacturer vs principal FAR | Template tables and generic manufacturer narrative | `HMV-24-Final Local File.docx` Section 5 | `STATIC` | Carry forward verified FAR profile (contract manufacturer); review for any business model shift |
| **Section 6** | Economic Analysis & Method Selection | Selection of TNMM / Net Cost Plus method, tested party | Template methodology text (Decree 20-2025) | Benchmark Study / `Financial Analysis` | `UPDATE` | Update tested party financial year metrics; verify selected PLI and 3-year average range |
| **Section 7** | Benchmarking Analysis & Search Process | Quantitative screening matrix, rejection steps, final set | Skeleton tables with sample rows | Benchmark Study Report (`Draft BM FY24`) | `REPEATABLE` | Expand search matrix steps, populate comparable companies list and quartile calculations |
| **Section 8** | Conclusion & Tax Compliance | Arm's length conclusion, CIT declaration reference | Template concluding formula | Benchmark IQR vs Tested Party margin | `UPDATE` | Compare tested party margin (e.g. 3.86%) against Interquartile Range (Q1-Q3); conclude arm's length |
| **Appendix** | Document Archive Checklist | 25 compliance items per Decree 20 | 25-row standard table | Local File generated structure | `UPDATE` | Update table of cross-references to internal sections |

---

## 5. Media & Visual Figures Inventory

| Figure # | Historical File Asset (FY23) | Template Placeholder | Ground Truth Asset (FY24) | Description / Purpose | Roll-Forward Classification | Required Generation / Replacement Capability |
|---|---|---|---|---|---|---|
| **Figure 1** | `word/media/image1.png` (45 KB) | Drawing container #1 | `word/media/image1.png` (42 KB) | Global Ownership & Shareholder Structure Chart | `UPDATE` / `REGENERATE` | Replace image binary with updated ownership structure diagram (e.g. 100% Martin Magnusson) |
| **Figure 2** | `word/media/image2.png` (88 KB) | Drawing container #2 | `word/media/image2.png` (85 KB) | Local Organization & Management Hierarchy Chart | `UPDATE` / `REGENERATE` | Replace image binary with updated organizational chart (General Director, Factory Manager, QC, etc.) |
| **Figure 3** | `word/media/image3.png` (120 KB) | Drawing container #3 | `word/media/image3.png` (120 KB) | Manufacturing & Operations Flowchart | `STATIC` | Carry over existing manufacturing process flow diagram verbatim |
| **Figure 4** | `word/media/image4.png` (15 KB) | Drawing container #4 | `word/media/image4.png` (15 KB) | Transfer Pricing Analysis Framework Chart | `STATIC` | Carry over standard KPMG TP framework graphic verbatim |
| **Figure 5** | `word/media/image5.png` (65 KB) | None (in Benchmarking) | `word/media/image5.png` (62 KB) | Benchmarking Interquartile Range Scatter Plot / Graph | `REGENERATE` | Generate new IQR bar/scatter chart reflecting FY2024 quartile thresholds (Min, Q1, Median, Q3, Max) |
| **Logos** | `word/media/image6.png` | None | `word/media/image6.png` | KPMG brand mark & headers | `STATIC` | Preserve master template branding verbatim |

---

## 6. Structural Writeback Operation Specification

Comparison of required future operations vs current Foundation capabilities:

```
+-----------------------------------+--------------------+------------------------+------------------------------------------+
| Operation                         | Current Writeback  | Required Capability    | Technical Implementation Path            |
+-----------------------------------+--------------------+------------------------+------------------------------------------+
| replace_paragraph_text            | Supported (Scalar) | In-place text replace  | Already implemented in WritebackEngine   |
| replace_cell_value (DOCX/XLSX)    | Supported (Scalar) | In-place cell update   | Already implemented in WritebackEngine   |
| insert_table_row (DOCX)           | NOT Supported      | Structural insertion   | StructuralWritebackEngine.insert_row()   |
| clone_template_row (DOCX)         | NOT Supported      | Deep XML cloning       | StructuralWritebackEngine.clone_row()    |
| delete_table_row (DOCX)           | NOT Supported      | Row removal            | StructuralWritebackEngine.delete_row()   |
| preserve_gridspan_vmerge (DOCX)   | NOT Supported      | Layout topology sync   | Copy tcPr/gridSpan/vMerge on clone       |
| copy_cell_shading_borders (DOCX)  | NOT Supported      | Style replication      | Copy w:shd, w:tcBorders XML elements     |
| replace_media_asset (DOCX)        | NOT Supported      | Binary replacement     | Update zip word/media/ and document.xml.rels |
| update_table_anchors_post_growth  | NOT Supported      | Anti-Drift re-indexing | Automatic table_hash & row re-indexing   |
+-----------------------------------+--------------------+------------------------+------------------------------------------+
```
