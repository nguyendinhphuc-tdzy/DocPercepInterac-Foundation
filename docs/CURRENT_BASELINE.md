## Contract Baseline

Foundation Contract v0.1.0 is the frozen shared implementation contract.

See:

- `docs/contracts/CONTRACT_FREEZE_v0.1.md`
- `docs/contracts/domain-model.md`
- `docs/contracts/foundation.openapi.yaml`

Any implementation that conflicts with the frozen contract must be treated
as an implementation defect unless a formally approved contract change
supersedes the baseline.


# Document Processing Foundation — Current Architecture Baseline

**Effective date:** 2026-09-07  
**Status:** Current architecture authority  
**Scope:** Document Processing Foundation, including its pioneer Local File transformation workflow.

This file is the single current architecture baseline. It supersedes contradictory historical implementation decisions in `foundation/STATUS.md`, old Foundation Build Plans, old UI Specs and current prototype code. Historical artifacts remain available as records; their presence, implementation or passing tests do not make a superseded decision current.

This baseline defines required architecture and provisional technology choices. It does not assert that the architecture is implemented, that candidate engines are production-approved or that the evidence gates below have passed.

## Business Objective

Foundation is a **governed document transformation platform, not an autonomous AI document editor**. Its pioneer business workflow is Local File transformation, including controlled roll-forward of business information into a target document.

For each proposed change, the system must determine:

1. What exists in the document.
2. What business information requires change.
3. Whether sufficient authoritative evidence supports that change.
4. Which exact native document object is authorized to change.
5. What requires human review and what decision the reviewer approves.
6. How the approved change can be executed within supported capabilities.
7. How independent validation and audit evidence prove that no unauthorized change occurred.

Foundation custom code should focus on business rules, target contracts, source sufficiency, evidence governance, mapping, approval, audit, orchestration and validation. Generic document mechanics should use proven external engines; building another generic DOCX/XLSX parser or serializer is not the architecture direction.

## Current Architecture

**Perceive != Understand != Authorize != Locate != Execute.** These responsibilities must remain distinct, even when one workflow coordinates them.

| Stage | Required responsibility and output |
| --- | --- |
| Intake and capability detection | Register source and target binaries, their hashes and versions; detect format, native structures, protections and operation capabilities. Preserve the input needed for replay and audit. |
| Semantic perception | Use Docling-slim as the provisional semantic perception baseline. Produce semantic structure and references for understanding and evidence association. |
| Native enrichment and location | Inspect native structures through suitable external readers or engines. Supply information absent from semantic perception and resolve version-bound Native Locators. XLSX sources require native enrichment. |
| Business requirements | Apply the Local File Rule Pack and target contracts to determine what must change, what evidence is required and what must be preserved. Rules are deterministic where business policy is known. |
| Interpretation and mapping proposals | Relate authoritative source information to Business Target IDs. Deterministic rules apply known policy; bounded AI assistance may propose interpretations, mappings and drafts or analyze ambiguity. Proposals carry no mutation authority. |
| Source Sufficiency and Evidence Gates | Deterministically evaluate required information, source authority, provenance, applicable period, consistency and unresolved gaps. Record explicit outcomes and blocking reasons. |
| Human Review | Present proposed changes, evidence, ambiguities, capability restrictions and preservation requirements. Record explicit approved, rejected or deferred decisions. |
| ApprovedChangeSet | Bind approved decisions to exact operations, payloads, targets, input versions, binary hashes, evidence and validation requirements. This is the only contract admitted to Controlled Replay. |
| Controlled Replay | Recheck approval, hashes, locators, evidence gates, protections and capabilities. Execute only authorized native operations against the approved document version using a qualified engine. |
| Independent validation and audit | Compare the result with the approved changes and preserved input. Verify intended changes and preservation outside their authorized scope; retain evidence and release only a validated result. |

Audit and exception handling span every stage. A blocked or rejected proposal remains traceable; it must not silently become an executable change. Failure of a replay or validation gate prevents release as a successful transformation.

### Three Separate Identities

Foundation must maintain all three identities and explicit relationships between them:

| Identity | Meaning | Authority and scope |
| --- | --- | --- |
| **Business Target ID** | The business field, requirement or target defined by a target contract or Rule Pack. | Identifies business intent; it is not a native execution address. |
| **Semantic/Docling Reference** | An ID in the semantic representation produced by perception. | Supports interpretation, navigation and evidence association within that representation. Docling references are semantic representation IDs, not native Office execution addresses. |
| **Native Locator** | The address and resolution constraints for the exact native object involved in an operation. | Document-version scoped and bound to the source binary hash of the document containing that object. Must resolve uniquely against that exact binary before execution. |

For a target mutation, the locator's source binary is the approved pre-mutation target document. Source-evidence locators similarly refer to the exact source binaries containing the evidence. Neither a Business Target ID nor a Docling reference may substitute for a Native Locator.

A binary or document-version change invalidates the prior locator's execution applicability. Re-perception, enrichment or remapping may propose a new binding, but must not silently reuse an old approval against the changed binary. A generated output is a new document version.

### ApprovedChangeSet and Replay Contract

An ApprovedChangeSet must make the following reviewable and auditable, with detailed schemas to be maintained under `docs/contracts/`:

- Approved business decisions, reviewer identity, approval time and approved change-set version.
- Business Target IDs, associated semantic references and exact Native Locators.
- Relevant source and target document versions and binary hashes, evidence references and deterministic gate results.
- Authorized native operations, their exact approved payloads, preconditions and permitted scope of change.
- Applicable Rule Pack and target-contract versions, capability requirements, protected content and required validation checks.

Changing an approved payload, operation, target binding or governing input invalidates the affected approval and requires renewed review. Human approval does not bypass insufficient evidence, an unsupported operation or a protected object. Only an ApprovedChangeSet may reach Controlled Replay, and its existence alone does not waive execution-time checks.

## Technology Baseline

| Technology | Current role | Qualification boundary |
| --- | --- | --- |
| **Docling-slim** | Provisional semantic perception baseline. | Semantic output must be evaluated against the pioneer corpus. Its references do not authorize or locate native Office mutations. |
| **Native XLSX enrichment** | Required alongside semantic perception for XLSX sources. | Docling may expose calculated values without sufficient native formula identity for governed processing. Capture native workbook, worksheet and cell identity, formulas and available calculated or cached values as distinct information, with provenance and limitations. |
| **Open XML SDK 3.5.1** | Provisional primary replay-engine candidate. | Supported operations and preservation guarantees require corpus evidence and independent validation. This selection is not blanket mutation support. |
| **docx4j 17.0.5** | Production challenger pending Golden Corpus A/B benchmark. | Compare against the primary candidate on the same relevant inputs, approved operations, preservation requirements and independent acceptance criteria. Production selection remains evidence-gated. |
| **python-docx / openpyxl** | May be retained as restricted readers or helpers. | They are not universal authoritative replay engines. Existing writeback paths do not establish approved execution support. |
| **Existing Foundation parser, anchor and writeback code** | Prototype/reference material for inspection, migration and evaluation. | It is not authoritative architecture. Reuse requires conformance to this baseline and evidence for the intended restricted role. |

Semantic extraction, native formula inspection and formula recalculation are different capabilities. Seeing a calculated value does not prove its formula identity, freshness or correctness. Formula and calculation limitations must be represented explicitly and block any operation whose evidence requirements cannot be met.

**Strict OOXML mutation is unsupported until explicitly validated.** Reader support, package recognition or an engine's general format support does not establish mutation support.

## System Authority Boundaries

- **Local File Rule Pack and target contracts:** Define what must change, what must remain, required business information and evidence policy. Known business policy is deterministic.
- **AI:** May assist only with bounded interpretation, mapping proposals, drafting, explanation and ambiguity analysis. AI cannot authorize document mutation, weaken governance gates or directly perform native document mutation.
- **Source Sufficiency and Evidence Gates:** Deterministic governance layers decide whether the required evidence conditions are satisfied. Plausibility, a model response or a generic confidence score cannot substitute for these checks.
- **Human Review:** Produces explicit approved decisions over concrete proposed changes and their evidence. A conversation, draft or unexplained acceptance flag is not an ApprovedChangeSet.
- **Native location and capability checks:** Establish that the exact approved object can be addressed uniquely and the operation is supported on the approved binary. They do not decide business intent.
- **Controlled Replay:** Executes only the operations admitted by an ApprovedChangeSet and successful preflight checks. It cannot invent changes or expand approved scope.
- **Independent validation:** Determines whether the produced artifact satisfies the approved changes and preservation requirements. An engine's success response cannot serve as the sole validation result.
- **Audit:** Preserves traceability from rule and source evidence through mapping, approval, execution, validation and exceptions. Logs or scores alone do not prove correctness.

