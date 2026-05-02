"""
Config loading and caching for PM Agent.
Configuration is loaded once at startup via load_config() and cached.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml
from pm_agent.config.models import AppConfig


@lru_cache(maxsize=1)
def load_config(config_path: str = "config.yaml") -> AppConfig:
    """
    Load application configuration from YAML file.
    Configuration is cached (LRU, maxsize=1) - subsequent calls return the cached instance.
    
    Args:
        config_path: Path to config.yaml file (default: "config.yaml" in current directory)
    
    Returns:
        AppConfig: Validated configuration object
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValueError: If config doesn't validate against AppConfig schema
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_file.resolve()}\n"
            "Please create config.yaml by copying config.yaml.example and filling in your values."
        )
    
    with open(config_file) as f:
        raw: Any = yaml.safe_load(f)
    
    if raw is None:
        raise ValueError(f"Config file {config_file} is empty")
    
    return AppConfig.model_validate(raw)


def reload_config(config_path: str = "config.yaml") -> AppConfig:
    """
    Force reload of configuration, clearing the cache.
    Useful for testing or dynamic config updates.
    
    Args:
        config_path: Path to config.yaml file
    
    Returns:
        AppConfig: Fresh configuration object
    """
    load_config.cache_clear()
    return load_config(config_path)


def get_config() -> AppConfig:
    """
    Get the cached configuration. Alias for load_config() for convenience.
    
    Returns:
        AppConfig: Cached configuration object
    """
    return load_config()
