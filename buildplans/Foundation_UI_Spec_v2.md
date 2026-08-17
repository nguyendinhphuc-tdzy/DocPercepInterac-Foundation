# UI Specification — Foundation Document Intelligence Workbench

## 0. Document Overview

**Product:** Foundation  
**UI concept:** AI-assisted Document Review Workbench  
**Version:** 2.0  
**Date:** August 2026  
**Primary references:** Existing Foundation UI Specification + existing HTML demo  
**Design direction:** Linear + VS Code + Chrome DevTools

This specification replaces the previous 4-pane framing of:

> Input Viewer → Element Index → Intent / Mapping → Output + Trace

with a new workspace model:

> **Document → Elements → Agent → Results**

The core principle remains a single desktop workspace in which reviewers can inspect the source document, inspect extracted elements, interact with an AI Agent, and verify generated results without navigating across separate routes.

---

# 1. Product UX Positioning

Foundation should not be presented as a conventional SaaS dashboard.

It should behave as a:

> **Document Intelligence Workbench**

The user is a reviewer or power user who needs to repeatedly inspect documents, identify extraction problems, ask questions, verify AI decisions, and inspect provenance.

The interface therefore prioritizes:

- persistent context
- high information density
- fast interaction
- synchronized views
- progressive disclosure
- precise visual feedback
- minimal navigation overhead
- explainability and provenance
- keyboard-friendly workflows

The design language combines three references:

### Linear — Visual and Motion Reference

Use Linear as the reference for:

- visual polish
- spacing
- typography
- micro-interactions
- restrained animation
- hover states
- command surfaces
- loading states
- clean hierarchy

The objective is to make the product feel responsive and refined without excessive decoration.

### VS Code — Workspace Reference

Use VS Code as the reference for:

- multi-pane workspace architecture
- resizable panels
- compact information presentation
- persistent context
- tabs and secondary views
- keyboard interaction
- progressive disclosure
- power-user workflows

The objective is to make the interface feel like a professional working environment rather than a collection of dashboard cards.

### Chrome DevTools — Interaction Reference

Use Chrome DevTools as the reference for:

- object-centric interaction
- active context
- cross-panel synchronization
- inspect → focus → trace workflows
- contextual details
- dense but navigable information

The objective is that selecting one document element causes every relevant representation of that element to react.

---

# 2. Core UX Model

The four panes represent four different questions:

| Pane | Name | User question | Primary action |
|---|---|---|---|
| 1 | **Document** | What is actually in the source? | Inspect |
| 2 | **Elements** | What did Foundation detect? | Review |
| 3 | **Agent** | What can Foundation explain or do? | Ask / Act |
| 4 | **Results** | What did the system produce and how? | Verify |

The primary information flow is:

```text
SOURCE
  ↓
DOCUMENT
  ↓
ELEMENTS
  ↓
AGENT
  ↓
RESULTS
```

However, this is not a strictly linear workflow.

The user can move between any pane while retaining the same active document and active element context.

---

# 3. Workspace Architecture

## 3.1 Desktop-first layout

Foundation is an internal professional tool and is optimized for desktop/laptop screens.

Minimum recommended viewport:

```text
1280px width
```

Below the threshold, show a clear message asking the user to open the application on a larger screen.

Mobile optimization is not required for this workbench.

---

## 3.2 Default layout

Recommended default proportions:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Workspace Header                                                         │
├──────────────────────────────┬───────────────────────────────────────────┤
│                              │                                           │
│                              │                 ELEMENTS                  │
│          DOCUMENT            │                                           │
│                              │                                           │
│                              │                                           │
│                              │                                           │
├──────────────────────────────┼───────────────────────────────────────────┤
│                              │                                           │
│           AGENT              │                 RESULTS                   │
│                              │                                           │
│                              │                                           │
│                              │                                           │
└──────────────────────────────┴───────────────────────────────────────────┘
```

Default grid:

```text
50% / 50%
```

for the primary horizontal split and:

```text
55% / 45%
```

for the vertical distribution.

The layout must remain resizable.

The exact default ratio should be tuned against real document-review workloads rather than treated as a fixed design constant.

---

# 4. Workspace Header

The header should behave more like a professional application shell than a SaaS dashboard header.

Recommended structure:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Foundation   ·   report.pdf                     ● Ready       ⌘K         │
└──────────────────────────────────────────────────────────────────────────┘
```

