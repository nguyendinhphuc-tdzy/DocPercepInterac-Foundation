# Foundation UI Information Architecture

**Document status:** U0 BASELINE — ACCEPTED (Product/BA implementation guidance; not a Frozen Foundation Contract; does not override CURRENT_BASELINE.md, accepted ADRs, or docs/contracts/)
**Date:** 2026-09-09
**Workstream:** Frontend U0 — Governed Workspace Foundation
**Branch:** `build/ui-foundation-v2`
**Precedence authority:** `docs/CURRENT_BASELINE.md`, accepted ADRs (`docs/adr/`), Frozen Foundation Contract v0.1 (`docs/contracts/`).

---

## 1. Executive Summary & Epistemic Taxonomy

This document specifies the Information Architecture (IA) for the Foundation v2 frontend. Foundation is a governed workbench where workspace layout, prominent affordances, and data displays dynamically respond to the authoritative lifecycle state of the governing `FoundationTask`.

Epistemic classifications used herein:
- `[FACT]`: Direct reflection of Frozen Contract v0.1 (`TaskStatus`, `DocumentStatus`, `domain-model.md`).
- `[DECISION]`: Approved product architecture (task-state-driven layout, progressive disclosure, selection/extraction separation).
- `[INFERENCE]`: Architectural derivation from frozen domain invariants.
- `[RECOMMENDATION]`: Specific UI component arrangement proposed for U0 implementation.

---

## 2. Global Application Hierarchy

```text
Application Root
├── Global Shell Header
│   ├── Workspace Brand & Environment Status (e.g., SIMULATED BACKEND indicator)
│   ├── Active Task Selector & Governed Status Badge (TaskStatus)
│   ├── Document Version & Integrity Hashes (SHA-256)
│   └── User Identity & Role Context
├── Primary Workspace
│   ├── Navigation Rail (Collapsible: Home, Workspaces, Audit Log, Settings)
│   ├── Context Rail (File & Document Intake Collection)
│   ├── Central Document Viewing & Selection Surface
│   │   ├── Document Viewer (Format-specific: DOCX, XLSX, PDF)
│   │   ├── Selection Overlay & Interaction Primitives
│   │   └── Viewport Controls (Zoom, Fit, Split View)
│   ├── Contextual Work Inspector (Task-State Driven Panel)
│   │   ├── Intake & Source Readiness Panel
│   │   ├── Evidence & Exception Review Panel
│   │   ├── Approved Changes & Execution Readiness Panel
│   │   ├── Validation & Verification Report Panel
│   │   └── Selection Inspector (Contextual on region/object selection)
│   └── Auxiliary Drawer / Dock
│       ├── Agent Assistance Pane (Auxiliary, assist-only, non-authorizing)
│       └── Technical Trace / Forensic Details Drawer
└── System Status Bar
    ├── Active Task ID & Target Contract Version
    ├── Replay Candidate Engine Status
    └── Network & Event Stream Connectivity
```

---

## 3. Conceptual Information Model

