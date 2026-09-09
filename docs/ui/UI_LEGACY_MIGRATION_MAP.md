# Foundation UI Legacy Migration Map

**Document status:** U0 BASELINE — ACCEPTED (Product/BA review passed 2026-09-09)  
**Date:** 2026-09-09  
**Workstream:** Frontend U0 — Governed Workspace Foundation  
**Branch:** `build/ui-foundation-v2`  
**Precedence authority:** `docs/CURRENT_BASELINE.md`, accepted ADRs (`docs/adr/`), Frozen Foundation Contract v0.1 (`docs/contracts/`).

---

## 1. Executive Summary & Epistemic Taxonomy

This migration map audits all existing frontend prototype components, state stores, and interaction patterns in `frontend/src/`, comparing them against the target architecture of Foundation v2.

It defines an orderly, phased transition that shuts down un-governed mutation shortcuts, isolates legacy prototypes, and replaces ad-hoc data structures with machine-generated types from Frozen Contract v0.1.

**Governing Migration Rule:**  
`No legacy artifact is deleted during U0 documentation. Legacy code is classified and bounded; destructive removals occur in subsequent authorized code workstreams.`

Epistemic classifications:
- `[FACT]`: Verified code in `frontend/src/` or backend reports.
- `[DECISION]`: Approved deprecation or target UX pattern.
- `[RECOMMENDATION]`: Proposed migration sequencing and adapter strategy.

---

## 2. Core Paradigm Shifts: Legacy Prototype vs. Foundation v2

| Legacy Prototype Pattern | Target Foundation v2 UX Pattern | Rationale & Architectural Rule |
|---|---|---|
| **`EditableText`** (Direct text input on rendered elements) | **Contextual Action Palette → `Propose Change` Modal** | `[DECISION]` Inline editing falsely implied direct document mutation. Direct selection does NOT create a proposal (`Selection != ChangeProposal != ApprovedChangeSet`). Selecting an object offers `Inspect`, `Extract`, `Ask AI`, or `Propose Change`. Only an explicit user choice to propose a change creates a `ChangeProposal` (`DRAFT`). |
| **Direct `PATCH /api/elements/{id}`** | **`ChangeProposal` → Review → `ApprovedChangeSet` → Controlled Replay** | `[FACT]` Backend is authoritative. Direct PATCH was a prototype shortcut bypassing source sufficiency, evidence gates, and approval contracts. |
| **`Confirm & Apply` Button** | **`ReviewDecision` (`APPROVE`, `REJECT`, `DEFER`, `REQUEST_MORE_SOURCE`)** | `[DECISION]` Review decisions are explicit, auditable business determinations, not generic UI confirmations. |
| **`Approve & Execute` Combined Action** | **Sealed `ApprovedChangeSet` followed by Controlled Replay Dispatch** | `[FACT]` Approval and execution are distinct stages. Approval seals the change set; execution dispatches to a qualified engine. |
| **`ConfidenceBadge %`** (e.g., "95% Confident") | **Deterministic Verification State (`VERIFIED`, `BLOCKED`, `STALE`, `UNVERIFIED`)** | `[DECISION]` Percentages visually masquerade as system verification. Governed UI requires deterministic evidence outcomes. |
| **`GTPS Mapping Output` (`GptsMappingAction`)** | **Governed Task Transformation & Validation Result** | `[DECISION]` Legacy GTPS action was an unstructured prototype bypass. Foundation v2 uses structured RulePacks and target contracts. |
| **Local Client `editHistory` / Undo** | **Immutable `AuditEvent` Stream & Server Task Projections** | `[FACT]` Client-side undo arrays cannot guarantee cryptographic document recovery. All historical changes belong in the append-only audit log. *(AuditEvent domain/hash mechanics is `ACCEPTED_V2`; concrete persistent store is `NOT_IMPLEMENTED`).* |
| **Agent / Chat as Primary Operating Surface** | **Agent as Auxiliary Assistance Panel** | `[DECISION]` AI is assist-only (explaining, drafting, clarifying). The primary surface is the governed document viewer and review inspector operated by the Associate and Reviewer. |

---

## 3. Comprehensive Artifact Classification

Every component, store, and type in `frontend/src/` is categorized into one of four migration actions:
1. **`RETAIN`**: Core utility, layout shell, or high-fidelity renderer that aligns with Foundation v2 and requires minimal adjustment.
2. **`ADAPT`**: Valuable component that will be refactored to consume generated contract types and respect governed lifecycle boundaries.
3. **`DEPRECATE`**: Legacy component that is bypassed or disabled in target UX; retained temporarily during U0 to preserve build stability.
4. **`REMOVE_LATER`**: Obsolete prototype code scheduled for complete deletion in U1/U2 once replacement adapters are active.

