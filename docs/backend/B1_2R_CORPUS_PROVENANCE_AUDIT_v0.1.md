# B1.2R Corpus Provenance & Business-Role Audit v0.1

> Branch baseline: `91fe8a802156fe2d0b72250d6666944eb1881682`
>
> Purpose: verify that representative qualification evidence is bound to the correct business artifact, version and role before any SME fidelity conclusion is promoted.
>
> This document does not change the Frozen Foundation Contract v0.1, runtime capability, Docling qualification or existing Run-002 evidence.

## 1. Why this audit is now mandatory

The GTPS Local File Workflow Profile has been clarified at product/business level:

- Approved Local File Template = execution `TARGET` / output base.
- Prior-year Local File = `HISTORICAL_REFERENCE` used for semantic and mapping context.
- Current-year FA&RPTs / Appendix I / FS = current source/evidence according to target-specific authority rules.
- Final current-year Local File used for comparison = `GOLDEN_EVALUATION_ONLY`; it must never become an execution input.
- First Draft is a derived version of the approved Target Template after approved bounded changes. It is not a whole-document AI regeneration.

The authoritative workflow profile is merged on `master` in:

`docs/business/GTPS_LOCAL_FILE_WORKFLOW_PROFILE_v0.2.md`

The representative B1.2R branch intentionally remains isolated at its accepted baseline and must not be rebased merely to import this documentation. Read the profile from `master` when needed, for example with `git show origin/master:docs/business/GTPS_LOCAL_FILE_WORKFLOW_PROFILE_v0.2.md`.

## 2. Audit question

Before SME review, answer this for every representative case:

> Does this opaque case ID resolve to the exact intended business artifact/version, and is its qualification role consistent with the GTPS workflow role we intend to validate?

A repeatable semantic conversion of the wrong file is not valid qualification evidence.

## 3. Expected GTPS business artifacts for the current representative case family

The current GTPS example set is expected to contain the following business artifact types:

| Business artifact | Intended workflow role | Qualification purpose |
|---|---|---|
| Approved generic/current Local File template | `TARGET` | Prove Foundation can perceive the actual document that will be transformed and preserve business-relevant target structure |
| Prior-year completed Local File | `HISTORICAL_REFERENCE` | Prove Foundation can perceive historical business context needed to derive mapping meaning |
| Current-year FA&RPTs workbook | `CURRENT_SOURCE` | Prove Foundation can perceive current structured FA/RPT facts needed by bounded Business Targets |
| Prior-year structured workbook where retained in corpus | `HISTORICAL_SOURCE` | Comparison / representative spreadsheet perception only; not current authority |
| Current-year completed Local File | `GOLDEN_EVALUATION_ONLY` | Evaluation benchmark for expected business outcome and representative structure; strictly prohibited as execution input |

Do not infer these roles from filename alone. Verify the exact binary privately.

## 4. Candidate case-role mapping to verify, not assume

Current public Run-002 summary exposes these coarse evaluation categories:

- `LF-DOCX-001` = DOCX / `TARGET`
- `LF-DOCX-003` = DOCX / `TARGET`
- `LF-DOCX-004` = DOCX / `REFERENCE`
- `LF-XLSX-001` = XLSX / `SOURCE`
- `LF-XLSX-002` = XLSX / `SOURCE`

The following business-role interpretation is a **candidate requiring private verification**:

| Case ID | Candidate business artifact / role | Audit expectation |
|---|---|---|
| `LF-DOCX-001` | Approved Local File Template / `TARGET` | Expected to be the actual template/skeleton used as output base |
| `LF-DOCX-003` | Current-year completed Local File / `GOLDEN_EVALUATION_ONLY` | If true, current public `TARGET` category is too coarse and must not be interpreted as execution target |
| `LF-DOCX-004` | Prior-year completed Local File / `HISTORICAL_REFERENCE` | Expected to provide prior-year semantic context |
| `LF-XLSX-001` | Historical structured workbook / `HISTORICAL_SOURCE` | Verify exact year/purpose privately |
| `LF-XLSX-002` | Current-year FA&RPTs / `CURRENT_SOURCE` | Expected to contain current-year FA/RPT values used for bounded mapping |

Do not modify the manifest or schema until the private binary mapping has been verified.

## 5. Provenance evidence required per case

Privately record/verify, without publishing sensitive values:

- opaque case ID;
- exact resolved private path;
- file format;
- exact byte size;
- SHA-256;
- intended business artifact role;
- relevant fiscal period / template version where applicable;
- current manifest `document_role`;
- whether role is acceptable as a qualification-only coarse category;
- whether the case can remain in the current reviewed scope;
- whether existing Run-002 evidence is still valid for that exact binary.

The public repository must not contain private paths, client filenames, input hashes, source text or reviewer-private notes.

## 6. Decision rules

### PASS: identity and role verified

Use existing Run-002 evidence only when:

1. the private manifest resolves to the intended exact binary;
2. the Run-002 `input_sha256` matches that binary;
3. the business role is understood and does not cause misleading qualification interpretation;
4. the artifact remains part of the intended bounded representative scope.

SME review may then proceed for that case.

### ROLE_CLARIFICATION_REQUIRED

If the exact binary is correct but the existing coarse public category (`TARGET`, `REFERENCE`, `SOURCE`) is misleading relative to the GTPS workflow role:

- preserve Run-002 binary/semantic evidence;
- do not reinterpret the category silently;
- propose a versioned evaluation-schema/summary clarification such as separate non-sensitive `business_role_category` metadata;
- recompute coverage scope only if a scope-bound manifest field actually changes.

Do not automatically force a new Docling run if only non-evidence documentation semantics change.

### BINARY_MISMATCH

If the private binary differs from the artifact intended for qualification:

- stop SME review for that case;
- preserve Run-002 unchanged as historical evidence;
- correct the private manifest in a new immutable qualification scope;
- recalibrate qualification-only preflight limits if required by the replacement binary;
- create a new run identity; never overwrite Run-002;
- bind all new review evidence to the new input hash and observation digest.

### WRONG_ARTIFACT_MAPPING

If an opaque case ID resolves to the wrong business artifact entirely:

- treat Run-002 evidence for that case as not usable for the intended business qualification claim;
- correct mapping under a new immutable scope/run;
- do not attempt to fix this by editing human review fields.

### CROSS-CASE / CROSS-DOCUMENT CONTAMINATION SUSPECTED

If the exact private source is correct but semantic output contains substantial content from another case/version that is not present in the source:

- classify as a perception/evaluation defect;
- preserve evidence;
- isolate reproduction before SME promotion;
- do not classify it as a normal semantic limitation or Native Identity loss.

## 7. Specific checks triggered by current evidence

### Check A: `LF-DOCX-004`

The case is expected to be the prior-year historical Local File. Verify that the private source and Run-002 observation correspond to the same prior-year binary.

If the source is prior-year but the retained semantic output materially contains current-year document content not present in the source, stop and investigate possible mapping/observation contamination.

### Check B: `LF-DOCX-003`

Verify whether this case is the current-year completed Local File used as evaluation ground truth. If yes, it must be treated as `GOLDEN_EVALUATION_ONLY` for workflow semantics and must never be used by the execution path as source/target authority.

Also verify exact version identity. Page-count or other harmless version differences can indicate a different legitimate binary and therefore still require explicit provenance binding.

### Check C: `LF-DOCX-001`

Verify that this is the approved generic/current Local File template that Foundation will transform in the GTPS workflow.

This is the primary execution `TARGET` role for the future vertical slice.

### Check D: `LF-XLSX-002`

Verify that this is the current-year FA&RPTs working source used for Section 4 / Section 7 / bounded profitability targets.

### Check E: `LF-XLSX-001`

Determine whether this is a prior-year/historical workbook and document why it remains necessary in representative perception coverage. It must not be confused with current-year authority.

## 8. Relationship to SME fidelity review

Do not begin or finalize human fidelity judgments for a case whose identity is not verified.

The order is:

```text
Case ID
→ exact binary/version
→ business role
→ Run evidence binding
→ human source-vs-semantic comparison
→ feature evidence / loss classification
→ coverage review
→ qualification decision
```

The existing B1.2R rule that automated presence/repeatability does not establish fidelity remains unchanged.

## 9. Relationship to the GTPS vertical slice

Once corpus identity is trusted, representative evidence should support the future GTPS vertical slice:

```text
Approved Template TARGET
+
Prior-year HISTORICAL_REFERENCE
+
Current-year CURRENT_SOURCE
        ↓
Business Target mapping proposals
        ↓
User-visible highlighted proposed changes
        ↓
Human decision
        ↓
ApprovedChangeSet
        ↓
Controlled Replay on Template
        ↓
Validation
        ↓
Downloadable First Draft
```

The current-year completed Local File may be used only as a Golden evaluation benchmark to compare expected business outcome. It is never an execution input.

## 10. Audit exit criteria

The provenance gate is complete only when:

- all five private case IDs are mapped to verified exact binaries;
- every case has an explicit business role;
- no case has unresolved source/version ambiguity;
- any Run-002 invalidation is explicitly recorded;
- any schema/role clarification is versioned rather than silently reinterpreted;
- no private path/hash/client content has entered Git;
- decision is made on whether SME review can continue on Run-002 or a new immutable run is required.

Until then, keep:

```text
B1.2R = INSUFFICIENT_EVIDENCE
production_qualified = false
```

## 11. Non-goals

This audit does not:

- change Foundation runtime capability;
- modify Frozen Contract v0.1;
- implement Replay or mutation;
- authorize Run-003;
- perform SME fidelity judgment;
- promote any B1 capability to production qualification;
- publish private corpus identity.