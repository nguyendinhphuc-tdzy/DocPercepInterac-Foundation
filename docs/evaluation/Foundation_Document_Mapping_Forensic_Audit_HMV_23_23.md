# Foundation Document Mapping Forensic Audit: HMV 23&23 EN compare.docx

**Audit Target File**: `anonymize client/Demo files/Demo files/Compare LF/HMV 23&23 EN compare.docx`  
**File Size**: 2,997,575 bytes (2.86 MB)  
**Audit Scope**: Forensic Root Cause Analysis of 3,728 Unavailable/Ambiguous Elements (Audit Only — Zero Production Code Changes)  
**Date**: August 20, 2026  

---

## 1. Workbench / Fallback Status

Before analyzing document perception, the runtime request path for the Foundation Agent was verified:

```
============================================================
WORKBENCH RUNTIME STATUS
============================================================
provider_connected : False
model_called       : None (Config error: WORKBENCH_SUBSCRIPTION_KEY environment variable is not set)
fallback_used      : True (Deterministic local fallback engine)
============================================================
```

- **Analysis**: In this execution environment, Azure OpenAI Workbench credentials (`WORKBENCH_SUBSCRIPTION_KEY` and `WORKBENCH_CHARGE_CODE`) are not populated in the shell environment.
- **Request Flow**: `orchestrator.py` caught `WorkbenchConfigError` in `_call_workbench_or_fallback` and engaged the local deterministic fallback.
- **Finding**: The mapping issue is **strictly a Document Perception & Identity Bridge issue** in the Foundation Core and has **zero dependency on LLM models or Agent routing**.

---

## 2. Document Overview

`HMV 23&23 EN compare.docx` is an automated **Word Document Comparison (Compare Documents)** artifact between two revisions of the Hestra Vietnam Transfer Pricing Local File. It contains dense revision markup (Track Changes) comprising **4,372 tracked insertions (`<w:ins>`)** and **4,245 tracked deletions (`<w:del>`)**.

```
============================================================
DOCUMENT PROPERTIES & CONSTRUCT COUNTS
============================================================
Total Canonical Elements (Perception) : 4,763
Total Word XML Sub-Files               : 108
Top-Level Body Paragraphs (<w:p>)     : 664
Top-Level Body Tables (<w:tbl>)       : 22
All Paragraphs Anywhere (<w:p>)       : 4,664
All Table Rows (<w:tr>)               : 987
All Table Cells (<w:tc>)              : 3,886
All Drawings (<w:drawing>)            : 38
Tracked Insertions (<w:ins>)          : 4,372
Tracked Deletions (<w:del>)           : 4,245
Footnote References                   : 15 (14 valid non-separator notes)
============================================================
```

---

## 3. Element Type Distribution

The canonical perception pipeline (`extract_geometry` -> `assign_anchors` -> `classify_blocks`) produced **4,763 elements** with the following distribution:

| Element Type | Count | % of Document | Empty Text Count | Sample Anchor Shape |
| :--- | :--- | :--- | :--- | :--- |
| **`cell`** | **4,231** | **88.83%** | **3,883 (91.8%)** | `table_index: 0, table_hash: "3419cd43", row_index: 0, col_index: 0` |
| **`para`** | **411** | **8.63%** | 0 (0.0%) | `paragraph_index: 3, style_id: "zcontents", text_fingerprint: "437aea62"` |
| **`heading`** | **71** | **1.49%** | 0 (0.0%) | `paragraph_index: 139, style_id: "Heading1", text_fingerprint: "4c4e436f"` |
| **`image`** | **31** | **0.65%** | 31 (100.0%) | `relationship_id: "rId21", drawing_id: "43", media_id: "rId21"` |
| **`footnote`** | **14** | **0.29%** | 0 (0.0%) | `note_id: "2", style_id: "footnote", text_fingerprint: "0775fbbe"` |
| **`drawing`** | **4** | **0.08%** | 4 (100.0%) | `drawing_id: "2142777214", paragraph_index: 215` |
| **`footer`** | **1** | **0.02%** | 0 (0.0%) | `style_id: "footer", text_fingerprint: "de7d1b72"` |
| **Total** | **4,763** | **100.0%** | **3,918** | — |

---

## 4. Perception Coverage

