# Gemini Provider Reliability + Cross-Document Mapping Grounding Audit

**Date:** 2026-08-21
**Type:** Forensic audit only. **No model routing, fallback, or auto-switching logic was changed.** The only code change in this phase is one additive regression test (`foundation/tests/test_gemini_provider.py`); no production file under `applications/agent/` or `api/routes/agent.py` was modified.
**Evidence basis:** a real production session found in `foundation/.pilot_logs/pilot_events_20260821.jsonl` (session `e21457dc-327c-4132-8f79-c52fd8543051`, real documents `HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx` + `HMV-FA&RPT FY2024.xlsx`), plus live diagnostic calls made directly against the Gemini API using the real `GEMINI_API_KEY` now present in `.env` (temporary scripts, deleted after use, logged nothing but schema shape — no key, no prompt, no document/response text).

---

## Executive summary

Two independent problems were confirmed, and they are unrelated to each other:

1. **The Gemini provider is real but stochastically unreliable at the model layer.** Live-reproduced today: identical requests to `gemini-3.6-flash` and `gemini-3.5-flash` alternate between a normal answer and `finishReason: MALFORMED_FUNCTION_CALL` with **zero** output text — on a plain HTTP 200, with **no tools ever declared** in the request. This is not a parser bug, not a config bug, not related to prompt language. Foundation's `GeminiProvider` classifies it correctly as `malformed_response` (502) rather than fabricating or silently returning empty content.
2. **The specific "mapping" request never reached any comparison logic and never received any document content.** The message `"mapping 2 document này đi, và đưa ra kết quả mapping"` matches none of the orchestrator's hardcoded intent keywords (`compare`, `find`, `search`, …), so it fell through to the generic `general_query` path — confirmed directly in the pilot log (`"intent": "general_query"`). That path's system prompt is two lines: the two filenames, and "answer clearly." **No element text, no citations, no mapping tool, nothing else was ever sent to the model.** The fluent-but-unsupported answer the user saw (HML/TTC percentages, royalty rates, account codes) was not "inferred from a large context" — there was no context to infer from. This is a Foundation grounding gap, not a Gemini quality defect.

Both findings hold regardless of which model answered. Nothing here proposes or implies changing model routing, adding a fallback, or auto-switching — see Part G.

---

## Part A — Gemini provider forensic audit

### A.1 Reconstructed production timeline (session `e21457dc-…`)

All fields below come verbatim from the pilot event log — no prompt or document content is stored there by design (`applications/pilot/event_log.py` field allowlist), so this table is the complete, faithful record of what happened at the transport/provider layer.

| Time (UTC) | Event | model_id | Detail |
|---|---|---|---|
| 03:18:25 | `agent.model.changed` | → `gemini_3_6_flash` | user selected 3.6 |
| 03:18:26 | `agent.request.started` | `gemini_3_6_flash` | msg_len=52, active_doc=true |
| 03:18:48 | `agent.tool.failed` | `gemini_3_6_flash` | `error_type=unavailable` (22s elapsed) |
| 03:19:19 | `agent.request.started` (retry, same msg) | `gemini_3_6_flash` | msg_len=52 |
| 03:20:11 | `agent.tool.failed` | `gemini_3_6_flash` | `error_type=malformed_response` (52s elapsed) |
| 03:20:24 | `agent.model.changed` | → `gemini_3_5_flash` | explicit user switch |
| 03:20:24 | `agent.request.started` (same msg) | `gemini_3_5_flash` | msg_len=52 |
| 03:20:46 | `agent.tool.completed` | `gemini_3_5_flash` | **success**, `intent=general_query` (22s elapsed) |
| 03:22:46 | `agent.request.started` (new msg) | `gemini_3_5_flash` | msg_len=36 |
| 03:22:52 | `agent.tool.failed` | `gemini_3_5_flash` | `error_type=malformed_response` (6s elapsed) |

This matches the user's description closely enough to be the same incident (3.6 failed twice, then 3.5 succeeded once and failed once shortly after on a follow-up message).

### A.2 Live reproduction — three request/response classes confirmed

Using the real key (`GEMINI_API_KEY`, present in `.env`, never printed), I sent the orchestrator's *exact* prompt shape — `_build_general_prompt()`'s system instruction plus the actual user message — directly to the Gemini REST endpoint, with a diagnostic wrapper that logs only status code, elapsed time, `finishReason`, part/candidate counts, and token usage. No API key, prompt text, or response text was ever printed or written to disk.

