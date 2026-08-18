# Document Perception & Interaction Foundation
## Context 3 — Current Product, Architecture, Codebase & Working Memory for Claude Code

> **Status:** Current working context as of **2026-08-18**
>
> **Repository:** `nguyendinhphuc-tdzy/DocPercepInterac-Foundation`
>
> **Current HEAD verified:** `f71769cda24f3a39371519aa5f67087a80805d06` (`UI update`)
>
> **Purpose:** This file is the operational context Claude Code should read before making changes. It consolidates the previous project context with the latest verified engineering/product decisions and the latest repository state.
>
> **Important source-of-truth rule:** when historical documentation conflicts with current code or later decisions, prefer the order **(1) current code + tests, (2) latest verified `foundation/STATUS.md`, (3) latest implementation notes / build context, (4) older build plans and historical context**. Do not resurrect superseded architecture decisions merely because they still appear in older documents.

---

## 0. Executive Summary

Foundation is a **Document Intelligence Workbench / shared document-processing infrastructure**, not a standalone business application.

Its job is to give downstream AI/application layers a dependable, governed substrate for:

- perceiving document structure;
- extracting deterministic document elements;
- locating those elements again through stable anchors;
- synchronizing those elements across a professional review workspace;
- allowing controlled human edits/write-back;
- keeping lineage/provenance and traceability;
- exposing clean API boundaries so application-specific logic stays outside the perception core.

The central architectural principle remains:

> **AI states intent; Foundation executes against governed document primitives.**

The current repository has moved beyond the old "Element Index only" concept into a **single AI-native workspace**:

```text
┌──────────────────────────────────────────────────────────────┐
│                      Foundation Workspace                    │
├───────────────────────┬──────────────────────────────────────┤
│                       │                                      │
│       DOCUMENT        │              ELEMENTS                │
│                       │                                      │
├───────────────────────┼──────────────────────────────────────┤
│                       │                                      │
│        AGENT          │               RESULTS                │
│                       │                                      │
└───────────────────────┴──────────────────────────────────────┘
```

The current workspace is **not a generic chatbot UI** and is **not a conventional SaaS dashboard**. It is a dense, desktop-first professional workbench inspired by Linear, VS Code, and Chrome DevTools.

---

# 1. Product Positioning

## 1.1 What Foundation is

Foundation is a reusable infrastructure layer — effectively the **eyes, hands, location system, and audit substrate for document AI**.

Downstream applications can sit above it for use cases such as:

- extraction;
- translation;
- redlining;
- comparison;
- mapping/finalization;
- summarization;
- review workflows;
- future agent workflows.

The Foundation core must remain use-case agnostic.

## 1.2 What Foundation is not

Do not turn Foundation into:

- Word/Excel replacement software;
- a client-specific Tax application;
- a GTPS/HMV hard-coded engine inside `perception/`;
- a generic chat product;
- an autonomous AI that writes files directly without controlled execution.

## 1.3 UX invariants

These remain important product promises:

1. **Input stays natural.** Users upload the files they already have.
2. **Output is usable immediately.** Write-back should preserve the source document structure as far as the selected output strategy permits.
3. **Do not add unnecessary process steps.** Foundation should fit into the user's existing document workflow rather than create ceremony.

---

# 2. Current Mental Model: Document, Session, Task

This distinction is now explicitly locked into the backend and frontend mental model.

```text
Session
  │
  ├── Document A (doc_id) ── status ── Elements / Anchors
  ├── Document B (doc_id) ── status ── Elements / Anchors
  ├── Document C (doc_id) ── status ── Elements / Anchors
  └── ...

Task = an explicit user-requested operation against one or more documents.
```

### Document

One uploaded/perceived artifact.

Identifier:

```text
doc_id
```

Rules:

- UUID-based;
- never derive identity from filename;
- never use upload order as identity;
- each document owns its own processing status;
- format is stored independently (`docx`, `xlsx`, `pdf`);
- each document can be addressed independently regardless of upload order.

### Session

The workspace context that owns 0+ documents.

