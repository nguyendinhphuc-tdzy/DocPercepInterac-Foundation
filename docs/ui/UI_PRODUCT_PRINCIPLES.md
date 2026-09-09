# Foundation UI Product Principles

**Document status:** U0 BASELINE — ACCEPTED (Product/BA review passed 2026-09-09)  
**Date:** 2026-09-09  
**Workstream:** Frontend U0 — Governed Workspace Foundation  
**Branch:** `build/ui-foundation-v2`  
**Precedence authority:** `docs/CURRENT_BASELINE.md`, accepted ADRs (`docs/adr/`), Frozen Foundation Contract v0.1 (`docs/contracts/`).

---

## 1. Executive Summary & Epistemic Taxonomy

The Document Processing Foundation frontend is a **governed professional document transformation workbench**, not an autonomous AI chat application and not a generic in-browser document editor.

Every user-visible element, workflow state, and affordance must reinforce architectural integrity, evidentiary transparency, and fail-closed governance.

To ensure clarity and precision across all product and engineering discussions, assertions in this document use the following epistemic tags:
- `[FACT]`: Backed by frozen contracts, accepted ADRs, or verified system code.
- `[DECISION]`: Formally approved architecture or product direction.
- `[INFERENCE]`: Logical deduction derived directly from facts and decisions.
- `[ASSUMPTION]`: Explicit premise requiring ongoing empirical or user validation.
- `[RECOMMENDATION]`: Proposed engineering or design guidance subject to architectural review.

---

## 2. Core Product Principles

### Principle 1: Governed Workflow Over Generic Document Editing
- **Classification:** `[DECISION]`
- **Principle:** The UI is structured around deterministic, governed lifecycle stages rather than unstructured, arbitrary in-place canvas editing.
- **Why It Matters:** Foundation's mission is proving that document transformations adhere strictly to authoritative business rules and evidence. Uncontrolled rich-text editing bypasses governance gates, evades target contract bindings, and destroys verifiable auditability.
- **Implication for UI:** The primary workspace adapts to the task's current lifecycle stage (Intake, Preflight, Review, Execution, Validation). The document viewer is an inspection and interaction surface, not a rich-text canvas with floating formatting ribbons.
- **Anti-Pattern:** Providing Word-like formatting toolbars (bold, italic, font pickers) or allowing unconstrained inline text modification directly to source files.

---

### Principle 2: Backend Is Authoritative
- **Classification:** `[FACT]` / `[DECISION]`
- **Principle:** The backend owns all document state, lifecycle state transitions, source sufficiency verdicts, locator bindings, and execution authority. The frontend is a faithful projection of server truth.
- **Why It Matters:** Frontend-computed business rules or locally derived permissions lead to state desynchronization, client-side vulnerabilities, and corrupted transformations.
- **Implication for UI:** The UI never computes whether a task is "ready to execute" or transitions a `FoundationTask` status locally. The UI renders available actions strictly according to permissions and capabilities returned by backend contracts.
- **Anti-Pattern:** Calculating source sufficiency in a Zustand store or enabling an "Approve" button based purely on a client-side enum check without backend capability authorization.

---

### Principle 3: Evidence Over Confidence
- **Classification:** `[DECISION]`
- **Principle:** Governed UI states are driven by deterministic verification checks and authoritative source evidence, never by generic model probabilities or heuristic confidence percentages.
- **Why It Matters:** A 98% AI confidence score provides zero legal or audit guarantee that a financial or transfer pricing figure is correct. Displaying percentages breeds misplaced user trust.
- **Implication for UI:** Target values and proposals display deterministic verification states (`VERIFIED`, `BLOCKED`, `STALE`, `UNVERIFIED`). If model assessment confidence is shown for an auxiliary AI suggestion, it must be explicitly labeled: `AI assessment confidence — NOT system verification`. Generic confidence percentages are prohibited.
- **Anti-Pattern:** Displaying a green badge reading `95% Confident` next to an unverified business target.

---

