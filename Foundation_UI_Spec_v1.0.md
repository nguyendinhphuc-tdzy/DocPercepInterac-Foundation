# Foundation UI Spec
## Document Intelligence Workspace
### UI/UX Specification v1.0

**Project:** Document Perception & Interaction Foundation  
**Primary Use Case:** Enterprise document processing and GTPS Transfer Pricing Local File automation  
**Status:** Proposed build specification  
**Date:** 2026-08-17  
**Scope:** End-to-end product UI/UX direction, screen architecture, workspace behavior, panel system, AI Agent interaction, Element Explorer, output/review flows, and implementation principles.

---

# 0. Product UI Direction

The Foundation should not behave like a conventional analytics dashboard or a developer-oriented document parser.

It should behave as an:

> **AI-native Document Intelligence Workspace**

The user should be able to work through the system without understanding the underlying perception, extraction, anchoring, mapping, lineage, and writeback pipeline.

### Core UX principle

> **The user should never need to understand the Foundation pipeline to use the Foundation.**

### Secondary UX principle

> **The workspace reveals complexity only when the user asks for it.**

The product should expose complexity progressively:

```text
Simple task
    ↓
Upload files
    ↓
Describe request
    ↓
AI processes document context
    ↓
Review result
    ↓
Download output

Optional deeper interaction
    ↓
Elements
    ↓
Inspector
    ↓
Provenance / Trace
    ↓
Diff / Compare / Diagnostics
```

The UI should therefore prioritize:

1. AI Agent as the primary working surface.
2. File-first onboarding.
3. Document context as a secondary surface.
4. Element Explorer as a trust and verification layer.
5. Output as the completion layer.
6. Advanced technical information as contextual or hidden by default.

# 1. Product Mental Model

```text
                    USER
                      │
                      ▼
               ┌─────────────┐
               │  AI AGENT   │
               │   Primary   │
               └──────┬──────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
     FOUNDATION                 OUTPUT
     Intelligence                File
          │
     ┌────┴─────┐
     ▼          ▼
 ELEMENTS    PROVENANCE
  Verify        Trust
```

**AI Agent** is the primary work surface.  
**Foundation Intelligence** is mostly invisible.  
**Elements** are the verification layer.  
**Provenance** is the trust layer.  
**Output** is the completion layer.

# 2. Primary User Journey

```text
HOME
  ↓
NEW TASK
  ↓
DROP / SELECT FILES
  ↓
ANALYZE
  ↓
WORKSPACE
  ↓
WRITE REQUEST TO AI AGENT
  ↓
FOUNDATION PERCEIVES + RETRIEVES + REASONS + ACTS
  ↓
REVIEW RESULT
  ↓
DOWNLOAD OUTPUT
```

The user should not be forced through the Element Explorer or diagnostics before completing the primary task.

# 3. Application Information Architecture

| Screen | Purpose | Priority |
|---|---|---:|
| Home | Start or reopen a task | P0 |
| New Task / Input Setup | Upload and organize input files | P0 |
| AI Workspace | Primary working environment | P0 |
| Element Explorer | Verification and controlled inspection | P0 |
| Output / Review | Review and download generated output | P0 |
| History / Runs | Reopen prior tasks and outputs | P1 |
| Compare Workspace | Compare documents or versions | P1 |
| Settings | User and system configuration | P2 |
| Evaluation / Diagnostics | Internal engineering and QA workflows | P2 |

# 4. Screen: Home

Home should help the user do only two things: start a new document task or reopen an existing task.

```text
┌─────────────────────────────────────────────────────────────┐
│ Foundation                                    Search   +New │
├──────────────┬──────────────────────────────────────────────┤
│ Home         │ Start a new document task                    │
│ Workspaces   │                                              │
│ History      │ [ Drop files here / Browse ]                 │
│ Settings     │                                              │
│              │ Recent work                                  │
│              │ ─────────────────────────                     │
│              │ HMV Local File · Aug 17                      │
└──────────────┴──────────────────────────────────────────────┘
```

No Element Index, Trace, permanent Agent, or analytics-heavy dashboard on Home.