Identifier:

```text
session_id
```

A session can accumulate documents over multiple upload operations.

**Critical invariant:** multiple documents selected together, uploaded sequentially, or added later must all belong to the same logical session.

There was a real race condition where two uploads without a session ID in flight at the same time created two sessions. That was fixed on the frontend using `pendingSessionPromise` so the first session-creating request is serialized and subsequent uploads join it.

The backend contract intentionally remains simple:

- no `session_id` → create a new session;
- supplied `session_id` → join that session.

Do not invent a second server-side "merge sessions" mechanism unless explicitly requested.

### Task

A task is an explicit user request, for example:

```text
POST /api/gpts/map
```

Uploading/perceiving a document does **not** implicitly create a task.

This separation is essential for the Perceive → Intent → Execute model.

---

# 3. Current High-Level Architecture

```text
Layer / Concern                     Current responsibility
────────────────────────────────────────────────────────────────────────
Format / Geometry                  Parse physical structure of files
Perception                         Detect + classify + anchor elements
Application                         Use Foundation primitives for a specific job
Output                             Lineage + controlled write-back
Access                              HTTP API for frontend / external callers
Frontend                            Review / inspect / interact / verify
```

Conceptually:

```text
INPUT FILES
   │
   ▼
Geometry extraction
   │
   ▼
Element classification
   │
   ▼
Stable anchors
   │
   ▼
Document / Session state
   │
   ├──────────────► Document pane
   ├──────────────► Elements pane
   ├──────────────► Agent context
   └──────────────► Results / trace

Explicit user action
   │
   ▼
Application layer
   │
   ▼
Foundation execution primitives
   │
   ▼
Lineage + governed write-back
```

---

# 4. Current Backend Architecture

## 4.1 Geometry Layer

Primary file:

```text
foundation/perception/parser.py
```

Current deterministic parsers:

### DOCX

Uses:

```text
python-docx
```

Behavior:

- one block per non-empty paragraph;
- preserves paragraph index;
- preserves style ID;
- one block per table cell;
- **empty table cells are preserved intentionally** because they are real fill-in placeholders, not noise;
- table blocks carry a table hash for anti-drift resolution.

### XLSX

Uses:

```text
openpyxl
```

Behavior:

- reads all sheets;
- extracts non-empty cells;
- records `sheet_name` + `cell_address`;
- detects named ranges;
- preserves `named_range` when available;
- records leftmost non-empty `row_label` to support row drift healing.

### PDF

Uses:

```text
pdfplumber
```

Behavior:

- deterministic text-line extraction;
- records page number;
- records PDF point bounding box;
- stores page dimensions;
- no OCR in the current core.

### PDF rendering

The frontend can display a structural PDF representation, but exact page-image rendering still depends on:

```text
Poppler / pdftoppm / pdftocairo
```

Poppler is not installed on the current development environment. The UI therefore explicitly avoids pretending that a real PDF page image is available.

## 4.2 Historical parser decision that must not be resurrected

**Docling was removed.**

The project previously experimented with Docling but later replaced it with the current deterministic parser stack:

- `python-docx` for DOCX;
- `openpyxl` for XLSX;
- `pdfplumber` for PDF;
- `pdf2image` only for optional PDF page rendering when Poppler is available.

Do not reintroduce Docling simply because older context files still describe it as the core parser.

---

# 5. Element Classification

Primary file:

```text
foundation/perception/element_classifier.py
```

The classifier is currently **deterministic and structural**.

Current baseline:

- XLSX cell → `CELL`;
- DOCX table cell → `CELL`;
- DOCX heading-style paragraph → `HEADING`;
- other DOCX paragraph → `PARA`;
- PDF text line → `PARA`.

The classifier deliberately knows nothing about:

- Tax;
- GTPS;
- HMV;
- mapping rules;
- client-specific semantics.

## 5.1 Future AI classification seam

The code now defines a document-level `Classifier` protocol.

Important design decision:

> The seam is **document-level**, not one-block-per-call.

Why:

- AI classification may need neighboring document context;
- a model can batch one invocation per document instead of one call per element;
- future model-backed classifiers can be dropped in without changing the caller contract.

This is an integration seam, **not a decision to add an AI model to perception immediately**.

---

# 6. Anchor System — Core IP

Primary file:

```text
foundation/perception/anchor_builder.py
```

Anchor is the mechanism that allows Foundation to locate an element again after the document has changed.

The anchor system must remain:

- deterministic;
- format-specific where necessary;
- use-case agnostic;
- fail-safe;
- never silently match an unrelated element.

## 6.1 DOCX paragraph anchors

Current anchor fields include:

```json
{
  "format": "docx",
  "paragraph_index": 5,
  "style_id": "Heading1",
  "text_fingerprint": "a3f2b1c0",
  "duplicate_ordinal": 0
}
```

### Resolution ladder

1. `style_id + text_fingerprint`
2. `paragraph_index + style_id`
3. `paragraph_index` only, with a low-confidence warning
4. fail with `ValueError`

### Duplicate text handling

Repeated paragraphs can occur in real documents. The anchor therefore may carry `duplicate_ordinal` so the resolver can choose the correct occurrence even under uneven structural drift.

## 6.2 DOCX table-cell anchors

Current effective identity:

```text
table_index + table_hash + row_index + col_index
```

The table hash is derived from the table header row.

When the table index changes because tables are inserted/reordered, the resolver self-heals by looking for the same table hash.

## 6.3 XLSX anchors

Current fields:

```json
{
  "format": "xlsx",
  "sheet_name": "BCTC",
  "cell_address": "B5",
  "named_range": "Revenue_2025",
  "row_label_fingerprint": "..."
}
```

Resolution priority:

1. named range;
2. direct cell address with row-label corroboration;
3. self-heal by scanning the same column for the recorded row label;
4. fail rather than silently writing to the wrong row.

## 6.4 PDF anchors

Current position-based model:

```json
{
  "format": "pdf",
  "page": 1,
  "bbox_relative": [0.1, 0.2, 0.8, 0.05],
  "reading_order_index": 3
}
```

Do not identify PDF elements solely by text content. Financial PDFs can contain repeated boilerplate.

## 6.5 Mandatory anti-drift invariant

The old P3-04 requirement is now effectively a core regression invariant:

> insert structural content into a document → re-parse → resolve the old anchor → the same semantic element must be returned.

If the correct element cannot be proven, raise rather than guess.

---

# 7. Application Layer: Current Demo Mapping

Primary files:

```text
foundation/applications/gpts/mapping_service.py
foundation/applications/gpts/demo_mapper.py
```

This layer is where use-case-specific orchestration belongs.

The current GTPS/HMV logic is intentionally isolated here.

## 7.1 Current behavior

The mapping service:

1. extracts geometry from target;
2. assigns target anchors;
3. classifies target elements;
4. extracts geometry from any number of source documents;
5. assigns source anchors;
6. builds source lookup information;
7. applies `DEMO_RULES` when the uploaded source content matches the known demo fixture;
8. logs mapping lineage;
9. optionally writes a patched DOCX output.

## 7.2 Important limitation

`DEMO_RULES` is **not** the general Foundation logic.

Current behavior for arbitrary inputs:

- extraction still works;
- anchors still work;
- element classification still works;
- mapping may legitimately return `mapped: []` when no demo rule matches.

Do not "fix" this by putting HMV/GTPS knowledge into `perception/`.

## 7.3 Target element highlighting

Mapping results now carry a resolved `target_element_index` so the frontend can highlight the correct target element even when table self-healing changes the effective table index.

This prevents stale string-anchor/table-index assumptions from leaking into the UI.

---

# 8. Output and Write-Back

Current output concerns are kept separate from perception.

Relevant paths:

```text
foundation/output/
```

Responsibilities include:

- lineage logging;
- controlled write-back;
- resolving target elements;
- applying patches without silently modifying unrelated content.

## 8.1 Current edit behavior