### Principle 4: Human Review Is Exception Resolution
- **Classification:** `[DECISION]`
- **Principle:** Human review exists to inspect evidence, resolve flagged ambiguities, and make explicit, binding business decisions—not to mechanically re-enter data or manually rubber-stamp hundreds of uncontested lines.
- **Why It Matters:** Professional reviewers suffer fatigue when overwhelmed by trivial noise. UI efficiency requires spotlighting material discrepancies, missing source documents, and policy violations.
- **Implication for UI:** The review interface groups items by exception severity and readiness. It presents side-by-side evidence excerpts (source vs. target), highlighting the exact policy rationale. Reviewers take structured actions: `APPROVE`, `REJECT`, `DEFER`, or `REQUEST_MORE_SOURCE`.
- **Anti-Pattern:** Forcing the user to click through every single paragraph of a 100-page document when 95% of sections are unchanged and verified.

---

### Principle 5: Progressive Disclosure
- **Classification:** `[DECISION]`
- **Principle:** Present business context first, reserving deep technical, forensic, and XML structures for on-demand inspection.
- **Why It Matters:** Ordinary tax, finance, and legal reviewers are overwhelmed by raw OpenXML paths, UUIDs, and Docling JSON references. Conversely, technical auditors and developers require immediate access to these exact forensic artifacts.
- **Implication for UI:** The default view exposes business meaning, section context, source excerpt, target value, and verification status. A collapsible "Technical Trace" drawer or inspector reveals `BusinessTargetID`, `SemanticReference`, `NativeLocator`, binary hashes, and evaluator keys.
- **Anti-Pattern:** Rendering raw JSON payloads, element UUID5 hashes, or XPath expressions directly in the main business review table.

---

### Principle 6: Business Meaning Before Technical Identity
- **Classification:** `[DECISION]`
- **Principle:** Never conflate or substitute `BusinessTargetID`, `SemanticReference`, and `NativeLocator`.
- **Why It Matters:** As established in ADR-002, a business target (e.g., `VN_LOCAL_FILE.FINANCIAL.NCP`) is version-stable. A semantic reference (e.g., `#/texts/137`) is perception-dependent. A native locator is bound strictly to an immutable binary hash. Conflating them breaks document replay and corrupts audits.
- **Implication for UI:** The UI clearly separates the logical business field label from the physical document object. When a user inspects a target, the UI shows what business rule requires it, which perceived excerpt supports it, and what native structure will receive it.
- **Anti-Pattern:** Labeling a UI input with a raw XML bookmark name or using a Docling reference as if it were a permanent database key.

---

### Principle 7: Fail Closed But Explain Clearly
- **Classification:** `[DECISION]`
- **Principle:** When data is stale, evidence is ambiguous, or operations are unsupported, the UI blocks progression and provides actionable, plain-language diagnostic explanations.
- **Why It Matters:** Silent degradation or speculative fallbacks in document processing lead to catastrophic business errors. However, unexplained blocking breeds user frustration and support tickets.
- **Implication for UI:** A blocked state clearly identifies: (1) what is blocked, (2) which specific rule or evidence check failed, (3) what document version or input caused it, and (4) how the user can remediate (e.g., upload prior-year audit report, update template).
- **Anti-Pattern:** Disabling an action button with no tooltip or displaying an opaque error code like `BLOCK_400` without explanatory context.

---

### Principle 8: No Fake Successful Behavior
- **Classification:** `[DECISION]`
- **Principle:** The UI never simulates or promises successful completion of backend operations that have not actually executed and passed independent validation.
- **Why It Matters:** Faking success compromises system integrity and violates professional trust. A document that "looks edited" on screen is not a validated native transformation.
- **Implication for UI:** Optimistic UI updates are strictly restricted to non-governed transient actions (e.g., UI tab switching, local filter text). Document mutation, proposal approval, and task execution progress strictly reflect authoritative backend server events.
- **Anti-Pattern:** Showing a green checkmark "Document Saved!" immediately after an edit without waiting for backend persistence and validation report generation.

---

