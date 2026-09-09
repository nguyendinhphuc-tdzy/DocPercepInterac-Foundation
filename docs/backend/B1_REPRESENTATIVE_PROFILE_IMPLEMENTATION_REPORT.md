# B1.2R Explicit Representative Preflight Profile

Date: 2026-09-10. Branch: `build/backend-b1-representative-profile`.
Starting baseline: `f926d9c4318c42548bc84a7b860660e16961fedd`.
Architecture generation: Foundation v2. Frozen Contract: **0.1.0, unchanged**.

## Purpose and boundary

The representative evaluator now uses the explicit non-contract profile
`b1-representative-core-v1`. It exists only to let the approved B1 CORE corpus
reach semantic qualification. Qualification eligibility is not production
capability, general Local File support, general XLSX support, mutation support,
or evidence of semantic fidelity.

The general `PreflightConfig()` defaults and `OoxmlPreflight(resolver)` behavior
remain unchanged. Only the representative harness supplies the qualification
configuration explicitly.

## Exact configuration

| Limit | General default | Representative profile |
| --- | ---: | ---: |
| `max_package_bytes` | 33,554,432 | 3,004,377 |
| `max_uncompressed_bytes` | 134,217,728 | 22,302,224 |
| `max_part_bytes` | 16,777,216 | 17,856,208 |
| `max_parts` | 4,096 | 132 |
| `max_xml_elements` | 500,000 | 796,703 |

Only the single-part and XML-element limits exceed the general defaults. The
package, aggregate-expanded and part-count limits are intentionally narrower.
All five values are the exact measured minima for the approved immutable CORE
corpus and include no numeric headroom. A corpus binary or reviewed scope change
requires recalibration; the profile must not silently grow to admit it.

The profile was calibrated for the approved immutable corpus. The numeric values
are not a cryptographic corpus identity. Input SHA-256, coverage scope digest,
observation digest and bound review evidence continue to provide their separate
identity and review functions.

## Evidence and review invalidation

`OoxmlPreflight` continues to create configuration evidence from the complete
configuration and parser strategy. Its `configuration_ref` therefore identifies
the exact preflight mechanics used for a case. Private representative evidence
also records `representative_preflight_profile_id` and the bound preflight
configuration reference.

The stable observation payload includes both values. Changing the profile ID or
any configuration value changes the observation digest. Because completed SME
review binds that digest and the input hash, prior review evidence cannot remain
valid after either change. Existing reviews are neither migrated nor relabeled.

The public sanitizer remains a closed allowlist. It does not publish the profile
ID, configuration reference, private path, filename, document hash, or private
evaluation material. The representative evaluation schema remains 1.1.0.

## Capacity and security behavior

Synthetic tests prove that one shape exceeding both the default 16 MiB part gate
and 500,000-element gate is refused by the default profile and proceeds under the
representative profile. Separate tests exceed each representative limit by one
unit and receive `DOCUMENT_TOO_LARGE`.

The qualification profile does not bypass any capacity gate. DEFLATE input/output
bounds, actual expanded-size and CRC authority, true EOF, trailing-data refusal,
no-flush behavior, ZIP64 refusal, unknown and duplicate extra-field refusal, the
LOCAL OPC Growth Hint allowlist, data-descriptor refusal and encryption refusal
are unchanged.

Formal representative Run-002, private Docling, new SME review, coverage approval
and a public qualification conclusion were not executed. Run-002 remains gated
on independent acceptance of this implementation.

## Validation evidence

Validation used the pinned B1 Python 3.12 environment. Representative/privacy
and Golden suites invoked only their authorized synthetic Docling regressions.

| Check | Result |
| --- | --- |
| Contract fixture validator | OpenAPI PASS; 8/8 scenarios PASS |
| Contract unittest suite | 23 passed |
| Focused profile suite | 11 passed |
| Focused preflight suite | 117 passed |
| Representative/privacy suite | 94 passed |
| Full backend suite | 310 passed |
| Golden suite | 5 passed |
| Private preflight-only confirmation | CORE 7/7; CHALLENGE 3/3 completed |
| Private corpus boundary | PASS |
| Dependency consistency | No broken requirements |
| Compilation and `git diff --check` | PASS |
| Frozen Contract diff | Empty |
