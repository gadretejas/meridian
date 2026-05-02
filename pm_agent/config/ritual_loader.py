"""
Ritual configuration loading for PM Agent.
Handles ritual_config.yaml which contains per-ritual overrides and scheduling.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml


@lru_cache(maxsize=1)
def load_ritual_config(config_path: str = "ritual_config.yaml") -> Any:
    """
    Load ritual-specific configuration overrides from YAML file.
    
    Returns a dict[str, dict] keyed by ritual name, where each value contains:
    - model_override: Optional ModelTierConfig override
    - schedule: Optional cron expression for APScheduler
    - approval_required: Optional override of approval gate
    - Other ritual-specific settings
    
    Args:
        config_path: Path to ritual_config.yaml file
    
    Returns:
        dict[str, Any]: Ritual overrides keyed by ritual name, empty dict if file doesn't exist
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        # ritual_config.yaml is optional - return empty dict if missing
        return {}
    
    with open(config_file) as f:
        raw: Any = yaml.safe_load(f)
    
    if raw is None:
        return {}
    
    if not isinstance(raw, dict):
        raise ValueError(f"ritual_config.yaml must be a YAML object (dict), got {type(raw)}")
    
    return {**raw}


def reload_ritual_config(config_path: str = "ritual_config.yaml") -> Any:
    """
    Force reload of ritual configuration, clearing the cache.
    
    Args:
        config_path: Path to ritual_config.yaml file
    
    Returns:
        dict[str, Any]: Fresh ritual overrides
    """
    load_ritual_config.cache_clear()
    return load_ritual_config(config_path)


def get_ritual_config() -> Any:
    """
    Get the cached ritual configuration. Alias for load_ritual_config() for convenience.
    
    Returns:
        dict[str, Any]: Cached ritual overrides
    """
    return load_ritual_config()


def get_ritual_override(ritual_name: str) -> dict[str, Any]:
    """
    Get overrides for a specific ritual by name.
    
    Args:
        ritual_name: Name of the ritual (e.g., "standup_agenda")
    
    Returns:
        dict[str, Any]: Override dict for this ritual, or empty dict if not configured
    """
    config = get_ritual_config()
    if not isinstance(config, dict):
        return {}
    return config.get(ritual_name, {})  # type: ignore[no-any-return]
