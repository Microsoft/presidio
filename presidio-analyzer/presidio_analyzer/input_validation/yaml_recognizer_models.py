"""Pydantic models for YAML recognizer configurations."""

from typing import Any, Dict, List, Literal, Optional, Type, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from presidio_analyzer.input_validation import validate_language_codes
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    PredefinedRecognizerNotFoundError,
    RecognizerListLoader,
)


class LanguageContextConfig(BaseModel):
    """Configuration for language-specific validation with context words.

    :param language: Language code (e.g., 'en', 'es')
    :param context: Context words for this language
    """

    language: str = Field(..., description="Language code (e.g., 'en', 'es')")
    context: Optional[List[str]] = Field(
        default=None, description="Context words for this language"
    )

    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validate language code format."""
        validate_language_codes([v])
        return v


class BaseRecognizerConfig(BaseModel):
    """Base validation for all recognizer configuration types.

    :param name: Instance name used in analysis results. Defaults to class name.
    :param class_name: Python class name for lookup. If not provided, uses 'name'.
    :param enabled: Whether the recognizer is enabled
    :param type: Type of recognizer (predefined/custom)
    :param supported_language: Single supported language (legacy)
    :param supported_languages: Multiple supported languages with optional context.
    Passing multiple languages will result in multiple actual
    recognizers initialized in Presidio.
    :param context: context words. Context is best defined
    in the language-specific configuration,
    as it is language-dependent. If context is defined outside,
    it should only work if the user passed one language
    (either in supported_language or have a supported_languages with length 1).
    :param supported_entity: Supported entity for this recognizer (legacy)
    :param supported_entities: List of supported entities for this recognizer.
    """

    name: str = Field(..., description="Instance name for the recognizer")
    class_name: Optional[str] = Field(
        default=None,
        description=(
            "Python class name for predefined recognizers "
            "(if different from instance name)"
        ),
    )
    enabled: bool = Field(default=True, description="Whether the recognizer is enabled")
    type: Optional[str] = Field(
        default="predefined", description="Type of recognizer (predefined/custom)"
    )
    supported_language: Optional[str] = Field(
        default=None, description="The language this recognizer supports"
    )
    supported_languages: Optional[Union[List[str], List[LanguageContextConfig]]] = (
        Field(
            default=None,
            description="Multiple supported languages with optional context",
        )
    )
    context: Optional[List[str]] = Field(
        default=None, description="Global context words"
    )
    supported_entity: Optional[str] = Field(
        default=None, description="Supported entity for this recognizer"
    )
    supported_entities: Optional[List[str]] = Field(
        default=None, description="List of supported entities for this recognizer"
    )
    score_thresholds: Optional[Any] = Field(
        default=None,
        description="Default and entity-specific score thresholds",
    )

    @field_validator("supported_language")
    @classmethod
    def validate_single_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate single language code format."""
        validate_language_codes([v])
        return v

    @model_validator(mode="after")
    def validate_language_configuration(self):
        """Ensure proper language validation."""
        if self.supported_language and self.supported_languages:
            raise ValueError(
                "Cannot specify both 'supported_language' and 'supported_languages'"
            )

        return self

    @model_validator(mode="after")
    def validate_entity_configuration(self):
        """Ensure proper entity validation."""
        # Check if user provided both (before we modify them)
        user_provided_both = (
            self.supported_entity is not None and self.supported_entities is not None
        )

        if user_provided_both:
            raise ValueError(
                f"Recognizer {self.name} has both "
                "'supported_entity' and 'supported_entities' specified."
            )

        return self

    @model_validator(mode="after")
    def validate_context_configuration(self):
        """Validate context configuration according to language settings."""
        # Check if global context is defined
        if self.context:
            # Global context is only valid if we have exactly one language
            if self.supported_languages and len(self.supported_languages) > 1:
                raise ValueError(
                    "Global context can only be used with a single language. "
                    "For multiple languages, define context in "
                    "language-specific configurations."
                    "Example: "
                    "    supported_languages: "
                    "    - language: en "
                    "      context: [credit, card, visa, mastercard] "
                    "    - language: es "
                    "      context: [tarjeta, credito, visa, mastercard] "
                )
        return self


