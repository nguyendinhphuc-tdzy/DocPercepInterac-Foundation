# Foundation UI Specification v0.1

**Document status:** U0 BASELINE — ACCEPTED (Product/BA review passed 2026-09-09)  
**Date:** 2026-09-09  
**Workstream:** Frontend U0 — Governed Workspace Foundation  
**Branch:** `build/ui-foundation-v2`  
**Precedence authority:** `docs/CURRENT_BASELINE.md`, accepted ADRs (`docs/adr/`), Frozen Foundation Contract v0.1 (`docs/contracts/`).

---

## 1. Executive Summary & Product Purpose

`[DECISION]` Document Processing Foundation is a **governed enterprise document transformation platform**, not an autonomous AI chatbot and not an unconstrained in-browser document editor.

The pioneer business use case is **Vietnam Local File (Transfer Pricing) transformation and roll-forward**: taking prior-year local file templates and updating financial ratios, operating descriptions, intercompany transaction benchmarks, and entity metrics based strictly on authoritative current-year financial statements and transfer pricing rule packs.

The Foundation UI serves as the **governed professional workbench** where users:
1. Intake and inspect complex Office and PDF document binaries.
2. Verify that sufficient authoritative source evidence exists before any transformation is attempted.
3. Review proposed changes with side-by-side evidentiary proof and deterministic policy checks.
4. Issue legally binding, auditable approval decisions.
5. Monitor controlled native execution and inspect independent post-execution validation reports.
6. Directly interact with document regions to extract derived data artifacts (tables to CSV/XLSX, images, text) without mutating the source document.

---

## 2. User Personas

### 2.1 Primary Persona: Team Member / Associate (Preparer)
- **Profile:** Junior to mid-level professional in corporate tax, transfer pricing, or accounting.
- **Key Responsibilities:**
  - Prepares working papers and collates source documentation.
  - Extracts current-year financial and narrative information from audited reports.
  - Updates narratives, transaction benchmarks, and financial tables in the draft document.
  - Resolves working-level exceptions and evidentiary gaps.
  - Prepares the complete First Draft for supervisory review.
- **Primary UX Objective:** Reduce repetitive document preparation effort while making exceptions, evidence, and proposed changes easy to understand, navigate, and resolve.

### 2.2 Secondary Persona: Senior in Charge / Reviewer (Reviewer)
- **Profile:** Experienced senior specialist supervising document transformations.
- **Key Responsibilities:**
  - Reviews working-level output prepared by the Associate.
  - Verifies business logic, policy adherence, and source evidence.
  - Resolves higher-risk exceptions and material discrepancy flags.
  - Consolidates review feedback and may submit `ReviewDecision` actions where authorized by the governing backend policy.
- **Primary UX Objective:** High-density review surfaces, rapid side-by-side evidence inspection, deterministic verification states, and clear blocker remediation paths.

### 2.3 Tertiary Persona: Manager / Partner (Business Sign-Off Role)
- **Profile:** Senior practice leader accountable for client delivery and compliance sign-off.
- **Key Responsibilities:**
  - High-level quality, risk, and regulatory sign-off.
  - Verifies audit completeness and independent validation pass rates.
  - Limited interaction with detailed document editing or line-by-line mechanics.
- **Primary UX Objective:** Executive summary of validation results, release status gates, and immutable audit certificate package.

### 2.4 Operational / Future Persona: Platform Administrator / Systems Engineer
- **Profile:** Technical operator configuring RulePacks, inspecting parser outputs, or monitoring infrastructure.
- **Scope Note:** Documented strictly as a future operational persona, **NOT** as a primary or secondary pioneer workflow persona.

---

## 3. Core User Journeys

### Journey A: Start Local File Workflow & Understand Missing/Blocked Source
1. **User Action:** Associate navigates to Workspace and selects "Start VN Local File Transformation".
2. **System State (`CREATED` / `INTAKE`):** The workspace loads in Intake emphasis. FileRail prompts for required document roles:
   - Target Template: `VN_Local_File_2024_Template.docx`
   - Current Source: `Audited_Financial_Statements_2025.pdf`
   - Historical Source: `VN_Local_File_2024_Final.docx`
3. **User Action:** Associate uploads the 2024 template and historical local file, but omits the 2025 audited financial statement.
4. **Governed Response (`BLOCKED`):** 
   - Backend evaluates `SourceAssessment` -> outcome: `MISSING`.
   - The Source Readiness panel highlights a red shield blocker: *"Mandatory Source Missing: Audited Financial Statement FY2025"*.
   - Target financial fields in the document viewer are tagged `BLOCKED`.
   - "Start Review" CTA is disabled with clear explanation.
