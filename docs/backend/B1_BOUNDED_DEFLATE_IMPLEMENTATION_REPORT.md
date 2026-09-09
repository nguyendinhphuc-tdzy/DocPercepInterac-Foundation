# B1.1D Foundation-Bounded DEFLATE Implementation Candidate

Date: 2026-09-09. Branch: `build/backend-b1-bounded-deflate`.
Starting baseline: `f5844ee95680f714f2d59541420ed963e92251ca`.
Architecture generation: Foundation v2. Frozen contract: **0.1.0, unchanged**.

## Outcome and scope

The accepted B1.1D qualification decision was **B — implement a
Foundation-bounded zlib path**. The OOXML preflight adapter now admits STORED
and DEFLATE members within a deliberately narrow ZIP profile. For DEFLATE,
Foundation reads the exact compressed physical member range and uses raw
`zlib.decompressobj(-15)` with bounded input and output. It independently
establishes actual expanded size, CRC, stream completion and capacity rather
than treating `ZipInfo.file_size` or `ZipExtFile` consumer EOF as integrity
authority.

This is an implementation candidate for independent acceptance. It does not
qualify DEFLATE for representative or production use. BZIP2, LZMA, encrypted
members, data descriptors, ZIP64 and unqualified general-purpose flags remain
unsupported. Numeric capacity limits are unchanged. The Frozen Contract,
domain schemas, ADRs, Docling integration, NativeLocator, NativeBinding,
mutation, replay and frontend are outside this change.

## Qualification basis and Option A rejection

Qualification evidence demonstrated a complete raw DEFLATE stream that expands
to 1,048,576 bytes while forged ZIP metadata declares 128 bytes and binds CRC
only to that prefix. Python `ZipExtFile` exposed the declared 128-byte prefix as
the complete consumer result. It therefore cannot serve as final DEFLATE size,
CRC or true-stream-completion authority for Foundation.

The exact counterexample is a committed regression. The new path reaches raw
DEFLATE completion, observes all 1,048,576 bytes and refuses the member as
CORRUPTED_DOCUMENT because actual expanded size disagrees with declared ZIP
metadata. The test also demonstrates the old `ZipExtFile` prefix behavior, so
the refusal is attributable to Foundation's independent actual-size check.

## ZIP and DEFLATE trust boundary

Python `ZipFile` parses the central directory. Before decompression, Foundation
validates each local header against that parsed entry: signature, method,
general-purpose flags, CRC, compressed and expanded sizes, filename and extra
fields must agree. Members must start at offset zero and be physically
contiguous through the central directory. The validated local header and
compressed size define the exact physical compressed range.

Foundation refuses ZIP64 indicators in local or central extra fields, ZIP64
sentinel sizes, extraction versions at or above 4.5 and a ZIP64 end-of-central-
directory locator. Data descriptors remain refused. STORED permits only the
UTF-8 name flag. DEFLATE permits that flag and the defined DEFLATE compression
option bits. Encryption and every other flag remain refused. Unsupported
compression or layout features are rejected before a DEFLATE object is created.

For STORED, the accepted physical-layout validation and terminal `ZipExtFile`
CRC finalization remain in place. The equality of compressed and expanded size
continues to apply to STORED only.

## Bounded decompression and acceptance state

Each raw DEFLATE call receives at most 32 KiB of compressed input and always
sets `max_length` to 64 KiB. Output is consumed immediately by the existing XML
event parser or non-XML drain. The implementation retains the compressed source
package, a view of the current physical member range, at most one bounded input
slice, zlib state and one bounded output chunk. It does not retain a complete
expanded member or write expanded temporary files.

`unconsumed_tail` is processed before more physical input is supplied. Once the
physical range is exhausted, any required empty-input call remains output
bounded. No `flush()` call is used. A call that cannot consume input or produce
output, and an exhausted stream that cannot produce output or reach EOF, fail
closed instead of looping.

A DEFLATE member is accepted only when all of these conditions hold:

- zlib reports true EOF;
- every byte of the exact physical compressed range has been supplied;
- `unconsumed_tail` and `unused_data` are empty;
- actual expanded size equals declared size;
- incremental CRC32 over actual output equals declared CRC;
- actual per-part and aggregate expanded-byte limits were not exceeded.

Unexpected trailing stream data, incomplete input, invalid blocks, size
mismatch and CRC mismatch return deterministic CORRUPTED_DOCUMENT refusals.
Actual emitted bytes, rather than declared expanded size, are the final
capacity authority. The regression at byte 16,777,217 returns
DOCUMENT_TOO_LARGE under the unchanged 16 MiB part limit.