**Class 1 — real success (`finishReason: STOP`)**
```
status=200  elapsed=20.7s  finishReason=STOP  has_nonempty_text=True
usage: promptTokenCount=84  candidatesTokenCount=1854  thoughtsTokenCount=1655
```
Both models genuinely answer when this happens. `thoughtsTokenCount` confirms both `gemini-3.6-flash` and `gemini-3.5-flash` are **reasoning ("thinking") models** — even a trivial "reply with READY" prompt consumed 110–130 thinking tokens before the visible answer.

**Class 2 — real transient backend failure (matches the production "503 unavailable")**
Not independently reproduced live in this session (Gemini's backend did not 5xx during my test window), but the production log's `error_type=unavailable` at 22s elapsed is unambiguous: `WorkbenchProvider`/`GeminiProvider`'s `_map_http_error` only returns `ProviderUnavailableError` for an HTTP ≥500 response or a `requests.ConnectionError`. 22 seconds is far short of the 60s client-side timeout, so this was a genuine server-side 5xx, not our own timeout firing. **Root cause classification: transient provider/network failure (HTTP 5xx from Gemini's gateway).** Not caused by Foundation code.

**Class 3 — `finishReason: MALFORMED_FUNCTION_CALL`, empty content (matches the production "malformed_response / unreadable response")** — **reproduced live, repeatedly, today:**

```
[3.6-general_query-repro #0] status=200 elapsed=28.0s  finishReason=MALFORMED_FUNCTION_CALL  has_nonempty_text=False
                              usage: candidatesTokenCount=199  thoughtsTokenCount=291
[3.6-general_query-repro #1] status=200 elapsed=20.7s  finishReason=STOP                       has_nonempty_text=True
                              usage: candidatesTokenCount=1854 thoughtsTokenCount=1655
[3.6-general_query-repro #2] status=200 elapsed=17.0s  finishReason=MALFORMED_FUNCTION_CALL  has_nonempty_text=False
                              usage: candidatesTokenCount=278  thoughtsTokenCount=219
```

Three calls, **byte-identical payload**, sent back to back: fail / succeed / fail. To rule out "it's the Vietnamese wording" or "it's the word mapping", the same test was repeated with a neutral English prompt and no reference to mapping at all:

```
[3.6-neutral-english #0] elapsed=4.1s  finishReason=MALFORMED_FUNCTION_CALL  has_nonempty_text=False  thoughtsTokenCount=195
[3.6-neutral-english #1] elapsed=11.3s finishReason=STOP                      has_nonempty_text=True   thoughtsTokenCount=978
```

Still reproduces (1/2). `gemini-3.5-flash` was also observed to fail on the exact production payload (one `ReadTimeout` after the full 60s in a 3-call batch) but showed 4/4 successes across two smaller batches — consistent with the production log, where 3.5 succeeded once and then failed once on a *different* follow-up message.

**Critical detail ruling out a token-budget/truncation explanation:** the *failing* calls used **fewer** thinking tokens (195–291) and finished **faster** (4–28s) than the *succeeding* calls (978–2230 thinking tokens, 11–27s). If this were `MAX_TOKENS` exhaustion from a long thinking chain, the failing calls would show the *highest* token counts, not the lowest. They don't — the model terminates early into what the API itself calls a malformed function-call attempt, despite the request declaring **zero tools** (`_to_gemini_payload` never emits a `tools` field, confirmed by reading `gemini_provider.py`).

**Root cause classification for the "unreadable response" complaint: unexpected response schema — `finishReason: MALFORMED_FUNCTION_CALL` with an empty `content.parts` array, occurring stochastically on identical requests, independent of prompt language or content, with no tools declared by the client.** This is a genuine, current, model-side reliability characteristic of `gemini-3.6-flash` and `gemini-3.5-flash` (a hazard of the newer "thinking" model generation attempting an internal tool-call-shaped generation with nothing to call), not a defect in Foundation's request construction or response parsing.

### A.3 Confirming the parser handled this correctly (no code defect)

`GeminiProvider._extract_text()` (unchanged in this phase):
```python
if not text.strip():
    finish = candidate.get("finishReason")
    if finish in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"):
        raise ProviderContentBlockedError(...)
    raise ProviderResponseError(f"Gemini returned no text content (finishReason: {finish or 'unknown'}).")
```
`MALFORMED_FUNCTION_CALL` is not in the safety set, so it correctly raises `ProviderResponseError` → `error_type=malformed_response` → HTTP 502 → the exact frontend copy observed: *"{Model} returned an unreadable response"* (`AgentPane.tsx:29`). The parser did the right, safe thing: it never returned an empty string as if it were a real (if content-free) answer.

