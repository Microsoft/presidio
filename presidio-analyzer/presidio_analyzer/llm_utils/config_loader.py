"""Configuration loading utilities for LLM recognizers."""

import logging
from pathlib import Path
from typing import Dict, List, Union

import yaml

logger = logging.getLogger("presidio-analyzer")

__all__ = [
    "get_conf_path",
    "load_yaml_file",
    "resolve_config_path",
    "get_model_config",
    "validate_config_fields",
]


def get_conf_path(filename: str, conf_subdir: str = "conf") -> Path:
    """Get absolute path to file in configuration directory.

    :param filename: Name of the file to locate.
    :param conf_subdir: Subdirectory name within package (default: "conf").
    :return: Absolute path to the configuration file.
    """
    return Path(__file__).parent.parent / conf_subdir / filename


def resolve_config_path(config_path: Union[str, Path]) -> Path:
    """Resolve configuration file path to absolute path.

    Handles paths in multiple formats (checked in order):
    1. Absolute paths: returned as-is
    2. Relative paths that exist from CWD: returned as-is
    3. Paths resolved from the package conf/ directory
    4. Relative paths resolved from repository root

    :param config_path: Configuration file path (string or Path object).
    :return: Resolved absolute path.
    """
    config_path_obj = Path(config_path)

    if config_path_obj.is_absolute():
        return config_path_obj

    if config_path_obj.exists():
        return config_path_obj

    conf_resolved = get_conf_path(str(config_path))
    if conf_resolved.exists():
        return conf_resolved

    presidio_analyzer_root = Path(__file__).parent.parent
    repo_root = presidio_analyzer_root.parent.parent
    repo_resolved = repo_root / config_path

    return repo_resolved


def load_yaml_file(filepath: Union[str, Path]) -> Dict:
    """Load and parse YAML configuration file.

    Automatically resolves relative paths from presidio_analyzer package root.

    :param filepath: Path to YAML file (string or Path object).
    :return: Parsed YAML content as dictionary.
    :raises FileNotFoundError: If file doesn't exist.
    :raises ValueError: If YAML parsing fails.
    """
    resolved_path = resolve_config_path(filepath)

    if not resolved_path.exists():
        raise FileNotFoundError(f"File not found: {resolved_path}")

    try:
        with open(resolved_path) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML: {e}")


def get_model_config(config: Dict, provider_key: str) -> Dict:
    """Extract and validate model configuration from provider config.

    :param config: Full configuration dictionary.
    :param provider_key: Provider key (e.g., "openai", "ollama").
    :return: Model configuration dictionary.
    :raises ValueError: If required model fields are missing.
    """
    validate_config_fields(
        config,
        [
            (provider_key,),
            (provider_key, "model"),
            (provider_key, "model", "model_id"),
        ],
    )

    return config[provider_key]["model"]


def validate_config_fields(
    config: Dict,
    required_fields: List[Union[str, tuple]],
    config_name: str = "Configuration",
) -> None:
    """Validate that required fields exist in configuration.

    :param config: Configuration dictionary to validate.
    :param required_fields: List of required field names (str) or nested paths (tuple).
    :param config_name: Name of config for error messages (default: "Configuration").
    :raises ValueError: If any required field is missing or empty.
    """
    for field in required_fields:
        if isinstance(field, str):
            if not config.get(field):
                raise ValueError(f"{config_name} must contain '{field}'")
        elif isinstance(field, tuple):
            current = config
            for i, key in enumerate(field):
                if not isinstance(current, dict) or key not in current:
                    path = ".".join(field[: i + 1])
                    raise ValueError(f"{config_name} must contain '{path}'")
                current = current[key]
                if i == len(field) - 1 and not current:
                    path = ".".join(field)
                    raise ValueError(f"{config_name} must contain '{path}'")