## Existing XML behavior and two-pass cost

Bounded output feeds the existing Expat event stream directly. DTD and external
entity refusal, aggregate element counting, conformance observations, unknown
structures, relationship processing, protection observations and deterministic
evidence are unchanged. No XML DOM or complete expanded XML value is created.

The accepted two-pass design remains: pass one proves package integrity and
capacity; pass two performs structural inspection. DEFLATE members are therefore
expanded twice. This avoids caching expanded content at the cost of CPU and
latency. No CPU timeout or production performance threshold is introduced.

## Versions and unchanged capacities

| Item | Accepted STORED-only baseline | B1.1D candidate |
| --- | --- | --- |
| OoxmlPreflight engine | 1.1.2 | 1.2.0 |
| PreflightConfig profile | 1.1.1 | 1.2.0 |
| Streaming/decompression strategy | 1.1.1 | 1.2.0 |
| Qualified compression | STORED | STORED, DEFLATE |
| DEFLATE input bound | N/A | 32,768 bytes |
| DEFLATE output bound | N/A | 65,536 bytes |
| max_package_bytes | 33,554,432 | 33,554,432 |
| max_uncompressed_bytes | 134,217,728 | 134,217,728 |
| max_part_bytes | 16,777,216 | 16,777,216 |
| max_parts | 4,096 | 4,096 |
| max_xml_elements | 500,000 | 500,000 |

Configuration evidence records qualified methods, both chunk bounds, raw window
mode, Python version, zlib compile/runtime versions, required EOF, actual-size
and CRC policies, trailing-data refusal and the prohibition on unbounded flush.
Historical 1.1.x assessments remain STORED-only and are not relabeled.

## Synthetic verification

The test matrix covers normal DEFLATE, high and low compression ratios, a
dominant member, multiple-member aggregate accounting, the exact part boundary,
actual part and aggregate overflow, zero-length output, truncation, invalid
blocks, forged CRC, understated and overstated sizes, trailing data,
`unused_data`, incomplete EOF and deterministic no-progress refusal. It also
covers XML element overflow, deep XML, a large text token and a large attribute.
Pre-decompression tests cover data descriptors, ZIP64, unqualified flags and a
hidden physical suffix. Instrumentation proves every zlib input and returned
output remains within its configured structural bound and observes
`unconsumed_tail` processing.

The resource probe runs generated packages in fresh processes. All nine
expected behaviors passed across the prior accepted implementation, the
resource-safe STORED implementation and the DEFLATE candidate. The candidate
completed dominant and distributed cases in approximately 0.97 and 0.93
seconds. Its process lifetime peak working sets were approximately 47.66 and
46.35 MiB. The above-element-limit case refused in approximately 0.29 seconds
with a lifetime peak near 52.22 MiB. These local measurements include fixture
generation and imports; they are diagnostic observations, not portable memory,
latency or production thresholds.

## Regression and remaining qualification

All STORED tests remain in the focused suite. F01 continues to distinguish
structured malformed-input refusal from programmer failure. F02 retains STORED
physical-layout and terminal CRC closure while adding independent DEFLATE size,
CRC, EOF and trailing-data closure. F03 continues to refuse BZIP2 and LZMA
before decompression. F04 finding identity uniqueness and determinism is
unchanged.

Synthetic evidence cannot establish representative DEFLATE qualification,
portable memory behavior or production performance. The source package is
still materialized by the content port, ZIP directory parsing precedes the
part-count gate, Expat may allocate token/attribute/depth state, and reduced
observations can grow within admitted limits. Two-pass decompression adds CPU
amplification. Independent acceptance must review these bounds and regressions
before representative qualification is reopened. Private Docling and
representative Run-001 were not executed.

## Local validation evidence

Validation used the pinned Python 3.12 B1 environment. Representative/privacy
and Golden suites invoked only their authorized synthetic Docling regressions;
no private document was sent to Docling.

| Check | Result |
| --- | --- |
| Contract fixture validator | OpenAPI PASS; 8/8 scenarios PASS |
| Contract unittest suite | 23 passed |
| Focused B1 preflight suite | 94 passed |
| Representative/privacy suite | 83 passed |
| Full backend suite | 276 passed |
| Golden suite | 5 passed |
| Private corpus boundary | PASS |
| Dependency consistency | No broken requirements |
| Preflight/test/tool compilation | PASS |
| `git diff --check` | PASS |

No test, invariant or refusal policy was relaxed. Frozen Contract files have no
diff.
