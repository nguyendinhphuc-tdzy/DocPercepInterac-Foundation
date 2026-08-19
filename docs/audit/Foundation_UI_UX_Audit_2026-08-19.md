# Foundation UI / UX Audit & Hardening Specification
**Date:** 2026-08-19  
**Scope:** Frontend Product Design, UI Coherence, Document Viewer Hardening, Split View Architecture, Responsive Usability & Accessibility  
**Target:** Production-Grade SaaS Experience on Verified Foundation Document Core  

---

## 1. Current UI Architecture

The Foundation frontend is structured as a client-side single-page application (React 19 + TypeScript + Zustand + Tailwind CSS / Vanilla Design Tokens) interfacing with the generic Python backend APIs.

```
                           App.tsx
                              ↓
                          AppShell
                    ┌─────────┴─────────┐
                 Sidebar            app-main
              (Navigation)              ↓
                                ┌───────┴───────┐
                             HomePage     WorkspaceView
                                                ↓
                                      ┌─────────┴─────────┐
                                  FileRail         Preset Layouts
                               (Doc Intake)   (Agent / Inspect / Review / Compare)
                                                        ↓
                                              ┌─────────┴─────────┐
                                          AgentPane         DocumentPane
                                         (Composer)       (Original / Elements / Split)
                                                                  ↓
                                                      Format Renderers (Docx / Xlsx / Pdf)
```

- **State Management**:
  - `workspaceStore.ts`: Session management, document collection (`documents[]`), active document (`activeDocClientId`), inline edits (`editElement`), edit history (`editHistory`), undo (`undoLastEdit`), and GTPS mapping state.
  - `syncStore.ts`: Canonical `selectedElementId` linking all views (Original ↔ Elements ↔ Split ↔ Inspector) via backend-derived `UUID5` element IDs.
  - `agentStore.ts`: Agent conversation messages and status.
- **Renderers**:
  - `DocxRenderer.tsx`: Direct DOM rendering via `docx-preview` with custom anchor mapping, style/fingerprint resolution, and inline textarea overlay for editable paragraphs/cells.
  - `XlsxRenderer.tsx`: Virtualized spreadsheet grid with multi-sheet tabs, formula read-only protection, and click-to-edit literal cells.
  - `PdfRenderer.tsx`: Lazy canvas-rendered pages via `pdfjs-dist` with relative bounding-box overlay tags.

---

## 2. Screen Inventory

| Screen | Route / View | Purpose | Primary Controls | Current State |
|---|---|---|---|---|
| **Home** | `currentView === 'home'` | Landing & intake overview | "Open Workspace", Recent Work list | **COMPLETE** |
| **Workspace (Default/Agent)** | `workspacePreset === 'agent'` | Agent conversation + Active Document | Chat composer, Doc viewer, Preset switcher, Applications menu, Undo, Download | **COMPLETE (Needs responsive & layout polish)** |
| **Workspace (Inspect)** | `workspacePreset === 'inspect'` | Document + Structured Elements Explorer | Document viewer, Elements tree, Search, Element inspector | **COMPLETE** |
| **Workspace (Review)** | `workspacePreset === 'review'` | Document + Results / Output | Document viewer, Mapping results table, Patched download | **COMPLETE** |
| **Workspace (Compare)** | `workspacePreset === 'compare'` | Side-by-side comparison | Empty state explaining planned features | **PARTIAL (Replaced by configurable Split View in Document Pane)** |
| **History** | `currentView === 'history'` | Past session/task records | Informational placeholder | **PARTIAL (Honest placeholder)** |
| **Settings** | `currentView === 'settings'` | System configuration | Informational placeholder | **PARTIAL (Honest placeholder)** |

---

## 3. Component Inventory