5. **Resolution:** Associate uploads the missing PDF. The backend runs preflight and source assessment, transitioning the task to `ANALYZING` and then `AWAITING_REVIEW`.

---

### Journey B: Inspect Evidence & Understand Verification State
1. **User Action:** In `AWAITING_REVIEW`, the Associate clicks on paragraph 4.2 in the target document, displaying: *"In 2025, the Company achieved a Net Cost Plus (NCP) margin of 9.45%."*
2. **System Presentation:**
   - The Contextual Inspector displays the business target: `VN_LOCAL_FILE.FINANCIAL.NCP`.
   - Verification status: `VERIFIED` (green border, shield icon).
   - Side-by-side Evidence Card shows:
     - Target: `9.45%`
     - Authoritative Source: `Audited_Financial_Statements_2025.pdf`, Page 14, Table 3 ("Operating Results").
     - Evaluator: `eval_financial_ratio_deterministic_v1` (Evaluated formula: `Operating Profit / Total Operating Costs`).
     - Freshness: `PASS` (as of 2026-03-31).
3. **User Action:** Associate clicks "Technical Trace" to inspect underlying identities:
   - `BusinessTargetID`: `VN_LOCAL_FILE.FINANCIAL.NCP`
   - `SemanticReference`: `#/tables/2/rows/4/cells/1`
   - `NativeLocator`: `DOCX_CONTENT_CONTROL` (SDT ID: `8775518`)
   - Complete factual backing is established deterministically.

---

### Journey C: Review Proposed Change (Approve, Reject, Defer, Request Source)
1. **Context:** A proposed change updates the entity director name from "Nguyen Van A" to "Tran Thi B".
2. **Presentation:** Senior in Charge opens the Review panel displaying `ChangeProposal` #104 in `IN_REVIEW`.
   - Current Text: *"Nguyen Van A"*
   - Proposed Text: *"Tran Thi B"*
   - Evidence Source: `Business_Registration_Certificate_Amend_5.pdf`, Page 1.
3. **Affordances:** Four distinct action buttons:
   - `[APPROVE]`: Approves change; records reviewer timestamp; queues for `ApprovedChangeSet`.
   - `[REJECT]`: Rejects proposal; retains original text; records mandatory rejection note.
   - `[DEFER]`: Defers decision for later inspection; proposal remains `IN_REVIEW`.
   - `[REQUEST_MORE_SOURCE]`: Opens modal prompting for missing document requirements; moves proposal to `BLOCKED`.
4. **Governed Rule:** The reviewer cannot click "Approve All" if any proposal is in `BLOCKED` status.

---

### Journey D: Select Complete Table & Extract to CSV / XLSX
1. **User Action:** Associate drags a selection box over Table 4 ("Intercompany Transaction Benchmark Summary") in the DOCX viewer.
2. **System State (`SELECTION_READY`):**
   - The UI evaluates intersected DOM cells and queries semantic perception.
   - Semantic Snapping prompt activates when the selection substantially overlaps the table:
     *"Table detected (5 columns × 12 rows). Snap to complete table?"*  
     *(Snapping threshold is TBD / REQUIRES UX AND CORPUS VALIDATION).*
   - Associate clicks `[Use Full Table]`.
3. **Selection Inspector Displays:**
   - Detected: `1 Structured Table (60 cells)`.
   - Actions: `[Extract to CSV]`, `[Extract to XLSX]`, `[Propose Change]`.
4. **User Action:** Associate clicks `[Extract to CSV]`.
5. **System Execution:** A derived export task generates RFC 4180 compliant CSV. The browser triggers file download: `VN_Local_File_Table_4.csv`.
6. **Governance Rule:** Source document is untouched; no `ApprovedChangeSet` or mutation review required. An immutable `AuditEvent` (`SELECTION_EXTRACTED`) is appended.

---

### Journey E: Select Mixed DOCX Region & Extract Components Separately
1. **User Action:** Associate drags a selection box enclosing an introductory heading, two explanatory paragraphs, a financial summary table, and a market share chart image.
2. **Selection Inspector Displays:**
   - Detected: `2 Paragraphs`, `1 Structured Table`, `1 Embedded Image`.
   - Actions:
     - `[Extract Text Only (Markdown)]`
     - `[Extract Table Only (XLSX)]`
     - `[Extract Image Only (PNG)]`
     - `[Extract Components Separately (ZIP)]`
     - `[Extract Region as Structured DOCX]`