---

### 3.1 State Stores (`frontend/src/state/`)

| File | Current Role | Target Role | Classification | Migration Action Plan |
|---|---|---|---|---|
| `workspaceStore.ts` | Monolithic store managing documents, active doc, inline edits (`editElement`), undo, and GTPS mapping. | Split into `taskStore.ts` (governed business projection) and `presentationStore.ts` (UI chrome). | **ADAPT** | Extract document collection into `taskStore`. Strip out `editElement`, `undoLastEdit`, and direct element patching. |
| `syncStore.ts` | Cross-pane element selection synchronization (`selectedElementId`). | Retain as transient selection synchronization primitive; adapt to handle `ResolvedSelection`. | **ADAPT** | Update to support multi-object selection and region bounding boxes alongside single element IDs. |
| `agentStore.ts` | Chat conversation messages, streaming tokens, model selection. | Auxiliary assistance state; restrict agent actions to drafting `ChangeProposal` DTOs. | **ADAPT** | Remove any direct document mutation tool calls from agent handlers; enforce assist-only prompt boundaries. |
| `workflowStore.ts` | Local roll-forward workflow state, intake steps. | Project authoritative backend `FoundationTask` and `SourceAssessment` states. | **ADAPT** | Replace client-calculated readiness flags with backend `SourceSufficiencyOutcome` projections. |
| `pilotStore.ts` | Pilot evaluation feedback and scoring metrics. | Retain as developer/evaluator feedback capture during U0/U1 testing. | **RETAIN** | Keep isolated in evaluation tooling drawer; ensure zero influence on business transformations. |

---

### 3.2 Document Renderers (`frontend/src/components/document/`)

| File | Current Role | Target Role | Classification | Migration Action Plan |
|---|---|---|---|---|
| `DocxRenderer.tsx` | DOM rendering via `docx-preview`, anchor mapping, inline editing textarea overlay. | Primary DOCX visual surface, selection marquee listener, highlight overlay. | **ADAPT** | Remove the inline `<textarea>` editing overlay. Add mouse drag selection listeners for region extraction. |
| `XlsxRenderer.tsx` | Virtualized sheet grid, formula protection tooltip, click-to-edit cell. | Primary XLSX inspection surface, cell/range selection (`Sheet1!B12:F28`). | **ADAPT** | Disable direct click-to-edit cell mutation. Replace with "Propose Cell Change" and range selection for CSV/XLSX export. |
| `PdfRenderer.tsx` | Lazy canvas rendering via `pdfjs-dist`, bbox overlay. | Primary PDF inspection surface, normalized marquee selection (`page + bbox`). | **RETAIN** | Preserve high-quality canvas rendering; add region selection drag interaction for PDF extraction. |
| `SplitView.tsx` | Configurable 2-pane comparison workspace with independent zoom and doc selectors. | Core comparison surface for side-by-side inspection (Target vs. Source, Input vs. Output). | **RETAIN** | Keep current hardened implementation; ensure cross-pane selection isolation is preserved. |
| `DocumentPane.tsx` | Document container, toolbar (Zoom, Split), element diagnostics bar. | Document viewing workbench container; hosts Selection Inspector overlay. | **ADAPT** | Remove monospace developer diagnostics from header; add Selection Inspector contextual drawer trigger. |
| `docxAnchorMapping.ts`| Client-side paragraph/cell anchor and fingerprint mapping. | Prototype reference helper; will be supplemented by backend Docling and native locators. | **ADAPT** | Maintain as client DOM fallback until backend semantic resolution endpoints are live. |
| `VisualObjectNotice.tsx`| Notification banner for unsupported drawings/shapes. | Capability-gated notice explaining unsupported OOXML structures. | **RETAIN** | Align notice wording with Frozen Contract v0.1 `CapabilityStatus.UNSUPPORTED`. |

---

### 3.3 Workspace, Shell & Navigation (`frontend/src/components/workspace/`, `shell/`)

