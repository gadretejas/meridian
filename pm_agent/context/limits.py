"""
Model context limit registry.

Maps model names to their token context windows.
Ollama models default to a conservative 8,192 if not explicitly configured
(matches the default num_ctx for many locally pulled models).
"""

from pm_agent.config.models import ModelTierConfig

MODEL_CONTEXT_LIMITS: dict[str, int] = {
    # Gemini
    "models/gemini-2.0-flash": 1_048_576,
    "models/gemini-2.5-pro": 1_048_576,
    # Claude
    "claude-sonnet-4-20250514": 200_000,
    "claude-opus-4-20250514": 200_000,
    "claude-sonnet-4-6": 200_000,
    "claude-opus-4-7": 200_000,
    # Azure OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    # Ollama — defaults at standard num_ctx; override with ollama_context_limit in config
    "llama3.2": 131_072,
    "llama3.1": 131_072,
    "mistral": 32_768,
    "mistral-nemo": 131_072,
    "qwen2.5-coder": 131_072,
    "qwen2.5": 131_072,
    "deepseek-r1": 131_072,
    "phi4": 16_384,
    "gemma2": 8_192,
}

_OLLAMA_FALLBACK = 8_192
_CLOUD_FALLBACK = 128_000


def get_context_limit(model_config: ModelTierConfig) -> int:
    """
    Return the token context limit for the given model config.

    Resolution order:
    1. Explicit ollama_context_limit in config (matches your actual num_ctx)
    2. MODEL_CONTEXT_LIMITS registry lookup by model name
    3. Conservative fallback (8k for Ollama, 128k for cloud providers)

    Args:
        model_config: Resolved ModelTierConfig for the active model.

    Returns:
        Token context window size as an integer.
    """
    if model_config.provider == "ollama" and model_config.ollama_context_limit:
        return model_config.ollama_context_limit

    limit = MODEL_CONTEXT_LIMITS.get(model_config.model)
    if limit:
        return limit

    return _OLLAMA_FALLBACK if model_config.provider == "ollama" else _CLOUD_FALLBACK