### Principle 9: Explicit Mock / Simulated Mode
- **Classification:** `[DECISION]`
- **Principle:** While backend capabilities are in development, simulated or mock data must be prominently and globally identified at the environment/workspace level.
- **Why It Matters:** During workstream U0 and U1, developers and stakeholders will test UI interactions against simulated fixtures. If mock data looks identical to live data, users and testers will confuse prototypes with certified releases.
- **Implication for UI:** When running in mock mode, a persistent workspace banner displays `SIMULATED BACKEND`. Individual mock data cards state their simulated status cleanly without overwhelming the screen with noisy individual badges.
- **Anti-Pattern:** Hiding mock status in browser developer tools or displaying fake production timestamps and hashes.

---

### Principle 10: Preserve Document Visibility Even When Perception Is Partial
- **Classification:** `[DECISION]`
- **Principle:** The user must always be able to view, read, pan, and inspect the original document binary, even if backend perception, semantic parsing, or native binding is incomplete, degraded, or failed.
- **Why It Matters:** Users rely on the visual document as their grounding truth. If a parser error hides the entire document pane, the workbench becomes completely useless.
- **Implication for UI:** Document rendering (PDF canvas, DOCX DOM preview, XLSX virtual sheet) is decoupled from semantic perception. If semantic perception fails or is partial, the document remains readable, and an honest banner explains that semantic features (e.g., element snapping, target highlighting) are temporarily limited.
- **Anti-Pattern:** Blanking out the document viewer or showing a full-screen crash screen because a single footnote could not be parsed by Docling.

---

### Principle 11: Direct Manipulation Without Direct Mutation
- **Classification:** `[DECISION]`
- **Principle:** Users interact directly with document content (clicking paragraphs, selecting tables, dragging regions), but interaction never creates mutation authority and does NOT automatically create a proposal.
- **Why It Matters:** Direct manipulation is intuitive and productive, but direct mutation violates Frozen Contract v0.1 and ADR-004. An approved change requires source sufficiency, evidence gates, and review. Furthermore, selecting or inspecting an object must not presume the user intends to modify it.
- **Implication for UI:** Selecting or inspecting document content opens a contextual action palette allowing the user to choose among distinct actions: `Inspect`, `Extract`, `Ask AI`, or `Propose Change`. Only an explicit user choice to `Propose Change` initiates proposal intent. That intent is processed by governed backend/application logic into a `ChangeProposal` with status `DRAFT`, which then routes into governed review. Direct in-place editing that mutates the file is prohibited.
- **Fundamental Separation:**
  ```text
  Selection != ChangeProposal != ApprovedChangeSet
  Extract != Propose Change
  Extract != Mutation
  ```
- **Anti-Pattern:** Directly issuing a `PATCH /api/elements/{id}` that mutates the source file on disk upon pressing Enter in a table cell, or automatically generating a mutation proposal merely because a user selected a region.

---

### Principle 12: Extract != Propose Change
- **Classification:** `[DECISION]`
- **Principle:** Region extraction and change proposals are fundamentally distinct operations with different governance boundaries and lifecycles.
- **Why It Matters:** Extraction derives a secondary read-only artifact (e.g., table to CSV/XLSX, text excerpt) without altering the source document binary. Mutation modifies the target binary and requires an `ApprovedChangeSet`.
- **Implication for UI:** The Selection Inspector explicitly separates extraction actions (`Extract Table to CSV`, `Extract Text`, `Extract Structured DOCX`) from mutation actions (`Propose Change`). Extraction triggers a background generation task resulting in an export artifact; mutation enters the task proposal pipeline.
- **Anti-Pattern:** Conflating export and edit into a single ambiguous "Apply & Export" button.

---

### Principle 13: Selection Geometry != Semantic / Native Identity
- **Classification:** `[DECISION]`
- **Principle:** Screen pixel coordinates (`SelectionGeometry`) do not represent document identity.
- **Why It Matters:** A drag rectangle on screen is a viewport artifact. In DOCX (flow layout) or zoomed PDFs, pixel coordinates change with screen resolution, DPI, and window resizing. They have no meaning in OOXML or Docling semantic hierarchies.
- **Implication for UI:** The UI uses geometry only as an initial transient input. It maps geometry to candidate rendered DOM elements, requests semantic resolution, and binds to structured document objects (`ResolvedSelection`).
- **Anti-Pattern:** Storing `{ x: 120, y: 340, w: 200, h: 100 }` in an audit record or attempting to use screen coordinates as a `NativeLocator`.