| File | Current Role | Target Role | Classification | Migration Action Plan |
|---|---|---|---|---|
| `AppShell.tsx` | Main application shell, header, sidebar integration. | Governed workbench shell, hosts `SIMULATED BACKEND` banner and task status. | **RETAIN** | Add persistent environment mode indicator (`SIMULATED BACKEND`) and active `TaskStatus` badge. |
| `Sidebar.tsx` | Navigation rail (Home, Workspaces, History, Settings). | Governed navigation rail; provides access to Audit Timeline and Validation Reports. | **RETAIN** | Add navigation items for "Audit Log" and "Validation"; ensure accessible keyboard collapse. |
| `WorkspaceHeader.tsx` | Document title, preset switcher, applications menu, Undo, Download. | Governed task header, displays document version hash, target contract, and task state. | **ADAPT** | Remove "Undo" button and "Presets" (Agent/Inspect/Review); replace with task-state-driven status indicators. |
| `FileRail.tsx` | Document list, upload button, role status badges. | Governed intake rail; displays document roles (`TARGET`, `SOURCE`, `TEMPLATE`) and hash verification. | **ADAPT** | Integrate `DocumentRole` tags and SHA-256 integrity check status chips. |
| `WorkspaceView.tsx` | Preset-based layout switcher (AgentLayout, InspectLayout, etc.). | Task-state-driven dynamic workspace layout manager. | **ADAPT** | Refactor layout switching to key off `TaskStatus` rather than hardcoded static UI presets. |

---

### 3.4 Review, Results & Legacy Actions (`frontend/src/components/`)

| File | Current Role | Target Role | Classification | Migration Action Plan |
|---|---|---|---|---|
| `ElementsPane.tsx` | Tree view of parsed document elements and inline inspector. | Structured Element Inspector; reveals semantic references and DOM hierarchy. | **ADAPT** | Move technical locator details into Technical Trace drawer; focus main view on business context. |
| `ResultsPane.tsx` | Table displaying mapping results and patched download button. | Governed Review & Approved Changes Inspector. | **ADAPT** | Replace ad-hoc results table with `ChangeProposal` cards and `ReviewDecision` actions. |
| `GptsMappingAction.tsx` | Legacy action calling custom GTPS mapping backend endpoint. | Unused legacy prototype action. | **DEPRECATE** | Remove from UI menus; mark as deprecated; isolate until final removal in U2. |
| `ConfidenceBadge.tsx` | Renders color-coded percentage badges (e.g., green 95%). | Explicit Evidence / Verification Status Badge. | **DEPRECATE** | Deprecate generic percentages. Replace with `StatusBadge` showing `VERIFIED`, `BLOCKED`, `STALE`. |
| `EditableText.tsx` | In-place editable text wrapper with click-to-edit. | Governed Propose Change trigger button. | **DEPRECATE** | Disable direct editing behavior. Render static text with a contextual "Propose Change" pencil icon. |
| `StatusBadge.tsx` | Generic status badge renderer. | Reusable badge supporting Frozen Contract v0.1 closed enums. | **RETAIN** | Update palette to map frozen status enums (`TaskStatus`, `ValidationStatus`, `CheckOutcome`). |
| `EmptyState.tsx` | Universal empty state placeholder. | Standard empty state component across all panels. | **RETAIN** | Keep as-is. |
| `WorkflowIntakePanel.tsx`| Roll-forward workflow intake steps and source document checklist. | Governed Source Readiness & Intake Panel. | **ADAPT** | Bind checklist directly to backend `SourceAssessment` and `SourceSufficiencyOutcome` contracts. |
| `ReadinessSummary.tsx`| Visual progress summary for source readiness. | Source Readiness summary card in Task Header. | **RETAIN** | Update to reflect frozen `SourceSufficiencyOutcome` states (`SUFFICIENT`, `MISSING`, `STALE`). |

---

### 3.5 Agent Assistance Components (`frontend/src/components/agent/`)

| File | Current Role | Target Role | Classification | Migration Action Plan |
|---|---|---|---|---|
| `AgentPane.tsx` | Main conversation pane, default workspace center in legacy preset. | Auxiliary side drawer or bottom dock; assist-only. | **ADAPT** | Relocate from primary screen center to collapsible auxiliary drawer. Enforce assist-only disclaimer. |
| `AgentComposer.tsx` | Message input box with document context pill counters. | Auxiliary prompt input; supports querying policy rules and drafting proposals. | **RETAIN** | Retain composer; ensure submitted prompts cannot trigger direct document mutation. |
| `AgentMessage.tsx` | Chat bubble renderer with markdown and tool call rendering. | Message bubble displaying explanations, citations, and draft proposal cards. | **ADAPT** | If an agent message contains a proposed change, render it as an interactive `ChangeProposal` preview card. |
| `RollForwardStateCard.tsx`| In-chat card displaying roll-forward status and progress. | Auxiliary summary card; replaced by central task status header. | **DEPRECATE** | Keep for backward compatibility during U0 testing; deprecate in favor of central header. |
| `RollForwardResultCard.tsx`| In-chat card displaying mapping results and download CTA. | Replaced by Governed Review panel and Validation report. | **DEPRECATE** | Disconnect from writeback actions; deprecate in favor of central review inspector. |
| `PilotFeedback.tsx` | Evaluator feedback submission form. | Developer / QA feedback tool in diagnostics drawer. | **RETAIN** | Relocate to diagnostics popover. |

