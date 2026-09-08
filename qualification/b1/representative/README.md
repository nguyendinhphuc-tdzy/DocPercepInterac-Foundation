# Representative B1 qualification — public specification only

`corpus.schema.json` is a closed Draft 2020-12 evaluation manifest schema, not a
Foundation domain contract. `corpus.example.json` and `review.example.json` are
inert templates containing no actual corpus values. Never fill them with private
information in this directory. The only versioned binaries remain synthetic.

Approved actual binaries must be outside the Git repository. Set
`FOUNDATION_B1_PRIVATE_CORPUS_DIR` to that existing private directory in your local
environment. Do not echo its value to public logs. Resolve filenames privately
in `.foundation-private/b1-representative/manifest.local.json`. Paths in the
manifest are relative to the external root, or absolute inside it. The root may
not be the repository or an ancestor of it.

Use the already pinned B1 Python 3.12 environment. Do not upgrade dependencies.
From the repository root, the exact private run command is:

```powershell
python tools/b1/representative_probe.py `
  --manifest .foundation-private/b1-representative/manifest.local.json `
  --private-report .foundation-private/b1-representative/reports/run-001/full.json `
  --public-summary qualification/b1/representative/reports/representative-summary.json
```

Private output paths must be Git-ignored and must not already exist. Use run-002
for a subsequent run; do not overwrite a prior full report. The public summary
contains only safe status/profile information and may replace its previous
snapshot. An exit code of zero means a report was produced, not qualification
approval. Read `corpus_status` and `decision`.

When the environment variable is absent, the runner does not read the manifest
or create fake case evidence. It writes a public summary with no cases,
CORPUS_NOT_PROVIDED and INSUFFICIENT_EVIDENCE. A configured but missing corpus
directory, unsafe path or invalid manifest produces a fixed safe refusal and
nonzero exit; no exception text or input filename is printed.

## Private review workflow

1. Select approximately 5–10 approved representative cases where available. Use
   LF-DOCX-001 / LF-XLSX-001 style opaque IDs, unrelated to client identity.
2. Declare required profiles and set each approved case to
   APPROVED_FOR_EVALUATION. A PENDING case is not read. Missing inputs stay
   NOT_EVALUATED and block a forward recommendation.
3. Run to create private preflight, semantic output and three-run observations.
4. Compare input and output privately. Copy the review template into each private
   case's optional `review` field. Bind the exact input_sha256 and
   observation_digest from that case's full report. Record actual reviewer/time,
   dimensions and loss descriptions. No raw excerpt is required in public output.
5. Complete coverage_review with reviewer identity and rationale for the selected
   scope. Unrepresented required profiles block a forward recommendation.
6. Rerun into a new private path. The stable observation digest excludes elapsed
   time; changed evidence cannot reuse a completed review. Review the allowlisted
   public summary before staging it.

Human dimensions: CONTENT_FIDELITY, STRUCTURE_FIDELITY, TABLE_FIDELITY,
BUSINESS_RELEVANT_STRUCTURE, SEMANTIC_LOSS, NATIVE_IDENTITY_LOSS and
FAILURE_TRANSPARENCY. Values: PASS, PARTIAL, FAIL, UNSUPPORTED, NOT_EVALUATED,
REVIEW_REQUIRED. Loss classes: SEMANTIC_REQUIRED, NATIVE_REQUIRED, OPTIONAL,
UNKNOWN. A critical loss must be semantic-required and not recoverable through
Native Identity. Reviews are local SME evidence, not authenticated authorization.

Automatic feature-presence values: OBSERVED, NOT_OBSERVED, NOT_EVALUATED.
They do not establish fidelity. Case execution values: EVALUATED, FAILED,
NOT_EVALUATED. Repeatability compares conversion, content, structure, tables,
ordering and references separately: PASS, OBSERVED_LIMITATION, NOT_EVALUATED.
All values describe qualification observations, never native execution support.

## Engineering tests and public CI

```powershell
$env:FOUNDATION_B1_REQUIRE_DOCLING = '1'
python -m pytest tests/backend/b1/representative tests/backend/b1/privacy -q
python tools/b1/verify_private_corpus_boundary.py
```

These tests use synthetic temporary inputs only. CI does not require a private
corpus or run the representative CLI. Its existing upload allowlist contains
only synthetic B1 and contract reports, never `.foundation-private/` or these
private run outputs. The Git guard checks tracked/index paths, including forced
staging of ignored content, without reading or printing document contents.

Before committing, run the guard and privately inspect `git status`,
`git diff --cached --name-only` and `git ls-files`. The guard cannot recognize
confidential material renamed into arbitrary unrelated directories. If private
content is staged, stop and unstage it; do not commit or rewrite Git history.

See `docs/backend/B1_REPRESENTATIVE_CORPUS_PLAN.md` for decision rules, coverage
questions and deferred B1.2B/B1.3 boundaries. Synthetic test results cannot be
published as representative Local File qualification evidence.