# 5. Screen: New Task / Input Setup

The first interaction should be intentionally simple:

> **The only thing the user needs to do is input files.**

Initial state:

```text
                  NEW DOCUMENT TASK

          What would you like to work with?

┌────────────────────────────────────────────────────────────┐
│                     Drop files here                        │
│                 or Browse from computer                    │
└────────────────────────────────────────────────────────────┘

Supported: PDF · XLSX · DOCX

                         [Continue]
```

After upload, show compact file rows rather than full document contents.

Each file row may expose:
- filename
- file type
- size
- processing state
- remove
- optional reorder
- optional role classification

# 6. Multi-file Input Strategy

The product must support multiple source files in one task.

Recommended UX soft limit: **10 source files per task**.

Example:

```text
9 / 10 files
```

When exceeded:

```text
You've reached the recommended limit of 10 files.
You can continue with another task.
```

This is a product/UX recommendation, not a core architectural constraint. The existing backend currently accepts multiple source files in one request.

# 7. Multi-file Viewing Principle

Never render several input files as one long vertically stacked document feed.

Avoid:

```text
FILE 1
content...
content...
FILE 2
content...
content...
FILE 3
content...
```

Prefer a compact file rail or tab switcher:

```text
[Financial.xlsx] [RPTs.xlsx] [Appendix.pdf] [LocalFile.docx]
```

Only the active file should occupy the primary document viewer unless the user explicitly enters Compare mode.

# 8. Main Workspace

The main workspace is the core product surface and should be **composable**, not a fixed dashboard.

Conceptual structure:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Foundation     HMV Local File      ● Ready        Share   Export  ⋯ │
├───────────┬──────────────────────────────────────────────┬───────────┤
│ FILES     │                                              │ CONTEXT   │
│ 4 files   │                  AI WORKSPACE                │ Elements  │
│ ✓ RPTs    │                                              │ Inspector │
│ ✓ FA      │                                              │           │
│ ✓ Appx    │                                              │           │
│ ✓ Local   │                                              │           │
├───────────┴──────────────────────────────────────────────┴───────────┤
│ AI AGENT                                                             │
│ Ask Foundation to analyze, map, compare or update this document...  │
└──────────────────────────────────────────────────────────────────────┘
```

The exact arrangement should depend on workspace preset and active task.

# 9. AI Agent as Primary Surface

The Agent is the primary working surface, not a decorative chatbot.

Core flow:

```text
Upload
  ↓
Foundation extracts
  ↓
User describes desired outcome
  ↓
Agent acts over extracted context
  ↓
Output is produced
```

Example progress:

```text
Understanding request...

✓ Read 4 input documents
✓ Identified 4,612 target elements
✓ Found 37 relevant financial elements
✓ Matched 29 elements
✓ 5 require review
✓ 3 have conflicting sources

[Review] [Apply changes]
```

Then:

```text
OUTPUT
HMV-25-Updated-Local-File.docx

[Open output]
[Download]
```

# 10. AI Agent is an Orchestrator, Not a Chatbot

The Agent should conceptually implement:

```text
User request
      ↓
Intent interpretation
      ↓
Retrieve relevant elements
      ↓
Cross-reference source material
      ↓
Semantic reasoning
      ↓
Generate proposed changes
      ↓
Validate
      ↓
Writeback
      ↓