Frontend direct editing is already connected for the supported flow:

```text
UI edit
  → PATCH /api/elements/<id>
  → write to output
```

The existing verified route supports direct output editing for DOCX.

XLSX write capability exists in the underlying engine, but the direct PATCH route is not yet fully exposed for XLSX. Do not assume parity merely because the lower-level library can write XLSX.

---

# 9. Access Layer and API Contracts

Important files:

```text
foundation/api/app.py
foundation/api/routes/documents.py
foundation/api/routes/process.py
foundation/api/routes/gpts.py
foundation/api/routes/agent.py
```

Current document lifecycle model is file-based; there is no production database in the current foundation implementation.

Development storage:

```text
.uploads/<session_id>/
```

with a manifest linking `doc_id` to document metadata.

## 9.1 Current important routes

### Upload / perceive documents

```http
POST /api/documents
```

Creates or joins a session and creates an independent document.

### List session documents

```http
GET /api/documents/{session_id}
```

### Retrieve document elements

```http
GET /api/documents/{session_id}/elements/{doc_id}
```

### Direct element edit

```http
PATCH /api/elements/{id}
```

### Download output

```http
GET /api/download/{id}
```

### Explicit GTPS mapping task

```http
POST /api/gpts/map
```

This is a **Task** endpoint, not a document-upload endpoint.

### Agent

Agent route support exists, but the frontend Agent surface remains intentionally constrained and honest about what is actually backed by live retrieval/action support.

---

# 10. Multi-Document Session Invariant

This was explicitly locked on 2026-08-18.

Required behavior:

```text
User selects:
PDF + XLSX + DOCX

        ↓

One logical Session

        ↓

Document A = PDF
Document B = XLSX
Document C = DOCX

        ↓

Each has:
- separate doc_id
- independent format
- independent status
- independent element collection

        ↓

Later task can choose any combination by doc_id
```

Upload order must not define semantics.

A task may reference:

```json
{
  "source_doc_ids": ["...", "..."],
  "target_doc_id": "..."
}
```

No implicit "Source" / "Target" UI role should appear during generic document upload.

No GTPS/HMV branding should leak into the generic document intake experience.

---

# 11. Current Frontend Product Model

Frontend is a React + TypeScript professional workbench.

Key areas:

```text
frontend/src/
├── components/
│   ├── agent/
│   ├── document/
│   ├── elements/
│   ├── results/
│   └── shared/
├── state/
│   ├── agentStore.ts
│   ├── workspaceStore.ts
│   └── syncStore.ts
└── api/
```

## 11.1 Current workspace presets

There are preset workspace configurations including:

- Agent;
- Inspect;
- Review;
- Compare.

These are workspace arrangements, not separate products.

## 11.2 Core panes

### Document

Answers:

> What is actually in the source document?

### Elements

Answers:

> What did Foundation detect?

### Agent

Answers:

> What can Foundation explain, investigate, or do with the current context?

### Results

Answers:

> What did the system produce and how can I verify it?

---

# 12. Latest UI Implementation — 2026-08-18

The latest verified UI work was **not a rewrite of the architecture**. It closed the remaining gaps between the existing workspace and `Foundation_UI_Spec_v1.0.md` / v2-style workspace requirements.

## 12.1 Format-aware Document pane

`frontend/src/components/document/DocumentPane.tsx`

Now supports explicit view modes:

```text
Original
Elements
Split
```

### XLSX Original mode

- real row/column grid;
- groups by sheet;
- column headers A/B/C...;
- row numbers;
- element coordinates inferred from `cell_address`;
- element interaction synchronized with the shared workspace state.

### PDF Original mode

- groups by page;
- preserves `reading_order_index` order;
- displays page cards;
- explicitly states when page-image preview is unavailable.

### DOCX Original mode

- renders the existing structural flow inside document-like page cards.

### Elements mode

Retains the structured element list.

### Split mode

Mounts the two relevant representations side-by-side.

## 12.2 Semantic element hierarchy

`ElementsPane.tsx::groupElements()` now groups:

- DOCX by semantic structure;
- XLSX by sheet;
- PDF by page.

Previously XLSX/PDF could collapse into a flat "Document" bucket.

## 12.3 Confidence noise reduction

Deterministic extraction yields confidence `1.0` / `100%` for every baseline element.

Showing `100%` on hundreds of rows is useless visual noise.

Current behavior:

- hide confidence badge in dense list when confidence is effectively 100%;
- still show exact confidence in detailed inspector/selection context.

Do not interpret this as removing confidence data from the model.

## 12.4 Provenance in Results

`ResultsPane.tsx` now exposes a visible provenance chain for mapped values:

```text
Output
  ↓
Mapped to
  ↓
Source
  ↓
Confidence + timestamp
```

This is a presentation of lineage, not model chain-of-thought.

## 12.5 Generic 10-document recommendation limit

The workspace explicitly enforces the recommended document limit of 10.

The limit is generic and does not distinguish between "source" and "target".

Do not reintroduce role-based restrictions at this intake stage unless a specific application task requires them.

## 12.6 Honest Agent context indicator

`AgentComposer.tsx` now shows:

```text
N documents in context
```

Only real context is shown.

It deliberately does **not** show a fake "Elements" or "Context" chip implying element-level retrieval/selection that the Agent does not currently implement.

This is a non-negotiable product principle:

> **Never visually imply functionality that is not actually backed by the system.**

## 12.7 UI loading states

A document whose elements are still loading must not be represented as permanently empty.

Current explicit states include messages such as:

```text
Reading document…
Loading elements…
```

This distinction matters because the header may already indicate that the document is ready while element payloads are still arriving.

---

# 13. Important Bugs Found and Fixed in the Latest UI Session

## 13.1 Infinite render loop

Real browser testing exposed:

```text
Maximum update depth exceeded
```

Scenario:

- XLSX or PDF active;
- Inspect preset;
- Document + Elements mounted together;
- `elements === null` while the fetch is in flight.

Root cause:

```ts
activeDoc?.elements ?? []
```

creates a **new array reference on each render**, which invalidated memo/effect dependencies and caused a `setExpandedGroups` loop.

Fix:

- stable `EMPTY_ELEMENTS` constant shared by the affected panes;
- `setHoveredElement` is a no-op when the index did not change;
- XLSX grid hover handling moved from thousands of individual handlers to event delegation on the table.

This is an important React performance correctness lesson for future changes: avoid unstable fallback objects/arrays inside render paths when they participate in effect dependencies.

## 13.2 False empty state while loading

Previous UI could show:

```text
No document loaded
No elements extracted
```

while data was merely pending.

This is fixed with explicit loading UI.

---

# 14. Cross-Pane Synchronization

The workspace relies on shared state rather than DOM polling/query hacks.

Core idea:

```text
activeDocument
activeElement
activeTrace
```

A selection or hover should be able to propagate to relevant surfaces.

Expected synchronization:

```text
Elements selection
   ↓
Document highlight / scroll
   ↓
Inspector detail
   ↓
Results trace / mapped-value context
```

Agent context should derive from the active workspace rather than requiring the user to restate file IDs manually.

Do not reintroduce ad-hoc DOM `querySelector` / custom document events when React shared state can express the same behavior.

---

# 15. UI Honesty and Explainability Rules

The product should expose:

- evidence;
- execution summaries;
- provenance;
- model version where applicable;
- actor/type of action;
- timestamps;
- deterministic processing steps;
- user/human edits.

The product should **not** expose hidden model chain-of-thought.

Use wording such as:

```text
Evidence
Analysis summary
Execution trace
Why this result was selected
```

not:

```text
Here is the model's private chain of thought
```

Trace actors should remain distinguishable:

| Actor | Meaning |
|---|---|
| System | Deterministic processing |
| AI Agent | AI proposal/action |
| Human | Human confirmation or modification |

Do not rely on color alone to distinguish actors.

---

# 16. Latest Test / Verification State

