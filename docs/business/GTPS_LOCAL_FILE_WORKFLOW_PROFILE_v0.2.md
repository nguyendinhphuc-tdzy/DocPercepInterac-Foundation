# GTPS Local File Workflow Profile v0.2

> Status: Business / Workflow Profile baseline for the GTPS Local File pioneer use case.
>
> This document defines use-case-specific business logic. It does **not** override `docs/CURRENT_BASELINE.md`, accepted ADRs, or Frozen Foundation Contract v0.1.
>
> The generic Foundation must remain reusable. GTPS-specific rules belong in a versioned Workflow Profile, Business Targets, source requirements, mapping rules, and validation obligations rather than being hard-coded into generic core behavior.

## 1. Product intent

The GTPS Local File use case is **not** a whole-document generation problem.

Foundation must not behave like a general-purpose AI assistant that reads several inputs and rewrites a new Local File from scratch.

The intended behavior is governed document transformation:

1. take an approved Local File template as the **TARGET** document;
2. take the prior-year Local File as a **HISTORICAL SEMANTIC REFERENCE**;
3. take current-year FA&RPTs / Appendix I / FS and other approved documents as **CURRENT SOURCES / EVIDENCE**;
4. use prior-year content to understand the business meaning and historical representation of current-year facts;
5. map each approved Business Target to the corresponding region/object in the TARGET template;
6. present proposed mapped changes to the user with visible highlight / traceability;
7. execute only approved changes on a copy/version of the TARGET template;
8. validate that intended changes are correct and non-target content is preserved;
9. release the resulting updated template as the downloadable **First Draft Local File**.

The output is therefore a **derived version of the approved template**, not an AI-regenerated document.

## 2. Canonical document roles

| Artifact | Workflow role | Purpose | Prohibited assumption |
|---|---|---|---|
| Approved Local File Template | `TARGET` | Output base / structural container / controlled wording baseline | Do not treat it as a data source for client-specific current-year facts |
| Prior-year Local File | `HISTORICAL_REFERENCE` | Historical business context, wording, section relationships, previous target representation | Do not treat prior-year values as current-year authority |
| Current-year FA&RPTs | `CURRENT_SOURCE` | Structured current-year FA and RPT data, calculations and business facts within approved scope | Do not assume it is authoritative for every narrative/legal/contract fact |
| Appendix I | `CURRENT_SOURCE` or upstream structured source | Current-year RPT/FA source where available | Do not require it for every engagement |
| Financial Statements | `UPSTREAM_SOURCE` | Source for extraction when Appendix I / structured working file is unavailable or requires verification | Do not silently prefer extracted FS data over an already confirmed higher-authority source |
| Contract / client confirmation / legal documents | `SUPPORTING_EVIDENCE` | Authority for contract terms, legal facts, new/changed transaction narrative, subjective information | Do not infer these facts solely from historical wording |
| Benchmarking file | `CURRENT_BENCHMARK_SOURCE` | Current-year benchmarking / arm's-length range for later draft stage | Full current-year benchmarking is not required for MVP First Draft unless explicitly configured |
| Expected/Final Local File used for evaluation | `GOLDEN_EVALUATION_ONLY` | Qualification/evaluation benchmark | Strictly prohibited as an execution input source |

### Key invariant

```text
TARGET Template != Prior-year Local File

Prior-year Local File = semantic/historical reference
TARGET Template      = document that will be transformed
Current Source       = evidence used to propose current-year values/content
```

## 3. Why the prior-year Local File is still required

Current-year structured sources often contain values without enough information to determine the exact Local File business target or wording context.

The prior-year Local File acts as a semantic bridge:

```text
Current Source Fact
        ↓
Historical representation / business context
        ↓
Business Target identity
        ↓
Corresponding region in current TARGET Template
        ↓
Exact Native Locator
        ↓
Change Proposal
```

Example conceptually:

```text
Current FA&RPT fact:
Processing Services amount = <current value>
        ↓
Prior-year Local File establishes:
"Provision of processing services" is the Transaction under Review
        ↓
BusinessTargetID:
RPT.PROCESSING_SERVICES.AMOUNT
        ↓
Template region for Section 4 transaction table
        ↓
Exact target cell
        ↓
Proposed value
```

Foundation must map by business meaning / Business Target, not simply by section number, text similarity, or document position.

## 4. Conditional source-entry routes

The Workflow Profile must not assume one universal starting source.

### Route A: Appendix I / structured source available

```text
Appendix I available
        ↓
Simple engagement: bounded direct mapping where approved
        or
Standard engagement: compile/use FA&RPTs
        ↓
Local File mapping
```

### Route B: Appendix I unavailable

```text
Financial Statements + other approved information
        ↓
Extract FA + RPT
        ↓
Create / confirm structured FA&RPTs working source
        ↓
Local File mapping
```