Output
```

The user should never need to manually provide element IDs, table positions, or anchor internals for ordinary tasks.

# 11. Agent Context Model

The Agent should receive structured document context from the Foundation.

Conceptual request context:

```json
{
  "message": "Explain this section.",
  "document": "...",
  "selected_element": {
    "type": "Cell",
    "content": "...",
    "confidence": 0.996
  },
  "mapped_results": [],
  "trace": []
}
```

Potential context sources:
- active task
- active file
- active document
- selected element
- extracted elements
- mapped elements
- provenance
- prior actions
- generated output state

# 12. Agent Composer

The composer should be clean and visually dominant.

```text
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Ask Foundation to analyze these documents...               │
│                                                             │
│  +  Files  Elements  Context                Model ▾   ↑     │
└─────────────────────────────────────────────────────────────┘
```

Default copy should remain simple:

```text
Write your request...
```

Context chips such as Files, Element, Document, and Results are optional assistance, not mandatory concepts.

# 13. Agent Pane Behavior

The Agent pane should support:

- dock left
- dock right
- dock bottom
- floating
- fullscreen
- drag
- resize
- collapse
- expand
- snap
- close
- restore

Recommended constraints:

```text
min-width: 360px
max-width: 80vw
min-height: 280px
```

Avoid unconstrained freeform resizing that can destroy workspace usability.

# 14. Workspace Pane System

Use a semantic pane system instead of hard-coded simultaneous panels.

### Primary pane
- AI Agent

### Context panes
- Files
- Document
- Elements
- Inspector

### Output panes
- Preview
- Changes
- Output
- Diff

### Advanced panes
- Trace
- Raw JSON
- Lineage
- Logs
- Model metadata
- Evaluation diagnostics

# 15. Pane Visibility Rules

### Always visible
- Global navigation
- Current task context
- AI Agent

### Usually available
- Input Files
- Document Preview
- Output

### Contextual
- Elements
- Inspector
- Trace
- Diff

### Hidden by default
- Raw element JSON
- Anchor structure
- Lineage log
- Model metadata
- Evaluation diagnostics
- Debug details

# 16. Workspace Presets

Provide presets so users can change work mode without manually building every layout.

### Agent
Agent + Document

### Inspect
Document + Elements + Inspector

### Review
Document + Diff + Output

### Compare
Source A + Source B

Example menu:

```text
View ▾

Workspace

● Agent
○ Inspect
○ Review
○ Compare

───────────────────
Customize layout
Reset layout
Save as preset
```

# 17. Screen: Element Explorer

Element Explorer is a **Trust & Verification Layer**, not the default primary workspace.

It should allow users to:
- understand what Foundation extracted
- inspect elements
- verify confidence
- understand structural location
- reveal exact document location
- make supported manual adjustments

Conceptual layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ Elements                                      Search  Filter │
├──────────────────────┬───────────────────────────────────────┤
│ ELEMENT TREE         │ ELEMENT INSPECTOR                     │
│ ▾ Document           │ Type          Cell                    │
│   ▾ Section 7        │ Confidence   99.6%                    │
│      7.1             │ Content                               │
│      7.2             │ "Transfer pricing method"             │
│   ▾ Table 3          │ Source                                │
│      Row 1           │ Financial.xlsx!D12                    │
│      Row 2           │                                       │
│ 4,612 elements       │ [Reveal in document]                 │
└──────────────────────┴───────────────────────────────────────┘
```

# 18. Element Explorer Information Hierarchy

Avoid raw spreadsheet-like presentation:

```text
# | TYPE | ELEMENT | CONFIDENCE
```

Prefer semantic information first:

```text
ELEMENT

3.2
Financial Information
Transactions
Transfer pricing method
```

Then metadata:

```text
TYPE
Cell

ANCHOR
table:3 / row:2 / col:2

CONFIDENCE
99.6%

SOURCE
RPTs.xlsx → Sheet → D12
```

# 19. Element Tree

Group elements semantically where possible:

```text
ELEMENTS

▾ Section 7.1
   ├─ 3.2
   ├─ Financial data
   └─ Summary of financial data

▾ Table 3
   ├─ Header
   ├─ Row 1
   ├─ Row 2
   └─ Row 3

▾ Table 4
   └─ ...
```

# 20. Element Inspector

When selected:

```text
ELEMENT
──────────────────

Type
Cell

Content
"Transfer pricing method"

Position
Table 3 · Row 1 · Col 2

Confidence
99.8%

Source
Financial Analysis!D7

[Reveal in document]
[Edit]
[Reset]
```

# 21. Reveal-in-Document Interaction

Core interaction:

```text
Element Explorer
        ↓
selected Anchor
        ↓
Document Preview
        ↓
highlight exact location
```

The document viewer should scroll to and highlight the exact source location while preserving selection state.

# 22. Synchronized Selection Model