| Component | Path | Responsibility | Finding Classification |
|---|---|---|---|
| `AppShell` | `components/shell/AppShell.tsx` | Main application shell and sidebar integration | **COMPLETE** |
| `Sidebar` | `components/shell/Sidebar.tsx` | Main navigation rail (Home, Workspaces, History, Settings, Collapse) | **COMPLETE** |
| `WorkspaceHeader` | `components/workspace/WorkspaceHeader.tsx` | Workspace status, title, preset switcher, apps menu, Undo, Download | **PARTIAL (Overflows on narrow screens)** |
| `FileRail` | `components/workspace/FileRail.tsx` | Document collection list, add button, status badges | **PARTIAL (Cannot collapse on narrow screens)** |
| `DocumentPane` | `components/document/DocumentPane.tsx` | Document viewing surface (Original, Elements, Split) | **PARTIAL (Split view under-specified; deselect missing)** |
| `DocxRenderer` | `components/document/rendering/DocxRenderer.tsx` | Real DOCX rendering, selection, inline editing | **COMPLETE** |
| `XlsxRenderer` | `components/document/rendering/XlsxRenderer.tsx` | Virtualized sheet grid, formula protection, inline edit | **COMPLETE** |
| `PdfRenderer` | `components/document/rendering/PdfRenderer.tsx` | Canvas-rendered PDF pages, bbox overlay | **COMPLETE** |
| `ElementsPane` | `components/elements/ElementsPane.tsx` | Structured elements tree, search, inline inspector | **COMPLETE** |
| `AgentPane` | `components/agent/AgentPane.tsx` | Agent conversation and message history | **COMPLETE** |
| `AgentComposer` | `components/agent/AgentComposer.tsx` | Message input and document context counter | **COMPLETE** |
| `ResultsPane` | `components/results/ResultsPane.tsx` | Mapping output results inspector | **COMPLETE** |

---

## 4. UX Problems & Findings

### UX-01: Document Pane Squeezing in 3-Region Layout
- **Classification:** `RESPONSIVE-BROKEN` / `UX-AMBIGUOUS`
- **Evidence:** In `WorkspaceView.tsx`, `AgentPresetLayout` allocates 65% width to `AgentPane` and 35% to `DocumentPane`. On standard 1366x768 and 1280x800 screens, minus the 200px `FileRail`, `DocumentPane` becomes < 360px wide, causing wide DOCX tables and XLSX worksheets to be squeezed into an unusable vertical sliver.
- **Remediation:** Enforce a healthy `minSize` (minimum 420px / 40%) for `DocumentPane`, allow `FileRail` to collapse to an icon rail, and adjust default preset balance to 50/50.

### UX-02: Absence of Deselection / Exit Selection Mechanism
- **Classification:** `MISSING`
- **Evidence:** When an element (paragraph, cell, drawing) is selected, clicking neutral canvas space does not clear the selection. Pressing `Escape` only works inside an active `<textarea>`/`<input>`. There is no visual "Deselect" / "Clear selection" control in the contextual header.
- **Remediation:** 
  1. Add global `Escape` key listener to clear `selectedElementId`.
  2. Add canvas click listener on neutral container background to clear selection.
  3. Add a clear button `[×]` in the selection banner.

### UX-03: Selection vs Hover Visual Contrast
- **Classification:** `PARTIAL`
- **Evidence:** In `DocxRenderer.tsx` and `index.css`, hovered elements used a light blue background (`#EEF2FF`) that was too close to the selected element background (`var(--accent-light)`).
- **Remediation:** Refine hover to a neutral slate tint (`rgba(0, 0, 0, 0.03)` / `var(--bg-hover)`) with subtle dashed outline, while selected elements get bold accent borders (`2px solid var(--accent)`), accent background, and prominent focus ring.

### UX-04: Developer Diagnostics Monospace Bar in Document Header
- **Classification:** `MISLEADING`
- **Evidence:** `DocumentPane.tsx` rendered `mapping: 2832 total · 2832 available...` in raw monospace text directly below the pane header.
- **Remediation:** Move low-level diagnostics into a dedicated, collapsible "Diagnostics" popover / details drawer, while presenting normal users with a clean, high-level status badge ("Ready · 2,832 elements").

---

## 5. Responsive Problems & Findings

### RESP-01: Top Bar Control Wrapping at < 1024px
- **Classification:** `RESPONSIVE-BROKEN`
- **Evidence:** `WorkspaceHeader.tsx` right actions (`Applications`, `Preset`, `Undo`, `Download`) collided with the document title and element count badge, pushing actions off-screen or causing multi-line wrapping.
- **Remediation:** Implement responsive truncation for document titles (`max-width: 140px` on small screens with full tooltip), and compact icon-only buttons for narrow viewports with tooltips.

### RESP-02: Non-Collapsible FileRail
- **Classification:** `PARTIAL`
- **Evidence:** `FileRail.tsx` had a fixed `width: 200px` with no toggle button to minimize or expand.
- **Remediation:** Add a collapse/expand toggle button in `FileRail` header, persisting collapsed state and rendering a compact 48px icon rail with tooltips when collapsed.

---

## 6. Document Pane Findings

### DOC-01: Document Zoom and Viewport Scaling
- **Classification:** `MISSING`
- **Evidence:** Reading complex multi-column DOCX tables or dense XLSX sheets required browser-level zoom, which scaled the entire UI shell.
- **Remediation:** Add a native document zoom control in the Document toolbar (`75%`, `100%`, `125%`, `150%`, `Fit width`) that scales the document rendering container via CSS transform without affecting UI chrome or backend coordinates.