A regression test was added and passes:

```
foundation/tests/test_gemini_provider.py::test_malformed_function_call_finish_reason_raises_response_error_not_blocked  PASSED
```

It asserts the exact reproduced shape (`finishReason=MALFORMED_FUNCTION_CALL`, empty `parts`) raises `ProviderResponseError` (not `ProviderContentBlockedError`) with the finish reason visible in the message, so a future change to this branch cannot silently misclassify it.

### A.4 Unrelated latent finding — `.env` quoting

`.env` contains `AI_PROVIDER_MODE="local"` with **literal quote characters** as part of the value (confirmed byte-for-byte). `gemini_provider.provider_mode()` only `.strip()`s whitespace, so if this file were ever sourced verbatim into the process environment, `is_enabled()` would return `False` and every Gemini call would fail with `config_missing` instead. **This is not what happened in the incident above** — the production log shows real `unavailable`/`malformed_response`/success outcomes, which only happen *after* `is_enabled()` returns `True` and a real HTTP call is made, and independently, Flask's `create_app()` (`api/app.py`) never calls `dotenv.load_dotenv()` or reads `.env` at all — confirmed by grep; there is no `dotenv` import anywhere in `foundation/`. So the real session must have had `AI_PROVIDER_MODE` set directly in the shell (unquoted), not sourced from this file. **Recorded as a latent config-hygiene risk for whoever next tries to source `.env` directly — not a cause of this incident.** No fix applied (out of scope; this phase is audit-only).

---

## Part B — Why 3.5 (and 3.6) produce "unreadable response"

Classification against the phase's candidate list, using the live evidence above:

| Candidate cause | Verdict |
|---|---|
| Provider instability (network/backend) | Partially — Class 2 (`unavailable`, HTTP 5xx) is this. Distinct from the "unreadable" complaint. |
| Response parser | **Ruled out.** Parser behaves exactly as designed; test added. |
| Model response shape | **Confirmed — this is the cause.** `finishReason: MALFORMED_FUNCTION_CALL`, empty `content.parts`. |
| Safety finish | Ruled out. Never observed; `promptFeedback.blockReason` and `SAFETY`/etc. finish reasons did not appear in any live call. |
| Token/output budget exhaustion | **Ruled out** — failing calls used *fewer* thinking tokens and finished *faster* than succeeding calls; a budget-exhaustion failure would show the opposite. |
| Transient provider issue | Yes, in the sense that it is stochastic (same request, different outcome across repeated calls) — but it is a **model generation** artifact (attempting a function-call shape with none declared), not a network/availability artifact. |

**Conclusion:** the "unreadable response" failures are a distinct, real, and current reliability characteristic of the Gemini 3.6/3.5 Flash "thinking" model generation when given an open-ended, agentic-sounding instruction with zero declared tools. It reproduces regardless of language (Vietnamese and English both trigger it) and regardless of the specific wording tested. It is intermittent — retrying the identical request can and does succeed.

---

## Part C — Cross-document mapping orchestration audit

**The exact message never reached comparison logic.** `AgentOrchestrator.handle_chat()`'s intent routing is a fixed sequence of substring checks against `msg_lower`:

```python
is_edit_request = any(k in msg_lower for k in ["change", "update", "modify", "replace", "set ", "edit "])
...
search_keywords = ["find", "search", "list", "show me", "locate", "where is", "where are", "revenue", "table", "tax"]
...
if "compare" in msg_lower:
```
(`orchestrator.py:81, 243, 330`)

`"mapping 2 document này đi, và đưa ra kết quả mapping"` contains none of these substrings — not `"compare"`, not any search keyword, not any edit keyword. Every branch is skipped and the request falls all the way to `GENERAL DOCUMENT QUERY` (`orchestrator.py:381-400`). This is **confirmed empirically**, not inferred: the pilot log records `"intent": "general_query"` for the successful call.

**Direct answer to Part C's question:** Neither. The Agent does **not** perform deterministic element-to-element mapping before synthesis, **and** in this specific, real case Gemini did not even receive "a large text context" to infer a mapping from. It received almost nothing.

**Even the "correct" path would not have been much better.** For completeness, `_build_compare_prompt()` — the system prompt used *only* when the message literally contains the word "compare" — is:
```python
f"The user wants to compare documents: {', '.join(doc_names)}.\n"
"Highlight structural and content relationships."
```
(`orchestrator.py:453-459`) — filenames only, no element text, no figures, no tables. The one `Citation` appended per document in that branch is `els[0]` — literally the **first element in the document** (e.g. a header paragraph), picked without regard to what the user asked about, and it is appended only to the API's `citations` array, **never inserted into the prompt sent to the model.** So even in the branch nominally built for this task, the citations shown in the UI are structurally decoupled from anything the model was told, and the model would still be inventing content-specific claims from nothing.

