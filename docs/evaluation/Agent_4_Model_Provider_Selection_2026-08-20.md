# Agent — Four-Model Provider Selection

**Phase:** Extend the Agent model selector from two models to exactly four user-selectable models across two providers.
**Date:** 2026-08-20
**Status:** Implemented. Backend, frontend and tests complete. Verification status per provider is stated explicitly in sections L and M — read those before quoting any "verified" claim.

---

## A. Current HEAD

| | |
|---|---|
| Branch | `master` |
| HEAD at start of phase | `3b60ddace300e3106b19fdb3a285cc43ad2e316f` — *infras update* |
| Working tree at start | clean |

Baseline before this phase:

- Foundation Document Core, UI/UX, Agent Architecture V1, Agent Evaluation, Deep Architecture Audit, Pilot Instrumentation, XLSX Undo remediation, DOCX mapping remediation, deterministic Agent fallback elimination — all complete.
- Two Workbench models (`luna`, `sol`) reached through `applications/workbench_client.py`, called directly from the orchestrator.
- No deterministic Agent fallback: Agent generation already required a real external model provider.

---

## B. Four-model strategy

The selector exposes exactly four choices and nothing else:

| Model | Application-level id | Provider | Provider-native model |
|---|---|---|---|
| Luna | `workbench_luna` | `workbench` | `gpt-5-6-luna-2026-07-09-gs-ae` |
| Sol | `workbench_sol` | `workbench` | `gpt-5-6-sol-2026-07-09-gs-ae` |
| Gemini 3.6 Flash | `gemini_3_6_flash` | `gemini` | `gemini-3.6-flash` |
| Gemini 3.5 Flash | `gemini_3_5_flash` | `gemini` | `gemini-3.5-flash` |

Stable public Gemini model ids only — no `-preview` ids.

**The default remains Luna.** New conversations start on `workbench_luna`; corporate/default behaviour stays Workbench-first. The user may explicitly choose any of the other three at any time.

Gemini 3.6 Flash is listed above Gemini 3.5 Flash because it is the preferred Gemini option for local/demo use. That ordering is *presentation only*. It does not make 3.5 a fallback for 3.6, and nothing in the code treats the order as a priority chain — see section H.

---

## C. Provider architecture

```
Agent (ONE orchestrator: context, intent, tools, governance, response assembly)
  ↓
ModelProvider  (transport only: auth, wire format, parsing, error mapping)
  ├── WorkbenchProvider  → Luna, Sol
  └── GeminiProvider     → Gemini 3.6 Flash, Gemini 3.5 Flash
```

New package: `foundation/applications/agent/providers/`

| File | Responsibility |
|---|---|
| `base.py` | `ModelProvider` ABC, `ProviderMessage`, `ProviderResponse`, the normalized `ProviderError` hierarchy |
| `workbench_provider.py` | Wraps the unchanged `applications/workbench_client.py`; maps `Workbench*` exceptions onto the normalized errors |
| `gemini_provider.py` | Gemini `generateContent` REST transport, request translation, response parsing, error mapping, environment gating |
| `__init__.py` | `get_provider(provider_id)` factory and public exports |

There is **no** `LunaOrchestrator`, `SolOrchestrator` or `GeminiOrchestrator`. `AgentOrchestrator.handle_chat` is the only orchestrator, and no branch inside it tests which provider is in use. The single point of contact with a model is `AgentOrchestrator._call_model(message, system_prompt, spec)`, which resolves the provider and forwards one provider-neutral message list.

`get_provider()` constructs a **fresh instance per request** by design: provider selection is per-request state. There is no cached singleton and no module-level mutable provider/model configuration, so a request selecting Sol cannot leave Workbench state behind for a following request selecting Gemini (asserted by `test_switching_models_across_requests_leaks_no_provider_state`).

No new Python dependency was added. `GeminiProvider` uses `requests`, the same HTTP client `workbench_client.py` already uses.

---

## D. Model registry

One authoritative registry in `foundation/applications/agent/models.py`:

```python
ProviderId  = Literal["workbench", "gemini"]
AgentModelId = Literal["workbench_luna", "workbench_sol",
                       "gemini_3_6_flash", "gemini_3_5_flash"]

@dataclass(frozen=True)
class AgentModelSpec:
    model_id: AgentModelId
    provider: ProviderId
    model: str        # provider-native name — server-side only
    label: str
    description: str
    group: str

AGENT_MODELS: dict[AgentModelId, AgentModelSpec]
AGENT_MODEL_ORDER: tuple[AgentModelId, ...]   # selector order (presentation only)
DEFAULT_MODEL: AgentModelId = "workbench_luna"
```

- `resolve_agent_model(model_id) -> AgentModelSpec` validates against the allowlist and raises `ValueError` on anything else.
- `GET /api/agent/models` is generated from this registry, so the frontend list and the backend allowlist cannot drift.
- The frontend mirror lives in `frontend/src/api/agent.ts` (`AGENT_MODELS`, `AGENT_MODEL_GROUPS`). It carries ids, labels and descriptions only — never provider-native model names.

`get_model_key()`, which used to coerce any unrecognized string to the default, was removed. Silent coercion is the same failure mode as silent switching.

---

## E. Backend changes

**`applications/agent/models.py`**
- Replaced the two-entry `AGENT_MODELS: dict[str, str]` with the four-entry `AgentModelSpec` registry above.
- `AgentResponse.model` → `AgentResponse.model_id` + `AgentResponse.provider`.

**`applications/agent/orchestrator.py`**
- Resolves the selected model to an `AgentModelSpec` exactly once per request; `spec` is the sole authority for that request's provider and model name.
- `_call_workbench(...)` → `_call_model(..., spec=spec)`, which goes through `get_provider(spec.provider).chat(...)`.
- Every `AgentResponse` now carries `model_id` and `provider`.
- No `try`/`except` around the provider call: a `ProviderError` propagates untouched to the route.

**`api/routes/agent.py`**
- `GET /api/agent/models` returns all four with `provider`, `group`, `is_default`, generated from the registry.
- `POST /api/agent/chat` accepts `model_id` (or legacy key `model`), validates against the strict allowlist, and returns **HTTP 400** for anything else — including raw provider names (`gpt-5-6-luna-…`, `gemini-3.6-flash`), the pre-phase short ids (`luna`, `sol`), and empty/whitespace values.
- The six near-identical Workbench-specific `except` blocks collapsed into one `except ProviderError`, which reads `error_type` and `http_status` off the exception. A new provider inherits the whole error vocabulary by mapping onto it.
- Error payloads carry `model_id`, `provider`, `error_type` — and deliberately **no `response` field**, so a failure cannot be mistaken for an answer.

**`applications/workbench_client.py`** — unchanged. Same `BASE_URL`, deployment/instance semantics, credentials, 60s timeout, region override and error mapping. The corporate/VPN path is untouched by this phase.

### Breaking API change

Requests must now send one of the four new ids. `"luna"` and `"sol"` are rejected with HTTP 400. This follows the phase requirement that the backend accept only the four application-level ids; keeping short aliases would have meant a second, undocumented accepted vocabulary. Frontend and all tests were updated accordingly. Response field `model` is likewise replaced by `model_id` + `provider`.

---

## F. Frontend changes

**`src/api/agent.ts`** — four-model registry mirroring the backend, `AGENT_MODEL_GROUPS` (provider-grouped view), `getModelOption()` / `getModelLabel()`, `DEFAULT_AGENT_MODEL`. Request field `model` → `model_id`; response types gain `model_id` + `provider`. `AgentApiError.model` → `.modelId`.

**`src/state/agentStore.ts`** — `selectedModel` defaults to `workbench_luna`. `providerError.failedModel` records the model that actually failed. `retryFailedMessage()` passes that model explicitly. `switchModelAndRetry(target)` requires an explicit target.

**`src/components/agent/AgentComposer.tsx`** — the dropdown renders `AGENT_MODEL_GROUPS`: a `role="group"` per provider with an `aria-label` and a visible uppercase group heading, four `role="option"` rows inside.

```
Model  [ Luna ▾ ]

  WORKBENCH
  ● Luna              Fast · Everyday tasks          [Default]
  ○ Sol               Deep reasoning · Complex analysis
  ─────────────────────────────────────────
  GEMINI
  ○ Gemini 3.6 Flash  Fast · Local/demo
  ○ Gemini 3.5 Flash  Gemini · Alternative
```