Synchronize:

```text
Element
   ↕
Document
   ↕
Inspector
   ↕
Provenance
   ↕
Output
```

A single selected element should update all relevant surfaces.

# 23. Provenance / Trace UX

Trace should not look like a developer console.

Prefer:

```text
PROVENANCE

Output
  ↓
Mapped value
  ↓
Financial Analysis!D7
  ↓
Source document
  ↓
Page 8
  ↓
Cell D7
```

Trace should expose source, location, target, relationship, confidence, and version/timestamp where relevant.

# 24. Results UX

Results should communicate meaningful outcomes rather than raw debug rows.

```text
RESULTS
3 mapped values

┌───────────────────────────────┐
│ RPTs!E8                       │
│ 1,937,297,852                 │
│ Confidence 99.6%              │
└───────────────────────────────┘
```

Results should work well as cards or a scannable contextual list.

# 25. Confidence UX

Do not make repeated 100% values visual noise.

Prefer:

```text
High
99.8%
```

or:

```text
● 99.8%
```

Suggested semantic bands:

```text
High      98–100
Medium    90–98
Low       <90
```

# 26. Screen: Output / Review

```text
OUTPUT

HMV-25-Updated-Local-File.docx

29 elements updated
5 elements require review
3 source conflicts

[Open Preview]   [Review Changes]

[Download DOCX]
```

Distinguish clearly between applied changes, review items, conflicts, warnings, and final output.

# 27. Output Review

When output is not fully clean:

```text
DONE WITH REVIEW ITEMS

29 changes applied
3 items require review

[Review 3 issues]
[Preview output]
[Download]
```

# 28. Document View

The Document View is a context surface.

It should support:
- scrolling
- zooming
- selection
- highlight
- exact element reveal
- page/section context
- comparison when explicitly requested

It should not automatically render every input file simultaneously.

# 29. Multi-document Compare

Compare is a dedicated mode.

```text
┌───────────────────────────────┬───────────────────────────────┐
│ Source A                      │ Source B                      │
│                               │                               │
│ Document view                 │ Document view                 │
└───────────────────────────────┴───────────────────────────────┘
```

For three or more files, use a source selector or pairwise compare rather than four permanent panes.

# 30. Visual Design Direction

The product should not look like a generic developer dashboard.

It should feel like a professional AI workspace.

### Principles
- high clarity
- strong hierarchy
- restrained color
- generous whitespace around primary actions
- dense metadata only in secondary surfaces
- consistent borders and surface elevation
- calm professional typography
- clear selected states
- no unnecessary decorative UI

### Suggested palette direction

```text
Background       #F7F8FA
Surface           #FFFFFF
Border            #E5E7EB
Primary text      #111827
Secondary text    #6B7280
Accent            #2563EB
Success           #16A34A
Warning           #D97706
```

Use accent primarily for selected elements, active tabs, highlights, and interactive actions.

# 31. Typography

Do not solve density by shrinking all typography.

Suggested hierarchy:

```text
Primary heading        18–22px
Section heading        14–16px
Primary body           14–16px
Secondary text         13–14px
Metadata               11–12px
Table content          13px
```

Use spacing, grouping, and hierarchy rather than tiny type.

# 32. Navigation

Suggested global navigation:

```text
Home
Workspaces
History
Settings
```

Potential future items:

```text
Compare
Evaluation
```

Advanced diagnostics should not dominate primary navigation.

# 33. Workspace Header

The header should answer:
1. What task/file am I working on?
2. What is the current processing state?
3. What is the current task status?
4. What can I do next?

Conceptual:

```text
Foundation
HMV 23&23 EN compare.docx
● Ready       4,612 elements
[Export] [...]
```

# 34. Processing State

Show operational progress rather than hidden behavior.

```text
Analyzing request

✓ Parsed 4 documents
✓ Identified 4,612 elements
✓ Retrieved 37 relevant elements
✓ Cross-referenced sources
● Applying changes...
○ Validating output
```

Do not expose model chain-of-thought.

# 35. AI Agent and Foundation Relationship

The Agent should operate over structured Foundation context.