The most recent verified engineering state from the 2026-08-18 sessions:

```text
Backend + frontend test suite: 91 passed
TypeScript build: clean
npm build: clean
Browser verification: clean
Final browser console errors: 0
```

The browser run explicitly covered:

1. Home;
2. New Task / document selection;
3. 3-document mix: PDF + XLSX + DOCX;
4. workspace creation;
5. Agent default preset;
6. Inspect preset;
7. Document Original / Elements / Split;
8. XLSX, PDF, DOCX structural representations;
9. cross-pane element selection synchronization;
10. Applications menu / GTPS access surface;
11. final console verification.

Playwright was used temporarily for verification and removed from the project dependencies afterward.

---

# 17. Current Known Limitations / Deferred Work

These are intentional or explicitly known, not reasons to break existing architecture.

## 17.1 Agent is not a fully live autonomous agent yet

The Agent UI exists and is context-aware at the workspace level, but the system should not pretend that arbitrary element retrieval / arbitrary execution actions are already implemented.

Current UI behavior must remain honest.

## 17.2 Compare mode is not fully implemented

Current surface still has placeholder behavior such as:

```text
Source A / Source B
```

Do not describe Compare as production-complete.

## 17.3 History / Settings / Diagnostics

These are still deferred / partial compared with the complete UX specification.

## 17.4 Command menu

`Cmd+K` / command menu is planned but not complete.

## 17.5 Saved layouts / preset customization

Customize / reset / save behavior is not fully implemented.

## 17.6 Advanced docking

Current layout supports resizing through `react-resizable-panels`.

True floating / drag / snap docking is deferred.

Do not call the current implementation a complete VS Code docking system.

## 17.7 Pixel-perfect rendering

There is no full-fidelity document rendering engine for DOCX/XLSX/PDF in the current browser stack.

The UI intentionally uses structure reconstructed from anchors and extracted geometry instead of pretending to be pixel-perfect native rendering.

## 17.8 Poppler / PDF page image rendering

Still environment-dependent / unavailable on the current development machine.

## 17.9 XLSX direct PATCH route

Underlying write support exists, but the current direct editing access path is not fully equivalent to DOCX.

## 17.10 Database

Current foundation remains file-based for development.

Do not add a database migration merely as a cleanup task unless required by a concrete product requirement.

## 17.11 Normalization layer

Older build plans introduced a normalization layer as a future architecture requirement. There is not yet a completed production implementation in the current codebase.

Do not claim it exists merely because a historical plan describes it.

---

# 18. Technical Debt

Known technical debt that was deliberately not changed in the latest UI pass:

```text
frontend/src/state/workspaceStore.ts
```

still contains older GTPS mapping/task-related state such as:

```text
GptsMappingState
runGptsMappingTask
```

This was not moved during the latest UI session because the current work was explicitly frontend-focused and moving it was unnecessary for the verified UX changes.

Treat it as debt, not as evidence that GTPS logic belongs in the generic workspace architecture.

---

# 19. Historical Decisions That Still Matter

## 19.1 Foundation core vs application boundary

Core capabilities include:

- read / perceive;
- locate;
- select;
- inspect;
- controlled write / replacement;
- anchor resolution;
- lineage / trace substrate.

Application-specific behavior belongs in:

```text
foundation/applications/
```

Never put:

- HMV rules;
- GTPS rules;
- client-specific mappings;
- tax-specific business semantics

inside `perception/`.

## 19.2 OCR

OCR is **not currently required for the main verified Local File Mapping flow**.

The current geometry parser handles digital documents and text-layer PDFs deterministically.

Scanned PDFs currently return no text blocks rather than silently fabricating OCR results.

Do not add OCR just because a PDF happens to be image-only unless the requirement is explicitly reactivated.

## 19.3 Air-gapped / local-first constraint

The project was designed around environments where sensitive documents may need to remain local / isolated.

Do not silently introduce external hosted APIs into core perception or document processing.

Any external service dependency requires an explicit architecture decision.

---

# 20. Important Current File Map

## Backend