class TextChunkerConfig(BaseModel):
    """Validated configuration for text chunker instantiation.

    :param chunker_type: Type of chunker ("character" or "tokenizer").
    :param chunk_size: Character chunk size (character chunker).
    :param chunk_overlap: Character overlap (character chunker).
    :param tokenizer: Tokenizer name or instance (tokenizer chunker).
    :param max_tokens: Max tokens per chunk (tokenizer chunker).
    :param overlap_tokens: Token overlap (tokenizer chunker).
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    chunker_type: Literal["character", "tokenizer"] = Field(
        ..., description="Type of chunker"
    )
    chunk_size: Optional[int] = Field(None, description="Character chunk size")
    chunk_overlap: Optional[int] = Field(None, description="Character overlap")
    tokenizer: Optional[Any] = Field(None, description="Tokenizer name or instance")
    max_tokens: Optional[int] = Field(None, description="Max tokens per chunk")
    overlap_tokens: Optional[int] = Field(None, description="Token overlap")

    @model_validator(mode="after")
    def validate_params_match_chunker_type(self):
        """Reject params that don't belong to the selected chunker_type.

        Catches misconfigurations (e.g. ``max_tokens`` on a character chunker)
        at validation time with a clear message, instead of letting them fail
        later in TextChunkerProvider with a generic TypeError-wrapped error.
        """
        if self.chunker_type == "character":
            invalid = [
                name
                for name in ("tokenizer", "max_tokens", "overlap_tokens")
                if getattr(self, name) is not None
            ]
            if invalid:
                raise ValueError(
                    f"chunker_type='character' does not accept {invalid}; "
                    "only 'chunk_size' and 'chunk_overlap' are allowed."
                )
        else:  # tokenizer
            invalid = [
                name
                for name in ("chunk_size", "chunk_overlap")
                if getattr(self, name) is not None
            ]
            if invalid:
                raise ValueError(
                    f"chunker_type='tokenizer' does not accept {invalid}; "
                    "only 'tokenizer', 'max_tokens' and 'overlap_tokens' are allowed."
                )
        return self


class PredefinedRecognizerConfig(BaseRecognizerConfig):
    """Configuration for predefined recognizers."""

    type: str = Field(default="predefined", description="Type of recognizer")

    @model_validator(mode="after")
    def validate_predefined_recognizer_exists(self):
        """Validate that the predefined recognizer class actually exists."""
        recognizer_class_name = self.class_name if self.class_name else self.name
        try:
            RecognizerListLoader.get_existing_recognizer_cls(recognizer_class_name)
        except PredefinedRecognizerNotFoundError as e:
            raise ValueError(
                f"Predefined recognizer '{recognizer_class_name}' not found: {str(e)}"
            ) from e
        return self


class HuggingFaceRecognizerConfig(PredefinedRecognizerConfig):
    """Configuration specifically for HuggingFace NER models."""

    model_config = ConfigDict(extra="allow")

    model_name: Optional[str] = Field(None, description="HuggingFace model name")
    tokenizer_name: Optional[str] = Field(
        None, description="HuggingFace tokenizer name"
    )
    label_mapping: Optional[Dict[str, str]] = Field(None, description="Label mapping")
    threshold: Optional[float] = Field(None, description="Confidence threshold")
    aggregation_strategy: Optional[str] = Field(
        None, description="Aggregation strategy"
    )
    chunk_overlap: Optional[int] = Field(None, description="Chunk overlap")
    chunk_size: Optional[int] = Field(None, description="Chunk size")
    device: Optional[Union[str, int]] = Field(None, description="Device (cpu/gpu)")
    label_prefixes: Optional[List[str]] = Field(
        default=None, description="Prefixes to strip from labels (e.g. B-, I-)"
    )
    text_chunker: Optional[Union[TextChunkerConfig, Dict[str, Any]]] = Field(
        None, description="Text chunker configuration"
    )

    @field_validator("text_chunker", mode="before")
    @classmethod
    def validate_text_chunker(cls, v):
        """Validate text_chunker dict against TextChunkerConfig."""
        if isinstance(v, dict):
            return TextChunkerConfig(**v)
        return v

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Serialize the config without None values by default.

        HuggingFace recognizer kwargs are passed directly to the recognizer constructor.
        Excluding None values preserves constructor defaults for omitted YAML fields
        instead of overriding them with explicit None.
        """
        kwargs.setdefault("exclude_none", True)
        result = super().model_dump(*args, **kwargs)
        # Convert TextChunkerConfig back to plain dict for the loader
        if "text_chunker" in result and isinstance(
            self.text_chunker, TextChunkerConfig
        ):
            result["text_chunker"] = self.text_chunker.model_dump(exclude_none=True)
        return result


