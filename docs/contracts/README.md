## Contract Status

**Status:** FROZEN  
**Version:** 0.1.0  
**Architecture Generation:** Foundation v2  
**Validated Baseline:** `8b6f6bba0e588ee0a7202ff98beb01259ffa25e6`

Formal freeze evidence:

`docs/contracts/CONTRACT_FREEZE_v0.1.md`

Foundation Contract v0.1 is the implementation baseline for Backend,
Frontend, Replay, Validation and Audit.

Implementation may not silently redefine contract semantics.



# Foundation Shared Contracts

This directory defines the shared language between:

- Foundation backend;
- frontend;
- AI semantic services;
- Controlled Replay Service;
- validation;
- audit.

These contracts are architecture boundaries.

Neither frontend nor backend may silently redefine contract semantics.

## Contract Ownership

The backend/domain architecture owns the canonical contract definitions.

Frontend consumes these contracts.

Changes that affect both sides require an explicit contract change.

## Versioning

Contracts must include a version when persisted or transmitted across
system boundaries.

Breaking changes require:

- documented migration;
- compatibility decision;
- contract tests.

## Current Contract Documents

- `domain-model.md`
- `status-model.md`
- `error-catalog.md`
- `event-model.md`
- `foundation.openapi.yaml`

## Principle

Domain status and error semantics must be defined here rather than
invented independently by individual services or UI components.