```text
foundation/
├── api/
│   ├── app.py
│   └── routes/
│       ├── documents.py
│       ├── process.py
│       ├── gpts.py
│       └── agent.py
│
├── applications/
│   └── gpts/
│       ├── mapping_service.py
│       └── demo_mapper.py
│
├── perception/
│   ├── parser.py
│   ├── models.py
│   ├── element_classifier.py
│   └── anchor_builder.py
│
├── output/
│   ├── lineage.py
│   └── writeback.py
│
└── tests/
    ├── test_parser.py
    ├── test_element_classifier.py
    ├── test_anchor_builder.py
    ├── test_documents_route.py
    └── test_agent_route.py
```

## Frontend

```text
frontend/src/
├── api/
│   ├── client.ts
│   └── agent.ts
│
├── components/
│   ├── agent/
│   │   ├── AgentComposer.tsx
│   │   └── AgentMessage.tsx
│   ├── document/
│   │   └── DocumentPane.tsx
│   ├── elements/
│   │   └── ElementsPane.tsx
│   ├── results/
│   │   └── ResultsPane.tsx
│   └── shared/
│       └── EmptyState.tsx
│
├── state/
│   ├── workspaceStore.ts
│   ├── agentStore.ts
│   └── syncStore.ts
│
└── index.css
```

---

# 21. Current API / UI Contract Principles

Claude Code must preserve the following:

### 21.1 Generic upload is generic

Do not add source/target/client/task semantics to generic document intake.

### 21.2 Session is persistent workspace context

The session is the owner of multiple documents.

### 21.3 Task is explicit

No hidden task creation during upload or perception.

### 21.4 Document status is per-document

Never fall back to one session-wide processing flag when the UX needs independent document states.

### 21.5 doc_id is the document identity

Never infer identity from position in an array.

### 21.6 Anchors must be resolvable or fail

Never silently guess a different element.

### 21.7 UI must match reality

Do not render controls that imply a feature that does not exist.

### 21.8 Application logic must remain outside perception

If a feature requires business semantics, ask: "Is this an application?" before touching `perception/`.

---

# 22. Current Source-of-Truth Hierarchy

When files disagree, use this order:

1. **Executable code and tests on current HEAD**
2. `foundation/STATUS.md` current verified sections
3. latest implementation notes / current context appendices
4. current UI specification
5. build plans
6. older historical context

Examples of known stale statements that must not override current state:

- older documents describing **Docling as current**;
- older statements that MVP is **DOCX-only** when the verified demo now includes PDF + XLSX + DOCX document handling;
- older UI descriptions using **four separate routes** instead of the single workspace model;
- older generic UI descriptions that still assume manual Source/Target roles during intake.

---

# 23. Claude Code Operating Instructions

Before modifying code:

1. Read this context.
2. Inspect the actual current implementation.
3. Inspect the nearest relevant tests.
4. Confirm whether the requested change belongs to perception, application, output, access, or frontend.
5. Preserve the Document / Session / Task boundary.
6. Preserve anchor resolution safety.
7. Preserve current UI honesty.
8. Prefer the smallest change that satisfies the requirement without re-architecting unrelated modules.

## Do not do these by default

- do not reintroduce Docling;
- do not move GTPS logic into perception;
- do not add fake Agent chips or fake retrieval actions;
- do not add a database without a concrete requirement;
- do not add OCR merely because it sounds useful;
- do not replace stable anchor logic with filename/index assumptions;
- do not use a fresh fallback array/object in React dependency-sensitive render paths;
- do not change the generic session contract just to simplify one task flow;
- do not treat a passing TypeScript build as sufficient when a browser interaction path is involved.

## Verification expectations

For backend changes:

```text
Run focused tests → run full suite when practical.
```

For frontend changes:

```text
Type-check/build → browser verification for meaningful interactions → inspect console.
```

For synchronization behavior:

```text
verify the actual interaction path, not only unit logic.
```

For document-anchor changes:

```text
test drift / self-healing and test failure paths.
```

---

