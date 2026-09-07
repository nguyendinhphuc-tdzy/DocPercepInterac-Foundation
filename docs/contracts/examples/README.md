# Foundation Contract v0.1 Scenario Fixtures

These fixtures are machine-readable contract scenarios for Foundation
architecture generation v2 and contract schema version 0.1.0. They exercise
the governed path from immutable document identity through evidence, mapping,
human authorization, controlled replay, independent validation and release
eligibility.

Each file has the same top-level shape:

`schema_version`, `fixture_type`, `scenario_id`, `title`, `facts`,
`records`, `actions`, `audit_events`, and `expected`. Domain records
under `records` use only fields defined by
[`domain-model.md`](../domain-model.md). Scenario assertions and fault
injections belong under `facts`, `actions`, or `expected`.

The eight scenarios are:

| Fixture | Behaviour |
| --- | --- |
| 01-ncp-valid-change | Complete NCP change with sufficient current-period evidence, approval, replay, independent validation and release eligibility. |
| 02-missing-benchmark | The NCP branch is independently verified, while the arm's-length conclusion remains insufficient and withholds whole-task release. |
| 03-stale-target-after-approval | A new target binary appears after approval; replay refuses with `STALE_DOCUMENT_VERSION` and invalidates authorization. |
| 04-ambiguous-native-locator | Two exact resolver candidates produce `LOCATOR_AMBIGUOUS`; replay refuses without fuzzy fallback. |
| 05-ai-correct-evidence-insufficient | AI proposes the supplied value, but deterministic evidence is missing, so no authorization or replay is possible. |
| 06-unauthorized-change-detected | Replay mechanically succeeds, but independent preservation validation detects an unrelated native change and quarantines the output. |
| 07-request-more-source | A human requests the named missing benchmark source; new records and events preserve the prior evidence and AI history. |
| 08-strict-ooxml-unsupported | Strict OOXML capability is unqualified, so the operation is refused before an authorization or replay request exists. |

Fixture binaries and external source excerpts are explicitly illustrative.
Their `DocumentVersion` hashes, observations, and resolver fault injection
demonstrate contract identity and failure handling; they are not a native
Office-engine qualification corpus.

References use the contract `Ref` shape and resolve to records in the same
fixture. `ApprovedChangeSet` records contain a complete sealed
`AuthorizationBinding`; `ReplayRequest` actions contain exactly
`execution_id` and `approved_change_set_ref`. Event integrity hashes and
authorization digests are calculated over RFC 8785 JSON Canonicalization
Scheme output encoded as UTF-8 and hashed with SHA-256, represented as
lowercase hexadecimal.

The fixtures deliberately show that execution success is not validation
success, that AI output has no execution authority, and that partial
business progress does not make a blocked task releasable.