**`src/components/agent/AgentMessage.tsx`** — the per-message badge resolves its label from the registry and carries `data-provider`. Historical messages keep the model that answered them; changing the selector never rewrites them.

**`src/components/agent/AgentPane.tsx`** — error card rebuilt for four models (section G).

**`src/index.css`** — provider group styling; `.model-selector-current` capped with ellipsis (108px, 84px below 900px, where the redundant "Model" prefix is also hidden); dropdown `max-width: calc(100vw - 32px)` with `max-height` and scroll.

### In-flight requests (§16)

`sendMessage` captures the model once, at call time, and passes it explicitly all the way to the request body. Changing the selector while a request is in flight cannot retarget that request; the new selection applies to the next one. Verified end-to-end by Test 10 of `test_agent_model_selection.mjs` using a delayed mocked response.

### Model switching preserves state

Switching only calls `setSelectedModel`. It does not touch conversation, document state, selected element, split view, or zoom — all verified in the browser (section K).

---

## G. Error semantics

Normalized vocabulary, shared by both providers:

| `error_type` | HTTP | User-facing copy |
|---|---|---|
| `config_missing` | 503 | *{Model} is not configured in this environment.* |
| `auth_error` | 502 | *{Model} authentication failed. Please verify provider credentials.* |
| `timeout` | 504 | *{Model} request timed out. Please try again.* |
| `rate_limited` | 429 | *{Model} is temporarily unavailable because its current API quota/rate limit was reached.* |
| `unavailable` | 503 | *{Model} is currently unavailable because the AI service could not be reached.* |
| `invalid_request` | 502 | *{Model} rejected the request as invalid.* |
| `malformed_response` | 502 | *{Model} returned a response that could not be read.* |
| `content_blocked` | 502 | *{Model} declined to answer this request under its safety policy.* |
| `unsupported_operation` | 501 | *{Model} does not support this operation.* |
| `unexpected` | 500 | *An unexpected error occurred while communicating with {Model}.* |

Gemini HTTP mapping: `401/403 → auth_error`, `429 → rate_limited`, `404 → invalid_request` (model not available to this key — explicitly an error, the other Gemini model is **not** tried), `400 → invalid_request`, `5xx → unavailable`, `requests.Timeout → timeout`, other `RequestException → unavailable`. A blocked prompt or a candidate with no text raises rather than returning an empty answer.

### Error card

```
⚠  Gemini 3.6 Flash has reached its quota                        ✕

   Gemini 3.6 Flash is temporarily unavailable because its current
   API quota/rate limit was reached. Retry Gemini 3.6 Flash, or
   choose a different model.

   [ ⟳ Retry Gemini 3.6 Flash ]  [ → Switch Model ]
```

- The card names **only** the failed model. Asserted mechanically: for each of the four models, the card text must contain none of the other three labels.
- No assistant bubble is created. The user's prompt stays in the transcript.
- **Retry** always re-sends to the model that failed, even if the selector has since been changed — verified by changing the selector to Luna after a Gemini 3.6 failure and confirming the retry still went to `gemini_3_6_flash`.
- **Switch Model** is a neutral toggle. It reveals the other three models by name and sends nothing until the user picks one. No model is pre-selected and opening the list fires no request.
- No API keys, endpoints, stack traces or raw provider dumps. Only the vendor's own `error.message` text (capped at 300 chars) is ever appended, and credential-hygiene assertions cover every error path.

---

## H. No-fallback guarantee

There is **zero** executable fallback. Enforced at four levels:

1. **Structural** — `_call_model` has no `except`. A `ProviderError` propagates to the route, which converts it to an error payload. No code path exists that could call a second model.
2. **Route** — the single `except ProviderError` handler builds an error response and returns. It never re-enters the orchestrator.
3. **Behavioural tests** — for each of the four models, both providers are mocked simultaneously (one failing, the other *succeeding*) and the test asserts the succeeding provider was called **zero** times and its content appears nowhere in the response:
   - `test_gemini_failure_does_not_fall_back_to_workbench`
   - `test_workbench_failure_does_not_fall_back_to_gemini`
   - `test_gemini_3_6_failure_does_not_call_gemini_3_5`
   - `test_gemini_3_5_failure_does_not_call_gemini_3_6`
   - `test_each_model_fails_as_itself_with_no_substitute` (×4)