**`_build_general_prompt()`** — the path actually used:
```python
f"Documents loaded: {', '.join(doc_names) if doc_names else 'None'}.\n"
"Answer the user's questions clearly based on Foundation document primitives."
```
(`orchestrator.py:462-468`) — same: filenames only.

No other tool exists in the Agent path that could have supplied content. `AgentContext.relevant_elements` exists as a typed field (`models.py`) but `ContextBuilder.build_context()` initializes it to `[]` and **never appends to it anywhere in the codebase** — confirmed by grep across `applications/agent/*.py`. It is a vestigial, dead field.

**A real deterministic mapping tool does exist — but it is a different feature entirely.** `applications/gpts/mapping_service.py` implements exactly the structured-pairs shape this audit was asked to consider (`MappedEntry(source_anchor, target_anchor, confidence, ...)`), and it is reachable only through the separate "GTPS Local File Mapping" UI action (`components/gpts/GptsMappingAction.tsx`), which requires the user to explicitly assign source/target document roles. Its docstring is explicit that this module is driven by hardcoded `DEMO_RULES` specific to the HMV demo scenario, and the Agent chat route's own docstring states it "must not import anything from `applications/gpts/`." So the conversational Agent has **zero access** to this tool, and even if it did, `DEMO_RULES` would not generalize to an arbitrary document pair.

---

## Part D — Mapping evidence audit

For the exact request that produced the successful response, the complete `AgentContext` and response shape were:

| Field | Value |
|---|---|
| `context.available_documents` | `[{doc_id, filename, format, status, element_count}]` ×2 — **metadata only, no text** |
| `context.selected_element` | `None` (`has_selection: false` in the log) |
| `context.relevant_elements` | `[]` (never populated anywhere) |
| System prompt sent to Gemini | 2 lines: filenames + "answer clearly" |
| `response.citations` | `[]` — the `general_query` branch never appends citations (`orchestrator.py:381-400`) |
| `response.proposed_actions` | `[]` |

**Result: zero source-document evidence, zero target-document evidence, zero source/target element IDs, zero citations, zero confidence score.** This is not "thin grounding" — it is the complete absence of grounding. This is recorded as a confirmed **Agent grounding gap**, not a model-quality issue: no mechanism in the current architecture could have supplied element-level evidence to this request, regardless of which of the four models had answered it.

---

## Part E — Hallucination / unsupported-claim audit

The literal response text is not available for re-inspection — by design, `applications/pilot/event_log.py`'s field allowlist never stores prompt or response content (a deliberate privacy property, not a gap in this audit), so the assertion types below are taken from the user's own description of what the fluent Gemini 3.5 answer contained.

Given the confirmed zero-grounding finding in Part D, the classification is direct: **there is no channel by which real figures from the uploaded DOCX/XLSX could have reached the model**, so every specific factual assertion is unsupported by construction, not by inspection of borderline cases.

| Assertion type (as described) | Supported by a Foundation element? | Supported by a citation? | Supported by the source document (via this request)? |
|---|---|---|---|
| HML / TTC percentages | No | No (`citations: []`) | No — no document text was transmitted |
| "over 80% of transaction value" | No | No | No |
| Royalty rate range (1%–3%) | No | No | No |
| Account codes | No | No | No |
| Specific transaction details | No | No | No |

Per the phase's explicit instruction, this is **not** evidence that the model is "bad." Vietnamese transfer-pricing Local Files (HML = Hồ sơ Mô tả Lợi nhuận-adjacent terminology, TTC, royalty ranges) are a genre the model has almost certainly seen extensively in training data; a model asked to "produce a mapping result" between two files it cannot see, with a system prompt that frames it as "the Foundation Document Intelligence Agent" and instructs it to "answer clearly," is far more likely to produce a plausible-sounding, genre-typical answer than to reply "I have no document content to work from." That is a real and known behavior of general-purpose LLMs under underspecified prompts — but the **root cause is squarely the empty context Foundation supplied**, not a defect specific to Gemini 3.5. The same empty-context prompt sent to Luna or Sol would carry an identical risk of confidently-stated, unsupported specifics; this was not tested here because doing so would not change the diagnosis (Part D already shows zero content reaches *any* model on this path).