# 24. Recommended Next Engineering Priorities

These are ordered for continuity, not as an unconditional command to implement all of them immediately.

## Priority 1 — Protect the current foundation

Keep the current 91-test baseline green while making incremental changes.

## Priority 2 — Strengthen document editing parity

Complete the controlled XLSX PATCH/write-back path so the generic editing contract is less DOCX-biased.

## Priority 3 — Complete real Agent capabilities

Connect the Agent to the actual workspace/document/element APIs without introducing fake context controls.

The Agent should be able to:

- inspect active element/document context;
- return evidence;
- perform explicit workspace actions;
- produce traceable execution steps.

## Priority 4 — Complete Results / Trace

Strengthen output + provenance + actor visualization so the user can understand:

```text
what changed
who/what changed it
why it changed
which source element caused it
```

## Priority 5 — Compare mode

Replace Source A/B placeholders with an actual comparison application built above Foundation primitives.

## Priority 6 — Workspace maturity

After the core behavior is stable:

- command menu;
- history restoration;
- settings/diagnostics;
- saved layouts;
- advanced docking.

## Priority 7 — Rendering fidelity

Only introduce heavier rendering infrastructure when a concrete product requirement justifies the complexity.

---

# 25. Definition of Current Success

The current Foundation state should be considered healthy when all of the following remain true:

- multiple arbitrary document formats can coexist in one session;
- each document has independent identity/status/elements;
- documents can be referenced by `doc_id` regardless of upload order;
- geometry extraction is deterministic;
- anchors survive expected structural drift;
- application logic does not leak into perception;
- controlled edits are traceable;
- UI panes stay synchronized;
- loading is not confused with empty state;
- Agent UI does not claim unsupported capabilities;
- provenance is visible;
- the build/test suite stays green;
- browser verification shows no unexpected console/runtime errors for modified flows.

---

# 26. Compact Mental Model for Claude Code

When in doubt, keep this model in mind:

```text
                    FOUNDATION
                         │
            ┌────────────┴────────────┐
            │                         │
      PERCEIVE / LOCATE         CONTROLLED EXECUTE
            │                         │
      Geometry + Elements         Write / Replace
            │                     Lineage / Trace
            │                         │
          Anchors ───────────────────┘
            │
            ▼
        WORKSPACE

Document  ↔  Elements  ↔  Agent  ↔  Results
      \         │          │         /
       \        │          │        /
        └────── shared document / element context ──────┘

Session = owns documents
Task    = explicit operation
Application = domain-specific behavior
Perception = generic document intelligence
```

The most important question before every architectural change is:

> **"Am I adding a reusable document capability, or am I accidentally moving application/business logic into the Foundation core?"**

If it is business-specific, keep it above the perception layer.

---

# 27. Repository Snapshot Used to Produce Context 3

Verified against the public repository:

```text
Repository:  nguyendinhphuc-tdzy/DocPercepInterac-Foundation
Branch:      master
HEAD:        f71769cda24f3a39371519aa5f67087a80805d06
HEAD message: UI update

Recent commits relevant to current context:
- f71769c — UI update
- def0182 — logic update
- 91d57da — update logic leak
- b6309fe — update UI
- cf1934c — API test workbench
- 0fe59f6 — fixture update
- c95032f — mapping update
- f48580c — classifier and harness update
```

The latest commit was dated **2026-08-18** and the latest verified UI session explicitly reported:

```text
91 tests passed
TypeScript build clean
npm build clean
0 browser console errors in the final verified flow
```

---

# 28. Final Instruction

**Treat this document as the compact operational context for continuing the project.**

Do not assume that older project plans are still authoritative merely because they are detailed.

Always inspect the current code before editing.

Always preserve:

```text
Generic Foundation core
        ↓
Stable perception
        ↓
Safe anchors
        ↓
Explicit application task
        ↓
Governed execution
        ↓
Traceable result
```

And on the frontend:

```text
One workspace
Document ↔ Elements ↔ Agent ↔ Results
```

That is the current product and engineering direction.