## 4.1 Required information

- product/workspace name
- current document
- processing state
- optional gate state
- global command/search action
- workspace settings

## 4.2 Processing states

Supported states:

```text
Ready
Processing
Review required
Completed
Error
```

Use compact status indicators.

Do not use large banners unless the state materially blocks the user's workflow.

---

# 5. Pane 1 — Document

## 5.1 Purpose

The Document pane answers:

> **Did Foundation perceive the source document correctly?**

It displays the original document together with detected element boundaries.

Existing requirements for document rendering and bounding boxes remain applicable.

---

## 5.2 Layout

```text
┌─────────────────────────────────────────────┐
│ DOCUMENT                         Page 2 / 8 │
├─────────────────────────────────────────────┤
│                                             │
│                 PDF / DOCX                  │
│                                             │
│       ┌──────────────────────────┐          │
│       │ Element A-003             │          │
│       │                           │          │
│       └──────────────────────────┘          │
│                                             │
├─────────────────────────────────────────────┤
│ −   100%   +             Fit / Width       │
└─────────────────────────────────────────────┘
```

---

## 5.3 Interactions

### Hover element in Elements

The corresponding bounding box:

- becomes visible
- increases visual emphasis
- uses a short transition
- does not flash

### Click element in Elements

The Document pane:

1. scrolls to the element
2. centers it where practical
3. highlights its bounding box
4. keeps the highlight visible until another element becomes active

### Hover bounding box

The corresponding element row in Elements should receive a subtle hover state.

---

## 5.4 Bounding box behavior

Bounding boxes should be:

- visually subordinate when inactive
- clearly visible when active
- distinguishable by element/source where required
- stable during scrolling
- positioned using document coordinate data rather than screen coordinates

Avoid excessive glow.

Recommended active transition:

```text
120–180ms
```

---

# 6. Pane 2 — Elements

## 6.1 Purpose

The Elements pane answers:

> **What did Foundation extract from the document?**

This is the main structured review surface.

It replaces the previous concept of an "Element Index" as a more general Elements workspace.

---

## 6.2 Visual principle

The table should follow the density and compactness of VS Code rather than a conventional enterprise data table.

Do not expose every possible metadata field by default.

Use progressive disclosure.

Primary row:

```text
┌─────────────────────────────────────────────────────────────┐
│ #    TYPE        ELEMENT                     CONFIDENCE     │
├─────────────────────────────────────────────────────────────┤
│ A1   Heading     Independent Auditor             99%         │
│ A2   Paragraph   To the shareholders             95%         │
│ A3   Table       Revenue...                      78%  ⚠      │
└─────────────────────────────────────────────────────────────┘
```

Secondary information appears when the row is selected.

---

## 6.3 Filters

Provide compact controls for:

- type
- confidence
- review status
- source
- page
- search

Example:

```text
Search elements...
[Type] [Confidence] [Review] [Source]
```

Filters should remain visible while reviewing.

---

## 6.4 Selected element

When a row is selected, show contextual information without forcing navigation.

Example:

```text
A-003

Type             Table
Confidence       78%
Source           OCR
Anchor           page 2 · bbox
Review           Required

[Confirm]
[Change type]
[Ask Agent]
```

The detail surface can appear as:

- an inline expansion
- a compact side inspector
- or a floating contextual panel

The preferred implementation should be chosen based on available pane width.

---

## 6.5 Confidence

Confidence must remain visually scannable.

Use:

- percentage
- compact progress indicator
- review badge where applicable

The user should be able to identify low-confidence items without reading every value.

