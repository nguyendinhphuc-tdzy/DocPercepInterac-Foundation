# GTPS First Draft Vertical Slice v0.1

> Status: implementation target for the first business-value vertical slice after B1 perception qualification.
>
> This document is use-case-specific. It does not override Frozen Foundation Contract v0.1 or accepted architecture/governance documents.
>
> Read together with `docs/business/GTPS_LOCAL_FILE_WORKFLOW_PROFILE_v0.2.md`.

## 1. Product goal

Prove that Foundation can produce a usable GTPS Local File **First Draft DOCX** by performing governed transformation on an approved Local File Template.

The vertical slice must NOT regenerate or rewrite a new document from semantic text.

Canonical behavior:

```text
Approved Local File Template
        = TARGET / output base

Prior-year Local File
        = HISTORICAL_REFERENCE

Current-year FA&RPTs
        = CURRENT_SOURCE

Optional current-year Appendix I / other approved evidence
        = SUPPORTING_CURRENT_EVIDENCE

Completed current-year Local File
        = GOLDEN_EVALUATION_ONLY
```

Execution path:

```text
CURRENT_SOURCE
→ compare with HISTORICAL_REFERENCE
→ identify Business Target
→ resolve matching Target Region in TARGET Template
→ create ChangeProposal
→ show mapped/changed region to user
→ Human approve/edit/reject
→ ApprovedChangeSet
→ controlled native update on a COPY of TARGET Template
→ independent validation
→ downloadable First Draft .docx
```

The resulting file must remain a DOCX derived from the exact approved Template, not a newly authored Office document.

## 2. Non-negotiable invariants

1. `TARGET_TEMPLATE` is the only output base.
2. `HISTORICAL_REFERENCE` is never the output base.
3. `CURRENT_SOURCE` supplies current-year facts within its approved source authority.
4. `GOLDEN_EVALUATION_ONLY` is never an execution input, mapping authority, target, or historical source.
5. AI may propose semantic mappings/narrative changes but cannot authorize or execute them.
6. No mutation occurs before an `ApprovedChangeSet` exists.
7. Unsupported, ambiguous, conflicting or stale targets fail closed.
8. The downloaded First Draft must be `.docx` and must open as a valid Word document.
9. Non-target content must remain preserved within the qualified operation profile.
10. Foundation UI highlighting is review metadata. It must not require inserting Word highlight formatting into the downloaded DOCX unless a separate review-output option is explicitly added later.

## 3. First implementation scope

This vertical slice is intentionally bounded. It should prove the end-to-end product mechanics before expanding to full Local File automation.

### Business Target group A: Reporting / engagement context

Candidate targets:

- reporting fiscal year / year-ended date;
- configured company/entity label where supported by approved current evidence;
- current-year identifiers needed by the in-scope sections.

The exact source authority must be declared per target. Do not infer legal facts from historical text.

### Business Target group B: Section 4 Related Party Transactions

The initial current source is the configured FA&RPT / RPT source.

Foundation must be able to preserve and map the relationship:

```text
Transaction
→ Related Party
→ Country / relationship where required
→ Current-year Amount
→ percentage / supporting value where configured
```

The bounded representative transaction set should include multiple transaction categories so the slice proves row-level mapping rather than a single hard-coded value.

Foundation must compare current-year transactions with the prior-year Local File to identify:

- same transaction with changed amount;
- new transaction;
- removed transaction;
- changed related party;
- changed relationship/context;
- narrative that may require a proposal instead of deterministic replacement.

Deterministic fields may be mapped by rules. Narrative changes require human review.

### Business Target group C: Current client NCP / profitability context

The current-year client result may be mapped from the approved FA / Financial Analysis source when source authority and calculation context are sufficient.

The slice should preserve the Business Target relationship:

```text
Metric label
→ calculation/index context
→ period
→ current value
```

Do not treat full current-year benchmarking as in scope for this first slice.

### Business Target group D: Section 7 Financial Information

Initial scope should support deterministic current-year financial table values needed by the Local File, including the configured labels and calculated profitability result.

Each proposed value must retain source lineage.

## 4. Historical Reference responsibility

The prior-year Local File is used to understand historical business meaning and representation, for example:

```text
Current source fact
→ what business concept did this represent last year?
→ where was this concept represented in the prior Local File?
→ which BusinessTargetID does it map to?
→ where does that BusinessTargetID belong in the current Template?
```

Historical values are not automatically authoritative for the current year.

Historical text may be proposed for carry-forward only when a versioned Workflow Profile rule explicitly allows it and current evidence does not contradict it. Any subjective/client-specific narrative remains human-controlled.

## 5. Target Template responsibility

The Template is the controlled document skeleton and output base.

Implementation should resolve Business Targets to semantic Target Regions first and then to exact native DOCX objects.

Do not rely solely on page number, paragraph index, table ordinal, section number or fuzzy text similarity as execution authority.

Preferred chain:

```text
BusinessTargetID
→ TargetContract / TargetRegion
→ SemanticReference
→ exact NativeLocator
→ ChangeProposal
```