---

### Principle 14: Capability-Gated UX
- **Classification:** `[DECISION]`
- **Principle:** Actions are exposed, enabled, or disabled based on verified document capabilities detected during preflight, never based on generic file extensions or optimistic assumptions.
- **Why It Matters:** A `.docx` file may contain Strict OOXML, password protections, legacy VML shapes, or locked content controls that the replay engine cannot safely mutate. Attempting unsupported actions leads to failed executions.
- **Implication for UI:** If preflight marks an object `PROTECTED`, the UI displays a lock indicator and disables mutation proposals with an explicit explanation. If an operation is `UNSUPPORTED`, the UI indicates that only structured extraction is available, preventing invalid mutation attempts.
- **Anti-Pattern:** Allowing users to submit complex table alterations on password-protected or Strict OOXML documents, only to fail cryptically minutes later during replay.

---

### Principle 15: Validation and Audit Are User-Visible Product Concepts
- **Classification:** `[DECISION]`
- **Principle:** Post-execution independent validation reports and immutable audit trails are core user-facing features, not hidden backend logging mechanisms.
- **Why It Matters:** Foundation's value proposition is demonstrable proof of correctness. Associates, reviewers, and compliance stakeholders need immediate visual confirmation that authorized changes were applied accurately and out-of-scope content was preserved untouched.
- **Implication for UI:** The workbench includes dedicated, prominent views for `Validation` (showing check-by-check pass/fail outcomes against the approved plan) and `Audit` (displaying the chronological, hash-chained timeline of events and decisions).
- **Anti-Pattern:** Concluding a workflow with a generic "Done" message while burying validation logs in server console output.

---

### Principle 16: Accessibility and Desktop Professional-Workbench Usability
- **Classification:** `[DECISION]`
- **Principle:** The UI is designed as a desktop-first professional productivity workbench supporting dense data displays, rapid keyboard workflows, high contrast, and accessible navigation.
- **Why It Matters:** Associates and reviewers work with large, complex documents for hours at a time. Low-density mobile-style cards, missing keyboard shortcuts, or poor contrast cause severe operator fatigue and input errors.
- **Implication for UI:** Support comprehensive keyboard navigation (e.g., `Escape` to clear selection or exit drawer, `Ctrl+Z` undo where applicable, tab navigation across review items). Enforce WCAG 2.1 AA contrast standards, visible focus rings, ARIA roles, and collapsible panels to maximize screen real estate on standard laptop screens (1280x800 and 1366x768).
- **Anti-Pattern:** Giant touch-friendly padding that forces endless vertical scrolling and truncates wide financial comparison tables.

---

## 3. Summary of Core Invariants for UI Engineering

| Invariant ID | Rule | Enforced Surface |
|---|---|---|
| `INV-UI-01` | `SelectionGeometry != SemanticReference != NativeLocator` | Document Viewer & Selection Store |
| `INV-UI-02` | `Extract != Propose Change` | Selection Inspector & Context Menus |
| `INV-UI-03` | `Agent == Assist Only` (No direct mutation / authorization authority) | Agent Pane & Composer |
| `INV-UI-04` | `Backend == State Authority` (No client-side business transitions) | Task Stores & Action Handlers |
| `INV-UI-05` | `Simulated State == Globally Explicit` (`SIMULATED BACKEND` banner) | App Shell & Status Bar |
| `INV-UI-06` | `Fails Closed == Plain-Language Explanation` | Error Boundaries & Exception Cards |
| `INV-UI-07` | `Capability-Gated Affordances` (Strict adherence to preflight status) | Inspector Buttons & Context Actions |
| `INV-UI-08` | `Selection != ChangeProposal != ApprovedChangeSet` (Explicit user intent required) | Selection Action Palette & Proposal Handlers |