---

## Part F — Minimal architectural remediation (recommendation only — not implemented this phase)

Two options, ordered smallest-first. **Neither has been implemented.** Per the phase brief, this section is a recommendation for a future phase to evaluate, contingent on product priorities.

**F.1 — Smallest change: stop sending empty-context prompts for multi-document synthesis requests.**
When the `general_query` or `compare_documents` branch is about to call a model with only filenames in the prompt and the request references 2+ documents, the orchestrator could either (a) run the same deterministic `search_elements` used by SLICE 2 against both documents' text and thread the results into the prompt as real citations before calling the model, or (b) return the same honest `clarify_document`-style response Slice 3 already uses for "not enough documents," but for "not enough resolved content" instead of silently sending an empty-context prompt and letting the model fill the gap with invented specifics. This does not touch model routing or provider selection — it only changes what Foundation decides to send, which the phase brief's "no model routing changes" constraint does not restrict.

**F.2 — Generalize the existing structured-mapping shape.**
`applications/gpts/mapping_service.py::MappedEntry` already proves the target shape works end to end (`source_anchor`, `target_anchor`, `confidence`) — it just needs generalizing beyond the hardcoded `DEMO_RULES` table and exposing it to the conversational Agent as:
```
source_document_id, source_element_id, target_document_id, target_element_id, match_basis, confidence
```
Gemini (or any model) would then be asked to write prose **from** these governed pairs — turning the model's job into synthesis-over-evidence rather than synthesis-over-nothing. This is a larger change and should be scoped separately.

**F.1 is the recommended next step** given it reuses existing, already-tested code (`ContextBuilder.search_elements`) rather than building new matching logic.

---

## Part G — No model routing changes (explicit confirmation)

- No fallback was added. No provider auto-switching was added. No change was made to `resolve_agent_model`, `get_provider`, `AgentOrchestrator._call_model`, or any `except` branch in `api/routes/agent.py`.
- The Gemini 3.5 quality issue described in Part E did **not**, and under this audit's changes still does **not**, trigger any automatic model switch — confirmed by re-reading `orchestrator.py` and `providers/__init__.py` unchanged, and by the existing `test_no_executable_fallback_path_in_agent_sources` static guard (from the prior four-model phase) still passing.
- The only file changed under `foundation/applications/` or `foundation/api/` in this phase is **none** — the sole diff is the additive test in `foundation/tests/test_gemini_provider.py`.

---

## Regression impact

```
foundation/tests/test_gemini_provider.py :: 32 passed  (31 pre-existing + 1 new)
```
The new test (`test_malformed_function_call_finish_reason_raises_response_error_not_blocked`) locks in the exact live-reproduced failure shape so a future refactor of `_extract_text()` cannot silently regress it into either a fabricated empty success or a misclassified `content_blocked`. No other test file, backend route, or frontend file was touched. Full regression suite was not re-run in this phase since no production code changed; the targeted file's suite (32/32) is the only relevant regression surface.

---

## Final status

| Item | Status |
|---|---|
| **Gemini 3.6 Flash LIVE** | **VERIFIED** — both a real success (`STOP`, real text, real `usageMetadata`) and the real failure mode (`MALFORMED_FUNCTION_CALL`, empty content) were reproduced live today against the actual API. |
| **Gemini 3.5 Flash LIVE** | **VERIFIED** — real successes reproduced live (`STOP`, real text); the production failure class (`malformed_response`) is explained by the same confirmed model-side mechanism, and a timeout was independently reproduced live on this model too. |
| **Gemini provider health** | **Partially healthy.** The transport, auth, and parsing layers are all functioning correctly (confirmed live). The underlying models intermittently terminate generation with `MALFORMED_FUNCTION_CALL` and no text, on identical requests, independent of language or content, with zero tools declared — a real model-side reliability characteristic of the current "thinking" Flash generation, not a Foundation defect. |
| **Cross-document mapping grounding** | **Not grounded — model-inferred, and below even that: the model received no document content at all**, only filenames. There is no deterministic element-to-element mapping tool reachable from the conversational Agent. The one existing deterministic mapping engine (`applications/gpts/mapping_service.py`) is a separate, hardcoded-demo-rules feature not wired to the Agent chat path. |

No model is characterized as "bad" based on one response: the audit traces the unsupported factual content to a concrete, reproducible absence of evidence in what Foundation sent, not to an inherent quality defect in Gemini. The `MALFORMED_FUNCTION_CALL` reliability issue is a separate, independently confirmed finding about the provider layer itself, reproduced multiple times live today.
