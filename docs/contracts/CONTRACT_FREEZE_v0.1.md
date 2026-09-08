# Foundation Contract v0.1 Freeze Record

## Status

FROZEN

## Contract Version

0.1.0

## Architecture Generation

Foundation v2

## Freeze Date

2026-09-08

## Validated Baseline Commit

8b6f6bba0e588ee0a7202ff98beb01259ffa25e6

## Validation Evidence

GitHub Actions Workflow:
Foundation contract validation

Workflow Run:
34180805394

Result:
PASS

Validated gates:

- OpenAPI 3.1: PASS
- Behavioral fixtures evaluated: 8/8
- Schema validation: 8/8 PASS
- Reference validation: 8/8 PASS
- State-machine validation: 8/8 PASS
- Governance validation: 8/8 PASS
- Hash validation: 8/8 PASS
- Behavioral validation: 8/8 PASS
- Validator internal validation: 8/8 PASS
- Validator internal errors: 0
- Audit-event integrity hashes: 276/276 PASS
- Authorization digests: 8/8 PASS

## Frozen Scope

The following contract semantics are frozen for Foundation Contract v0.1:

- Domain model and record semantics
- BusinessTargetID / SemanticReference / NativeLocator separation
- DocumentVersion immutability and binary hash locking
- Document capability and preflight contracts
- Target Contract definition/instance separation
- Source Requirement and Source Sufficiency semantics
- Evidence model and deterministic evidence gates
- Local File Rule taxonomy
- MappingProposal and ChangeProposal authority boundaries
- AI authority boundary
- Human ReviewDecision semantics
- ApprovedChangeSet execution boundary
- ReplayRequest restrictions
- Controlled replay authorization semantics
- Validation independence from replay
- Error taxonomy
- Audit-event model
- State-machine semantics
- Partial-success behavior
- Fail-closed unsupported behavior
- OpenAPI 3.1 machine projection
- C2-01 through C2-08 behavioral expectations

## Explicitly Not Frozen

This freeze does not qualify or freeze:

- Docling as a production-qualified semantic engine
- Open XML SDK as the final production replay engine
- docx4j qualification outcome
- Golden Corpus executor results
- Real-world Local File rule coverage
- AI provider or model selection
- Production deployment architecture
- Database implementation
- UI implementation
- Security implementation
- Performance or availability SLOs

Those decisions require implementation and evaluation evidence.

## Authority

The architecture authority order remains:

1. docs/CURRENT_BASELINE.md
2. Accepted ADRs
3. Foundation Contract v0.1
4. Implementation
5. Historical documents

Runtime code must conform to the frozen contract.

Implementation must not silently redefine contract semantics.

## Change Control

After this freeze:

### Documentation-only clarification

Allowed without changing Contract version only when:

- no machine schema changes;
- no enum changes;
- no lifecycle changes;
- no behavioral expectation changes;
- no authority boundary changes.

Contract CI must remain green.

### Backward-compatible contract extension

Requires:

- explicit contract change proposal;
- updated Domain Model;
- updated OpenAPI;
- updated validator where required;
- new or updated behavioral fixture;
- CI PASS;
- new Contract version.

### Breaking or material semantic change

Examples:

- changing execution authority;
- changing identity semantics;
- changing Source Sufficiency behavior;
- changing ApprovedChangeSet boundary;
- changing AI authority;
- changing state-machine meaning;
- allowing fuzzy execution;
- changing validation/release semantics.

Requires:

- documented issue/evidence;
- impact analysis;
- ADR or superseding ADR when architectural;
- new Contract version;
- migration strategy;
- behavioral regression coverage;
- CI PASS.

The frozen v0.1 baseline must remain historically reproducible.

## Core Freeze Principle

Perceive != Understand != Authorize != Locate != Execute.

Similarity may determine where to investigate.

Evidence and governance determine whether a change is trustworthy.

Only an ApprovedChangeSet may authorize controlled replay.