```text
Raw documents
      ↓
Perception
      ↓
Elements
      ↓
Anchors
      ↓
Cross-reference
      ↓
Agent retrieval
      ↓
Semantic reasoning
      ↓
Writeback
      ↓
Validation
      ↓
Output
```

# 36. Architecture Boundary for UI Integration

The browser must not call Workbench directly.

Preferred:

```text
Browser
  ↓
Frontend
  ↓
Flask API
  ↓
Workbench integration
  ↓
KPMG Workbench
  ↓
Model
```

Workbench credentials remain backend-side.

The existing direct Workbench smoke test remains an integration test and should remain separate from Foundation core modules.

# 37. Current Backend Surface

Current API surface:

```text
POST  /api/process
PATCH /api/elements/<process_id>
GET   /api/download/<process_id>
```

`POST /api/process` accepts multiple source files and one target file, runs the existing mapping service, and returns source elements, target elements, mappings, and download information.

Future Agent integration should be layered alongside this surface without putting Workbench-specific code into:

```text
foundation/perception/
foundation/output/
foundation/eval/
```

# 38. Suggested Future Agent API Surface

Conceptual future UI-facing surface:

```text
POST /api/agent/chat
```

Possible payload:

```json
{
  "process_id": "...",
  "message": "...",
  "context": {
    "file_ids": [],
    "selected_element": null
  }
}
```

Potential future endpoints:

```text
POST /api/agent/chat
POST /api/agent/execute
GET  /api/agent/runs/<run_id>
GET  /api/agent/status/<run_id>
```

These are design targets only unless implemented.

# 39. Workspace Interaction Principle

Use:

> **Focus + Context + Action**

```text
Focus
= current primary task

Context
= document / elements / provenance / output

Action
= Agent request or explicit edit
```

Do not force all context to remain visible.

# 40. Complexity Management

Use progressive disclosure.

### Level 1 — Task completion

```text
Files
Agent
Output
```

### Level 2 — Verification

```text
Document
Elements
Inspector
```

### Level 3 — Trust

```text
Trace
Provenance
Changes
```

### Level 4 — Engineering

```text
Raw JSON
Anchors
Lineage
Evaluation
Diagnostics
```

# 41. Why the Current UI Fails

The current UI places too many competing surfaces on screen:

- Document
- Elements
- Results
- Trace
- Agent
- file title
- status
- mapping information

The fundamental issue is **hierarchy collapse**: everything appears equally important.

The multi-file problem is **input overload**: multiple documents appear as vertically stacked content rather than distinct workspace contexts.

The Agent is under-prioritized despite being the intended primary interaction surface.

The Element Index is presented as if it were the main workspace rather than a verification surface.

# 42. Design Objective

The redesign should feel like:

> **A clean AI-native document workspace**

not:

> **A developer dashboard showing internal parser output.**

The workflow should feel like:

```text
Upload
    ↓
Ask
    ↓
Review
    ↓
Download
```

# 43. Core Component System

The UI should define reusable components for:

- App shell
- Sidebar navigation
- Workspace header
- File rail
- File row
- Upload drop zone
- File chip/tab
- Status badge
- Agent pane
- Agent composer
- Context chip
- Pane container
- Dock divider
- Dock control
- Document viewer
- Element tree
- Element inspector
- Confidence badge
- Provenance drawer
- Result card
- Diff viewer
- Output preview
- Review issue card
- Workspace preset menu
- Toast/notification
- Modal
- Command menu
- Empty state
- Loading/progress state

# 44. Workspace States

Minimum states:

### Empty task
```text
No files → Upload
```

### Files uploaded
```text
Files ready → Analyze
```

### Processing
```text
Foundation processing → Progress
```

### Ready
```text
Elements available → Ask Agent
```

### Agent running
```text
Request in progress → Progress
```

### Review required
```text
Output exists → Issues available
```

### Complete
```text
Output ready → Preview / Download
```

### Error
```text
Actionable error → Retry / Fix
```

# 45. File Status States

Use explicit states:

```text
Uploading
Processing
Ready
Warning
Error
Removed
```