class GLiNERRecognizerConfig(PredefinedRecognizerConfig):
    """Configuration specifically for GLiNER models."""

    model_config = ConfigDict(extra="allow")

    model_name: Optional[str] = Field(None, description="GLiNER model name")
    flat_ner: Optional[bool] = Field(None, description="Use flat NER")
    multi_label: Optional[bool] = Field(
        None, description="Use multi-label classification"
    )
    threshold: Optional[float] = Field(None, description="Confidence threshold")
    map_location: Optional[str] = Field(None, description="Device (cpu/gpu/etc.)")
    load_onnx_model: Optional[bool] = Field(None, description="Load ONNX model")
    onnx_model_file: Optional[str] = Field(None, description="ONNX model file name")
    entity_mapping: Optional[Dict[str, str]] = Field(None, description="Entity mapping")
    text_chunker: Optional[Union[TextChunkerConfig, Dict[str, Any]]] = Field(
        None, description="Text chunker configuration"
    )

    @field_validator("text_chunker", mode="before")
    @classmethod
    def validate_text_chunker(cls, v):
        """Validate text_chunker dict against TextChunkerConfig."""
        if isinstance(v, dict):
            return TextChunkerConfig(**v)
        return v

    @model_validator(mode="after")
    def validate_entity_mapping_and_supported_entities(self):
        """Validate that entity_mapping and supported_entities are not both set."""
        if self.entity_mapping is not None and self.supported_entities is not None:
            raise ValueError(
                "GLiNER recognizer configuration cannot define both "
                "'entity_mapping' and 'supported_entities'; these fields are "
                "mutually exclusive."
            )
        return self

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Serialize the config without None values by default.

        GLiNER recognizer kwargs are passed directly to the recognizer constructor.
        Excluding None values preserves constructor defaults for omitted YAML fields
        instead of overriding them with explicit None.
        """
        kwargs.setdefault("exclude_none", True)
        result = super().model_dump(*args, **kwargs)
        if "text_chunker" in result and isinstance(
            self.text_chunker, TextChunkerConfig
        ):
            result["text_chunker"] = self.text_chunker.model_dump(exclude_none=True)
        return result


class LangExtractRecognizerConfig(PredefinedRecognizerConfig):
    """Configuration for language model (LangExtract) recognizers.

    Covers ``BasicLangExtractRecognizer`` and ``AzureOpenAILangExtractRecognizer``.
    ``extra="allow"`` lets recognizer-specific kwargs (most importantly
    ``config_path``, pointing at the langextract model YAML) survive validation
    and reach the recognizer constructor. Without this, the strict
    ``PredefinedRecognizerConfig`` schema drops ``config_path`` and the recognizer
    silently falls back to its bundled default model configuration.
    """

    model_config = ConfigDict(extra="allow")

    config_path: Optional[str] = Field(
        None, description="Path to the langextract model configuration YAML"
    )

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Serialize the config without None values by default.

        LangExtract recognizer kwargs are passed directly to the recognizer
        constructor. Excluding None values preserves constructor defaults for
        omitted YAML fields instead of overriding them with explicit None.
        """
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class CustomRecognizerConfig(BaseRecognizerConfig):
    """Configuration for custom pattern-based recognizers."""

    type: str = Field(default="custom", description="Type of recognizer")
    supported_entity: str = Field(
        ..., description="Entity type this recognizer detects"
    )
    country_code: Optional[str] = Field(
        default=None,
        description=("Optional ISO 3166-1 alpha-2 country tag for country filtering"),
    )
    patterns: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of patterns"
    )
    context: Optional[List[str]] = Field(
        default=None, description="Global context words"
    )
    deny_list: Optional[List[str]] = Field(
        default=None, description="Words to deny/exclude"
    )
    deny_list_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Deny list score"
    )

    # Language validation (legacy and new formats)
    supported_language: Optional[str] = Field(
        default=None, description="Single supported language (legacy)"
    )
    supported_languages: Optional[Union[List[str], List[LanguageContextConfig]]] = (
        Field(
            default=None,
            description="Multiple supported languages with optional context",
        )
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def check_predefined_name_conflict(cls, data: Any) -> Any:
        """Check if custom recognizer name conflicts with predefined recognizer.

        This validation runs BEFORE field validation to provide a clearer error message
        when someone tries to use a predefined recognizer name for a custom recognizer.
        """
        if isinstance(data, dict):
            name = data.get("name")
            if name:
                try:
                    RecognizerListLoader.get_existing_recognizer_cls(name)
                    # If we reach here, the recognizer IS predefined, so raise an error
                    raise ValueError(
                        f"Recognizer '{name}' conflicts with a predefined "
                        f"recognizer. "
                        f"Custom recognizers cannot use the same name "
                        f"as predefined recognizers. "
                        f"Either use type: 'predefined' or choose a different name "
                        f"for your custom recognizer."
                    )
                except PredefinedRecognizerNotFoundError:
                    pass
        return data

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: Optional[str]) -> Optional[str]:
        """Validate and normalize the optional custom recognizer country tag."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(
                "country_code must be a single non-empty string, "
                f"got {type(value).__name__}: {value!r}"
            )
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("country_code must be a non-empty string")
        return normalized

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, patterns: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Validate single language code format.

        :param patterns: List of patterns
        """
        if patterns and not isinstance(patterns, list):
            raise ValueError(f"Patterns should be a list: {patterns}")

        for pattern in patterns:
            if not isinstance(pattern, dict):
                raise ValueError(f"Pattern should be a dict: {pattern}")
            if "name" not in pattern:
                raise ValueError(f"Pattern should contain a name field: {pattern}")
            if "regex" not in pattern:
                raise ValueError(f"Pattern should contain a regex field: {pattern}")
            if "score" not in pattern:
                raise ValueError(f"Pattern should contain a score field: {pattern}")
            if not isinstance(pattern["score"], (int, float)):
                raise ValueError(f"Pattern score should be a float: {pattern}")
            if not (0.0 <= pattern["score"] <= 1.0):
                raise ValueError(f"Pattern score should be between 0 and 1: {pattern}")
        return patterns

    @model_validator(mode="after")
    def validate_patterns_or_deny_list(self):
        """Ensure custom recognizer has at least patterns or deny_list."""
        if not self.patterns and not self.deny_list:
            raise ValueError(
                "Custom recognizer must have at least one of 'patterns' or 'deny_list'"
            )
        return self