3. **User Action:** Associate clicks `[Extract Components Separately (ZIP)]`.
4. **Result:** Browser downloads `extracted_components.zip` containing:
   - `text_content.md`
   - `table_financial_summary.xlsx`
   - `chart_market_share.png`
   - `manifest.json` (selection provenance and hashes).

---

### Journey F: Select Region & Propose Change (No Direct Mutation)
1. **User Action:** In the Document Viewer, Associate highlights paragraph 1.3: *"The company operates under a limited risk distribution model."*
2. **Governed Boundary (`Selection != ChangeProposal`):** Highlighting the region does NOT automatically create a proposal. The contextual palette appears offering: `Inspect`, `Extract`, `Ask AI`, and `Propose Change`.
3. **User Action:** Associate clicks `[Propose Change]`.
4. **System Flow:**
   - An inline editor modal opens pre-filled with the current text.
   - Associate enters: *"The company operates under a fully-fledged manufacturer and distributor model."*
   - Associate selects required evidence reference: `Intercompany_Agreement_2025.pdf`.
   - Associate clicks `[Submit Proposal]`.
5. **Governance Rule:** The document on screen does NOT mutate immediately. A new `ChangeProposal` is created with status `DRAFT`, entering the governed Review queue.

---

### Journey G: Native-Fidelity Extraction Unsupported (Fail Closed With Explanation)
1. **User Action:** Associate selects a complex formatted region containing advanced Word drawing canvas shapes and SmartArt, then clicks `[Extract Native-Fidelity DOCX]`.
2. **System Evaluation:**
   - Preflight assessment indicates: `OpenXmlSdk 3.5.1` candidate engine does not qualify drawing canvas isolation for this document revision; status evaluates to `UNSUPPORTED`.
3. **UI Presentation:**
   - The UI **fails closed**. It does NOT attempt a broken native export.
   - An informative alert appears:
     > *"Native-Fidelity Export Unavailable: This document section contains advanced Word DrawingML canvas objects that cannot be isolated with guaranteed fidelity."*
   - Remediation Options provided:
     - `[Extract as Structured DOCX]` (Converts text and tables, exports shapes as raster images).
     - `[Extract Text Only]`
     - `[Cancel]`
4. **Result:** Associate clicks `[Extract as Structured DOCX]` and receives a clean, functional document without silent package corruption.

---

## 4. Workspace Mental Model & Layout System

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TOP SHELL: Logo | [⚠️ SIMULATED BACKEND] | Task: VN Local File 2025 (AWAITING_REVIEW) | Preparer: Alex │
├───────────┬───────────────────────────────────────────────┬────────────────────────────────────────────┤
│ FILE RAIL │ CENTRAL DOCUMENT VIEWER                       │ CONTEXTUAL WORK INSPECTOR                  │
│ (200px /  │ (Flexible 50% - 60% width)                    │ (Flexible 40% - 50% width)                 │
│  48px)    │                                               │                                            │
│           │ [Toolbar: Zoom 100% | Split View | Fit Width] │ [Tabs: Evidence | Exceptions | Trace]     │
│ [+] Add   │ ───────────────────────────────────────────── │ ────────────────────────────────────────── │
│           │                                               │ BUSINESS TARGET: NCP MARGIN                │
│ • Target  │ 4.2 Financial Performance Summary             │ Status: [VERIFIED]                         │
│   DOCX    │                                               │ Target Value: 9.45%                        │
│   (Ready) │ In 2025, the Company achieved a Net Cost Plus │ Prior Value:  8.12%                        │
│           │ (NCP) margin of 9.45% on its manufacturing    │                                            │
│ • Source  │ operations...                                 │ Authoritative Source:                      │
│   PDF     │                                               │ Audited Financials 2025 (Page 14, Table 3) │
│   (Ready) │ ┌───────────────────────────────────────────┐ │ Excerpt: "Operating profit: 18.9B VND..." │
│           │ │ Table 4: Benchmark Comparison             │ │                                            │
│ • Hist.   │ │ Upper Quartile: 11.2%                     │ │ Evaluator: eval_ratio_deterministic_v1   │
│   DOCX    │ │ Median:          9.1%                     │ │                                            │
│   (Ready) │ │ Lower Quartile:  6.4%                     │ │ Actions:                                 │
│           │ └───────────────────────────────────────────┘ │ [APPROVE]  [REJECT]  [DEFER]  [REQ SOURCE] │
│           │                                               │ ────────────────────────────────────────── │
│           │                                               │ Technical Trace:                           │
│           │                                               │ TargetID: VN_LOCAL_FILE.FINANCIAL.NCP      │
│           │                                               │ Locator:  DOCX_SDT (ID: 8775518)           │
├───────────┴───────────────────────────────────────────────┴────────────────────────────────────────────┤
│ AUXILIARY TRAY (Collapsible): Agent Assistance [Open] | Audit Timeline [Open] | Diagnostics [Open]     │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Governed Workspace State Transitions