---

# 7. Pane 3 — Agent

## 7.1 Purpose

The previous **Intent / Mapping** pane is replaced by an **AI Agent workspace**.

The Agent answers:

> **What can Foundation explain, investigate, or do with the current document context?**

This is not a generic chatbot.

The Agent is context-aware and operates inside the document-review workspace.

---

# 8. Agent Information Architecture

The Agent pane has three primary layers:

```text
History
   ↓
Conversation
   ↓
Actions / Evidence
```

Recommended layout:

```text
┌───────────────────────────────────────────────┐
│ AGENT                                   ⚙     │
├───────────────────────────────────────────────┤
│ HISTORY                                       │
│                                               │
│ Review tables                                 │
│ Explain A-003                                 │
│ Extract financial metrics                     │
│                                               │
├───────────────────────────────────────────────┤
│                                               │
│ You                                           │
│ Why is A-003 only 78% confident?              │
│                                               │
│ Foundation                                    │
│ A-003 was classified as a table with          │
│ 78% confidence.                               │
│                                               │
│ Evidence                                      │
│ ✓ OCR source                                  │
│ ✓ Bounding-box quality                        │
│ ✓ Classification model                        │
│                                               │
│ [Inspect element] [Review]                   │
│                                               │
├───────────────────────────────────────────────┤
│ Ask Foundation...                         ↑   │
└───────────────────────────────────────────────┘
```

---

# 9. Agent Context Model

The Agent must automatically inherit workspace context.

Example:

```text
activeDocumentId
activeElementId
currentPage
selectedElements
activeFilters
currentReviewState
```

If the user selects:

```text
A-003
```

and asks:

> Why is this low confidence?

the Agent should already understand that "this" refers to A-003.

The user should not need to manually provide IDs.

---

# 10. Agent Actions

The Agent may return contextual actions such as:

```text
[Inspect]
[Review]
[Change type]
[Show evidence]
[Filter similar]
[Apply]
```

Actions should operate on the workspace rather than only producing text.

Example:

```text
User:
Show me all low-confidence tables.

Agent:
Found 7 elements.

[Show 7 elements]
```

Clicking the action should update the Elements pane filter.

The Agent should then remain synchronized with the updated workspace.

---

# 11. Agent History

Chat history should be persistent within the current document/workspace.

Example:

```text
HISTORY

Today
──────────────
Review tables
Explain A-003
Find OCR elements

Yesterday
──────────────
Extract financial metrics
Review output
```

History should be compact.

Selecting a history item restores the relevant conversation context.

Do not make history consume more vertical space than the conversation itself.

---

# 12. Agent Explainability

The UI may expose **reasoning summaries, evidence, tool actions, and execution traces**.

It should not expose hidden model chain-of-thought.

Preferred format:

```text
Analysis

Analyzed 3 signals

✓ OCR source
✓ Bounding-box quality
✓ Classification confidence

Conclusion

Element likely represents a table.

Evidence

→ 12 detected cells
→ 2 rows
→ consistent column alignment

[Inspect evidence]
```

The purpose is to make the AI decision understandable and auditable.

---

# 13. Agent Tool / Action Trace

When the Agent performs an operation, show a compact execution summary.

Example:

```text
Agent action

1. Located 7 low-confidence elements
2. Filtered Elements view
3. Focused A-003
4. Loaded OCR evidence

Completed in 1.4s
```

This should connect visually with the Results trace.

---

# 14. Pane 4 — Results

## 14.1 Purpose

The Results pane answers:

> **What did Foundation produce, and what happened during processing?**

Results combines:

```text
Output
+
Trace
```

---

## 14.2 Layout

```text
┌───────────────────────────────────────────────┐
│ RESULTS                                       │
├───────────────────────────────────────────────┤
│ OUTPUT                                        │
│                                               │
│ Revenue          1,250,000                    │
│ Profit             340,000                    │
│                                               │
├───────────────────────────────────────────────┤
│ TRACE                                         │
│                                               │
│ ● Geometry                                    │
│ │                                             │
│ ● OCR                                         │
│ │                                             │
│ ● Classification                              │
│ │                                             │
│ ● Human Review                                │
│ │                                             │
│ ● Output                                      │
└───────────────────────────────────────────────┘
```

