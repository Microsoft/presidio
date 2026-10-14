from pathlib import Path
from typing import Any, Dict, List, Union

from pydantic import ValidationError

from presidio_analyzer.score_thresholds import (
    normalize_score_thresholds,
    validate_score_threshold,
)

from . import validate_language_codes
from .yaml_recognizer_models import RecognizerRegistryConfig


class ConfigurationValidator:
    """Class for validating configurations using Pydantic-enabled classes."""

    @staticmethod
    def validate_language_codes(languages: List[str]) -> List[str]:
        """Validate language codes format.

        :param languages: List of languages to validate.
        """
        validate_language_codes(languages)
        return languages

    @staticmethod
    def validate_file_path(file_path: Union[str, Path]) -> Path:
        """Validate file path exists and is readable.

        :param file_path: Path to validate.
        """
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Configuration file does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        return path

    @staticmethod
    def validate_score_threshold(threshold: float) -> float:
        """Validate score threshold is within valid range.

        :param threshold: score threshold to validate.
        """
        return validate_score_threshold(threshold)

    @staticmethod
    def validate_nlp_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate NLP configuration structure.

        :param config: NLP Configuration to validate.
        """
        if not isinstance(config, dict):
            raise ValueError("NLP configuration must be a dictionary")

        required_fields = ["nlp_engine_name", "models"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(
                f"NLP configuration missing required fields: {missing_fields}"
            )

        # Validate models structure
        if not isinstance(config["models"], list) or not config["models"]:
            raise ValueError("Models must be a non-empty list")

        for model in config["models"]:
            if not isinstance(model, dict):
                raise ValueError("Each model must be a dictionary")
            if "lang_code" not in model or "model_name" not in model:
                raise ValueError("Each model must have 'lang_code' and 'model_name'")

        return config

    @staticmethod
    def validate_recognizer_registry_configuration(
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate recognizer registry configuration using Pydantic models."""
        try:
            # Use Pydantic model for validation
            validated_config = RecognizerRegistryConfig(**config)
            dumped_config = (
                ConfigurationValidator._dump_recognizer_registry_configuration(
                    validated_config
                )
            )
            for recognizer in dumped_config["recognizers"]:
                if isinstance(recognizer, dict):
                    normalize_score_thresholds(recognizer.get("score_thresholds"))
            return dumped_config
        except ValidationError as e:
            raise ValueError("Invalid recognizer registry configuration") from e

    @staticmethod
    def _dump_recognizer_registry_configuration(
        validated_config: RecognizerRegistryConfig,
    ) -> Dict[str, Any]:
        """Dump registry config while preserving recognizer-specific dump rules."""
        dumped_config = validated_config.model_dump(
            exclude_unset=False, exclude={"recognizers"}
        )
        dumped_config["recognizers"] = [
            recognizer
            if isinstance(recognizer, str)
            else recognizer.model_dump()
            for recognizer in validated_config.recognizers
        ]
        return dumped_config

    @staticmethod
    def validate_analyzer_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate analyzer engine configuration."""
        if not isinstance(config, dict):
            raise ValueError("Analyzer configuration must be a dictionary")

        # Define valid top-level keys for analyzer configuration
        valid_keys = {
            "supported_languages",
            "default_score_threshold",
            "nlp_configuration",
            "recognizer_registry",
        }

        # Check for unknown keys
        unknown_keys = set(config.keys()) - valid_keys
        if unknown_keys:
            raise ValueError(
                f"Unknown configuration key(s) in "
                f"analyzer configuration: {sorted(unknown_keys)}. "
                f"Valid keys are: {sorted(valid_keys)}"
            )

        # Validate supported languages if present
        if "supported_languages" in config:
            validate_language_codes(config["supported_languages"])

        # Validate score threshold if present
        if "default_score_threshold" in config:
            ConfigurationValidator.validate_score_threshold(
                config["default_score_threshold"]
            )

        # Validate nested configurations
        if "nlp_configuration" in config:
            ConfigurationValidator.validate_nlp_configuration(
                config["nlp_configuration"]
            )

        if "recognizer_registry" in config:
            ConfigurationValidator.validate_recognizer_registry_configuration(
                config["recognizer_registry"]
            )

        return config
