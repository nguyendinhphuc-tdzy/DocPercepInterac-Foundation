# XLSX Visual Objects — Audit (Phase PROD-UX-1)

**Scope:** find out which drawing objects a workbook actually contains, which of them
survive into what the user sees, and why the rest do not. No Excel rendering engine is
built in this phase, and no perception semantics are changed.

**Code:** [`foundation/perception/xlsx_visual_inventory.py`](../foundation/perception/xlsx_visual_inventory.py)
· endpoint `GET /api/documents/<session_id>/visual-objects/<doc_id>`
· UI [`frontend/src/components/document/rendering/VisualObjectNotice.tsx`](../frontend/src/components/document/rendering/VisualObjectNotice.tsx)

---

## 1. Why objects are lost today

`perception/parser.py` reads workbooks through **openpyxl**, which exposes exactly two
members of a worksheet's drawing part:

| openpyxl API | OOXML element | Reaches an Element? |
|---|---|---|
| `ws._images` | `<xdr:pic>` | yes |
| `ws._charts` | `<xdr:graphicFrame>` holding a chart part | yes |

Everything else inside the same `xl/drawings/drawingN.xml` has **no openpyxl API at all**.
The parser therefore never observes it, so it cannot become a `GeometryBlock`, cannot get
an Anchor, cannot become an Element, and cannot be rendered. This is a library-capability
boundary, not a bug in `parse_xlsx()`:

| OOXML element | What it is | Status |
|---|---|---|
| `<xdr:sp>` | autoshape | **not perceived** |
| `<xdr:sp>` + `<xdr:txBody>` | text box (carries text!) | **not perceived** |
| `<xdr:cxnSp>` | connector / arrow | **not perceived** |
| `<xdr:grpSp>` | grouped drawing, and everything nested inside it | **not perceived** |
| `<xdr:graphicFrame>` + diagram part | SmartArt / diagram | **not perceived** |
| `<xdr:graphicFrame>` + other payload | embedded object | **not perceived** |
| `xl/drawings/vmlDrawingN.vml` | legacy shapes, form controls, comment boxes | **not perceived** (outside DrawingML entirely) |

Charts are a separate, milder case: they **are** perceived and anchored, but the renderer
draws a placeholder icon rather than the plotted chart, because no chart-rendering engine
is integrated. `element_classifier.py` already marks chart Elements `rendered=False`, and
the viewer honestly matches that.

Text boxes are the most consequential loss: their content is real document text that never
enters the element model at all, so it is invisible to search, to the Agent and to any
downstream reconciliation.

## 2. Measured on the project's own fixtures

Run: `audit_workbook(path)` — counts from the package, compared against what openpyxl read.

| Workbook | Pictures | Shapes | Text boxes | Connectors | Groups | Charts | Legacy VML | Fully shown? |
|---|---|---|---|---|---|---|---|---|
| `HMV-FA&RPT FY2024.xlsx` | 5 | 2 | 0 | 0 | 0 | 0 | 1 | **no** |
| `HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx` | 4 | 12 | 0 | 2 | 2 | 0 | 12 | **no** |
| `RPTs & Segment check .xlsx` | 0 | 0 | 0 | 0 | 0 | 0 | 3 | **no** |

Per-sheet, the gap is concrete — Appendix I:

| Sheet | Objects in file | Read by parser (images / charts) |
|---|---|---|
| I. Related parties | 1 | 1 / 0 |
| III. Summary-RPTs | 3 | **0** / 0 |
| IV. Segmented data | 1 | **0** / 0 |
| FS | 2 | 2 / 0 |
| Interest expenses | 3 | **1** / 0 |
| P&L | 9 | **0** / 0 |
| CF | 13 | **0** / 0 |

Sheets like *CF* and *P&L* render as pure grids today while carrying 13 and 9 drawing
objects respectively. That is exactly the case this phase refuses to keep quiet about.

## 3. What was changed

**Nothing is now rendered that was not rendered before.** What changed is that the product
stops implying completeness it does not have:

1. `inventory_xlsx_visual_objects()` walks the OOXML package read-only (zip + XML), counting
   every anchored object per sheet, including members nested inside groups, plus legacy VML
   shapes reached through the sheet's own relationships.
2. `parser_visual_counts()` reports what openpyxl actually read, so the report shows the gap
   rather than asserting one.
3. Each kind carries a fixed visibility (`RENDERED` / `PLACEHOLDER` / `NOT_PERCEIVED`) and the
   reason for it — the reason is the OOXML/library fact, not a vague apology.
4. The XLSX viewer shows an explicit status line whenever a sheet or workbook is not shown in
   full, expandable to the per-kind breakdown.

## 4. Deliberately not done in this phase

* No shape/text-box/connector/SmartArt rendering.
* No chart rendering.
* No change to `parse_xlsx()`, to anchors, or to any perception semantics — the inventory is
  a separate read-only module and a separate endpoint.

## 5. If these objects need to be supported later

In rough order of value per unit of risk:

1. **Text boxes** — parse `<xdr:sp>` `<xdr:txBody>` directly from `drawingN.xml`, anchored by
   its `<xdr:from>` cell, and emit it as a text-bearing block. This recovers real document
   content and reuses the anchor scheme drawings already use. It does not need any rendering
   work to be worth doing.
2. **Shapes / connectors / groups** — perceive as non-text drawing elements so they at least
   exist, are counted, and can be placed; visual fidelity can stay a badge.
3. **Charts** — a rendering engine decision, independent of perception, and the largest piece.
4. **Legacy VML** — form controls and comment boxes; lowest value, highest parsing cost.

Every one of those is additive to the same drawing part this audit already walks.