Template version/hash must be pinned for execution.

## 6. Proposal and review model

Before mutation, every mapped change must be represented as a proposal that can expose, at minimum:

- Business Target;
- current target content/value;
- proposed content/value;
- current source evidence;
- historical reference evidence where relevant;
- target region / native target status;
- mapping rationale;
- conflict / missing-source warning;
- review status.

Required user decisions:

```text
Approve
Edit proposal
Reject
Request more source / resolve exception
```

`Edit proposal` invalidates prior authorization and produces a newly reviewable proposal/version.

## 7. Highlight / review requirement

The Foundation viewer must visibly identify mapped or changed regions before release.

A user should be able to select a highlighted region and understand:

```text
What changed?
Why is it changing?
Which Business Target is this?
Which current source supports it?
What did the historical Local File show?
Where in the Template will the change be executed?
Has the change been approved?
```

Highlight state belongs to Foundation review/audit metadata.

The clean downloaded First Draft DOCX should not contain artificial yellow highlighting merely because the Foundation UI highlighted a proposed change.

## 8. Controlled DOCX execution

Execution must start from a copy/version of the approved TARGET Template.

Conceptually:

```text
Template bytes/package
→ create governed output copy
→ apply ApprovedChangeSet through bounded native operations
→ save DOCX
```

Forbidden implementation shortcuts:

- generate a new DOCX from HTML/Markdown/plain semantic text;
- copy the prior-year Local File and call it the new output;
- use the completed current-year Golden file as a source;
- call legacy direct patch/writeback as the governed v2 authority;
- rewrite entire paragraphs/documents when an exact bounded native update is required and available;
- silently approximate an unsupported structural mutation.

## 9. Minimum native operation set for vertical slice

The first slice should qualify only the native operations actually needed by the selected Business Targets.

Likely examples include:

- replace text in exact run/paragraph region;
- replace text in exact simple table cell;
- replace supported content-control text where the Template uses it;
- bounded repeatable-row insertion/deletion only if Section 4 cannot be represented without structural row changes.

Do not widen capability pre-emptively. If row growth/shrinkage is required and no governed operation exists, classify it as an explicit capability gap and stop the affected proposal.

## 10. Independent validation

Replay success alone does not make the First Draft releasable.

Post-execution validation must check, at minimum:

- output package opens as valid DOCX;
- output is derived from the correct pinned Template version;
- every approved target reached exactly one allowed native object;
- approved value/content is present after execution;
- protected/non-target regions did not change beyond allowed package-level differences;
- no unapproved change occurred;
- conflict/exception cases were not silently executed;
- audit lineage remains reconstructable.

If any release-critical validation fails, output remains staged and is not downloadable as released First Draft.

## 11. Golden evaluation rule

The completed current-year Local File may be used only to compare expected outcome characteristics during evaluation.

It must never be loaded into the execution context as:

```text
source
historical reference
target
mapping authority
fallback content
```

Any code path that makes Golden content available to runtime mapping/execution must fail qualification.

## 12. Vertical-slice success criteria

This slice is successful only when an end user can complete the following flow:

```text
Select/receive approved Template
→ load prior-year Historical Reference
→ load current FA&RPT source
→ Foundation identifies bounded Business Targets
→ proposals are created with evidence
→ mapped regions are highlighted in review UI
→ user approves selected proposals
→ Foundation updates a copy of Template
→ Foundation validates the resulting package
→ user downloads a valid First Draft .docx
```

Business-quality requirements for the representative case:

- wrong-target mutation: 0;
- unauthorized mutation: 0;
- silent source conflict: 0;
- silently changed protected content: 0;
- all in-scope current-year deterministic values have traceable source evidence;
- Golden file is never used as execution authority;
- output format is DOCX;
- user-visible review shows the mapped/changed regions before release.

These are acceptance expectations for the bounded representative case, not claims about production-wide statistical performance.

## 13. Recommended implementation order

Implement in this order unless evidence proves a dependency requires change:

```text
A. Workflow case + role intake
B. Business Target definitions for bounded Section 4 / Section 7 / current NCP
C. Source fact normalization
D. Historical-reference matching / comparison
E. Target Template region resolution
F. ChangeProposal creation
G. Review/highlight projection
H. ApprovedChangeSet sealing
I. Bounded DOCX Replay
J. Independent validation
K. First Draft release/download
L. Audit reconstruction
```

Do not start with whole-document generation, free-form AI drafting, or broad generic Replay capability.

## 14. Phase boundary

This vertical slice does not claim the full GTPS Local File production workflow.

Deferred unless explicitly promoted by later evidence/versioned scope:

- complete current-year benchmarking refresh;
- complex diagrams / organization-chart regeneration;
- broad client-specific narrative automation;
- full feedback loop from First Draft to Final;
- support for every Local File template variant;
- production qualification across the engagement population.

The learning objective is:

> Can Foundation safely transform the approved Template into a reviewable and downloadable First Draft DOCX for the bounded high-value GTPS mapping scope, with exact traceability and human control?