4. **Static guard** — `test_no_executable_fallback_path_in_agent_sources` scans every `.py` under `applications/agent/` plus `api/routes/agent.py`, strips comments, and fails on `fall back to`, `auto switch`, `try the other model`, `retry with a different`. Policy prose in comments and docstrings is allowed; executable fallback is not.

### §42 codebase sweep

Grepped `foundation/applications`, `foundation/api`, `frontend/src` for `fallback`, `auto switch`, `silent`. Every hit is one of:

- **Policy prose** stating that fallback does not exist (`models.py:76`, `agent.ts:9`, `agent.ts:35`, `agent.py:57`, `workbench_client.py:160`).
- **`request.get_json(silent=True)`** — Flask JSON parsing, unrelated to models.
- **DOM anchor mapping fallbacks** in `docxAnchorMapping.ts` / `elementId.ts` — rendered-node matching inside one document, a pre-existing perception/rendering concern with no relation to model or provider selection.

No executable model-fallback, provider-fallback or auto-switch path exists.

### The default is not a fallback

`resolve_agent_model(None)` returns Luna. That is the documented default for "the user did not choose", applied *before* any provider is contacted. It is never reached after a failure — a present-but-unrecognized value raises instead of being coerced.

---

## I. Telemetry

`applications/pilot/event_log.py` `ALLOWED_FIELDS` gains `model_id`, `provider`, `request_status`. Every `agent.*` event now carries `model_id` and `provider`; `agent.request.started` carries `request_status="started"`, and the terminal events carry `request_status` of `success` or `error` alongside `error_type` and `error_category`.

Allowed values: `provider ∈ {workbench, gemini}`; `model_id ∈ {workbench_luna, workbench_sol, gemini_3_6_flash, gemini_3_5_flash}`.

The field allowlist remains the enforcement mechanism, not a convention: anything not on it is dropped before the event reaches disk. `test_pilot_telemetry_model_tracking_and_privacy` asserts that no event contains prompt text, document content, API keys, internal endpoints, or raw provider deployment/model names (`gpt-5-6-sol-…`, `gemini-3.6-flash`), and that every `agent.*` event carries the correct `model_id`/`provider` pair.

---

## J. Privacy

Gemini Free Tier data-use terms differ from corporate Workbench terms. The Gemini provider is therefore **off unless explicitly enabled**:

```
AI_PROVIDER_MODE = workbench   # default, including when unset — Gemini disabled
                 | local       # Gemini 3.6 / 3.5 Flash permitted
```

- Unset defaults to `workbench`, so Gemini can never become silently active on a corporate machine.
- `GEMINI_API_KEY` is backend-only, read from the environment, never hard-coded, and sent as the `x-goog-api-key` **header** — never a query parameter, so it cannot leak through a logged URL. It is never sent to the frontend.
- When Gemini is not enabled, the models still appear in the selector and still fail with an explicit *"Gemini 3.6 Flash is not configured in this environment."* They are **not** hidden, and they are **not** silently served by Workbench (`test_gemini_disabled_environment_errors_instead_of_switching`).
- `.env.example` documents this, including the policy line: *Gemini models are intended for local/demo use with approved non-sensitive documents. Do not send company confidential documents through Gemini unless explicitly authorized.*

That policy is deliberately **not** encoded as automatic routing. The operator enforces it by choosing the model and the environment mode.

---

## K. Tests

### Backend — `pytest foundation -q`

```
229 passed, 2 skipped in 190.72s
```

The 2 skips are the live Gemini tests, skipped because `GEMINI_API_KEY` is not set (section L). Everything else passes with zero skips.

New test files:

| File | Count | Covers |
|---|---|---|
| `tests/test_gemini_provider.py` | 31 | Request shaping, response parsing, every error mapping, credential hygiene |
| `tests/test_agent_provider_invariance.py` | 8 | Context / tool / governance invariance across all four models |
| `tests/test_gemini_live.py` | 2 (skipped) | Real Gemini smoke test, gated on a real key |
| `tests/gemini_mocks.py`, `tests/conftest.py` | — | Shared mocked Gemini responses and the `gemini_enabled` fixture |

