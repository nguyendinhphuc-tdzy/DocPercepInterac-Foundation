# Foundation Architecture Decision Records

This directory contains the active Architecture Decision Records (ADRs)
for Document Processing Foundation.

## Authority

Architecture decisions must be interpreted using the following precedence:

1. `docs/CURRENT_BASELINE.md`
2. Accepted ADRs in this directory
3. Provisional ADRs in this directory
4. Current shared contracts under `docs/contracts/`
5. Current implementation
6. Historical documentation and prototype code

Historical Build Plans, STATUS files, previous UI specifications, and
prototype implementations may contain superseded decisions.

They are not implementation authority unless explicitly reaffirmed by
the current baseline or an active ADR.

## ADR Status

Each ADR must use one of:

- `ACCEPTED`
- `PROVISIONAL`
- `SUPERSEDED`
- `REJECTED`

`PROVISIONAL` means the architecture may be implemented behind a stable
contract, but the underlying technology decision remains subject to an
explicit validation gate.

## Change Policy

Do not silently change an accepted architecture decision.

If new evidence requires a change:

1. document the evidence;
2. create a new ADR;
3. mark the previous ADR as superseded;
4. identify migration impact;
5. update `docs/CURRENT_BASELINE.md` if necessary.

## Core Principle

> Perceive != Understand != Authorize != Locate != Execute

Foundation must keep these responsibilities explicitly separated.