```text
Workspace
├── Documents / Intake
│   ├── Document Registration (File metadata, size, MIME)
│   ├── Content Hash Verification (SHA-256)
│   ├── Document Role Assignment (TARGET, CURRENT_SOURCE, HISTORICAL_SOURCE, TEMPLATE)
│   └── Binary Capability Preflight (ConformanceClass, Encryption, Packaging)
├── Document Viewer
│   ├── Visual Surface (DOCX Flow, XLSX Sheet Grid, PDF Fixed Canvas)
│   ├── Inspect (Structured semantic elements tree)
│   ├── Select Region (Direct manipulation: Box, Range, Multi-object)
│   ├── Extract (Derived read-only export: CSV, XLSX, DOCX, Image)
│   └── Propose Change (Governed mutation proposal generation)
├── Task / Workflow Status
│   ├── Authoritative TaskStatus (CREATED -> ANALYZING -> AWAITING_REVIEW -> ...)
│   ├── Pinned TargetContractDefinition & Instance
│   └── Release Status Gate (WITHHELD, ELIGIBLE, RELEASED)
├── Source Readiness
│   ├── Required Source Requirements Matrix
│   ├── Source Sufficiency Outcomes (SUFFICIENT, MISSING, STALE, CONFLICTING, AMBIGUOUS)
│   └── Freshness & Period Policy Evaluations
├── Evidence
│   ├── Authoritative Source Excerpts & Provenance
│   ├── Native Formulas vs. Calculated Values
│   └── Evaluator Bindings & EvidenceCheck Outcomes
├── Exceptions
│   ├── Open Business & Evidentiary Blockers
│   ├── Structural & Capability Exceptions
│   └── Remediation Action Registry
├── Review
│   ├── ChangeProposal Queue (READY_FOR_REVIEW, IN_REVIEW)
│   ├── Side-by-Side Impact Diff (Current vs. Proposed)
│   └── Human Review Outcomes (APPROVE, REJECT, DEFER, REQUEST_MORE_SOURCE)
├── Approved Changes
│   ├── Materialized ApprovedChangeSet (Immutable, Sealed)
│   ├── Target Locators & Approved Payloads
│   └── Invalidation & Revocation Registry
├── Execution
│   ├── Controlled Replay Dispatch Status (QUEUED, PREFLIGHTING, RUNNING)
│   ├── Attempt History & Execution Conflicts
│   └── Staged Output Generation
├── Validation
│   ├── Independent ValidationReport (PASSED, FAILED, INCONCLUSIVE)
│   ├── Mandatory Invariant Checks & Scope Preservation Checks
│   └── Structural Anomaly Detection
├── Audit
│   ├── Immutable AuditEvent Chronological Stream
│   ├── Hash-Chained Actor Attributions (HUMAN, SYSTEM, AI)
│   └── Replay Proof Package
└── Agent Assistance
    ├── Read-Only Semantic Explanations & Summaries
    ├── Candidate Mapping & Drafting Proposals
    └── Ambiguity & Policy Clarification
```

---

## 4. Task-State-Driven Workspace Emphasis

`[DECISION]` The workspace is not hard-coded into fixed, static tabs ("Agent", "Inspect", "Review"). Instead, the primary layout shifts emphasis dynamically based on the authoritative backend `TaskStatus` from Frozen Contract v0.1:

| Backend TaskStatus | UI Workspace Emphasis | Primary Focus Region (Left/Center) | Contextual Work Inspector (Right) | Secondary / Auxiliary Tools |
|---|---|---|---|---|
| `CREATED` | Intake | Document Intake Rail + Source Registration Canvas | **Source Readiness Panel**: Missing files, period requirements, authority checks | Auxiliary Agent: "What files are required for VN Local File?" |
| `ANALYZING` | Analysis & Preflight | Document Viewer (Preflight overlay) | **Preflight Findings & Capability Detection**: Structure detection, OOXML conformance, protection locks | Diagnostic Log (Read-only) |
| `AWAITING_REVIEW` | Review & Verification | Document Viewer (Interactive targets highlighted) | **Governed Evidence & Review Panel**: ChangeProposal list, side-by-side excerpts, decision buttons | Agent: Explains discrepancy or source excerpt |
| `READY_FOR_EXECUTION` | Execution Preparation | Approved Change Summary (Diff view against target) | **Execution Readiness Gate**: Pinned binary hashes, locators confirmed, validation obligations | Technical Trace Drawer (Locators & Payloads) |
| `EXECUTING` | Execution Monitoring | Staged Document Canvas (Lock during run) | **Execution Progress Monitor**: Controlled replay status, dispatch attempt log | System Event Stream |
| `VALIDATING` | Validation Inspection | Side-by-Side: Original Input vs. Staged Output | **Independent Validation Report**: Mandatory invariant checks, preservation scope checks | Audit Event Inspector |
| `COMPLETED` | Release & Audit | Validated Output Document (Read/Export enabled) | **Release Summary & Audit Package**: Signed audit certificate, hash manifest, download artifact | Export & Archive Options |
| `BLOCKED` | Exception Remediation | Problem Document / Missing Evidence Viewer | **Exception Resolution Panel**: Explicit blocking checks, remediation options | Agent: Clarifies policy rule violation |
| `FAILED` | Diagnostics & Recovery | Quarantine / Error Diagnostic Surface | **Failure Root-Cause Analysis**: Assessor, executor, or validator failure records | Error Catalog Reference |
| `CANCELLED` | Cancellation Summary | Read-only task summary surface | **Cancellation Audit Record**: Reason code and cancellation actor | Audit Event Inspector |

**Governance Rule:** `TaskStatus` determines workspace emphasis and context. Authoritative backend-provided governance, capability, and action availability determine which user actions are actually enabled. Status alone must never authorize an action. Controls such as retry, re-evaluate, approve, remediation, or cancel are backend/capability driven (e.g., `FAILED` does not automatically enable generic retry; `BLOCKED` does not automatically enable re-evaluate).