Extended: `test_agent_orchestrator.py` (four-model selection, provider routing, allowlist rejection), `test_agent_fallback_elimination.py` (25 tests, now parametrized over all four models), `test_agent_route.py`, `test_pilot_instrumentation.py`, `eval_agent_readiness.py`.

Coverage of the §34 checklist:

| # | Requirement | Test |
|---|---|---|
| 1 | default = `workbench_luna` | `test_agent_chat_default_model_is_luna` |
| 2–5 | each of the four explicitly selectable | `test_agent_chat_explicit_luna` / `_sol` / `_gemini[×2]` |
| 6 | unknown model rejected | `test_agent_chat_unknown_model_rejected` (10 values), `test_agent_chat_empty_model_rejected` |
| 7 | correct provider per model | `test_agent_chat_explicit_*`, `test_selected_element_citation_identical_across_all_four_models` |
| 8 | correct model id passed to provider | asserted on the Workbench kwarg and the Gemini URL |
| 9 | provider errors propagated | `test_each_model_fails_as_itself_with_no_substitute` |
| 10 | no automatic model switching | call-count assertions on both mocked providers |
| 11 | no deterministic fallback | no `response` field on any error payload |
| 12 | retry uses same failed model | `test_retry_targets_the_same_failed_model` (×4) + Playwright Test 5 |
| 13 | provider-specific error type preserved | `test_gemini_provider.py` error-mapping tests |

### Gemini provider mocks (§35)

Success, timeout, auth error, 429 quota, 400 invalid request, 404 unknown model, 5xx, malformed body, non-JSON body, blocked prompt, `finishReason: SAFETY`. Every error path is additionally asserted to leak no API key, no `x-goog-api-key` header name, and no endpoint host.

### Frontend — `npm test` (oxlint + tsc + vite build)

Passes. One pre-existing unused-variable warning in `test_agent_eval.mjs`, untouched by this phase.

### Playwright — `test_agent_model_selection.mjs`

```
SUMMARY: 55 PASSED, 0 FAILED
```

Default is Luna · exactly four options in the required order · provider groups `["Workbench","Gemini"]` · each model selected and its response tagged with its own label · historical tags preserved across all switches · conversation preserved (5 responses) · documents and selected element preserved · governed proposal + confirmation still required under Gemini · zoom preserved (130% → 130%) · split view preserved (3 pane switchers → 3) · Enter/Escape, `aria-expanded`, exactly one `aria-selected="true"`, keyboard selection of a Gemini option · all five viewports fit the longest label with no horizontal body scroll and the dropdown inside the viewport · **in-flight request not retargeted** by a mid-flight selector change.

### Playwright — `test_agent_error_ux.mjs`

```
SUMMARY: 48 PASSED, 0 FAILED
```

All four models fail as themselves · no other model named in any card · zero assistant messages on failure · prompt preserved · retry button targets the failed model · quota wording correct and does not name Gemini 3.5 as a substitute · auth and config-missing wording · no secrets/endpoints/stack traces · **retry after changing the selector still goes to the failed model** · Switch Model offers exactly the other three, sends nothing until one is chosen, then sends exactly one request to that model · dismiss leaves no fabricated message.

### Foundation regression

| Suite | Result |
|---|---|
| `pytest foundation -q` | **229 passed, 2 skipped** |
| `eval_agent_readiness.py` | **47/47 scenarios, 16/16 hard gates, 0 violations** |
| `test_agent_architecture_audit.py` | **11 passed** |
| `npm test` / `npm run build` | **pass** |
| `test_both_fixtures.mjs` | **pass** |
| `test_xlsx_interaction.mjs` | **7/7 pass** |
| `test_agent_model_selection.mjs` | **55/55 pass** |
| `test_agent_error_ux.mjs` | **48/48 pass** |
| `test_ui_ux_closure.mjs` | 26/26 reported; exits 1 on sub-item 6a — **pre-existing**, see below |
| `test_agent_architecture.mjs` | **blocked** — requires live Workbench, see section M |
| `test_agent_eval.mjs` | **blocked** — requires live Workbench, see section M |

