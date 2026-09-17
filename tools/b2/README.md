# Private B2.1 mapping evidence

The runtime API is `foundation.applications.gtps_mapping`. The probe is a local
evaluation bridge, not a runtime intake route or qualification promotion tool.
It reuses retained Run-003 observations and never converts or writes Office files.

Run with the existing pinned B1 Python environment:

```powershell
python -m tools.b2.gtps_mapping_probe --report <private-run003-report> --config <private-selector-config> --output <new-private-plan>
```

All three paths must be under a `.foundation-private` directory; symlink path
substitution and existing output files are refused. Stdout contains counts only.
The private configuration pins the full report hash, each selected input hash
and observation digest, role, task/time, Workflow Profile, business concept
aliases, exact source/historical selectors and candidate template slots.
`created_at` is a machine planning timestamp, never a human review time.

Selections reference strings in retained semantics with JSON pointers. For table
cells use the actual `table_cells` array index, not the row ordinal. Row/column
relationships must be established from retained table coordinates when preparing
the bounded configuration. `field_patterns` are trusted configuration regexes
with one capture group for bounded string extraction, not user-supplied code.

The source/target definitions and RulePack references are supplied by the caller.
Evaluation references do not establish production registration or qualification.
Without a native provider, output consists of blocked mapping intents. A private
configuration with `native_identity: B21R_REVIEW_ONLY` enables the read-only
Template provider. It loads the hash-verified Template using the pinned external
reader after resource-safe preflight. Exact native addresses are fingerprinted
and independently re-resolved. UNKNOWN package conformance is retained; the
separate review profile does not qualify mutation. Source/evidence assessments,
approval and Replay remain outside this milestone.

The projection is a private application DTO for the existing UI. It does not add
ObjectType/status values or endpoints to the frozen shared contract. Persisting
it or serving it requires the normal private application boundary.

Do not publish the configuration, raw outputs, source identifiers or review notes.
Business role metadata is validated before any selected case's semantic content
is used. Changing or adding an unselected Golden case cannot affect mapping.

## B2.1R configuration

- `party_alias_entries` and `engagement_scope` bind explicit identities to exact
  current/historical observations. Evidence is an explicit definition or same-row
  name/narrative association; similarity is never evidence.
- `context_only` historical selections contain no numeric fields. A configured
  `context_concept` binds a target rule to observed historical business context.
  This supports historical financial images without inventing values.
- `transaction_container` identifies a unique heading and table header, existing
  cell coordinates and bound ordering evidence. Ordering is Transaction under
  Review first, then descending amount. Missing configuration, materiality ties,
  duplicate identities, ambiguous tables or inadequate capacity refuse allocation.
  No insertion or discretionary grouping.
- `occurrence_group` explicitly permits distinct occurrences for one BusinessTarget;
  duplicate/overlapping occurrences still refuse.
- `detailed_regions` binds exact semantic/native heading text for navigation.
  Numbering removal is explicit; fuzzy matching is absent. Navigation identities
  do not authorize narrative replacement.

The provider compares full table grids before using native coordinates; Docling
table indexes are never assumed to equal native indexes. Whitespace trimmed by
perception is recorded separately from exact native content. The private result
retains the fingerprint profile definition and preflight summary.

Render a new immutable private handoff:

```powershell
python -m tools.b2.render_mapping_review --result <private-plan> --output <new-private-review.md>
```

The handoff retains source/history/target/native/proposal/projection chains and
pending mapping review. It records no reviewer identity, human judgment, approval
or qualification promotion.