class RecognizerRegistryConfig(BaseModel):
    """Complete validation for the recognizer registry."""

    supported_languages: Optional[List[str]] = Field(
        default=None, description="List of supported languages"
    )
    global_regex_flags: int = Field(default=26, description="Global regex flags")
    recognizers: List[
        Union[
            HuggingFaceRecognizerConfig,
            GLiNERRecognizerConfig,
            PredefinedRecognizerConfig,
            CustomRecognizerConfig,
            str,
        ]
    ] = Field(default_factory=list, description="List of recognizer configurations")

    model_config = ConfigDict(extra="forbid")

    @field_validator("supported_languages")
    @classmethod
    def validate_language_codes(
        cls, languages: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Validate language codes format."""

        # Allow None or empty list for cases where languages will be inferred
        if languages is None:
            return None

        if len(languages) == 0:
            return []

        validate_language_codes(languages)
        return languages

    @model_validator(mode="after")
    def validate_languages_for_custom_recognizers(self):
        """Validate that custom recognizers have language configuration."""
        # If we have custom recognizers, we need language configuration somewhere
        custom_recognizers = [
            rec for rec in self.recognizers if isinstance(rec, CustomRecognizerConfig)
        ]
        for recognizer in custom_recognizers:
            if not recognizer.supported_language and not recognizer.supported_languages:
                # If no language config on recognizer, we need global languages
                if not self.supported_languages:
                    raise ValueError(
                        f"Language configuration missing for custom recognizer "
                        f"'{recognizer.name}': "
                        "Either specify 'supported_languages' "
                        "on the recognizer or provide "
                        "global 'supported_languages' in the "
                        "registry configuration."
                    )

        return self

    @model_validator(mode="after")
    def validate_recognizers_not_empty(self):
        """Ensure recognizers list is not empty after all defaults are applied."""
        if not self.recognizers:
            raise ValueError(
                "The 'recognizers' field must contain at least one recognizer. "
                "Found an empty recognizers list."
            )
        return self

    @field_validator("recognizers", mode="before")
    @classmethod
    def parse_recognizers(
        cls, recognizers: List[Union[Dict[str, Any], str]]
    ) -> List[BaseRecognizerConfig]:
        """Parse recognizers from various input formats without duplication."""
        if recognizers is None:
            raise ValueError(
                "Configuration error: 'recognizers' is required. "
                "Please provide a list of recognizers in the configuration."
            )

        if not isinstance(recognizers, list):
            raise ValueError("Recognizers must be a list")

        if len(recognizers) == 0:
            raise ValueError(
                "The 'recognizers' field must contain at least one recognizer. "
                "Found an empty recognizers list."
            )

        parsed_recognizers = []
        for recognizer in recognizers:
            if isinstance(recognizer, str):
                parsed_recognizers.append(recognizer)
                continue

            if isinstance(recognizer, dict):
                recognizer = recognizer.copy()
                recognizer_type = recognizer.get("type")

                # Validate conflicting custom-only fields if explicitly predefined
                if recognizer_type == "predefined" and (
                    "patterns" in recognizer or "deny_list" in recognizer
                ):
                    raise ValueError(
                        f"Recognizer '{recognizer.get('name')}' is marked "
                        f"as 'predefined' but contains 'patterns' or 'deny_list' "
                        f"which are only valid for custom recognizers. "
                        f"Either use type: 'custom' or remove these fields."
                    )

                if not recognizer_type:
                    if "patterns" in recognizer or "deny_list" in recognizer:
                        recognizer_type = "custom"
                        recognizer_name = recognizer.get("name")
                        if recognizer_name:
                            cls.__check_if_predefined(recognizer_name)
                    else:
                        recognizer_type = "predefined"
                    recognizer["type"] = recognizer_type

                if recognizer_type == "predefined":
                    # Determine config model based on recognizer class_name or name.
                    recognizer_class_name = recognizer.get("class_name")
                    recognizer_name = recognizer.get("name")
                    # Prioritize class_name for lookup
                    # (e.g., custom instance of HuggingFaceNerRecognizer)
                    config_model_key = recognizer_class_name or recognizer_name

                    config_model = CONFIG_MODEL_MAP.get(
                        config_model_key, PredefinedRecognizerConfig
                    )

                    parsed_recognizers.append(config_model(**recognizer))
                elif recognizer_type == "custom":
                    parsed_recognizers.append(CustomRecognizerConfig(**recognizer))
                else:
                    raise ValueError(
                        f"Invalid recognizer type: {recognizer_type}. "
                        f"Must be 'predefined' or 'custom'."
                    )
                continue

            parsed_recognizers.append(recognizer)

        return parsed_recognizers

    @classmethod
    def __check_if_predefined(cls, recognizer_name: Optional[Any]) -> None:
        try:
            RecognizerListLoader.get_existing_recognizer_cls(recognizer_name)
            raise ValueError(
                f"Recognizer '{recognizer_name}' conflicts with a predefined "
                f"recognizer. "
                f"Custom recognizers cannot use the same name "
                f"as predefined recognizers. "
                f"Either use type: 'predefined' or choose a different name "
                f"for your custom recognizer."
            )
        except PredefinedRecognizerNotFoundError:
            pass

    @model_validator(mode="after")
    def validate_language_presence(self):
        """Ensure custom recognizers define languages if no global languages are set."""
        if self.recognizers and (
            not self.supported_languages or len(self.supported_languages) == 0
        ):
            any_language_defined = False
            custom_without_language_present = False
            for r in self.recognizers:
                if isinstance(r, (PredefinedRecognizerConfig, CustomRecognizerConfig)):
                    if (r.supported_language and r.supported_language.strip()) or (
                        r.supported_languages and len(r.supported_languages) > 0
                    ):
                        any_language_defined = True
                    if (
                        isinstance(r, CustomRecognizerConfig)
                        and not r.supported_language
                        and not r.supported_languages
                    ):
                        custom_without_language_present = True

            if custom_without_language_present and not any_language_defined:
                raise ValueError(
                    "Language configuration missing for custom recognizer(s): "
                    "provide 'supported_languages' at registry level "
                    "or specify languages for each custom recognizer."
                )
        return self


# Map specific recognizer classes to their dedicated config models
# This allows for modular expansion without polluting the base config
CONFIG_MODEL_MAP: Dict[str, Type[BaseModel]] = {
    "HuggingFaceNerRecognizer": HuggingFaceRecognizerConfig,
    "GLiNERRecognizer": GLiNERRecognizerConfig,
    "BasicLangExtractRecognizer": LangExtractRecognizerConfig,
    "AzureOpenAILangExtractRecognizer": LangExtractRecognizerConfig,
}
