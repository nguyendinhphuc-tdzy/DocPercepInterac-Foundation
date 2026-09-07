# ADR-003: MVP Must Be Vertically Complete

## Status

ACCEPTED

## Date

2026-09-07

## Context

Foundation is being built first for the Transfer Pricing Local File
Roll-Forward use case.

There is a risk that MVP scope could be interpreted as permission to
remove difficult architectural mechanisms purely to reduce development
effort.

That would invalidate the primary learning objective because a demo
that bypasses governance, evidence, validation, audit, capability
detection, or controlled replay does not test whether Foundation can
operate safely in a real enterprise workflow.

## Decision

Foundation MVP must be vertically complete.

MVP scope may reduce:

- number of supported business rules;
- number of supported target types;
- number of validated mutation operations;
- breadth of business use cases.

MVP scope must not remove a core production control layer merely to
reduce implementation effort.

## Mandatory MVP Architecture Layers

The MVP must include:

1. Document Capability Preflight
2. Semantic Perception
3. Native Identity Binding
4. Foundation Object Model
5. Target Contract
6. Local File Rule Pack
7. Source Requirement Model
8. Source Sufficiency
9. Evidence Layer
10. Mapping and Change Proposal
11. Bounded AI Semantic Assistance
12. Structured Exceptions
13. Human Review and Approval
14. ApprovedChangeSet
15. Mutation Ownership
16. Controlled Replay
17. Post-Execution Validation
18. Business Reconciliation
19. Lineage and Audit

## Unsupported Capability Policy

If a capability cannot yet be safely executed, the architecture must
still recognize it.

The system must return an explicit capability or exception status such
as:

```text
PROTECTED_OBJECT
UNSUPPORTED_NATIVE_OBJECT
EXECUTION_UNSUPPORTED

It must not silently ignore the requirement.

Format Scope
DOCX

DOCX controlled transformation is on the critical Local File MVP path.

XLSX

XLSX understanding is mandatory because Excel files are important
current-year evidence sources.

Native Excel enrichment must preserve business-critical information
such as formulas, names, tables, ranges, and workbook structure where
relevant.

XLSX writeback must be implemented if the selected Local File workflow
requires modified Excel output.

If current business requirements do not require XLSX output mutation,
the execution capability may remain non-active while retaining the
appropriate contracts and capability model.

PDF / Scan / Image

The architecture must support capability classification.

OCR or image-specific transformation must not be simulated if it has
not passed its validation gate.

MVP Principle

Reduce breadth, not architectural integrity.

Why

This ensures the MVP validates the actual Foundation thesis rather than
a simplified demo path.

Consequences

Initial implementation effort is higher than a conventional prototype.

However, results from the MVP will be meaningful for production
decisions.

Validation

The MVP is considered architecturally valid only if one business
workflow can run end-to-end through all mandatory control layers,
including valid partial/refusal outcomes.