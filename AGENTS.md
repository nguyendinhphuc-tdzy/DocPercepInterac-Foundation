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

1. docs/CURRENT\_BASELINE.md
2. latest approved ADRs under docs/adr/
3. Foundation Implementation Plan dated 2026-09-07
4. consolidated research dated 2026-09-07
5. current contracts under docs/contracts/
6. current code
7. historical build plans and STATUS files

Historical files may contain superseded decisions.

Do not implement a historical decision merely because existing code uses it.

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



FOUNDATION CONTRACT FREEZE



Foundation Contract v0.1.0 is frozen.



Implementation must conform to:

docs/contracts/



Do not modify frozen contract semantics to make implementation easier.



If implementation evidence reveals a contract problem:

1\. stop;

2\. classify the issue;

3\. show evidence;

4\. assess impact;

5\. propose a versioned contract change;

6\. do not silently update the contract.

