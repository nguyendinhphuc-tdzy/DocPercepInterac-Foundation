# Foundation UI State Model

**Document status:** U0 BASELINE — ACCEPTED (Product/BA review passed 2026-09-09)  
**Date:** 2026-09-09  
**Workstream:** Frontend U0 — Governed Workspace Foundation  
**Branch:** `build/ui-foundation-v2`  
**Precedence authority:** `docs/CURRENT_BASELINE.md`, accepted ADRs (`docs/adr/`), Frozen Foundation Contract v0.1 (`docs/contracts/status-model.md`, `domain-model.md`).

---

## 1. Executive Summary & Epistemic Taxonomy

State management in the Foundation frontend must maintain an uncompromised separation between authoritative backend governance and transient client-side presentation. 

**The Golden Rule of Foundation UI State:**  
`Frontend MUST NOT own or compute legal business-state transitions.`

The frontend never decides whether an approval is permitted, whether source evidence is sufficient, or whether a task is ready to execute. The backend is the single source of truth; the frontend merely projects server state and renders actions explicitly authorized by backend responses.

Assertions in this document use the standard taxonomy:
- `[FACT]`: Defined in Frozen Contract v0.1 (`status-model.md`, `foundation.openapi.yaml`).
- `[DECISION]`: Approved architectural boundary or product decision.
- `[INFERENCE]`: Structural deduction regarding state segregation.
- `[RECOMMENDATION]`: Implementation design for Zustand stores and hooks.

---

## 2. Segregation of Five State Dimensions

To eliminate state confusion, the frontend categorizes all application state into five strictly separated dimensions:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ A. BACKEND BUSINESS STATE                                                   │
│ Server-owned, immutable snapshots, append-only event projections.           │
│ (TaskStatus, DocumentStatus, ChangeProposalStatus, ApprovedChangeSet, etc.)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Read-only API projection
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ B. SERVER DATA / TRANSPORT STATE                                            │
│ Network lifecycle of cached backend responses (React Query / SWR model).    │
│ (fetchStatus, error, isStale, lastUpdated, etag, revalidating)               │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┴──────────────────────────────────────┐
│ C. FRONTEND PRESENTATION STATE                                              │
│ Transient user workspace chrome, layout configurations, and viewport toggles.│
│ (activeDocId, splitViewRatio, zoomLevel, isFileRailCollapsed, activeTab)    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┴──────────────────────────────────────┐
│ D. SELECTION & EXTRACTION APPLICATION STATE                                 │
│ Transient in-memory state managing document region dragging and export UX.  │
│ (IDLE, SELECTING, RESOLVING, SELECTION_READY, EXTRACTION_CONFIGURING, etc.)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┴──────────────────────────────────────┐
│ E. MOCK & ENVIRONMENT STATE                                                 │
│ Global indicator declaring whether the UI is backed by live or mock services│
│ (isSimulatedBackend, mockScenarioId, simulatedLatencyMs)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Dimension A: Backend Business State (Server-Owned)

`[FACT]` The backend maintains exhaustive, closed state machines defined in `docs/contracts/status-model.md`. The frontend treats these as read-only server projections.

### 3.1 Governed Lifecycle Enums (Frozen Contract v0.1)

