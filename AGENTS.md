# Document Processing Foundation

## Mission

Build a governed document transformation platform.

The objective is not to build an AI chatbot that reads and rewrites Office
documents.

The system must determine:

1. what exists in the document,
2. what business information requires change,
3. whether sufficient authoritative evidence exists,
4. what exact native object is authorized to change,
5. whether a human must review,
6. how the approved change is executed,
7. how the system proves that no unauthorized change occurred.

## Source of Truth Priority

When documents conflict, use this precedence:

1. docs/CURRENT_BASELINE.md
2. accepted ADRs under docs/adr/
3. Frozen Foundation Contract v0.1 under docs/contracts/
4. current implementation plan / docs/PROJECT_PHASE.md
5. current supporting research
6. current implementation code
7. historical / superseded documents

Historical files may contain superseded decisions.

Do not implement a historical decision merely because existing code uses it.

## Current Product / Business Overview

Before designing product flows, frontend UX, Workflow Profiles, Business Targets,
or MVP use-case behaviour, read `docs/FOUNDATION_PRODUCT_OVERVIEW.md`.

That document captures the current product thesis, business pain points, stakeholder
direction, generic Foundation vs use-case-specific logic, technology direction and
MVP scope.

It is a product/business overview, not a contract authority. It must not override
`docs/CURRENT_BASELINE.md`, accepted ADRs or the Frozen Foundation Contract v0.1.

## GTPS Local File Pioneer Workflow

Before designing or implementing any GTPS Local File Roll-Forward behavior, read:

`docs/business/GTPS_LOCAL_FILE_WORKFLOW_PROFILE_v0.2.md`

This document is the current business/workflow interpretation for the pioneer Local File use case.
It defines the intended document roles, mapping logic, First Draft boundary, source-authority principles,
review/highlight requirement, and the distinction between governed transformation and whole-document generation.

For this workflow, the canonical interpretation is:

* the approved Local File Template is the `TARGET` / output base;
* the prior-year Local File is a `HISTORICAL_REFERENCE`, not the execution target;
* current-year FA&RPTs / Appendix I / FS / approved evidence are current sources according to the Workflow Profile;
* Foundation uses current sources plus historical context to identify Business Targets and map them into the TARGET Template;
* users must be able to review mapped/changed regions with visible traceability;
* only approved changes may mutate the TARGET;
* the downloadable First Draft is a derived version of the approved Template, not a newly AI-authored Office document.

Do not implement a "generate a new Local File from source documents" flow for this profile.
Do not copy the prior-year Local File and treat that copy as the default TARGET unless a future approved workflow version explicitly says so.

The GTPS Workflow Profile is use-case business guidance. It must not override higher-authority architecture or frozen contract documents.
If the Workflow Profile exposes a real contract gap, stop and follow the versioned contract-change process.

## Architecture Principles

Perceive != Understand != Authorize != Locate != Execute.

AI may assist semantic reasoning and proposal generation.

AI must not independently authorize or directly perform native document mutation.

All mutations require an ApprovedChangeSet.

Execution must fail closed when:

* document version is stale
* locator is ambiguous
* source is insufficient
* operation is unsupported
* object is protected
* validation detects unauthorized change

## MVP Definition

MVP means vertically complete architecture for the pioneer business use case.

Do not remove governance, evidence, validation, audit, capability detection,
exception handling, or human approval merely to reduce implementation effort.

Reduce business breadth, not architectural integrity.

## Engineering Rule

Prefer proven external engines for generic document mechanics.

Foundation custom code should focus on:

* business rules
* target contracts
* source sufficiency
* evidence governance
* mapping
* approval
* audit
* orchestration
* validation

Do not create another generic DOCX/XLSX parser or serializer.

## Before Changing Code

Always:

1. identify the requirement being implemented
2. identify affected contracts
3. inspect existing implementation
4. identify whether existing code is legacy/prototype
5. define tests first
6. implement
7. run relevant tests
8. report evidence of completion

Never claim success solely because the file opens.

## Foundation Contract Freeze

Foundation Contract v0.1.0 is frozen.

Implementation must conform to `docs/contracts/`.

Do not modify frozen contract semantics to make implementation easier.

If implementation evidence reveals a contract problem:

1. stop;
2. classify the issue;
3. show evidence;
4. assess impact;
5. propose a versioned contract change;
6. do not silently update the contract.