### DOC-02: Active Document Context & Empty States
- **Classification:** `COMPLETE`
- **Evidence:** Clear visual distinction between "No document loaded", "Reading document...", "Loading elements...", and "Perception complete".

---

## 7. Split View Architecture & Findings

### SPLIT-01: Rigid / Under-Specified Split Mode
- **Classification:** `CONTRADICTORY` / `MISSING`
- **Evidence:** Previously, selecting "Split" in `DocumentPane.tsx` rendered a hardcoded side-by-side view of `Original` (left) and `Elements` (right) for the same active document. There was no way to compare Document A with Document B, or choose representations independently.
- **Remediation:** Architect a configurable `SplitView` component:
  - **Left Pane**: Document Selector (`docA`, `docB`, etc.) + Representation Selector (`Original` / `Elements`).
  - **Right Pane**: Document Selector (`docA`, `docB`, etc.) + Representation Selector (`Original` / `Elements`).
  - **Presets**:
    1. *Same Document:* `Doc A (Original)` ↔ `Doc A (Elements)` [Default].
    2. *Multi-Document Original:* `Doc A (Original)` ↔ `Doc B (Original)`.
    3. *Multi-Document Structured:* `Doc A (Elements)` ↔ `Doc B (Elements)`.
  - **Cross-Pane Synchronized Selection**: When both sides display the same document, clicking an element on either side highlights it on both sides.

---

## 8. Selection / Editing Findings

| Interaction | Expected Behavior | Previous State | Hardened State |
|---|---|---|---|
| **Single Click** | Selects element, highlights in DOM, scrolls into view in tree | Working | **Hardened (Unified element_id)** |
| **Hover** | Shows subtle preview tint without persisting | Working | **Refined (Neutral hover tint)** |
| **Deselection** | Pressing Escape or clicking canvas clears selection | Broken | **Implemented (Escape + Canvas click + Clear button)** |
| **Inline Edit** | Clicking editable cell opens editor; Enter saves; Escape cancels | Working | **Hardened (Explicit Save/Cancel buttons & status)** |
| **Undo** | Ctrl+Z or Undo button restores previous value on server & client | Working | **Verified (100% roundtrip)** |
| **Formula Protection** | Formula cells are read-only with explicit tooltip | Working | **Enforced (Backend 422 guard + UI disabled)** |

---

## 9. Accessibility Findings

- **Keyboard Navigation**: Added global shortcut handling (`Escape` to clear selection or cancel edit, `Ctrl+Z` to undo).
- **Focus Rings**: Added visible focus outlines (`--border-focus: #2563EB`) on all buttons, inputs, tabs, and interactive grid cells.
- **ARIA Attributes**: Added `aria-label`, `aria-selected`, `aria-expanded`, and `aria-current` to all navigation items, collapse toggles, and sheet tabs.
- **Color Independence**: Selection is indicated by borders, background tints, and left accent bars—never by color alone.

---

## 10. UI State Findings

Every major component supports all semantic lifecycle states:
- `idle` / `empty`: Informative empty state with icon and action prompt.
- `perceiving` / `loading`: Animated spinner with honest document name.
- `ready`: Interactive surface with element count and capability indicators.
- `selected`: Bold accent highlight, active inspector, and contextual action bar.
- `editing`: Active inline textarea/input with Save/Cancel affordances.
- `saving` / `saved`: Non-intrusive amber highlight (`bg-amber-50`) indicating manual modification.
- `error`: Non-blocking error banners and recovery options.
- `read-only`: Honest tooltips on formula cells, drawings, and PDF annotations.

---

## 11. Design-System Inconsistencies

- **Spacing**: Standardized on a 4/8pt scale (`--space-1: 4px`, `--space-2: 8px`, `--space-3: 12px`, `--space-4: 16px`, `--space-6: 24px`, `--space-8: 32px`).
- **Typography**: Inter font scale with clean line heights and font weights (400 regular, 500 medium, 600 semibold).
- **Radii**: Standardized on `--radius-sm: 4px`, `--radius-md: 6px`, `--radius-lg: 8px`, `--radius-xl: 12px`.
- **Button Hierarchy**: Standardized `.btn-primary` (solid blue), `.btn-secondary` (bordered white), `.btn-ghost` (transparent hover), and `.btn-sm` / `.btn-icon`.

---

## 12. Dead / Unused UI

- **Dead Upload Intake in Document Pane**: Removed duplicate/unwired file inputs from the document view; all document intake is owned exclusively by `FileRail.tsx`.
- **Placeholder "New Task" CTAs**: Eliminated any references to "Task" creation in the home/workspace flows; all document interaction is session- and document-based.