The generic Foundation Extraction layer must therefore support multiple source types. The GTPS Workflow Profile determines which source role is required for each Business Target.

## 5. First Draft business boundary

MVP1 targets a **First Draft Local File**, not a final submission-ready Local File.

First Draft means an approved TARGET template has been populated/updated for the bounded current-year scope, with reviewer-visible evidence and change traceability.

The MVP must prioritize the repetitive, deterministic, high-risk update work before broadening into later-stage analysis and finalization.

### MVP1 in scope

- multi-file intake and document-role assignment;
- pre-flight / version / source sufficiency checks;
- FA and RPT extraction from approved current-year source(s);
- Business Target mapping from source → historical reference → target template;
- deterministic numerical updates for bounded Section 4 and Section 7 targets;
- reporting-period and other explicitly configured scalar targets;
- bounded current-year client profitability/NCP target where source authority and rule are defined;
- limited AI-assisted narrative proposal for changed transactions/counterparties;
- source conflict surfacing;
- human review and approval;
- controlled mutation of exact target objects in the template;
- independent post-execution validation;
- downloadable First Draft output;
- audit and lineage;
- Foundation UI highlighting for mapped/changed regions.

### MVP1 explicitly not claimed

- full current-year benchmarking workflow;
- complete industry analysis;
- complex diagram/chart regeneration;
- full appendix automation;
- full client feedback lifecycle;
- final engagement sign-off;
- autonomous business judgment;
- whole-document AI regeneration.

## 6. Section-level business logic

### 6.1 Section 4: Related Party Transactions

Primary current-year source is the configured RPT/APT/Appendix I source.

Required bounded processing pattern:

```text
Extract transactions
→ normalize transaction / party / amount
→ classify Transaction under Review vs Other RPT
→ group / sort / calculate configured subtotal(s)
→ compare current vs prior-year business structure
→ identify new / removed / changed transaction or counterparty
→ map deterministic fields to Business Targets
→ create narrative proposal only where semantic reasoning is required
```

Rules:

- amounts and deterministic classifications must not be invented by AI;
- a changed/new counterparty may trigger AI-assisted draft wording, but human approval is required;
- new or conflicting contract terms require supporting evidence;
- row growth/shrinkage in the template is a structural capability question and must fail closed if the required operation is unsupported.

### 6.2 Section 6: Benchmarking / Economic Analysis

Current-year benchmarking comes from a separate approved Benchmarking source, not from FA&RPTs by default.

For the First Draft profile, the normal bounded rule is:

```text
retain approved prior-year benchmarking analysis/data where business process permits
+
update only explicitly approved current-year client result(s)
```

Full current-year benchmark update belongs to a later draft stage unless explicitly enabled by a future Workflow Profile version.

### 6.3 Section 7: Financial Analysis

Primary source is the configured FA worksheet / approved financial source.

This is primarily deterministic mapping:

```text
Current financial source
→ normalized business facts
→ Business Targets
→ exact template regions/cells/paragraphs
→ proposal
→ approval
→ controlled write
```

Section 7 is a preferred MVP target because source/target relationships are generally more deterministic than open-ended narrative drafting.

## 7. Source authority is target-specific

There is no global rule such as "newest file wins" or "FA&RPT always wins".

Authority must be evaluated per Business Target.

| Business fact / target | Preferred evidence category |
|---|---|
| RPT amount | confirmed Appendix I / RPT / FA&RPT source configured for the engagement |
| Financial value | confirmed FA worksheet and/or FS lineage according to source policy |
| Current-year NCP / profitability result | approved financial analysis calculation / source policy |
| Contract number / contract term | contract or explicit client confirmation |
| Legal company information | current legal/client source |
| Employee count / organization fact | approved current-year client evidence |
| Current benchmarking range | approved Benchmarking file |
| Controlled regulatory/template wording | approved current template / guidance source |
| Subjective narrative | supporting evidence plus human review/confirmation |

If sources conflict or evidence is insufficient, Foundation must not silently select a value. It must create a structured exception / source request / human decision path.

## 8. Mapping model

For each bounded change, the logical chain is:

```text
Source Fact
→ Source Evidence / Authority Assessment
→ Business Meaning
→ Historical Reference Context
→ BusinessTargetID
→ TargetContract / TargetRegion in Template
→ Exact NativeLocator
→ ChangeProposal
→ Human Review
→ ApprovedChangeSet
→ Controlled Replay
→ Independent Validation
```

Important separations:

```text
BusinessTargetID != SemanticReference != NativeLocator

Perceive != Understand != Authorize != Locate != Execute
```

No AI mapping confidence is sufficient to authorize mutation.

## 9. Target template management

The Target Template may be:

1. uploaded/selected by the user, or
2. locked by the GTPS Workflow Profile for an MVP/approved process.

Hard-coding/locking an approved template is acceptable for the bounded GTPS MVP if template variability is intentionally reduced.

A locked template must still be versioned and integrity-bound, for example:

```text
workflow_profile = GTPS_LOCAL_FILE
profile_version   = 0.2
approved_template = GTPS_LOCAL_FILE_TEMPLATE
version           = <version>
sha256            = <exact hash>
```

A template revision must create a new version / target contract context. Foundation must not silently replace the approved template.

## 10. Output semantics

Foundation must not serialize a newly authored document from semantic text.

Execution must operate on the governed TARGET template version using bounded native operations.

Conceptually:

```text
Approved Template bytes/structure
        ↓
Approved ChangeSet only
        ↓
Exact native mutation
        ↓
Post-execution validation
        ↓
Derived TARGET version
        ↓
First Draft Local File
```

Untouched content is expected to remain untouched within the capability/validation guarantees of the supported operation profile.

Unsupported operations must be refused rather than approximated by whole-document regeneration.

## 11. User review and highlight requirement

The user must be able to see which regions of the resulting/proposed document are mapped or changed.

Highlighting is a review/audit surface, not merely UI decoration.

For a changed region, the review surface should be capable of showing:

- Business Target;
- source document and source location/evidence reference;
- historical reference where relevant;
- current/existing target value;
- proposed value/content;
- mapping rationale/status;
- review/approval status;
- warnings, conflicts or missing evidence.

Preferred product behavior:

- highlight mapped/changed regions in the Foundation viewer using overlay/annotation state;
- keep the downloadable First Draft clean unless a separate "review-highlighted draft" output is explicitly requested;
- do not mutate Word highlighting purely to implement the Foundation UI review state.

## 12. Human control points

Human decision is required when relevant for:

- conflicting sources;
- new/changed transaction narrative;
- subjective information;
- client-specific wording;
- unsupported/ambiguous target mapping;
- insufficient evidence;
- edited AI proposal;
- final First Draft acceptance/release.

AI may assist with semantic comparison, classification, mapping proposals and narrative drafting, but it must not independently authorize or execute a native document change.

## 13. Acceptance principles for MVP1

The MVP is successful only if it proves governed transformation, not merely content generation.

Key quality expectations:

- deterministic FA/RPT values map to the correct Business Targets;
- intended target locations are exact and auditable;
- source lineage is preserved;
- ambiguous/conflicting mappings fail closed;
- unauthorized changes = 0 in tested protected scope;
- wrong-target mutations = 0 in qualified operation profiles;
- non-target content is preserved according to post-execution validation;
- user can review highlighted proposed/changed regions before release;
- resulting First Draft is downloadable as a usable Office document.

Do not convert these into unsupported statistical claims without representative evidence.

## 14. Known open decisions / assumptions

The following remain configuration/discovery questions and must not be silently hard-coded as universal GTPS truth:

- exact percentage/frequency of Appendix I availability across engagements;
- direct Appendix I → Local File cases vs mandatory FA&RPT intermediary;
- full source precedence when Appendix I, FA&RPTs, FS, contracts and client confirmations disagree;
- exact definition of "First Draft sufficient for Senior review" for every engagement type;
- exact set of Section 6 current-year client metrics required in First Draft;
- template variation by client/PIC/year;
- which structural mutation profiles must be supported for repeatable RPT/financial table rows;
- which narratives may be carried forward automatically vs require explicit confirmation.

These should be validated through representative cases and working-level GTPS feedback.

## 15. Engineering / agent interpretation rule

When implementing the GTPS Local File Workflow Profile, do **not** describe the feature as "generating a Local File from source documents" without qualification.

Use the following canonical wording:

> Foundation takes an approved Local File template as the Target, uses current-year sources plus the prior-year Local File to determine business mappings, proposes and highlights controlled changes, and applies only approved changes to the Target template to produce a downloadable First Draft.

The core architectural identity of Foundation for this use case is:

> **governed document transformation engine, not whole-document AI generation.**

## 16. Relationship to existing research/evaluation artifacts

Existing Local File capability/evaluation documents may contain earlier assumptions or technical prototypes. Interpret them through this Workflow Profile where they do not conflict with higher-authority architecture/contract documents.

In particular, the existing Local File capability matrix that classifies the approved Template as `Target Container & Structural Schema`, prior-year Local File as `Historical Baseline`, current FA&RPT as current data source, and final FY2024 Local File as evaluation-only ground truth is directionally aligned with this profile.

Do not use legacy direct writeback paths as governed execution authority. Mutation for this Workflow Profile must eventually flow through proposal → human review → ApprovedChangeSet → controlled replay → validation.