The backend perception engine successfully ingested 100% of physical document primitives without throwing errors:
- **Geometry Extraction**: 4,763 / 4,763 blocks extracted.
- **Anchor Generation**: 4,763 / 4,763 anchors assigned.
- **Classification**: 4,763 / 4,763 elements classified.

However, a severe extraction defect occurs in **table cells**:
- **3,883 out of 4,231 cells** were extracted with **empty text (`""`)** despite containing visible text in Word / docx-preview.
- Why? In `foundation/perception/parser.py` line 297, table cell text is extracted via `cell.text` (`python-docx` default `_Cell.text`).
- `python-docx`'s `_Cell.text` only traverses `<w:p><w:r><w:t>`. In documents with Track Changes, runs are wrapped inside `<w:p><w:ins><w:r><w:t>`. Because `python-docx` does not traverse `<w:ins>`, **all tracked inserted text inside table cells was completely dropped by perception**.

---

## 5. Renderer Coverage

`docx-preview` was inspected in the live Chromium DOM runtime:
- **Rendered Paragraphs**: All 482 body paragraphs (`para` + `heading`) rendered cleanly into the DOM with stamped `data-el-rawtext` and `data-el-style` attributes.
- **Rendered Tables**: All 22 body tables were rendered into the DOM with their full HTML structure (`<table>`, `<tr>`, `<td>`).
- **Rendered Changes Mode**: `docx-preview` renders in "Accepted Changes" mode by default, displaying all `<w:ins>` text content.
- **Rendered Footnotes & Footers**: All 14 footnotes and footer elements rendered with `data-note-id`.
- **Rendered Images**: 31 image objects present in the package; 14 mapped via data URI matching, 17 failed due to Windows EMF vector metafile conversion discrepancies.

---

## 6. Mapping Coverage Matrix

Evaluating `buildDocxElementMap` against the live browser DOM yields the following precise matrix:

| Element Type | Total Extracted | Rendered in DOM | Available (Mapped) | Ambiguous | Unavailable | Mapping Success % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`para`** | 411 | 411 | **411** | 0 | 0 | **100.0%** |
| **`heading`** | 71 | 71 | **71** | 0 | 0 | **100.0%** |
| **`footnote`** | 14 | 14 | **14** | 0 | 0 | **100.0%** |
| **`footer`** | 1 | 1 | **1** | 0 | 0 | **100.0%** |
| **`image`** | 31 | 31 | **14** | 0 | **17** | **45.16%** |
| **`drawing`** | 4 | 4 | **2** | 0 | **2** | **50.00%** |
| **`cell`** | 4,231 | 4,231 | **522** | **239** | **3,470** | **12.34%** |
| **Total** | **4,763** | **4,763** | **1,035** | **239** | **3,489** | **21.73%** |

*(Total Unresolved Elements = 3,489 Unavailable + 239 Ambiguous = **3,728 elements**)*

---

## 7. Failure Taxonomy

Every single one of the 3,728 failures is classified below by exact failure mechanism:

```
========================================================================================
FAILURE TAXONOMY BREAKDOWN (3,728 TOTAL UNRESOLVED)
========================================================================================
1. table_hash_mismatch_due_to_tracked_changes : 3,709 elements (99.49% of all failures)
   - Unavailable (Table Hash Missing from DOM) : 3,470 cells
   - Ambiguous (Collision on Empty Hash 'e3b0c442') :   239 cells
2. emf_image_renderer_conversion_mismatch     :    17 elements ( 0.46% of all failures)
3. drawing_canvas_dom_identity_missing        :     2 elements ( 0.05% of all failures)
----------------------------------------------------------------------------------------
TOTAL FAILURES ACCOUNTED FOR                  : 3,728 elements (100.0%)
========================================================================================
```

---

## 8. DOCX XML Root Causes

### Root Cause 1: Tracked Changes (`<w:ins>`) Dropped in Table Cell Extraction (P0)
In `foundation/perception/parser.py`, while `_paragraph_text()` was implemented for top-level paragraphs (lines 103–147) to walk `<w:ins>` children, **table cell parsing (line 297) bypassed this function and called `cell.text` directly**:

```python
# parser.py line 297:
block = _base_block("table_cell", text=cell.text)  # BUG: cell.text drops all <w:ins> runs!
```