## MVP Definition

MVP means **vertically complete architecture for the pioneer business use case**. Business breadth may be constrained by limiting document families, templates, target fields and qualified mutation types.

Governance, evidence, validation, audit, capability detection, exception handling, human approval and controlled replay must not be removed merely to reduce implementation effort. Each supported MVP transformation must traverse the complete governed path from intake through validated output and audit evidence.

A constrained capability matrix and explicit blocked cases are acceptable MVP boundaries. Treating unvalidated operations as supported, bypassing review or replacing preservation checks with a successful file-open test is not acceptable.

## Supported, Protected and Unsupported Concept

Capability is determined for a **document version, native structure, operation and engine combination**, not merely a filename extension or a library's ability to load the file.

| Classification | Meaning | Required behavior |
| --- | --- | --- |
| **Supported** | The specific operation on the detected structure has passed applicable qualification and has a unique locator, sufficient evidence and defined independent validation. | May execute only through an ApprovedChangeSet and successful replay checks. Support never implies automatic authorization. |
| **Protected** | An object or region must be preserved because of document protection, policy or the approved transformation's scope. | Do not mutate it; verify that it remains unchanged. If the requested operation cannot preserve it, block the operation. |
| **Unsupported** | The structure or operation is unknown, unqualified, unlocatable or cannot be reliably executed and validated. This includes Strict OOXML mutation until explicitly validated. | Fail closed for the affected operation and record an exception. No best-effort fallback mutation. |

The presence of a protected or unsupported structure does not by itself establish whether an unrelated operation is safe. That operation may proceed only where qualified preservation and independent validation demonstrate that the structure remains unaffected; otherwise it is blocked.

Foundation must fail closed on a stale document version or binary-hash mismatch, an ambiguous locator, an unsupported native structure or operation, insufficient source, a protected object targeted for mutation, or an unauthorized change detected by validation. An unresolved capability or validation result is not a pass.

Every supported mutation must pass independent post-execution validation. Checks must cover the approved business result, exact authorized change scope, relevant native structure and relationships, and preservation of protected and out-of-scope content. Any permitted serialization differences must be explicitly bounded by the validation contract. Retain input and output hashes, approval and execution records, and validation results as evidence. Opening the file successfully or obtaining a high confidence score is insufficient.

## Source-of-Truth Precedence

When sources conflict, apply this order:

1. `docs/CURRENT_BASELINE.md` — this current baseline.
2. Latest approved ADRs under `docs/adr/`, subject to this baseline.
3. Foundation Implementation Plan dated **2026-09-07**.
4. Consolidated research dated **2026-09-07**.
5. Current contracts under `docs/contracts/`.
6. Current code, as implementation evidence subject to the authorities above.
7. Historical Foundation Build Plans, UI Specs, `foundation/STATUS.md` and other historical status or design records.

Lower-priority material cannot override a higher-priority decision. Draft ADRs, historical completion claims and prototype behavior do not establish approval. A future approved architecture change must update this baseline so it remains the single current baseline.

At creation of this baseline, `docs/adr/`, `docs/contracts/`, `docs/implementation/` and `docs/research/` contain no files in this checkout. The precedence above defines the authority of those records when available; it does not imply they are already published or approved. Earlier evaluation artifacts may inform contract development but remain subordinate to this baseline.

## Superseded Decisions

The following historical decisions are **NOT current implementation authority**:

- **"Docling is removed".** Docling-slim is now the provisional semantic perception baseline.
- **Custom python-docx Geometry Layer as long-term perception baseline.** Existing custom perception code is prototype/reference material; prefer proven external engines for generic document mechanics.
- **Generic direct python-docx/openpyxl writeback.** Restricted readers/helpers may remain, but native mutation requires an ApprovedChangeSet, Controlled Replay through a qualified engine and independent validation.
- **Deterministic-only mapping with absolute exclusion of AI.** Deterministic rules govern known business policy; bounded AI semantic assistance and mapping proposals are allowed, subject to evidence gates and human review.
- **AI Agent as autonomous writeback authority.** AI cannot authorize or directly perform native document mutation.
- **Generic confidence score as proof of verification.** Verification requires explicit deterministic evidence checks and independent post-execution validation.
- **Semantic references or prototype anchors as universally valid native execution addresses.** Business Target IDs, Semantic/Docling References and Native Locators are separate; Native Locators are version-scoped and binary-hash-bound.
- **Direct UI edits, API patches or agent tool calls as sufficient authority to write a document.** All mutation entry points must be governed by the ApprovedChangeSet and Controlled Replay boundary.
- **Reduced MVP scope as grounds to omit governance or review.** Reduce business breadth while preserving the complete governed architecture.
- **Successful parsing, serialization or file opening as proof of supported mutation.** Support requires operation-specific evidence, preservation guarantees and independent validation; Strict OOXML mutation remains unsupported until explicitly validated.

These decisions are superseded wherever they appear, including in old plans, UI specifications, status reports and current prototype code. Historical files are not rewritten by this baseline.

## Current Open Evidence Gates

The following gates remain open under this baseline. No historical test count, demo result or candidate designation closes them automatically. Each gate requires recorded acceptance criteria, reproducible evidence, limitations and an explicit qualification decision in the appropriate approved records.

| Gate | Evidence required to close it | Consequence while open |
| --- | --- | --- |
| Pioneer scope, Rule Pack and target contracts | Approved business requirements, Business Target IDs, deterministic rules, required source roles, supported operations and preservation requirements for the constrained Local File workflow. | No implied coverage of all Local File fields, templates or document operations. |
| Docling-slim semantic perception | Representative corpus results for required structure and content, semantic reference behavior, omissions and downstream mapping needs. | Remains provisional; perception output alone establishes neither evidence sufficiency nor native addressability. |
| XLSX native enrichment | Demonstrated native formula and cell identity, distinction between formulas and calculated/cached values, provenance, and explicit handling of unsupported formula or calculation cases. | Calculated values alone cannot satisfy requirements that depend on native formula identity or verified calculation state. |
| Three-identity mapping and Native Locator contract | Reproducible target-to-semantic-to-native bindings, unique resolution and negative cases for duplicates, ambiguous structures, changed versions and binary-hash mismatches. | Unresolved or stale bindings cannot reach execution. |
| Source Sufficiency and Evidence Gates | Approved deterministic policies and positive and negative cases for authority, completeness, period, consistency, missing evidence and conflicting evidence. | Insufficient or unresolved evidence blocks the affected change. |
| Golden Corpus A/B replay-engine benchmark | Compare Open XML SDK 3.5.1 and docx4j 17.0.5 on the same relevant corpus and approved operations; assess fidelity, preservation, capability coverage, failure behavior and operational suitability using independent checks. | Primary candidate and production challenger remain provisional; no universal engine qualification is claimed. |
| Capability detection, protection and format boundaries | Operation-level capability matrix with representative supported, protected and unsupported cases, including reliable detection and fail-closed behavior. Strict OOXML needs explicit mutation qualification. | Unknown capabilities and Strict OOXML mutation remain unsupported. |
| Human approval and Controlled Replay | ApprovedChangeSet contract and evidence that only explicit, version-bound approved decisions execute; reject changed payloads, stale inputs, unsupported operations and attempted bypasses. | Prototype write paths are not production execution authority. |
| Independent validation and preservation | Checks that detect incorrect intended changes, unauthorized changes, structural damage and protected-content changes; demonstrated separation from replay self-reporting. | An output cannot be released as successfully transformed without passing required validation. |
| Audit, exceptions and complete MVP workflow | Traceable records from intake to release or rejection, preserved input/output identity, explicit blocked states, controlled recovery and a complete pioneer workflow demonstration. | Partial demonstrations do not establish vertically complete MVP readiness. |

Closing a gate must identify the exact scope qualified. Evidence for one format, structure, operation or document family does not automatically qualify another.
