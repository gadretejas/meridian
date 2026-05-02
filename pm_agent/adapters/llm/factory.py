"""
LLM provider factory.

Routes a ModelTierConfig to the correct LangChain BaseChatModel subclass.
All callers receive BaseChatModel — no provider-specific types leak out.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI

from pm_agent.config.models import ModelTierConfig


def get_llm(config: ModelTierConfig) -> BaseChatModel:
    """
    Instantiate the correct LangChain chat model for the given config.

    Supported providers: gemini, claude, azure_openai, ollama.

    Args:
        config: Resolved ModelTierConfig (provider, model, temperature, max_tokens, …).

    Returns:
        A BaseChatModel instance ready for .invoke() / .with_structured_output().

    Raises:
        ValueError: If config.provider is not one of the four supported values.
    """
    match config.provider:
        case "gemini":
            return ChatGoogleGenerativeAI(
                model=config.model,
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            )

        case "claude":
            return ChatAnthropic(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        case "azure_openai":
            return AzureChatOpenAI(
                azure_deployment=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        case "ollama":
            return ChatOllama(
                model=config.model,
                temperature=config.temperature,
                num_predict=config.max_tokens,  # Ollama uses num_predict, not max_tokens
                base_url=config.base_url or "http://localhost:11434",
            )

        case _:
            raise ValueError(
                f"Unknown LLM provider '{config.provider}'. "
                "Expected one of: gemini, claude, azure_openai, ollama."
            )