---

## 5. Progressive Disclosure: Business View vs. Technical Trace

`[DECISION]` Foundation strictly enforces progressive disclosure to avoid confusing business reviewers with internal engineering constructs, while guaranteeing complete forensic transparency for auditors.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ BUSINESS VIEW (Primary Reviewer Surface)                                    │
│                                                                             │
│ Target Field:    Net Cost Plus Margin (NCP)                                 │
│ Document Context: Section 4.2 — Financial Performance Summary               │
│ Source Evidence: Audited Financial Report 2025 (Doc B), Page 14, Table 3    │
│ Target Value:    9.45%  (Prior Year: 8.12%)                                 │
│ Status:          [VERIFIED] Deterministic match against RulePack v1.2       │
│                                                                             │
│ Affordance: [View Evidence Excerpt]  [Technical Trace ▼]                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │ (Clicking expands on-demand drawer)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TECHNICAL TRACE DRAWER (Forensic Engineering & Audit Details)               │
│                                                                             │
│ Business Target ID:   VN_LOCAL_FILE.FINANCIAL.NCP                           │
│ Semantic Reference:   #/tables/2/rows/4/cells/1                             │
│ Native Locator:       Type: DOCX_CONTENT_CONTROL                            │
│                       Part: /word/document.xml                              │
│                       SDT ID: 8775518                                       │
│ Source Document Hash: 3a7f8b9c4d... (SHA-256)                               │
│ Target Document Hash: 9e2c1a5b8f... (SHA-256)                               │
│ Evaluator Binding:    eval_financial_ratio_deterministic_v1                 │
│ Evidence Check Kind:  PERIOD (2025-FY), FRESHNESS (Pass, as_of: 2026-03-31) │
│ Capability Result:    SUPPORTED (Engine: OpenXmlSdk 3.5.1, Transitional)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Identity Rule (`INV-UI-01`):**
`BusinessTargetID != SemanticReference != NativeLocator`
Under no circumstance may the UI use these three identifiers interchangeably.

---

## 6. Document Region Selection & Extraction IA

`[DECISION]` Direct manipulation of document regions must not bypass governance. Selection of document content provides inspection, extraction, and drafting options, but carries zero mutation authority.

### 6.1 Core Principle: Selection != ChangeProposal != ApprovedChangeSet
Direct manipulation does NOT automatically create a change proposal.

```text
User Region Selection (Mouse drag / range click)
         ↓
SelectionGeometry (Screen coordinates: viewport x, y, w, h)
         ↓
Candidate Rendered DOM Elements (Intersected paragraphs, cells, images)
         ↓
Semantic Resolution Request (Selection Resolution Service — API shape TBD [Simulated in U0])
         ↓
ResolvedSelection (Semantic objects, counts, ambiguity status)
         ↓
Selection Inspector (Presents available, capability-gated user actions)
         │
         ├── [Action: Inspect] ───────────> Inspect element tree & Technical Trace
         ├── [Action: Extract] ───────────> ExtractionPlan ──> Export Artifact (Derived read-only file)
         ├── [Action: Ask AI] ────────────> Query auxiliary Agent for explanation/summary
         └── [Action: Propose Change] ────> User Intent Modal ──> ChangeProposal (DRAFT) ──> Review
```

**Key Invariants:**
```text
Selection != ChangeProposal != ApprovedChangeSet
Extract != Propose Change
Extract != Mutation
```

### 6.2 Selection Inspector Specification
When a user selects content in the Document Viewer, the Selection Inspector activates in the contextual pane:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ SELECTED REGION                                                         │
│ Scope: Page 4, Section 2.1 (Docx Flow)                                  │
│                                                                         │
│ Detected Document Objects:                                              │
│ • 2 Paragraphs (Heading 2, Body Text)                                   │
│ • 1 Structured Table (4 columns × 6 rows)                               │
│ • 1 Embedded Image (Chart: "Historical Operating Margin")              │
│                                                                         │
│ Status: RESOLVED (Unambiguous boundary)                                 │
│                                                                         │
│ Available Actions (Capability-Gated):                                   │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🔍 INSPECTION & ASSISTANCE (Read-only)                              │ │
│ │  • [Inspect Elements Tree]                                          │ │
│ │  • [View Technical Trace]                                           │ │
│ │  • [Ask Agent to Explain Section]                                   │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📥 EXTRACTION (Derived read-only export — No mutation authority)    │ │
│ │  • [Extract Table to CSV]                                           │ │
│ │  • [Extract Table to XLSX]                                          │ │
│ │  • [Extract Text Only (Markdown)]                                   │ │
│ │  • [Extract Image Only (PNG)]                                       │ │
│ │  • [Extract Components Separately (ZIP)]                            │ │
│ │  • [Extract Region as Structured DOCX]                              │ │
│ │  • [Extract Native-Fidelity DOCX] (Gated: requires engine support)  │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ ✍️ GOVERNED MUTATION INTENT (Requires explicit user action)          │ │
│ │  • [Propose Change] ──> Opens proposal modal ──> DRAFT Proposal     │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Format-Specific Selection Interaction
1. **PDF Documents (Fixed Layout):**
   - Selection Geometry: `page_number + bounding_box { x, y, width, height }` (normalized 0.0 to 1.0).
   - Interaction: Precision bounding-box marquee drag.
