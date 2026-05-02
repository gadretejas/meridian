"""
ModelTierConfig resolution with a three-level priority chain:
  1. Ritual-level model_override from ritual_config.yaml
  2. (SDLC mode tier mapping — Phase 7 hook, currently falls through)
  3. Global llm.<tier> from config.yaml
"""

from typing import Literal

from pm_agent.config.models import AppConfig, ModelTierConfig


def resolve_model_config(
    ritual_name: str,
    tier: Literal["fast", "mid", "strong"],
    app_config: AppConfig,
    ritual_overrides: dict,
) -> ModelTierConfig:
    """
    Resolve the ModelTierConfig for a ritual + tier combination.

    Args:
        ritual_name: Name of the ritual requesting an LLM (e.g. "standup_agenda").
        tier: Requested model tier — "fast", "mid", or "strong".
        app_config: Loaded AppConfig (from config.yaml).
        ritual_overrides: Loaded ritual_config.yaml dict (may be empty).

    Returns:
        ModelTierConfig for the resolved provider/model.

    Raises:
        ValueError: If the ritual override contains an invalid ModelTierConfig.
    """
    override = ritual_overrides.get(ritual_name, {}).get("model_override")
    if override:
        return ModelTierConfig.model_validate(override)

    # Phase 7 will insert SDLC-mode tier mapping here before the global fallback.

    return getattr(app_config.llm, tier)