Required Foundation mapping — re-measured in the browser through the real rendering path:

| Fixture | Required | Measured |
|---|---|---|
| A — 848-element KPMG template | 848 / 848 | **848 / 848**, 0 unavailable, 0 ambiguous |
| B — 2,832-element HMV | 2832 / 2832 | **2832 / 2832**, 0 unavailable, 0 ambiguous |
| C — 4,764-element HMV comparison | 4744 / 4764 (20 honest unavailable) | **4744 / 4764**, 20 unavailable, 0 ambiguous |

Fixture C is not covered by `test_both_fixtures.mjs` (which loads A and B); it was measured by pointing the same in-browser mapping harness at `HMV 23&23 EN compare.docx`. The 20 unavailable are the documented image/drawing cases from `Foundation_Document_Mapping_Forensic_Audit_HMV_23_23.md` (`image` 14/31, `drawing` 2/4, `para` 411/412).

**`test_ui_ux_closure.mjs`** prints "ALL 26 UI/UX CLOSURE ACCEPTANCE TESTS PASSED" but exits 1 because of sub-item 6a (Elements → Original split-pane selection sync). This was confirmed pre-existing: with this phase's `frontend/src` changes stashed, the baseline run produces the identical failure and the identical exit code 1. It is unrelated to model selection and was not introduced here.

---

## L. Real Gemini verification

> **GEMINI LIVE VERIFIED: NO.**

`GEMINI_API_KEY` is not present in this environment. No real request was ever sent to `generativelanguage.googleapis.com` during this phase. Every Gemini result reported above is **MOCK VERIFIED** — `requests.post` replaced by fixtures in `tests/gemini_mocks.py`, exercising the real `GeminiProvider` parsing and error-mapping code but no network.

The live smoke test exists and is wired up: `tests/test_gemini_live.py` calls both `gemini-3.6-flash` and `gemini-3.5-flash` for real and asserts a non-empty response, correct model attribution, and the presence of `usageMetadata` (which a stub would not produce). It is `skipif`-gated on `GEMINI_API_KEY`, so it cannot silently pass without credentials — it currently reports:

```
SKIPPED [2] tests/test_gemini_live.py: GEMINI_API_KEY not set — live Gemini verification not performed
```

To perform live verification:

```powershell
$env:GEMINI_API_KEY = '...'
$env:AI_PROVIDER_MODE = 'local'
cd foundation
.venv/Scripts/python.exe -m pytest tests/test_gemini_live.py -v
```

Until that run is recorded, the Gemini wire format (`systemInstruction` + `contents`, no `generationConfig`) and the model ids `gemini-3.6-flash` / `gemini-3.5-flash` are **implemented and unit-tested but unconfirmed against the live API**.

---

## M. Workbench verification status

> **WORKBENCH LIVE VERIFIED: NO** (on this machine).

`applications/workbench_client.py` is byte-for-byte unchanged, so the corporate path is not expected to have regressed — but this was not proven here. This is a personal machine with no corporate VPN. `https://api.workbench.kpmg/...` answers `403`, and a live end-to-end request produces exactly the correct explicit failure:

```json
{ "error": "Luna authentication failed. Please verify provider credentials.",
  "error_type": "auth_error", "model_id": "workbench_luna",
  "provider": "workbench", "status": "error" }
```

That is the *no-fallback contract working as designed* — and it is also why `test_agent_architecture.mjs` and `test_agent_eval.mjs` cannot run here: both drive a real Agent conversation against the real backend with no HTTP mocking, and since deterministic fallback was eliminated in a previous phase, they require a reachable model provider. Neither is available on this machine (Workbench: no VPN; Gemini: no key).

Both suites were confirmed to fail for provider connectivity alone, not for anything in this phase: the request reaches the route, the orchestrator resolves the model, `WorkbenchProvider` calls the unchanged client, and the gateway rejects the credentials. They must be re-run on the corporate/VPN environment. Per §40, no corporate Workbench verification is claimed from this machine.

Live-verified on this machine using the running Flask server (`GET /api/agent/models`, `POST /api/agent/chat`):

