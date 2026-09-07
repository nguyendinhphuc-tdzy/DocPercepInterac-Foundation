# ADR-004: Bound AI Authority and Separate Proposal from Decision

## Status

ACCEPTED

## Date

2026-09-07

## Context

Foundation requires semantic interpretation that is difficult to encode
fully through deterministic rules.

AI can provide material value for:

- semantic interpretation;
- mapping assistance;
- ambiguity analysis;
- comparison;
- drafting;
- explanation.

However, experiments have shown that general AI can also:

- infer conclusions without required evidence;
- continue despite recognized uncertainty;
- produce internally inconsistent updates;
- confuse historical evidence with current evidence;
- produce technically valid but business-invalid output.

Therefore AI must not become an uncontrolled authority.

## Decision

AI may assist reasoning but may not independently authorize native
document mutation.

## AI May

- interpret semantic meaning;
- classify document content;
- generate mapping candidates;
- compare prior and current information;
- identify potential inconsistencies;
- draft proposed wording;
- explain proposals;
- identify ambiguity;
- assist root-cause analysis.

## AI Must Not

- declare a missing source sufficient;
- determine source authority outside governed rules;
- override Source Sufficiency;
- approve its own ChangeProposal;
- silently resolve a stale document;
- use fuzzy matching as an execution fallback;
- mutate an Office document directly;
- bypass protected-object policy;
- bypass validation;
- rewrite audit history.

## Authority Chain

```text
AI Semantic Assessment
        ↓
Change / Mapping Proposal
        ↓
Evidence Verification
        ↓
System Governance Decision
        ↓
Human Approval where required
        ↓
ApprovedChangeSet
        ↓
Controlled Replay

Evidence Rule

AI-generated explanations are not independent audit evidence.

Audit evidence must reference real source objects, source versions,
rules, validation results, and decisions.

Context Traceability

Every material AI decision record must make it possible to identify:

model/provider;
model version where available;
prompt/instruction version;
structured input context;
referenced source objects;
structured AI output;
downstream verification result.
Failure Diagnosis

When an AI-related output is incorrect, the system must determine the
earliest incorrect stage rather than automatically classify the event
as an AI model failure.

Potential failure origins include:

source;
perception;
context construction;
semantic interpretation;
evidence verification;
mapping;
approval;
execution.
Consequences

AI functionality must communicate through typed domain contracts.

Direct AI-to-writeback shortcuts are prohibited.

Validation

Negative evaluation cases must include:

missing evidence;
conflicting sources;
stale evidence;
misleading historical context;
ambiguous mapping;
prompt injection in document content;
unsupported inference.

Correct abstention/refusal is a valid success outcome.