The workspace layout shifts focus according to authoritative backend `TaskStatus`:

| TaskStatus | Layout Configuration | Dominant User Controls | Guard to Progress |
|---|---|---|---|
| `CREATED` | FileRail expanded, central intake dropzone active. | "Upload Document", "Assign Role", "Run Preflight". | All mandatory roles assigned (`TARGET`, `SOURCE`). |
| `ANALYZING` | Central viewer shows document outline with loading spinners. | "Cancel Analysis", view preflight log. | Backend preflight & perception complete. |
| `AWAITING_REVIEW` | Document viewer active with highlighted targets; Review Inspector active. | "Approve", "Reject", "Defer", "Request Source". | All proposals have explicit `ReviewDecision`. |
| `READY_FOR_EXECUTION`| Split-view: Proposed changes diff against original target. | "Inspect Approved ChangeSet", "Seal & Execute". | Backend verifies zero pending blockers and valid hashes. |
| `EXECUTING` | Central viewer locked; real-time execution attempt monitor. | "Cancel Dispatch" (if queued). | Controlled Replay stages output. |
| `VALIDATING` | Side-by-side comparison: Staged output vs. input. | "Inspect Validation Checks", "View Diff". | Independent validator produces `ValidationReport`. |
| `COMPLETED` | Validated output rendered; release certificate badge active. | "Download Validated Output", "Export Audit Package". | Task `ReleaseStatus` == `RELEASED`. |
| `BLOCKED` | Viewer dims non-blocked sections; Exception panel spotlights blockers. | "Inspect Blocker", "Upload Remediation", "Re-evaluate". | Remediation satisfies failing deterministic checks. |
| `FAILED` | Viewer displays failure diagnostic; technical trace open. | "Download Diagnostic Log", "Retry", "Quarantine". | Technical root cause diagnosed. |

---

## 6. Document Region Selection & Extraction Flow

```text
Step 1: User Marquee Drag
- User clicks and drags across document viewer.
- Client captures transient `SelectionGeometry` (viewport x, y, width, height).

Step 2: Candidate Resolution & Semantic Snapping
- Client identifies rendered DOM elements within selection bounds.
- When selection substantially overlaps a structured object (e.g., table), the UI offers semantic snapping.
  (Threshold parameter is TBD / REQUIRES UX AND CORPUS VALIDATION).
- User chooses to use full object or keep current selection bounds.

Step 3: Semantic Resolution
- Client dispatches candidate element IDs to `/api/selection/resolve` (Simulated in U0).
- Response returns `ResolvedSelection` with typed document objects and available export capabilities.

Step 4: Selection Inspector Presentation
- Contextual pane opens displaying detected counts: paragraphs, tables, images.
- Buttons are capability-gated: if candidate engine cannot do native DOCX, that button explains why.
- User selects action: [Inspect] | [Extract] | [Ask AI] | [Propose Change].

Step 5: Export Execution (If Extract Chosen)
- User selects export format (e.g., Table -> CSV).
- Client submits `ExtractionPlan`.
- Derived artifact generated, hash logged to `AuditEvent`, file downloaded.
```

---

## 7. Auxiliary Agent Assistance Protocol

`[DECISION]` To prevent uncontrolled AI mutation, the Agent / Chat panel operates under strict behavioral constraints:

```text
                              ┌────────────────────┐
                              │  User Prompts AI   │
                              └─────────┬──────────┘
                                        ▼
                              ┌────────────────────┐
                              │ Bounded AI Assist  │
                              │ (Reads context)    │
                              └─────────┬──────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
┌─────────────────────────┐                               ┌─────────────────┐
│ Explains / Summarizes   │                               │ Drafts Proposal │
│ (Read-only text output) │                               └────────┬────────┘
└─────────────────────────┘                                        │
                                                                   ▼
                                                          ┌─────────────────┐
                                                          │ ChangeProposal  │
                                                          │ (Status: DRAFT) │
                                                          └────────┬────────┘
                                                                   │
                                                                   ▼
                                                          ┌─────────────────┐
                                                          │ Governed Review │
                                                          │ (Human APPROVE) │
                                                          └─────────────────┘
```