| Domain Object | Frozen Enum Name | Allowed Closed Values | Frontend Role |
|---|---|---|---|
| **Foundation Task** | `TaskStatus` | `CREATED`, `ANALYZING`, `AWAITING_REVIEW`, `READY_FOR_EXECUTION`, `EXECUTING`, `VALIDATING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELLED` | Drives workspace layout emphasis and overall progress banner. |
| **Document Version** | `DocumentStatus` | `REGISTERED`, `PREFLIGHTING`, `READY`, `BLOCKED`, `REJECTED`, `SUPERSEDED`, `STAGED`, `RELEASED`, `QUARANTINED` | Controls document viewer status badges and intake availability. |
| **Preflight Assessment** | `DocumentPreflightStatus` | `PENDING`, `ASSESSING`, `COMPLETED`, `FAILED`, `SUPERSEDED` | Shows capability detection progress; completed does NOT mean supported. |
| **Source Assessment** | `SourceAssessmentStatus` | `PENDING`, `ASSESSING`, `COMPLETED`, `SUPERSEDED`, `FAILED` | Reflects deterministic evaluation run progress. |
| **Source Verdict** | `SourceSufficiencyOutcome` | `SUFFICIENT`, `MISSING`, `STALE`, `CONFLICTING`, `NOT_AUTHORITATIVE`, `AMBIGUOUS` | Renders business sufficiency chips and blocker explanations. |
| **Change Proposal** | `ChangeProposalStatus` | `DRAFT`, `BLOCKED`, `READY_FOR_REVIEW`, `IN_REVIEW`, `APPROVED`, `REJECTED`, `SUPERSEDED` | Renders individual proposal cards in the Review panel. |
| **Approved ChangeSet**| `ApprovedChangeSetStatus`| `APPROVED`, `INVALIDATED`, `REVOKED`, `SUPERSEDED` | Renders sealed authorization manifest in Execution view. |
| **Controlled Replay** | `ExecutionStatus` | `QUEUED`, `PREFLIGHTING`, `RUNNING`, `SUCCEEDED`, `REFUSED`, `FAILED`, `CANCELLED` | Renders execution attempt monitor and logs. |
| **Validation Report** | `ValidationStatus` | `PENDING`, `RUNNING`, `PASSED`, `FAILED`, `INCONCLUSIVE`, `CANCELLED` | Displays check-by-check invariant results. |
| **Document Release**  | `ReleaseStatus` | `WITHHELD`, `ELIGIBLE`, `RELEASED` | Controls final export and release download buttons. |
| **Exception Case**    | `ExceptionStatus` | `OPEN`, `ACKNOWLEDGED`, `REMEDIATION_PENDING`, `RESOLVED`, `CLOSED` | Displays active blockers and remediation steps. |
| **Target Verification**| `TargetVerificationStatus`| `UNVERIFIED`, `VERIFIED`, `BLOCKED`, `STALE` | Highlights target values in document viewer. |

### 3.2 Strict Prohibition: No Frontend Business State Machine
`[DECISION]` The frontend must NEVER maintain an authoritative allowed-transitions table or decide if a business action is valid.

**Incorrect Anti-Pattern:**
```typescript
// VIOLATION of architectural boundary:
if (task.status === 'AWAITING_REVIEW') {
  enableButton('Approve & Execute'); // FORBIDDEN: Frontend assumes authority
}
```

**Correct Governed Pattern:**
```typescript
// Conforming governed projection:
// The backend response provides allowed operations or capability flags:
const isApprovePermitted = task.capabilities?.can_submit_review_decision ?? false;
const blockers = task.blocking_exceptions ?? [];

<Button 
  disabled={!isApprovePermitted || blockers.length > 0}
  onClick={() => submitReviewDecision({ outcome: 'APPROVE' })}
>
  Submit Approval
</Button>
```

---

## 4. Dimension B: Server Data & Transport State

`[INFERENCE]` Represents the asynchronous network lifecycle of querying and mutating backend data:
- `idle`: Query has not been initiated.
- `loading`: First-time network request in flight; render skeleton placeholders.
- `revalidating`: Background polling or event stream refresh in progress; keep current UI interactive.
- `success`: Authoritative server response received and cached.
- `error`: Network timeout, 5xx server failure, or 4xx client contract error.
- `stale`: Server data version or ETag no longer guaranteed fresh; UI prompts or background refreshes.

**Optimistic Updates Policy:**  
Optimistic UI updates are **prohibited** for all governed business mutations (approving proposals, submitting change sets, executing transforms). The UI displays a pending spinner until the backend commits the event and returns an updated snapshot.

---

## 5. Dimension C: Frontend Presentation State

`[DECISION]` Ephemeral user interface configuration stored strictly in local client state (e.g., Zustand or React Context). This state is wiped on session reset and never saved as business truth.

| Presentation State Key | Type | Default | Purpose |
|---|---|---|---|
| `activeDocumentId` | `string \| null` | `null` | Currently focused document in the multi-file workspace. |
| `viewportZoom` | `number` (float) | `1.0` (100%) | Zoom scale (0.75, 1.0, 1.25, 1.5, Fit Width). |
| `isFileRailCollapsed`| `boolean` | `false` | Collapses document list to a 48px icon rail for narrow screens. |
| `isTechnicalTraceOpen`| `boolean` | `false` | Toggles the deep forensic details drawer for reviewers/auditors. |
| `activeInspectorTab` | `enum` | `'evidence'` | Contextual inspector tab: `'evidence'`, `'exceptions'`, `'selection'`, `'trace'`. |
| `splitViewConfig` | `SplitViewConfig` | Same-Doc Split | Left/Right pane document and representation assignments (`Original` vs `Elements`). |
| `neutralDeselectTrigger`| `number` (timestamp)| `0` | Signals canvas click or `Escape` key to clear active highlights. |

