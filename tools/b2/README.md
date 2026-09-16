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
The probe uses no native provider, so representative output consists of blocked
mapping intents. Runtime callers may supply the native candidate interface to
obtain frozen DRAFT ChangeProposals after checks. Source/evidence assessments,
approval and Replay remain outside this milestone.

The projection is a private application DTO for the existing UI. It does not add
ObjectType/status values or endpoints to the frozen shared contract. Persisting
it or serving it requires the normal private application boundary.

Do not publish the configuration, raw outputs, source identifiers or review notes.
Business role metadata is validated before any selected case's semantic content
is used. Changing or adding an unselected Golden case cannot affect mapping.