2. **XLSX Workbooks (Tabular Grid):**
   - Selection Geometry: Semantic sheet coordinates: `SheetName!ColRow:ColRow` (e.g., `Financials!B12:F28`).
   - Interaction: Grid cell range drag, column/row header click. Arbitrary diagonal pixel cropping is discouraged.
3. **DOCX Documents (Flow Layout):**
   - Selection Geometry: Transient DOM bounding box.
   - Resolution: Client intersects DOM bounding box with rendered paragraph/table/run spans, extracts semantic IDs, and resolves to logical document objects.

### 6.4 Semantic Snapping
- When a user selection substantially overlaps a structured object (e.g., a table), the UI may offer semantic snapping to the complete object:
  > *"Table detected (4 cols × 6 rows). Snap to complete table?"*
  > Actions: `[Use Full Table]` | `[Keep Current Selection]`
- `[DECISION]` The snapping threshold is **TBD / REQUIRES UX AND CORPUS VALIDATION**. It is an ergonomic technical parameter, not business truth. Exact overlap percentages must not be proposed, invented, or hardcoded as product truth.

### 6.5 Extraction Quality Levels
- **Structured DOCX Export:** Preserves reading order, text, basic heading hierarchies, table structures, and images. Does not guarantee exact native Word margins, shapes, or style manifests.
- **Native-Fidelity DOCX Export:** Preserves native OOXML dependency closure (styles, numbering, relationships, headers, footers). This mode is **capability-gated**. If the candidate engine or preflight reports missing bindings or unsupported structures, the UI **fails closed**: it disables native-fidelity export, explains why, and offers structured export as an alternative. Silent degradation is strictly prohibited.

### 6.6 Image Handling: Extraction vs. Understanding
- `EXTRACT_IMAGE`: Exports the raw binary image stream as embedded in the package.
- `UNDERSTAND_IMAGE`: Distinct, auxiliary AI/VLM perception capability requiring separate invocation and validation. The UI must never claim an image is "understood" merely because it was successfully extracted.

---

## 7. Auxiliary Agent Assistance IA

`[DECISION]` The Agent / Chat interface is an auxiliary side panel, not the primary operating surface or workspace home.

- **Placement:** Collapsible right-hand drawer or bottom-docked tray.
- **Role:** Assist-only. Capable of explaining findings, summarizing evidence, identifying ambiguity, and drafting candidate proposals.
- **Forbidden Actions:**
  - Cannot directly mutate the document.
  - Cannot approve a proposal.
  - Cannot authorize execution.
  - Cannot dismiss a blocking evidence check.
- **Contract Boundary:** Agent interactions yield candidate drafts (`ChangeProposal` in `DRAFT` status). A human reviewer must explicitly approve the proposal through the governed Review interface.

---

## 8. Contract Type Generation Architecture

`[DECISION]` Frontend contract types must be automatically generated from:
`docs/contracts/foundation.openapi.yaml`

```text
docs/contracts/foundation.openapi.yaml
         ↓ (open-api-typescript code generator — machine owned)
frontend/src/types/contract.generated.ts
         ↓ (Strict TypeScript type projection)
frontend/src/state/adapters/
         ├── taskAdapter.ts      (Maps generated task DTOs to view state)
         ├── evidenceAdapter.ts  (Maps evidence models to review cards)
         └── selectionAdapter.ts (Maps non-contract UI selection DTOs)
```

**Rule:** Developers must NOT manually recreate, edit, or maintain TypeScript interfaces duplicating Frozen Contract v0.1. Hand-crafted view models may format strings or compute display colors, but backend schemas remain machine-generated.
