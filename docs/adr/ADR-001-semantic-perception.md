# ADR-001: Adopt External Semantic Perception Engine

## Status

ACCEPTED

## Date

2026-09-07

## Context

Foundation must understand the semantic and structural content of
enterprise documents before business mapping, evidence verification,
review, or controlled transformation can occur.

The existing Foundation prototype contains custom document parsing and
geometry logic. Research has shown that maintaining a generic Office
semantic parser is not the business differentiation of Foundation and
would introduce unnecessary maintenance, format coverage, regression,
and compatibility risk.

Docling-slim has been researched as a strong candidate for semantic
document perception.

However, Docling's representation is not lossless relative to the
native Office package and its internal references are not stable native
execution addresses.

## Decision

Foundation will use Docling-slim as the provisional semantic perception
baseline for supported digital documents.

Docling is responsible for:

- document semantic structure;
- paragraphs and text objects;
- tables;
- hierarchy;
- relationships represented by the Docling model;
- normalized semantic representation.

Foundation remains responsible for:

- native Office identity;
- business target identity;
- target contracts;
- business rules;
- source sufficiency;
- evidence governance;
- mapping;
- approval;
- controlled execution;
- validation;
- audit.

Foundation must not treat a Docling reference as a native Office
mutation address.

## Architectural Boundary

```text
Native Document
      ↓
Docling
      ↓
Semantic Representation
      ↓
Foundation Semantic Adapter

A separate Native Office View must provide execution identity and
Office-specific information not preserved by Docling.

Why

This decision:

reduces custom parsing logic;
benefits from an external maintained engine;
gives Foundation a richer semantic representation;
keeps Foundation focused on differentiated business governance;
prevents the project from recreating a generic document-processing
engine.
Alternatives Considered
Custom python-docx/openpyxl parser

Rejected as long-term semantic baseline.

It remains useful for restricted native inspection or helper operations,
but Foundation should not maintain a second generic semantic engine.

Fully custom OOXML parser

Rejected.

This would recreate a large and fragile Office parsing stack with low
business differentiation.

LLM/VLM-only document understanding

Rejected as the core perception layer.

Semantic interpretation by AI may complement deterministic document
perception, but it must not replace structural parsing and provenance.

Consequences

Foundation must maintain an adapter between Docling objects and the
Foundation domain model.

Additional native readers are required for information such as:

Word content-control identity;
bookmarks;
fields;
revision structures;
Office relationships;
Excel formulas;
defined names;
tables;
native sheet/cell identity.
Risks
Docling version changes may alter output structures.
Some Office constructs may not be represented with enough fidelity.
Semantic references may change after re-perception.
Controls
pin exact production dependency versions;
maintain a Golden Perception Corpus;
regression-test every dependency upgrade;
never use semantic references as execution addresses.
Validation

This ADR remains accepted as long as Golden Corpus evaluation confirms
that Docling provides sufficient semantic perception for Foundation
business workflows.

Individual unsupported constructs must be represented through
capability detection rather than silently ignored.

Supersedes

Historical architecture decisions that removed Docling and treated
custom python-docx/pdfplumber parsing as the long-term Foundation
semantic baseline.