- The four-model registry is served correctly with `provider`, `group` and `is_default`.
- `model_id: "luna"` → **HTTP 400** (allowlist enforced).
- `model_id: "workbench_luna"` → explicit `auth_error`, `provider: "workbench"`, no `response` field.
- `model_id: "gemini_3_6_flash"` → explicit `config_missing`, `provider: "gemini"`, and Workbench was not called.

---

## N. Remaining limitations

1. **No live Gemini verification** (section L) — the highest-priority follow-up. Sampling-parameter behaviour, exact error envelopes and model availability are unconfirmed against the real API.
2. **No live Workbench verification** (section M) — must be re-run on the corporate environment, including `test_agent_architecture.mjs` and `test_agent_eval.mjs`.
3. **Breaking request/response contract** — `model` → `model_id`, and the short ids `luna`/`sol` are now rejected with HTTP 400. Any external caller of `/api/agent/chat` outside this repository must be updated.
4. **Conversation history is not sent to the model.** Pre-existing: `_call_model` sends one system turn plus the current user turn. The provider interface accepts a full turn list and `GeminiProvider` already merges consecutive same-role turns and rejects a trailing prefilled model turn, so multi-turn is ready at the provider boundary whenever the Agent starts sending it.
5. **Structured output / function calling was not needed** (§25). Inspecting the current architecture: intent classification, target resolution, capability checks and proposal construction are all **deterministic Python** in the orchestrator; the model is used only to generate prose. Governance therefore never depends on model-emitted structure, and no function-calling adaptation was required for Gemini. `ProviderUnsupportedError` (`unsupported_operation`, HTTP 501) exists so that if a future phase does require structured operations, an incapable provider raises an explicit unsupported-provider error rather than being given a weakened governance path or a deterministic substitute.
6. **`test_ui_ux_closure.mjs` sub-item 6a** fails and the script exits 1. Confirmed pre-existing against the stashed baseline; out of scope for this phase.
7. **`AI_PROVIDER_MODE` gates Gemini only.** Workbench is always permitted, so `AI_PROVIDER_MODE=local` enables Gemini *in addition to* Workbench rather than replacing it. This keeps the corporate path unchanged, but it means the variable is not a general provider switch.
8. **No `.env` auto-loading.** The Flask app reads credentials straight from the process environment; `.env` is documentation, not something the server parses. Unchanged by this phase.

---

## O. Final status

| Acceptance item | Status |
|---|---|
| Luna selectable | **PASS** |
| Sol selectable | **PASS** |
| Gemini 3.6 Flash selectable | **PASS** (mock verified) |
| Gemini 3.5 Flash selectable | **PASS** (mock verified) |
| Default = Luna | **PASS** |
| Luna → Workbench | **PASS** |
| Sol → Workbench | **PASS** |
| Gemini 3.6 → Gemini | **PASS** (mock verified) |
| Gemini 3.5 → Gemini | **PASS** (mock verified) |
| Governance identical for all four | **PASS** |
| Zero automatic fallback | **PASS** |
| Zero deterministic fallback | **PASS** |
| Zero silent switching | **PASS** |
| Provider errors explicit | **PASS** |
| Four-model selector | **PASS** |
| Responsive (5 viewports) | **PASS** |
| Accessible | **PASS** |
| Foundation mapping A / B / C | **PASS** (848/848 · 2832/2832 · 4744/4764) |
| **Gemini live verification** | **NOT PERFORMED** — no `GEMINI_API_KEY` |
| **Workbench live verification** | **NOT PERFORMED** — no corporate VPN |

**Verification legend used throughout this report**

- **MOCK VERIFIED** — the real provider code ran against a mocked HTTP layer. Applies to every Gemini result here.
- **GEMINI LIVE VERIFIED** — not claimed anywhere in this report.
- **WORKBENCH LIVE VERIFIED** — not claimed anywhere in this report.

### Final architectural principle, as implemented

The user chooses exactly one model. That model is authoritative for that request, and so is its provider. If it works, its response is returned and attributed to it. If it fails, the error is shown, naming that model and nothing else. The system does not decide for the user: it never falls back, never auto-routes, never silently switches, and never fabricates a model response. Foundation remains the source of truth for document state, identity, capabilities, writeback and governance — identically for all four models.