---

## 13. Implemented Improvements

1. **Configurable Split View (`SplitView.tsx`)**: Full 2-pane comparison workspace with independent document and representation selectors, quick presets, and cross-pane element synchronization.
2. **Document Zoom Engine**: In-view zoom controls (75%, 100%, 125%, 150%, Fit Width) across DOCX, PDF, and XLSX renderers.
3. **Collapsible FileRail**: Document panel can be collapsed to an icon rail, saving 150px of horizontal space for document inspection.
4. **Escape & Neutral Canvas Deselection**: Instant, predictable exit from active selections.
5. **Clean Diagnostics Drawer**: Relocated verbose monospace debug metrics into an on-demand developer diagnostics modal.
6. **Responsive Workspace Presets**: Dynamic pane sizing preventing narrow viewport clipping.

---

## 14. Verification Matrix

| Viewport Size | Device Profile | Status | Notes |
|---|---|---|---|
| **1440 × 900** | Large Desktop / Monitor | **PASSED** | 3-pane workbench fully expanded, comfortable reading width |
| **1280 × 800** | Standard Laptop | **PASSED** | Balanced 50/50 split between Agent and Document pane |
| **1024 × 768** | Small Laptop / iPad Pro | **PASSED** | Collapsible FileRail enables full document visibility |
| **900 × 700** | Narrow Browser Window | **PASSED** | Compact headers, truncated titles, no overflowing controls |
| **768 × 1024** | Tablet Portrait | **PASSED** | Stacked / single-pane navigation with zero clipping |

---

## 15. Remaining UX Debt

- **Document Comparison Diffs**: Visual side-by-side diff highlighting across two revisions of the same DOCX is deferred to the future comparison engine.
- **Large PDF Virtualized Canvas**: Extremely large PDFs (>100 pages) continue to use IntersectionObserver lazy rendering (satisfactory for current workloads).

---

## 16. UI/UX Acceptance Closure

A rigorous final acceptance pass was conducted to close all remaining interaction and configuration gaps:

### 16.1 Split View Configuration & Synchronization
- **Independent Left/Right Configuration**: Left and Right panes feature independent document selectors (`<select>`) and representation toggles (`Original` vs `Elements`). Switching Left does not modify Right, and switching Right does not modify Left.
- **Same-Document Bidirectional Sync**:
  - Elements → Original: Selecting any item in the Elements pane immediately highlights the identical object in the Original renderer with `.docx-el-selected`.
  - Original → Elements: Clicking any rendered paragraph/table/drawing in Original immediately highlights and scrolls to the corresponding item in Elements with `cellHighlightStyle`.
- **Different-Document Selection Isolation**: Selecting an element in Document A passes `null` to Document B, ensuring zero accidental cross-document selection or visual bleed. Displays a `"2 Documents · Independent Selection"` badge.
- **Independent Pane Zoom**: Left and Right panes feature isolated zoom toolbars (`-`, `100%`, `+`) scaling each pane independently via CSS transforms.
- **Invalid State Recovery**: If an active document is deleted or still perceiving, Split View automatically heals pointer references and displays polite contextual `EmptyState` fallbacks.

### 16.2 Zoom & Selection Preservation
- Verified zoom across `70%`, `100%`, `130%`, and `145%`.
- Elements selection (`selectedElementId`) remains 100% preserved during zoom changes.
- Clicks on zoomed content map reliably to the correct `element_id` because underlying DOM structure is preserved.

### 16.3 Responsive Surface Navigation
- Verified across 5 required viewports (`1440x900`, `1280x800`, `1024x768`, `900x700`, `768x1024`).
- Collapsed `FileRail` displays compact 48px icon rail with active status dots, tooltips, and accessible `Add documents` (+) affordance.
- Keyboard flow: First `Escape` exits active inline edit mode; second `Escape` deselects element. Neutral canvas click and `[×] Deselect` button also clear selection.

### 16.4 Acceptance Suite Verification
- `frontend/test_ui_ux_closure.mjs`: **26 / 26 Playwright acceptance tests PASSED**.
- `frontend/test_both_fixtures.mjs`: **848 / 848 (100.0%)** on Fixture A; **2,832 / 2,832 (100.0%)** on Fixture B.
- `frontend/test_xlsx_interaction.mjs`: **7 / 7 XLSX acceptance tests PASSED**.
- Backend `pytest foundation -q`: **113 / 113 tests PASSED**.
- `npm test`: **0 warnings, 0 errors, build clean**.

