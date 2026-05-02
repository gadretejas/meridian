"""
Unit tests for Phase 2 — LLM Provider Router.

All LLM provider classes are mocked. No live API calls are made.
See TEST_SCENARIOS_LLM_ROUTER.md for the full scenario catalogue.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from pm_agent.adapters.llm.factory import get_llm
from pm_agent.adapters.llm.resolver import resolve_model_config
from pm_agent.adapters.llm.structured import get_structured_llm
from pm_agent.config.models import AppConfig, LLMConfig, ModelTierConfig, ProjectConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _tier(provider: str, model: str, **kwargs) -> ModelTierConfig:
    return ModelTierConfig(provider=provider, model=model, temperature=0.3, max_tokens=1024, **kwargs)


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig(
        project=ProjectConfig(name="test-project"),
        llm=LLMConfig(
            fast=_tier("gemini", "models/gemini-2.0-flash"),
            mid=_tier("claude", "claude-sonnet-4-6"),
            strong=_tier("claude", "claude-opus-4-7"),
        ),
        ticket_sources={"primary": "github", "github": {"repo": "test/repo"}},
    )


# ---------------------------------------------------------------------------
# resolve_model_config
# ---------------------------------------------------------------------------

class TestResolveModelConfig:
    def test_returns_global_fast_tier_when_no_override(self, app_config):
        result = resolve_model_config("standup_agenda", "fast", app_config, {})
        assert result == app_config.llm.fast

    def test_returns_global_mid_tier_when_no_override(self, app_config):
        result = resolve_model_config("standup_agenda", "mid", app_config, {})
        assert result == app_config.llm.mid

    def test_returns_global_strong_tier_when_no_override(self, app_config):
        result = resolve_model_config("standup_agenda", "strong", app_config, {})
        assert result == app_config.llm.strong

    def test_ritual_override_takes_precedence_over_global_tier(self, app_config):
        overrides = {
            "standup_agenda": {
                "model_override": {
                    "provider": "ollama",
                    "model": "llama3.2",
                    "temperature": 0.1,
                    "max_tokens": 512,
                }
            }
        }
        result = resolve_model_config("standup_agenda", "fast", app_config, overrides)
        assert result.provider == "ollama"
        assert result.model == "llama3.2"

    def test_override_for_different_ritual_does_not_apply(self, app_config):
        overrides = {
            "other_ritual": {
                "model_override": {
                    "provider": "ollama",
                    "model": "llama3.2",
                    "temperature": 0.1,
                    "max_tokens": 512,
                }
            }
        }
        result = resolve_model_config("standup_agenda", "fast", app_config, overrides)
        assert result == app_config.llm.fast

    def test_ritual_with_no_model_override_key_falls_back_to_global(self, app_config):
        overrides = {"standup_agenda": {"schedule": "0 9 * * 1-5"}}
        result = resolve_model_config("standup_agenda", "mid", app_config, overrides)
        assert result == app_config.llm.mid

    def test_empty_ritual_overrides_uses_global_tier(self, app_config):
        result = resolve_model_config("task_creator", "strong", app_config, {})
        assert result == app_config.llm.strong

    def test_override_model_tier_config_fields_are_correct(self, app_config):
        overrides = {
            "task_creator": {
                "model_override": {
                    "provider": "gemini",
                    "model": "models/gemini-2.5-pro",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                }
            }
        }
        result = resolve_model_config("task_creator", "fast", app_config, overrides)
        assert result.provider == "gemini"
        assert result.model == "models/gemini-2.5-pro"
        assert result.temperature == 0.7
        assert result.max_tokens == 2048


# ---------------------------------------------------------------------------
# get_llm — correct subclass is returned per provider
# ---------------------------------------------------------------------------

class TestGetLlmProviderRouting:
    @patch("pm_agent.adapters.llm.factory.ChatGoogleGenerativeAI")
    def test_gemini_returns_google_model(self, mock_cls):
        config = _tier("gemini", "models/gemini-2.0-flash")
        get_llm(config)
        mock_cls.assert_called_once_with(
            model="models/gemini-2.0-flash",
            temperature=0.3,
            max_output_tokens=1024,
        )

    @patch("pm_agent.adapters.llm.factory.ChatAnthropic")
    def test_claude_returns_anthropic_model(self, mock_cls):
        config = _tier("claude", "claude-sonnet-4-6")
        get_llm(config)
        mock_cls.assert_called_once_with(
            model="claude-sonnet-4-6",
            temperature=0.3,
            max_tokens=1024,
        )

    @patch("pm_agent.adapters.llm.factory.AzureChatOpenAI")
    def test_azure_openai_returns_azure_model(self, mock_cls):
        config = _tier("azure_openai", "gpt-4o")
        get_llm(config)
        mock_cls.assert_called_once_with(
            azure_deployment="gpt-4o",
            temperature=0.3,
            max_tokens=1024,
        )

    @patch("pm_agent.adapters.llm.factory.ChatOllama")
    def test_ollama_returns_ollama_model(self, mock_cls):
        config = _tier("ollama", "llama3.2")
        get_llm(config)
        mock_cls.assert_called_once_with(
            model="llama3.2",
            temperature=0.3,
            num_predict=1024,
            base_url="http://localhost:11434",
        )

    @patch("pm_agent.adapters.llm.factory.ChatOllama")
    def test_ollama_uses_custom_base_url_when_set(self, mock_cls):
        config = _tier("ollama", "mistral", base_url="http://gpu-server:11434")
        get_llm(config)
        mock_cls.assert_called_once_with(
            model="mistral",
            temperature=0.3,
            num_predict=1024,
            base_url="http://gpu-server:11434",
        )

    @patch("pm_agent.adapters.llm.factory.ChatOllama")
    def test_ollama_uses_num_predict_not_max_tokens(self, mock_cls):
        """Ensure Ollama-specific kwarg is used — max_tokens is wrong for ChatOllama."""
        config = _tier("ollama", "qwen2.5-coder", base_url=None)
        get_llm(config)
        call_kwargs = mock_cls.call_args.kwargs
        assert "num_predict" in call_kwargs
        assert "max_tokens" not in call_kwargs

    def test_unknown_provider_raises_value_error(self):
        # model_construct bypasses Pydantic's Literal validation so we can test the factory's own guard
        config = ModelTierConfig.model_construct(
            provider="openai",
            model="gpt-4o",
            temperature=0.3,
            max_tokens=1024,
        )
        with pytest.raises(ValueError, match="Unknown LLM provider 'openai'"):
            get_llm(config)

    def test_empty_provider_raises_value_error(self):
        config = ModelTierConfig.model_construct(
            provider="",
            model="some-model",
            temperature=0.3,
            max_tokens=1024,
        )
        with pytest.raises(ValueError):
            get_llm(config)


# ---------------------------------------------------------------------------
# get_llm — return type is always BaseChatModel
# ---------------------------------------------------------------------------

class TestGetLlmReturnType:
    @patch("pm_agent.adapters.llm.factory.ChatGoogleGenerativeAI")
    def test_gemini_result_is_base_chat_model_compatible(self, mock_cls):
        from langchain_core.language_models.chat_models import BaseChatModel
        mock_instance = MagicMock(spec=BaseChatModel)
        mock_cls.return_value = mock_instance
        result = get_llm(_tier("gemini", "models/gemini-2.0-flash"))
        assert result is mock_instance

    @patch("pm_agent.adapters.llm.factory.ChatAnthropic")
    def test_claude_result_is_base_chat_model_compatible(self, mock_cls):
        from langchain_core.language_models.chat_models import BaseChatModel
        mock_instance = MagicMock(spec=BaseChatModel)
        mock_cls.return_value = mock_instance
        result = get_llm(_tier("claude", "claude-sonnet-4-6"))
        assert result is mock_instance


# ---------------------------------------------------------------------------
# get_structured_llm
# ---------------------------------------------------------------------------

class SampleSchema(BaseModel):
    answer: str
    confidence: float


class TestGetStructuredLlm:
    def test_returns_runnable(self):
        mock_llm = MagicMock()
        mock_runnable = MagicMock()
        mock_llm.with_structured_output.return_value = mock_runnable
        result = get_structured_llm(mock_llm, SampleSchema)
        assert result is mock_runnable

    def test_calls_with_structured_output_with_include_raw(self):
        mock_llm = MagicMock()
        get_structured_llm(mock_llm, SampleSchema)
        mock_llm.with_structured_output.assert_called_once_with(SampleSchema, include_raw=True)

    def test_default_max_retries_is_three(self):
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()
        result = get_structured_llm(mock_llm, SampleSchema)
        assert result.max_retries == 3

    def test_custom_max_retries_is_stored(self):
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()
        result = get_structured_llm(mock_llm, SampleSchema, max_retries=5)
        assert result.max_retries == 5

    def test_passes_schema_class_not_instance(self):
        mock_llm = MagicMock()
        get_structured_llm(mock_llm, SampleSchema)
        call_args = mock_llm.with_structured_output.call_args
        assert call_args.args[0] is SampleSchema


# ---------------------------------------------------------------------------
# Public API surface (__init__ re-exports)
# ---------------------------------------------------------------------------

class TestPublicApi:
    def test_get_llm_importable_from_package(self):
        from pm_agent.adapters.llm import get_llm as _get_llm  # noqa: F401
        assert callable(_get_llm)

    def test_resolve_model_config_importable_from_package(self):
        from pm_agent.adapters.llm import resolve_model_config as _r  # noqa: F401
        assert callable(_r)

    def test_get_structured_llm_importable_from_package(self):
        from pm_agent.adapters.llm import get_structured_llm as _g  # noqa: F401
        assert callable(_g)