**Forbidden Agent Actions:**
1. Agent cannot execute document writeback.
2. Agent cannot emit `ApprovedChangeSet`.
3. Agent cannot approve its own proposal.
4. Agent cannot dismiss or override a `SourceSufficiencyOutcome` blocker.

---

## 8. Frontend Engineering Architecture: U0 & Future Phases

### 8.1 Workstream U0 Breakdown: Governed Frontend Foundation
- **U0.1 Contract Projection Architecture:** Setup automated type generation from `docs/contracts/foundation.openapi.yaml`. Implement adapter layers for task, evidence, and preflight projections.
- **U0.2 UI State Architecture:** Implement segregated state stores (Task Store, Presentation Store, Selection Store) enforcing `INV-UI-04` (no frontend business transitions).
- **U0.3 Legacy Authority Shutdown Plan:** Deprecate direct in-place editing (`EditableText`), disconnect `GptsMappingAction`, remove generic confidence badges, and redirect actions to `Propose Change`.
- **U0.4 Governed Workspace Shell:** Build task-state-driven layout shell with collapsible FileRail, Document Viewer, Contextual Inspector, and Technical Trace drawer.
- **U0.5 Typed Simulated Scenarios:** Create deterministic mock scenarios (Perfect Verification, Missing Source, Conflicting Source, Strict OOXML Unsupported). Implement Selection Inspector with client-side table/text extraction primitives.
- **U0.6 UI Test Foundation:** Automated Playwright test suite verifying state projections, keyboard navigation, selection snapping, and fail-closed behaviors across desktop viewports.

### 8.2 Proposed Future UI Phases Sequence
- **U0 — Governed Workspace Foundation:** (Current workstream: shell, typed contracts, selection primitives, mock scenarios).
- **U1 — Intake + Preflight + Source Readiness:** Live integration with B0/B1 upload, hash verification, OOXML preflight, and source readiness evaluation.
- **U2 — Evidence + Exception Resolution:** Live integration with deterministic evaluators, evidence excerpt rendering, and blocker resolution flows.
- **U3 — Change Proposal + Human Review:** Live integration with proposal review queue, side-by-side diffs, and explicit review decision submissions.
- **U4 — Approved Change + Execution Monitoring:** Live integration with sealed ApprovedChangeSet inspection and controlled replay execution monitoring.
- **U5 — Validation + Audit + Release:** Live integration with independent post-execution validation reporting, audit timeline inspection, and release downloading.
- **U6 — Integrated Local File UX:** Full end-to-end production hardening of the complete Vietnam Local File transformation pioneer workflow.

---

## 9. Testable Acceptance Criteria

### Criteria 1: Task-State Workspace Driving
- When `TaskStatus` is `CREATED`, FileRail intake is expanded and document dropzone is prominent.
- When `TaskStatus` is `AWAITING_REVIEW`, review inspector is active and interactive targets are highlighted.
- When `TaskStatus` is `BLOCKED`, the blocking exception is prominently displayed with remediation steps; execution CTAs are disabled.

### Criteria 2: Zero Direct Mutation
- Clicking any document element (paragraph, cell) never triggers an immediate `PATCH` to the source document.
- Selecting a document region does NOT automatically create a change proposal.
- Submitting an explicit edit proposal produces a `ChangeProposal` with status `DRAFT`.

### Criteria 3: Progressive Disclosure & Identity Separation
- Default view displays business field names, source citations, and verification status.
- Technical Trace drawer opens on demand, revealing distinct `BusinessTargetID`, `SemanticReference`, and `NativeLocator`.
- Under no circumstance do these three identities conflate.

### Criteria 4: Region Selection & Extraction
- Dragging a selection box over a table triggers the Selection Inspector.
- Clicking `[Extract to CSV]` downloads a clean, valid CSV file containing table cell text without modifying the source document.
- Semantic snapping prompt appears when selection substantially overlaps a structured object (threshold TBD / REQUIRES UX AND CORPUS VALIDATION).

### Criteria 5: Capability-Gated Fail-Closed Behavior
- If preflight marks an object `PROTECTED` or `UNSUPPORTED`, mutation actions are disabled with clear plain-language explanations.
- Native-fidelity export is disabled if replay engine qualification is open, offering structured export as an explicit fallback.

### Criteria 6: Mock Transparency
- When connected to mock fixtures, the persistent `SIMULATED BACKEND` banner is visible in the top shell header.
