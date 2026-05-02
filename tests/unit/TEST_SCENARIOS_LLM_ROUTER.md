# LLM Router — Test Scenarios

Unit test coverage for `pm_agent/adapters/llm/` (Phase 2).
All scenarios run without live API calls — provider constructors are mocked.

Corresponding test file: `tests/unit/test_llm_router.py`

---

## 1. `resolve_model_config` — Model Config Resolution

Tests the three-level priority chain: ritual override → (SDLC mode, Phase 7) → global tier.

| # | Scenario | Expected |
|---|----------|----------|
| 1.1 | No override, tier = `fast` | Returns `app_config.llm.fast` |
| 1.2 | No override, tier = `mid` | Returns `app_config.llm.mid` |
| 1.3 | No override, tier = `strong` | Returns `app_config.llm.strong` |
| 1.4 | Ritual has `model_override` matching the called ritual | Returns the override config (provider/model/temp/tokens) |
| 1.5 | Override exists but for a **different** ritual | Falls back to global tier |
| 1.6 | Ritual entry exists with no `model_override` key (e.g. only `schedule`) | Falls back to global tier |
| 1.7 | `ritual_overrides` is empty dict | Falls back to global tier |
| 1.8 | Override specifies all fields (provider, model, temperature, max_tokens) | All fields correctly reflected in returned `ModelTierConfig` |

### Notes
- The resolver does **not** validate that the override's provider string is one of the four known providers — `ModelTierConfig.model_validate` handles that via Pydantic.
- SDLC-mode tier mapping (between step 1 and step 3) is a Phase 7 hook. The resolver has a comment marking the insertion point; no test for it yet.

---

## 2. `get_llm` — Provider Factory

### 2a. Correct subclass instantiation

| # | Scenario | Expected constructor |
|---|----------|----------------------|
| 2.1 | `provider = "gemini"` | `ChatGoogleGenerativeAI(model=…, temperature=…, max_output_tokens=…)` |
| 2.2 | `provider = "claude"` | `ChatAnthropic(model=…, temperature=…, max_tokens=…)` |
| 2.3 | `provider = "azure_openai"` | `AzureChatOpenAI(azure_deployment=…, temperature=…, max_tokens=…)` |
| 2.4 | `provider = "ollama"`, no `base_url` | `ChatOllama(model=…, temperature=…, num_predict=…, base_url="http://localhost:11434")` |
| 2.5 | `provider = "ollama"`, custom `base_url` | `base_url` is passed through to `ChatOllama` unchanged |

### 2b. Ollama-specific kwarg correctness

| # | Scenario | Expected |
|---|----------|----------|
| 2.6 | Ollama config | Constructor kwargs contain `num_predict`, **not** `max_tokens` |
| 2.7 | Ollama config, `base_url = None` | Falls back to default `http://localhost:11434` |

> **Why this matters**: `ChatOllama` ignores `max_tokens` silently. Using the wrong kwarg would truncate output without any error, causing subtle context-overflow bugs in Phase 3.

### 2c. Error handling

| # | Scenario | Expected |
|---|----------|----------|
| 2.8 | `provider = "openai"` (unsupported) | `ValueError` with message mentioning the bad provider name |
| 2.9 | `provider = ""` (empty string) | `ValueError` raised |

### 2d. Return-type contract

| # | Scenario | Expected |
|---|----------|----------|
| 2.10 | Gemini config | Returned object is the mock `BaseChatModel` instance from the constructor |
| 2.11 | Claude config | Returned object is the mock `BaseChatModel` instance from the constructor |

> The factory must never return a provider-specific type to callers. Tests 2.10–2.11 verify the return value is whatever the constructor returns, enforcing the abstraction boundary.

---

## 3. `get_structured_llm` — Structured Output Helper

| # | Scenario | Expected |
|---|----------|----------|
| 3.1 | Normal call | Returns the Runnable from `llm.with_structured_output(…)` |
| 3.2 | `include_raw` flag | `llm.with_structured_output` called with `include_raw=True` |
| 3.3 | Default `max_retries` | Returned runnable has `.max_retries == 3` |
| 3.4 | Custom `max_retries=5` | Returned runnable has `.max_retries == 5` |
| 3.5 | Schema argument | The schema *class* (not an instance) is passed as first positional arg to `with_structured_output` |

### Notes
- `include_raw=True` returns `{"raw": AIMessage, "parsed": schema | None, "parsing_error": str | None}`. This shape is what ritual code must destructure — parse failures are visible rather than silently swallowed.
- `max_retries` is stored as metadata on the runnable. The actual retry loop lives in the calling ritual (using `tenacity`), not inside this helper, to keep the helper thin and stateless.

---

## 4. Public API Surface

| # | Scenario | Expected |
|---|----------|----------|
| 4.1 | `from pm_agent.adapters.llm import get_llm` | Importable and callable |
| 4.2 | `from pm_agent.adapters.llm import resolve_model_config` | Importable and callable |
| 4.3 | `from pm_agent.adapters.llm import get_structured_llm` | Importable and callable |

> These tests ensure `__init__.py` correctly re-exports all three functions and no import-time side-effects break the package load.

---

## Coverage Summary

| Module | Scenarios | Classes |
|--------|-----------|---------|
| `resolver.py` | 1.1 – 1.8 | `TestResolveModelConfig` |
| `factory.py` | 2.1 – 2.11 | `TestGetLlmProviderRouting`, `TestGetLlmReturnType` |
| `structured.py` | 3.1 – 3.5 | `TestGetStructuredLlm` |
| `__init__.py` | 4.1 – 4.3 | `TestPublicApi` |

**Total: 27 scenarios**

---

## What Is NOT Tested Here

| Scenario | Reason | Where it's tested |
|----------|--------|-------------------|
| Live API response from Gemini/Claude/Azure | Requires real credentials; flaky in CI | Manual smoke test in `Verification (Phase 2)` of implementation plan |
| Ollama context limit interaction with `ContextBudgetWatcher` | `ContextBudgetWatcher` doesn't exist yet | Phase 3 tests |
| SDLC-mode tier override | Phase 7 feature not implemented | Phase 7 tests |
| Tenacity retry on structured output parse failure | Retry lives in ritual layer, not this helper | Phase 6–8 ritual tests |
| `ritual_config.yaml` file loading end-to-end | Config loading is Phase 0 scope | `test_config_loader.py` (future) |