### Root Cause 2: Table Hash Header Computation Dropping Tracked Insertions (P0)
In `foundation/perception/anchor_builder.py` lines 51–60, `build_table_hash` concatenates `cell.text.strip()`:

```python
# anchor_builder.py lines 56-60:
header_text = "".join([cell.text.strip() for cell in table.rows[0].cells])
fingerprint = hashlib.sha256(header_text.encode('utf-8')).hexdigest()[:8]
```

Because `cell.text` drops `<w:ins>`:
1. **Empty Hash Collisions**: If the first row was entirely inserted or revised under Track Changes, `header_text` evaluates to `""`, producing SHA-256 hash `'e3b0c442'`. Five separate tables in `HMV 23&23 EN compare.docx` collided on this exact empty hash `'e3b0c442'`.
2. **Truncated Header Hashes**:
   - **Table 20 (1,724 cells)**: The header in Word is `"No.Company nameStock codeReason for rejection"`. In `python-docx`, `" code"` was dropped, evaluating to `"No.Company nameStockReason for rejection"` -> Hash `'b7d52be7'` (Backend) vs `'34584a82'` (Frontend).
   - **Table 21 (1,740 cells)**: In `python-docx`, the header evaluated to `""` -> Hash `'e3b0c442'` (Backend) vs `'684307f5'` (Frontend).
   - **Table 20 + Table 21 alone account for 3,464 unavailable cells (92.9% of all document failures)**!

---

## 9. Renderer Root Causes

1. **Table Rendering**: `docx-preview` correctly rendered all 22 tables. However, because it renders inserted text, its computed DOM header text reflects the true document content, resulting in hashes that do not match the backend's corrupted hashes.
2. **EMF Images**: 17 images in this document are Windows Enhanced Metafiles (`.emf`). `docx-preview` attempts to convert EMF to canvas/raster, changing the binary byte signature compared to the raw `.emf` file bytes in `word/media/image*.emf`.

---

## 10. Mapping Root Causes

In `frontend/src/components/document/rendering/docxAnchorMapping.ts`:
- `mapTableCells` matches `el.anchor.table_hash` against `tablesByHash.get(tableHash)`.
- When the backend's recorded hash (`'b7d52be7'` or `'e3b0c442'`) is looked up in `tablesByHash`, it either:
  1. Finds 0 candidates -> marks all 1,724 cells in Table 20 as `'unavailable'`.
  2. Finds candidate count mismatch (e.g. 5 backend tables with `'e3b0c442'` vs 0 frontend tables with `'e3b0c442'`) -> marks cells as `'unavailable'` or `'ambiguous'`.

---

## 11. Comparison with Verified Fixtures

| Metric | Fixture A (`Client-25-Template...docx`) | Fixture B (`HMV-26-Final...docx`) | Fixture C (`HMV 23&23 EN compare.docx`) |
| :--- | :--- | :--- | :--- |
| **Total Elements** | 848 | 2,832 | **4,763** |
| **Mapped Elements** | **848 (100.0%)** | **2,832 (100.0%)** | **1,035 (21.73%)** |
| **Unavailable / Ambiguous**| **0** | **0** | **3,728** |
| **Tracked Insertions (`w:ins`)**| 0 | 3 (paragraphs only) | **4,372** (heavy in table cells) |
| **Tracked Deletions (`w:del`)** | 0 | 0 | **4,245** |
| **Total Tables** | 1 | 16 | **22** |
| **Total Table Cells** | 505 | 2,319 | **4,231** |
| **Cells in Tracked Change Tables**| 0 | 0 | **3,709** |

### Why Fixture A and Fixture B Reached 100%:
- **Fixture A** had zero Track Changes markup.
- **Fixture B** had 3 `<w:ins>` elements located exclusively inside top-level paragraphs (which `_paragraph_text` already handled) and zero `<w:ins>` inside its 16 tables.
- **Fixture C** is an explicit document comparison with over 8,600 revision tags concentrated heavily within table cells.

---

## 12. Top Root Causes Summary