---

# 15. Output

Supported output types should follow the existing product contract.

Examples:

- XLSX preview
- DOCX preview
- generated structured data
- Cover / Note regions where applicable

Output should be visually close to the final artifact.

The user should not have to imagine how the exported document will look.

---

# 16. Trace

Trace is a timeline, not a flat table.

Example:

```text
● Geometry
│
● OCR
│
● Classification
│
● Human Review
│
● Output
```

Each item may expand to show:

```text
Timestamp
Actor
Step
Old value
New value
Model version
Evidence
```

---

# 17. Actor Visualization

The trace must distinguish:

| Actor | Meaning |
|---|---|
| System | Deterministic processing |
| AI Agent | AI proposal or action |
| Human | Human confirmation or modification |

The distinction should use both:

- icon
- visual treatment

Do not rely on color alone.

AI Agent trace entries must expose the relevant `model_version` where applicable.

---

# 18. Cross-Pane Synchronization

This remains one of the core UX principles.

The previous `data-sync` + DOM query approach should not be used in React.

Use a shared state model such as:

```typescript
interface WorkspaceState {
  activeDocumentId: string | null;
  activeElementId: string | null;
  activeTraceId: string | null;
  setActiveElement: (id: string | null) => void;
  setActiveTrace: (id: string | null) => void;
}
```

The following surfaces consume the shared state:

```text
Document
  └── BoundingBox

Elements
  └── ElementRow

Agent
  └── Context / Conversation

Results
  └── TraceItem
```

---

# 19. Example Synchronization Flow

User clicks A-003:

```text
A-003 selected
      │
      ├── Document
      │     └── scroll + highlight bbox
      │
      ├── Elements
      │     └── active row
      │
      ├── Agent
      │     └── context becomes A-003
      │
      └── Results
            └── relevant trace becomes active
```

User clicks a Trace item:

```text
Trace selected
      │
      ├── Results
      │     └── active trace
      │
      ├── Document
      │     └── relevant source region
      │
      ├── Elements
      │     └── relevant element
      │
      └── Agent
            └── evidence/context updated
```

This creates a bidirectional inspection system.

---

# 20. Workspace State

Recommended shared state:

```typescript
interface WorkspaceState {
  activeDocumentId: string | null;
  activeElementId: string | null;
  activeTraceId: string | null;

  selectedElementIds: string[];

  documentPage: number;

  elementFilters: {
    search: string;
    type?: string;
    source?: string;
    review?: string;
    confidence?: string;
  };

  agentConversationId: string | null;

  setActiveElement: (id: string | null) => void;
  setActiveTrace: (id: string | null) => void;
}
```

The exact implementation may use Zustand or another lightweight state library.

---

# 21. Interaction Design Principles

## 21.1 Immediate feedback

Every meaningful user action should receive immediate visual feedback.

Examples:

- row selection
- pane resize
- document navigation
- filter application
- Agent action
- trace selection

---

## 21.2 Progressive disclosure

Do not show every metadata field at once.

Primary information:

```text
Type
Element
Confidence
Review
```

Secondary information:

```text
Source
Anchor
Model
Evidence
Metadata
```

Secondary information appears through:

- inspector
- expansion
- hover
- contextual panel
- Agent

---

## 21.3 Context persistence

The user should not lose:

- selected element
- document page
- filters
- conversation
- trace context

when interacting with another pane.

---

# 22. Motion System

The motion language should follow the restraint of Linear.

Animation is used to communicate state, not decoration.

## Recommended durations