---

## 6. Dimension D: Selection & Extraction Application State

`[DECISION]` Region selection and derived extraction are client-side interactive flows that operate without mutating the source document.

### 6.1 Selection Lifecycle State Machine (Client Application Only)

`[DECISION]` Selection of document content provides inspection, extraction, and drafting options, but carries zero mutation authority. Direct manipulation does NOT automatically create a proposal.
```text
Selection != ChangeProposal != ApprovedChangeSet
Extract != Propose Change
Extract != Mutation
```

```text
              ┌──────────────┐
              │     IDLE     │◄───────────────────────────────────┐
              └──────┬───────┘                                    │
                     │ User mousedowns & drags                    │
                     ▼                                            │
              ┌──────────────┐                                    │ User hits Escape /
              │  SELECTING   │                                    │ clicks neutral canvas
              └──────┬───────┘                                    │
                     │ User mouseups                              │
                     ▼                                            │
         ┌───────────────────────┐                                │
         │  RESOLVING_SELECTION  │                                │
         └───────────┬───────────┘                                │
                     │ Intersected elements & semantic resolution │
         ┌───────────┴───────────┬────────────────────────────────┤
         ▼                       ▼                                ▼
┌─────────────────┐    ┌────────────────────┐            ┌──────────────────────┐
│ SELECTION_READY │    │ SELECTION_AMBIGUOUS│            │SELECTION_UNSUPPORTED │
└────────┬────────┘    └────────┬───────────┘            └──────────┬───────────┘
         │                      │ User picks disambiguation         │
         │                      └───────────┬───────────────────────┘
         │                                  ▼
         │ Choices: [Inspect] | [Extract] | [Ask AI] | [Propose Change]
         ├─────────────────────────────────────────┐
         │ User clicks "Extract"                   │ User clicks "Propose Change"
         ▼                                         ▼
┌─────────────────────────┐               ┌─────────────────────────────────┐
│  EXTRACTION_CONFIGURING │               │  PROPOSAL INTENT MODAL          │
└────────┬────────────────┘               │  (Drafts ChangeProposal)        │
         │ User clicks "Export"           └────────────────┬────────────────┘
         ▼                                                 │ Submits proposal
┌─────────────────────────┐                                ▼
│       EXTRACTING        │ (Derived background task)     ┌─────────────────────────────────┐
└────────┬───────────────┬┘                               │ ChangeProposal (Status: DRAFT)  │
         │               │ Technical error                │ (Enters Governed Review Queue)  │
         ▼               ▼                                └─────────────────────────────────┘
┌─────────────────┐    ┌────────────────────┐
│  EXPORT_READY   │    │   EXPORT_FAILED    │
└─────────────────┘    └────────────────────┘
```

### 6.2 Selection Lifecycle States Defined
1. `IDLE`: No active marquee, range, or bounding box selection.
2. `SELECTING`: User is currently dragging across the viewer canvas. Transient screen geometry updates in real-time.
3. `RESOLVING_SELECTION`: Mouse released. The UI evaluates intersected elements and queries semantic representation.
4. `SELECTION_READY`: Object boundaries resolved into discrete document objects (paragraphs, tables, images). Selection Inspector displays detected counts and available actions (`Inspect`, `Extract`, `Ask AI`, `Propose Change`).
5. `SELECTION_AMBIGUOUS`: Selection overlaps partial cells or ambiguous container bounds. UI prompts user for resolution (e.g., semantic snapping prompt: "Table detected. Snap to complete table?"). *Threshold parameter is TBD / REQUIRES UX AND CORPUS VALIDATION.*
6. `SELECTION_UNSUPPORTED`: Selection contains elements that cannot be extracted or addressed (e.g., protected shapes, unsupported OLE objects). UI explains limitations.
7. `EXTRACTION_CONFIGURING`: User has chosen an extraction target and is selecting format parameters (e.g., table to CSV delimiter, structured vs. native DOCX).
8. `EXTRACTING`: Export service or worker is generating the derived read-only file artifact.
9. `EXPORT_READY`: Artifact generated and verified; download link or preview rendered.
10. `EXPORT_FAILED`: Extraction failed; failure explanation displayed with retry affordance.

