# Foundation Project Phase

## Current Phase

Foundation v2 Implementation Phase

## Completed

- Research / Discovery
- Architecture Baseline
- ADR-001 to ADR-005
- Contract C1
- Contract C1.1
- Contract C2
- Contract C2.1
- Contract C3
- Foundation Contract v0.1 Freeze

### Completed Backend Workstream

B0 — Implementation Bootstrap — ACCEPTED

Accepted in PR #4, merge commit `b0f028e0b3de53debf99b38b898fbd7a9f7b9503`.

## Current Workstreams

### Backend

B1 — Capability Preflight + Semantic Perception + Native Identity

Current B1 iteration: **B1.2R Representative Local File Qualification**.
Current gate: **SME fidelity review — B1.2R remains OPEN**.

Accepted implementation baseline includes B1.0, B1.1 deterministic capability
preflight, resource-safe OOXML preflight, B1.1D bounded DEFLATE / OPC Growth Hint,
B1.2A synthetic Docling qualification, the B1.2R representative harness and its
explicit qualification-only preflight profile. These completed implementation
steps do not establish representative fidelity or production qualification.

Run-002 evaluated the approved five-case scope (three DOCX, two XLSX): preflight
completed, all fifteen conversions passed, input integrity passed, and all six
three-run repeatability dimensions passed per case. Human review is 0/5 and
coverage review remains pending. Recommendation: **INSUFFICIENT_EVIDENCE**.
Docling-slim 2.126.0 remains **PROVISIONAL_CONTINUE**; production_qualified=false.
See [current representative status](backend/B1_2R_REPRESENTATIVE_QUALIFICATION_STATUS.md).

### Frontend

U0 — Governed Workspace Bootstrap

- shared generated contract types
- UI state model
- workspace shell
- source readiness
- evidence / review
- exception UX
- approval UX

## Deferred Backend Work

- B1.2B — Production Docling Adapter
- B1.3 — Production Native Office Identity / Locator implementation
- B1.4 — Semantic → Native Binding
- B1.5 — Integrated B1 Qualification

Each requires explicit later authorization and its own evidence gates.

## Next Frontend Phase

U1 — Backend-integrated governed review workflow

## Not Yet Started

- business control plane
- ApprovedChangeSet materialization service
- controlled replay production implementation
- independent validation production implementation
- executor qualification
- E2E Local File MVP validation
- production hardening

## Current delivery references and P0 scope

Status synchronized on 2026-09-14 from planning baseline
`f29e218976b597100eb8e056055df647f3ab7305`; its prior runtime baseline remains
`41c92f7c775b12bf2dac5cf3091924d7dc293d24`.
The latest delivery documents are:

- [Implementation Plan v2.1](implementation/Foundation_Implementation_Plan_MVP_v2_1_2026-09-14.md)
- [Research Baseline v2.1](research/Foundation_Research_Baseline_v2_1_2026-09-14.md)
- [Backend Spec v1.0](backend/Foundation_Backend_Spec_MVP_v1_0_2026-09-14.md)
- [Frontend Spec v1.0](ui/Foundation_Frontend_Spec_MVP_v1_0_2026-09-14.md)

These documents do not override Frozen Contract v0.1.0. P0 working decisions
and the explicit precedence reconciliation are recorded in
[P0 Business Working Logic](decisions/P0_BUSINESS_WORKING_LOGIC_2026-09-14.md).
[Five-target learning scope](implementation/FOUNDATION_VERTICAL_SLICE_SCOPE_v0.1.md)
is locked; source authority, mandatory policy and exact native bindings remain
separate approval/qualification gates. No P2–P7 runtime implementation begins
in this documentation task. U0 remains the frontend workstream; U1 is deferred.