| Interaction | Duration |
|---|---:|
| Hover | 100–150ms |
| Selection | 120–180ms |
| Highlight | 120–180ms |
| Pane resize | native continuous interpolation |
| Expand / collapse | 150–220ms |
| Dialog / popover | 150–220ms |
| Data loading | skeleton / progressive |
| Confidence animation | 200–400ms |

Avoid continuous animations during normal document review.

---

# 23. Signature Interaction

The most important interaction in Foundation should be:

> **Select once, understand everywhere.**

Example:

```text
Click A-003
      ↓
Document highlights source
      ↓
Elements shows metadata
      ↓
Agent receives context
      ↓
Results highlights provenance
```

This should become the defining interaction of the product.

---

# 24. Keyboard Interaction

Because Foundation is a professional review tool, keyboard interaction should be considered part of the primary UX.

Recommended shortcuts:

```text
⌘ / Ctrl + K
Global command palette

⌘ / Ctrl + F
Search elements

↑ / ↓
Navigate elements

Enter
Open / focus selected element

Esc
Clear contextual focus

⌘ / Ctrl + Enter
Send Agent message

⌘ / Ctrl + Shift + A
Ask Agent about selected element
```

Shortcuts should be discoverable through the command palette.

---

# 25. Command Palette

Use a VS Code-inspired command palette.

Example:

```text
┌─────────────────────────────────────────────┐
│ Search commands...                          │
├─────────────────────────────────────────────┤
│ Inspect selected element                    │
│ Ask Agent about selected element            │
│ Show low-confidence elements                │
│ Filter OCR elements                          │
│ Review unresolved anchors                   │
│ Jump to page...                              │
│ Export result                                │
└─────────────────────────────────────────────┘
```

This should become the main escape hatch for power users.

---

# 26. Visual Design Direction

## 26.1 Avoid card-heavy UI

Do not visually treat every pane as a standalone card.

Avoid:

```text
shadow + rounded card
shadow + rounded card
shadow + rounded card
shadow + rounded card
```

Prefer:

```text
application shell
│
├── pane
├── pane
├── pane
└── pane
```

Use:

- subtle separators
- restrained borders
- compact headers
- strong active states
- consistent spacing

The visual hierarchy should be:

```text
Workspace
  ↓
Pane
  ↓
Content
  ↓
Object
```

not:

```text
Card
  ↓
Card
  ↓
Card
```

---

# 27. Typography

Typography should prioritize:

1. readability
2. hierarchy
3. compactness
4. scanability

Recommended hierarchy:

```text
Workspace title
  ↓
Pane title
  ↓
Section title
  ↓
Primary content
  ↓
Metadata
  ↓
Supporting information
```

Avoid oversized headings inside the workbench.

---

# 28. Status and Error Handling

Existing edge cases remain required.

## Anchor unresolved

Elements row:

```text
A-003  ⚠
```

Document pane:

- no false bounding box
- explain why location cannot be resolved

Agent may provide:

> "This element could not be located reliably in the source document."

---

## Low-confidence OCR element

Show both:

```text
Source: OCR
Review required
```

Do not collapse these into one generic warning.

---

## AI disabled

Agent pane should explicitly show:

```text
AI Agent unavailable

Classification and AI-assisted actions are disabled.
```

Do not leave the pane blank.

---

## Document processing

Use independent pane loading states.

Do not block the entire application.

Example:

```text
Document      ✓ Ready
Elements      Processing...
Agent         Available
Results       Waiting...
```

---

## Large documents

For documents above approximately 50 pages:

- lazy-load pages
- render only the required document region
- avoid rendering the entire document at once

---

# 29. Component Architecture

Recommended structure:

```text
src/
  components/
    workspace/
      WorkspaceLayout.tsx
      WorkspaceHeader.tsx
      Pane.tsx
      PaneHeader.tsx
      Splitter.tsx
      StatusIndicator.tsx
      CommandPalette.tsx

    document/
      DocumentPane.tsx
      DocumentCanvas.tsx
      DocumentToolbar.tsx
      BoundingBoxOverlay.tsx
      PageNavigator.tsx

    elements/
      ElementsPane.tsx
      ElementTable.tsx
      ElementRow.tsx
      ElementInspector.tsx
      ConfidenceIndicator.tsx
      SourceBadge.tsx
      ReviewBadge.tsx
      ElementFilterBar.tsx

    agent/
      AgentPane.tsx
      AgentHistory.tsx
      Conversation.tsx
      Message.tsx
      EvidenceBlock.tsx
      AgentAction.tsx
      AgentComposer.tsx
      ReasoningSummary.tsx

    results/
      ResultsPane.tsx
      OutputPreview.tsx
      TraceTimeline.tsx
      TraceItem.tsx
      TraceInspector.tsx

  state/
    workspaceStore.ts
    agentStore.ts

  api/
    client.ts
```

---

# 30. Data Relationships

The core relationship is:

```text
Document
   │
   ├── Page
   │     │
   │     └── Element
   │            │
   │            ├── Evidence
   │            ├── Agent context
   │            └── Trace events
   │
   └── Execution
          │
          └── Output
```

The UI should expose these relationships without forcing the user to understand the underlying data model.

---

# 31. API / Backend Boundary

This UI specification does not redefine the backend architecture.

Existing API contracts remain the source of truth for:

- document perception
- page rendering
- element retrieval/update
- execution trace
- output

The new Agent pane requires an Agent conversation/action contract.

At UI level, the Agent should support concepts equivalent to:

```text
conversation
message
context
action
evidence
execution
result
```

The exact endpoint names and backend implementation should be defined separately.

---

# 32. Agent-to-Workspace Action Contract

The Agent should be capable of returning structured UI actions.

Example:

```typescript
interface AgentAction {
  type:
    | "focus_element"
    | "filter_elements"
    | "focus_trace"
    | "navigate_page"
    | "show_evidence"
    | "request_review";

  payload: Record<string, unknown>;
}
```

Example:

```json
{
  "type": "focus_element",
  "payload": {
    "elementId": "A-003"
  }
}
```

The workspace then performs the action.

This keeps the Agent integrated with the application rather than treating it as a text-only chatbot.

---

# 33. Review Workflow

Recommended end-to-end workflow:

```text
1. Open document
       ↓
2. Inspect source
       ↓
3. Review Elements
       ↓
4. Identify low-confidence items
       ↓
5. Select element
       ↓
6. Ask Agent
       ↓
7. Inspect evidence
       ↓
8. Apply / confirm action
       ↓
9. Verify output
       ↓
10. Inspect trace
```

The user may enter the workflow at any step.

---

# 34. Design Goals

The finished interface should feel:

### Fast

Interactions should respond immediately.

### Dense

A reviewer should be able to inspect many elements without excessive scrolling.

### Calm

Animation and visual noise should remain restrained.

### Connected

Every pane should feel like another view of the same workspace.

### Explainable

The user should understand why the system produced a result.

### Professional

The interface should feel appropriate for long review sessions.

### Extensible

New processing stages and Agent capabilities should be addable without redesigning the entire workspace.

---

# 35. Non-Goals

The Foundation workbench should not become:

- a generic analytics dashboard
- a card-heavy SaaS admin panel
- a generic chatbot
- a decorative AI interface
- a mobile-first application
- a visual replacement for Excel
- a raw model chain-of-thought viewer

---

# 36. Final Product Mental Model

The final mental model should be:

```text
                    FOUNDATION
                         │
             Document Intelligence
                    Workbench
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
    LINEAR            VS CODE         DEVTOOLS
  visual/motion       workspace       interaction
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │      DOCUMENT      │
              │                    │
              │      ELEMENTS      │
              │                    │
              │       AGENT        │
              │                    │
              │      RESULTS       │
              └────────────────────┘
```

The core principle is:

> **One document. One workspace. One active context. Multiple synchronized views.**

The defining interaction is:

> **Select once, understand everywhere.**

And the defining AI interaction is:

> **Ask the Agent without leaving the document-review context.**
