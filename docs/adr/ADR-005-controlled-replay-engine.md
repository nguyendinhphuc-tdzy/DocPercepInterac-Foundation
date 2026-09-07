# ADR-005: Provisional Controlled Replay Baseline

## Status

PROVISIONAL

## Date

2026-09-07

## Context

Foundation requires deterministic, auditable native document mutation.

The executor must:

- target exact native objects;
- operate only on approved changes;
- preserve non-target content;
- detect unsupported structures;
- support post-execution validation;
- minimize mutation blast radius.

Research evaluated:

- python-docx;
- openpyxl;
- direct OOXML patching;
- Open XML SDK;
- docx4j;
- Apache POI;
- commercial Office libraries.

python-docx and openpyxl may perform narrow mutations successfully, but
their abstraction and unsupported-object behavior are insufficient to
treat them as universal authoritative replay engines.

Direct OOXML patching gives excellent mutation granularity but would
require Foundation to build and maintain another generic Office engine.

Open XML SDK and docx4j are the strongest current candidates.

## Decision

Open XML SDK 3.5.1 is the provisional primary Controlled Replay
candidate.

docx4j 17.0.5 remains the production challenger.

This is not yet a final technology decision.

## Open XML SDK Safe Profile

Foundation must not rely on default broad package save behavior.

The current mutation profile is Transitional OOXML only until other
conformance classes are explicitly qualified. Strict OOXML mutation
remains unsupported until explicitly validated.

The candidate execution profile is:

```text
AutoSave = false
MarkupCompatibility = NoProcess
version/hash locked source document
target part only
explicit target Save()
staging file
post-execution validation
atomic commit
```

## Replay Boundary

The Replay Service receives only an ApprovedChangeSet.

It must not:

- perform business mapping;
- decide evidence sufficiency;
- invoke AI to resolve a locator;
- decide whether a business change is appropriate.

It owns only safe mechanical execution.

## Initial Mutation Vocabulary

Examples:

```text
REPLACE_RUN_TEXT
REPLACE_SDT_TEXT
REPLACE_SIMPLE_TABLE_CELL_TEXT
```

Additional operations must be added only after Golden Corpus validation.

## Protected by Default

Examples include:

- tracked changes;
- complex fields;
- complex mathematics;
- drawings;
- charts;
- macros;
- unsupported table structures;
- Strict OOXML;
- unknown native constructs.

Readable does not imply mutable.

## Required Validation

Post-execution validation must be independent from the replay engine.
The replay engine's own success report cannot establish validation
success or authorize release.

Every replay must support:

- document hash validation;
- locator resolution;
- precondition validation;
- schema/package validation;
- package blast-radius analysis;
- intra-part blast-radius analysis;
- protected-object preservation;
- independent semantic re-perception;
- business postcondition reconciliation.

## Decision Gate

This ADR may become ACCEPTED only after Open XML SDK and docx4j are
tested against the same Golden Executor Corpus.

The benchmark must include at minimum:

- NO_OP;
- rich text;
- content controls;
- bookmarks;
- fields;
- tables;
- headers/footers;
- tracked changes;
- drawing/image;
- AlternateContent;
- Strict OOXML.

## Winner Criteria

Selection must consider:

- mutation correctness;
- unauthorized mutation;
- preservation;
- validation;
- Office construct coverage;
- integration complexity;
- maintainability;
- license;
- operational TCO.

Technology popularity alone is not a decision criterion.
