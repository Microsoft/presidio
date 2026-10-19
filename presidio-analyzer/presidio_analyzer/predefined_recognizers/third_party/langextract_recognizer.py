import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from presidio_analyzer.llm_utils import (
    check_langextract_available,
    convert_langextract_to_presidio_results,
    convert_to_langextract_format,
    extract_lm_config,
    get_model_config,
    get_supported_entities,
    load_prompt_file,
    load_yaml_examples,
    load_yaml_file,
    lx,
    render_jinja_template,
    validate_config_fields,
)
from presidio_analyzer.lm_recognizer import LMRecognizer

logger = logging.getLogger("presidio-analyzer")


class LangExtractRecognizer(LMRecognizer, ABC):
    """
    Base class for LangExtract-based PII recognizers.

    Subclasses implement _call_langextract() for specific LLM providers.
    """

    def __init__(
        self,
        config_path: str,
        name: str = "LangExtract LLM PII",
        supported_language: str = "en",
        extract_params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize LangExtract recognizer.

        :param config_path: Path to configuration file.
        :param name: Name of the recognizer (provided by subclass).
        :param supported_language: Language this recognizer supports (default: "en").
        :param extract_params: Dict with 'extract' and/or 'language_model'
            keys containing param defaults.
        """
        check_langextract_available()

        full_config = load_yaml_file(config_path)

        lm_config = extract_lm_config(full_config)
        langextract_config = full_config.get("langextract", {})

        supported_entities = get_supported_entities(lm_config, langextract_config)

        if not supported_entities:
            raise ValueError(
                "Configuration must contain 'supported_entities' in "
                "'lm_recognizer' or 'langextract'"
            )

        validate_config_fields(
            full_config,
            [
                ("langextract",),
                ("langextract", "model"),
                ("langextract", "model", "model_id"),
                ("langextract", "entity_mappings"),
                ("langextract", "prompt_file"),
                ("langextract", "examples_file"),
            ],
        )

        self.config = langextract_config
        model_config = get_model_config(full_config, provider_key="langextract")

        super().__init__(
            supported_entities=supported_entities,
            supported_language=supported_language,
            name=name,
            version="1.0.0",
            model_id=model_config["model_id"],
            temperature=model_config.get("temperature"),
            min_score=lm_config.get("min_score"),
            labels_to_ignore=lm_config.get("labels_to_ignore"),
            enable_generic_consolidation=lm_config.get("enable_generic_consolidation"),
        )

        examples_data = load_yaml_examples(langextract_config["examples_file"])
        self.examples = convert_to_langextract_format(examples_data)

        prompt_template = load_prompt_file(langextract_config["prompt_file"])
        self.prompt_description = render_jinja_template(
            prompt_template,
            supported_entities=self.supported_entities,
            enable_generic_consolidation=self.enable_generic_consolidation,
            labels_to_ignore=self.labels_to_ignore,
        )

        self.entity_mappings = langextract_config["entity_mappings"]
        self.debug = langextract_config.get("debug", False)
        self._model_config = model_config

        # Process extract params with config override
        self._extract_params = {}
        self._language_model_params = {}

        if extract_params:
            if "extract" in extract_params:
                for param_name, default_value in extract_params["extract"].items():
                    self._extract_params[param_name] = self._model_config.get(
                        param_name, default_value
                    )

            if "language_model" in extract_params:
                for param_name, default_value in extract_params[
                    "language_model"
                ].items():
                    self._language_model_params[param_name] = self._model_config.get(
                        param_name, default_value
                    )

    def _call_llm(self, text: str, entities: List[str], **kwargs):
        """Call LangExtract LLM."""
        # Build extract params
        extract_params = {
            "text": text,
            "prompt": self.prompt_description,
            "examples": self.examples,
            "debug": self.debug,
        }

        # Add temperature if configured
        if self.temperature is not None:
            extract_params["temperature"] = self.temperature

        # Add any additional kwargs
        extract_params.update(kwargs)

        langextract_result = self._call_langextract(**extract_params)

        return convert_langextract_to_presidio_results(
            langextract_result=langextract_result,
            entity_mappings=self.entity_mappings,
            supported_entities=self.supported_entities,
            enable_generic_consolidation=self.enable_generic_consolidation,
            recognizer_name=self.__class__.__name__,
        )

    def _call_langextract(self, **kwargs):
        """Call LangExtract with configured parameters."""
        try:
            extract_params = {
                "text_or_documents": kwargs.pop("text"),
                "prompt_description": kwargs.pop("prompt"),
                "examples": kwargs.pop("examples"),
            }

            extract_params.update(self._get_provider_params())
            extract_params.update(self._extract_params)
            if self._language_model_params:
                extract_params["language_model_params"] = self._language_model_params
            extract_params.update(kwargs)

            return lx.extract(**extract_params)
        except Exception:
            logger.exception(
                "LangExtract extraction failed (model '%s')", self.model_id
            )
            raise

    @abstractmethod
    def _get_provider_params(self) -> Dict[str, Any]:
        """Return provider-specific params.

        Examples: model_id, model_url, azure_endpoint, etc.
        """
        ...