---

## 4. Contract Type Generation & Schema Migration Plan

`[DECISION]` To eliminate schema discrepancies between backend and frontend, manual TypeScript type definitions are replaced with machine-generated types.

### 4.1 Target Type Architecture
```text
docs/contracts/foundation.openapi.yaml
         │
         │ (Command: npx openapi-typescript docs/contracts/foundation.openapi.yaml -o frontend/src/types/contract.generated.ts)
         ▼
frontend/src/types/contract.generated.ts  [MACHINE-OWNED — DO NOT MANUALLY EDIT]
         │
         ├── Extracted DTO Types:
         │   • TaskStatus, DocumentStatus, ChangeProposalStatus, ApprovedChangeSet
         │   • SourceAssessment, SourceSufficiencyOutcome, EvidenceAssessment
         │   • ValidationReport, CheckOutcome, AuditEvent, ReleaseStatus
         │
         ▼
frontend/src/state/adapters/
         ├── taskAdapter.ts      (Adapts generated task contracts to view models)
         ├── evidenceAdapter.ts  (Adapts evidence models to review cards)
         └── selectionAdapter.ts (Adapts non-contract selection DTOs)
```

### 4.2 Migration of Legacy Types
- `frontend/src/types/element.ts`: Contains legacy `DocElement`, `AnchorFingerprint`, and `GptsMappingResult`. These types are **DEPRECATED**. During U0, adapter functions will bridge legacy `DocElement` to generated OpenAPI schemas.
- `frontend/src/types/chat.ts`: Contains chat message structures. Will be updated to reference `ActorType.AI` and `ActorType.HUMAN` from OpenAPI definitions.

---

## 5. Workstream U0.3: Legacy Authority Shutdown Plan

The following sequential steps will be executed during frontend implementation to cleanly eliminate legacy mutation authority without breaking the test suite:

```text
Step 1: Disconnect Direct Writeback Routes
- Neutralize direct PATCH endpoints in API client (`frontend/src/api/`).
- Redirect edit submissions to create local or mock `ChangeProposal` DTOs with status `DRAFT`.

Step 2: Deprecate Inline Editing in Renderers
- Disable `<textarea>` overlays in `DocxRenderer.tsx` and click-to-edit in `XlsxRenderer.tsx`.
- Selecting content opens a contextual action palette (Inspect, Extract, Ask AI, Propose Change) carrying no automatic mutation authority.
- Only clicking "Propose Change" triggers the proposal intent modal to create a DRAFT `ChangeProposal`.

Step 3: Banish Generic Confidence Badges
- Search and replace `ConfidenceBadge.tsx` usage across review views.
- Replace with deterministic `StatusBadge.tsx` displaying `VERIFIED`, `BLOCKED`, `STALE`.

Step 4: De-emphasize Agent Workspace
- Change default workspace layout from `AgentPresetLayout` to `TaskStateDrivenLayout`.
- Dock `AgentPane` as a collapsible auxiliary drawer on the right side of the screen.

Step 5: Quarantine Legacy GTPS Mapping
- Remove `GptsMappingAction.tsx` and GTPS menu triggers from `WorkspaceHeader.tsx`.
- Mark GTPS API endpoints as `@deprecated` in `frontend/src/api/`.

Step 6: Activate Global Simulated Mode Indicator
- Implement the persistent `SIMULATED BACKEND` banner in `AppShell.tsx`.
- Connect banner to environment mode configuration.
```

---

## 6. Migration Safeguards & Validation Criteria

To ensure no regression occurs during migration:
1. **Existing Verification Suite Preservation:** Playwright tests verifying document zoom, split-view synchronization, and responsive layouts (`test_ui_ux_closure.mjs`, `test_both_fixtures.mjs`, `test_xlsx_interaction.mjs`) must continue to pass.
2. **Build Cleanliness:** TypeScript compilation (`npm run build`) must pass with zero errors and zero warnings.
3. **Audit Compliance:** Every user action that creates or modifies a proposal must record an auditable event with timestamp and actor attribution.