Do not rely on color alone.

# 46. Agent States

Support:

```text
Idle
Preparing
Retrieving context
Processing
Applying changes
Validating
Completed
Needs review
Error
```

Use human-readable labels rather than generic spinners.

# 47. Empty States

Empty states must provide one clear action.

Examples:

```text
No documents yet
Upload files to start a new document task.
[Upload files]
```

```text
No selected element
Choose an element from the Element Explorer to inspect its structure and source.
```

```text
No output yet
Ask the Agent to analyze or update your document.
```

# 48. Responsiveness

Desktop is the primary target.

### Wide desktop
- multiple panes
- docking
- split views

### Medium desktop
- collapsible sidebar
- secondary pane becomes drawer

### Narrow desktop / tablet
- single primary pane
- context panes as drawers
- Agent remains primary

Do not attempt to reproduce the entire multi-pane desktop layout on narrow screens.

# 49. Keyboard and Productivity

Support:
- keyboard shortcuts
- Enter / Cmd+Enter to submit Agent prompt
- Esc to close pane
- Cmd/Ctrl+K for command menu if appropriate
- arrow navigation in element tree
- keyboard navigation through results
- accessible focus states

# 50. Accessibility

Minimum requirements:
- WCAG-aligned contrast
- visible focus states
- keyboard navigation
- accessible status text
- semantic icon labels
- screen-reader-friendly controls
- non-color-only status indicators
- readable dense views at zoom

# 51. UX Trust Principles

Because the product modifies enterprise documents, users must be able to understand:
- what changed
- why it changed
- where the source came from
- what is uncertain
- what still needs review

The UI should provide:

```text
Result
+
Source
+
Confidence
+
Changes
+
Review status
```

without exposing unnecessary implementation detail.

# 52. Manual Editing

Manual editing is an exception path.

Primary flow:

```text
User request
→ Agent
→ Foundation
→ Output
```

Manual editing belongs in Element Explorer/Inspector where supported.

Manual edits should:
- identify selected element
- show current value
- show new value
- preserve anchor information
- support reset/undo where implemented
- preserve audit/lineage information

# 53. Compare Workspace

Compare supports:
- prior-year vs current-year
- source vs output
- draft vs final
- version A vs version B

Prioritize:

```text
Added
Modified
Removed
Unchanged
```

Each difference should be traceable to document location.

# 54. Output Diff

Diff should be a contextual pane.

```text
CHANGES · 29

Modified
─────────────
3.2 Financial Information
Table 4 Row 3

Added
─────────────
...

Review
─────────────
3 items
```

Clicking an issue should navigate to its corresponding document location.

# 55. Product-level Success Criteria

A new user should be able to:

1. Open the product.
2. Understand that the first action is uploading files.
3. Upload multiple files without losing visual clarity.
4. Start analysis without understanding internals.
5. Write a natural-language request.
6. Understand what the Agent is doing at a high level.
7. Review the generated output.
8. Download the result.
9. Optionally inspect Elements and Provenance.
10. Return to the main workflow without losing context.

# 56. Build Priority

## P0 — Core experience
- Application shell
- Home
- New Task
- Multi-file input
- Workspace shell
- Agent pane
- Agent composer
- Document context
- Output
- Basic pane docking
- Basic workspace states

## P0 — Verification
- Element Explorer
- Element Inspector
- Reveal in Document
- Selection synchronization

## P1 — Review
- Diff
- Provenance
- Trace
- Workspace presets
- Compare

## P1 — Productivity
- Keyboard shortcuts
- Saved layouts
- History
- Reopen task

## P2 — Advanced
- Evaluation
- Diagnostics
- Raw element view
- Raw anchor inspection
- Model metadata

# 57. Recommended Default Workspace

The cleanest first production configuration is:

```text
┌───────────────────────────────────────────────────────────────┐
│ Foundation   Current Task         ● Ready         ⋯           │
├────────────┬──────────────────────────────────────────────────┤
│ FILES      │                                                  │
│ 4 files    │                AI AGENT                         │
│ ✓ RPTs     │                                                  │
│ ✓ FA       │                                                  │
│ ✓ Appendix │                                                  │
│ ✓ Local    │                                                  │
└────────────┴──────────────────────────────────────────────────┘
```