### 6.3 Non-Contract UI Application DTOs
These data structures exist purely within the frontend application layer to manage selection ergonomics. **They are NOT additions to Frozen Contract v0.1.**

```typescript
// Proposed UI Application DTOs (Client / Application Scope Only)

export interface SelectionIntent {
  documentVersionRef: string; // Exact SHA-256 bound DocumentVersion
  surfaceFormat: 'DOCX' | 'XLSX' | 'PDF';
  geometry?: {
    pageNumber?: number;
    bbox?: { x: number; y: number; width: number; height: number };
  };
  cellRange?: {
    sheetName: string;
    startCell: string;
    endCell: string;
  };
  domElementIds?: string[];
}

export interface ResolvedSelectionItem {
  semanticReference: string;
  objectType: 'PARAGRAPH' | 'TABLE' | 'TABLE_CELL' | 'IMAGE' | 'DRAWING';
  summaryText?: string;
  isProtected: boolean;
  supportedExportFormats: ('CSV' | 'XLSX' | 'DOCX_STRUCTURED' | 'DOCX_NATIVE' | 'IMAGE_PNG')[];
}

export interface ResolvedSelection {
  documentVersionRef: string;
  status: 'RESOLVED' | 'AMBIGUOUS' | 'UNSUPPORTED';
  items: ResolvedSelectionItem[];
  ambiguityReason?: string;
  suggestedSnap?: {
    label: string;
    snappedItems: ResolvedSelectionItem[];
  };
}

export interface ExtractionPlan {
  documentVersionRef: string;
  selectedItems: ResolvedSelectionItem[];
  requestedFormat: 'CSV' | 'XLSX' | 'DOCX_STRUCTURED' | 'DOCX_NATIVE' | 'IMAGE_PNG';
  preservationLevel: 'STRUCTURED_ONLY' | 'NATIVE_FIDELITY';
}
```

---

## 7. Dimension E: Mock & Environment State

`[DECISION]` Because backend capabilities are implemented in phased workstreams (B0, B1, etc.), the frontend must support deterministic simulated mock fixtures without pretending to be live production data.

### 7.1 Environment Modes
- `LIVE_BACKEND`: Connected to authoritative Foundation v2 Python backend APIs.
- `SIMULATED_BACKEND`: Running against typed local fixtures conforming to Frozen Contract v0.1.

### 7.2 UI Requirements for Mock State
1. **Global Banner:** A permanent, high-contrast banner in the top shell header:
   ```text
   [⚠️ SIMULATED BACKEND — Development Mode]
   ```
2. **Deterministic Scenarios:** Pre-configured mock scenarios representing realistic governance situations:
   - Scenario A: *VN Local File — Perfect Verification (All Verified)*
   - Scenario B: *VN Local File — Blocked (Missing 2025 Audited Financial Statement)*
   - Scenario C: *VN Local File — Conflicting Source (Intercompany Loan Interest Discrepancy)*
   - Scenario D: *Document Preflight — Strict OOXML Unsupported*
3. **No Hidden Simulation:** The UI must never masquerade simulated responses as verified cryptographic hashes or genuine audit records.

---

## 8. Common UI Presentation States Matrix

Every component across the Foundation workbench must handle all six universal presentation states cleanly:

| State | Visual Treatment | Allowed User Actions | Prohibited Behavior |
|---|---|---|---|
| **`empty`** | Informative icon, title, description, and primary CTA. | Click CTA (e.g., "Add Document", "Start Preflight"). | Showing blank white canvas or broken layout. |
| **`loading`** | Pulsing skeleton loaders preserving final layout geometry. | Cancel request (if long-running). | Blocking browser main thread or shifting content. |
| **`error`** | Warning border, clear plain-language error message, retry button. | "Retry", "View Error Details", "Report". | Displaying raw stack trace or opaque HTTP status codes. |
| **`stale`** | Subtle amber outline, timestamp indicator ("Updated 5m ago · Rechecking"). | "Refresh Now", read current cached values. | Allowing user to approve stale change proposals. |
| **`partial`** | Progress bar, partial elements count badge ("848 / 2,832 perceived"). | Inspect perceived elements; zoom and read original. | Hiding entire document because perception is partial. |
| **`blocked`** | Red/Amber shield icon, list of failing evidence checks, remediation prompt. | "Inspect Exceptions", "Upload Missing Document". | Allowing user to click "Execute" or "Bypass". |