1. **Table Cell `<w:ins>` Blindness**: `parser.py` and `anchor_builder.py` did not extract `<w:ins>` text inside table cells. (Impact: **3,709 elements / 99.49%**).
2. **EMF Image Byte Conversion Discrepancy**: Metafile rasterization in browser vs raw bytes in media manifest. (Impact: **17 elements / 0.46%**).
3. **Canvas Drawing Container Identity Stamp**: Two SmartArt canvas drawings did not receive a stamped `data-drawing-id`. (Impact: **2 elements / 0.05%**).

---

## 13. Severity Classification

- **[P0] CRITICAL — Table Cell Tracked Changes Extraction & Hash Parity**:
  - Accounts for **3,709 / 3,728 failures (99.49%)**.
  - Without this, any compared or revision-marked document will fail table mapping.
- **[P2] MEDIUM — EMF Image Format Handling**:
  - Accounts for **17 / 3,728 failures (0.46%)**.
- **[P3] LOW — SmartArt/Canvas Drawing Container Identity**:
  - Accounts for **2 / 3,728 failures (0.05%)**.

---

## 14. Recommended Remediation Plan (DO NOT IMPLEMENT YET)

| Remediation Item | Affected Component(s) | Expected Coverage Gain | Implementation Risk | Verification Test Needed |
| :--- | :--- | :--- | :--- | :--- |
| **1. Apply `_paragraph_text` to Table Cells** | `foundation/perception/parser.py` (`_docx_tables`) | **+3,709 elements** (Coverage rises from 21.7% to **99.6%**) | Very Low (Reuses proven `_paragraph_text` traversal) | Verify Table 20 & 21 text extraction and cell text count. |
| **2. Update `build_table_hash` for Tracked Changes** | `foundation/perception/anchor_builder.py` (`build_table_hash`) | Ensures header hash matches between Python perception and browser DOM for all 22 tables. | Very Low (Hash computed on normalized post-insertion text) | Verify table hash match for all 22 tables in Fixture C while maintaining Fixture A/B hashes. |
| **3. EMF Image Relationship Fallback** | `frontend/src/components/document/rendering/docxAnchorMapping.ts` (`mapImages`) | **+17 elements** (Coverage rises to **99.96%**) | Low | Verify image mapping when data URI does not match raw EMF bytes. |
| **4. Canvas Drawing ID Stamping** | `frontend/src/components/document/rendering/DocxRenderer.tsx` | **+2 elements** (Coverage reaches **100.0%**) | Very Low | Verify `[data-drawing-id]` stamping on canvas containers. |

---

## 15. Audit Answers to Key Forensic Questions

1. **Why are 3,728 / 4,763 elements unavailable?**  
   Because 3,709 table cells belong to tables whose headers contain tracked changes (`<w:ins>`), causing `python-docx`'s default `cell.text` to drop the inserted text, resulting in mismatched or empty (`'e3b0c442'`) table hashes that fail the frontend identity bridge. The remaining 19 elements are 17 EMF vector images and 2 canvas drawings.
2. **Which element types account for them?**  
   - `cell`: 3,709 (99.49%)
   - `image`: 17 (0.46%)
   - `drawing`: 2 (0.05%)
   - `para`, `heading`, `footnote`, `footer`: **0 failures (100% mapped)**.
3. **Are they perception failures or renderer/mapping failures?**  
   It is a **Perception & Identity Bridge defect**: perception failed to extract `<w:ins>` text from table cells, while the renderer did render it, causing the SHA-256 table hash bridge to break.
4. **Why did Fixtures A and B reach 100% while Fixture C did not?**  
   Fixtures A and B did not contain tracked changes inside table cells. Fixture C is an explicit document comparison containing 4,372 `<w:ins>` tags heavily distributed throughout table cells.
5. **What exact technical changes will raise coverage?**  
   Extracting `<w:ins>` text inside table cells in `parser.py` and using that text in `build_table_hash()` in `anchor_builder.py`.
6. **What is the expected coverage after each fix?**  
   - Fix 1 & 2 (Table cells + Hash): **4,744 / 4,763 (99.60%)**
   - Fix 3 (EMF Images): **4,761 / 4,763 (99.96%)**
   - Fix 4 (Drawings): **4,763 / 4,763 (100.0%)**

```
============================================================
FORENSIC AUDIT COMPLETE — ZERO CODE CHANGES APPLIED
============================================================
```