Elements, Inspector, Trace and Output should open only when context requires them.

# 58. Target Emotional Experience

When first opened:

> **“I just need to upload my documents and tell it what I need.”**

While processing:

> **“The system understands what I asked and is working through the documents.”**

When reviewing:

> **“I can verify exactly what the system changed and where it came from.”**

When downloading:

> **“I know what I am getting and whether anything still needs my attention.”**

# 59. Design References

### Claude-style inspiration
Use AI-native multi-pane patterns for:
- persistent composer
- contextual workspaces
- split panes
- resizable/dockable panels
- document/artifact preview
- task-oriented workspace changes

### PandaDoc / Mobbin-style inspiration
Use SaaS workspace discipline for:
- restrained hierarchy
- persistent navigation
- clear primary workspace
- secondary information in supporting regions
- professional density without clutter

References should inform patterns rather than be copied literally.

# 60. Non-goals

The Foundation UI should not become:
- a generic BI dashboard
- a permanent debug console
- a full spreadsheet editor
- a page containing every element at all times
- a chatbot disconnected from document context
- a developer-only tool
- a fixed six-panel interface

# 61. Final Product Narrative

```text
        1. INPUT
     Upload documents
            ↓
       2. PERCEIVE
  Foundation extracts structure
            ↓
        3. ASK
    Describe the outcome
            ↓
        4. ACT
Agent retrieves relevant elements
and performs the requested work
            ↓
       5. VERIFY
 Review changes when needed
            ↓
       6. OUTPUT
    Download the result
```

The user experiences this as:

> **Upload → Ask → Review → Download**

The complexity of perception, anchors, mapping, provenance, semantic reasoning, evaluation, and deterministic writeback remains available as deeper workspace context.

# 62. Final UX Architecture

```text
Foundation
│
├── Home
│
├── New Task
│   └── Multi-file Input
│
├── Workspace
│   ├── AI Agent                 ← Primary
│   ├── Files                    ← Context
│   ├── Document                 ← Context
│   ├── Elements                 ← Verification
│   ├── Inspector                ← Verification
│   ├── Output                   ← Completion
│   ├── Diff                     ← Review
│   └── Trace / Provenance       ← Trust
│
├── History
├── Compare
├── Settings
└── Diagnostics
    ├── Raw JSON
    ├── Anchors
    ├── Lineage
    └── Evaluation
```

Primary hierarchy:

```text
AI Agent
   ↓
Document context
   ↓
Output
   ↓
Verification
   ↓
Diagnostics
```

# 63. Implementation Directive

Future UI implementations must follow these rules:

1. Do not add a permanent panel merely because the underlying system exposes data.
2. Do not expose technical metadata before semantic information.
3. Do not render multiple input documents as a single long vertical stream.
4. Do not make Element Explorer the primary workspace.
5. Make AI Agent the primary work surface.
6. Make panes dockable, resizable, collapsible, and context-aware.
7. Use progressive disclosure for Elements, Trace, Diff, and Diagnostics.
8. Keep the first-run workflow focused on file input.
9. Keep multi-file input visually compact and explicit.
10. Preserve synchronized selection across Document, Element, Inspector, Provenance, and Output.
11. Make output state and review requirements explicit.
12. Keep implementation details out of the default user experience.
13. Preserve Foundation/Application architecture boundaries while integrating the UI.
14. Treat Workbench Agent integration as backend orchestration, not a frontend direct API call.
15. Prefer reusable components and workspace presets over page-specific custom layouts.

# 64. One-Sentence Design North Star

> **Build the Foundation as an AI-native document workspace where the user uploads files, states an outcome, and lets the system handle the complexity, while Elements and Provenance remain available as precise verification layers whenever trust or control is required.**

---

## Build Note

This specification is the current baseline for the Foundation UI redesign. The implementation should proceed from the P0 screens and components first, then add review/verification surfaces without reintroducing a permanently dense dashboard layout.
