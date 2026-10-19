import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from presidio_analyzer.llm_utils import lx_factory
from presidio_analyzer.predefined_recognizers.third_party.langextract_recognizer import (  # noqa: E501  # noqa: E501
    LangExtractRecognizer,
)

logger = logging.getLogger("presidio-analyzer")

DEFAULT_EXTRACT_PARAMS = {
    "max_char_buffer": 400,
    "use_schema_constraints": False,
    "fence_output": False,
}

DEFAULT_LANGUAGE_MODEL_PARAMS = {"timeout": 240, "num_ctx": 8192}


class BasicLangExtractRecognizer(LangExtractRecognizer):
    """Basic LangExtract recognizer using configurable backend."""

    DEFAULT_CONFIG_PATH = (
        Path(__file__).parent.parent.parent / "conf" / "langextract_config_basic.yaml"
    )

    def __init__(
        self,
        config_path: Optional[str] = None,
        supported_language: str = "en",
        context: Optional[list] = None,
        name="BasicLangExtractRecognizer",
        **kwargs,
    ):
        """Initialize Basic LangExtract recognizer.

        :param config_path: Path to configuration file (optional).
        :param supported_language: Language this recognizer supports
            (optional, default: "en").
        :param context: List of context words
            (optional, currently not used by LLM recognizers).
        """
        actual_config_path = (
            config_path if config_path else str(self.DEFAULT_CONFIG_PATH)
        )

        super().__init__(
            config_path=actual_config_path,
            name=name,
            supported_language=supported_language,
            extract_params={
                "extract": DEFAULT_EXTRACT_PARAMS,
                "language_model": DEFAULT_LANGUAGE_MODEL_PARAMS,
            },
        )

        model_config: Dict[str, Any] = self.config.get("model", {})
        provider_config = model_config.get("provider", {})

        self.model_id = model_config.get("model_id")
        self.provider = provider_config.get("name")
        self.provider_kwargs = dict(provider_config.get("kwargs") or {})

        # Not ideal, but update _extract_params now that self.config is fully loaded.
        self._extract_params.update(provider_config.get("extract_params") or {})
        self._language_model_params.update(
            provider_config.get("language_model_params") or {}
        )

        # Surface language_model_params on the ModelConfig itself.
        # langextract.extract() honours `language_model_params` only when
        # `config` is NOT passed (see langextract/extraction.py elif config:
        # branch). Because _get_provider_params() returns a pre-built
        # ModelConfig, values like `timeout` and `num_ctx` would otherwise be
        # silently dropped. Merge them into provider_kwargs so they reach
        # the provider constructor (e.g. OllamaLanguageModel(timeout=...)).
        # `setdefault` ensures explicit `provider.kwargs:` entries always win.
        for key, value in self._language_model_params.items():
            self.provider_kwargs.setdefault(key, value)

        if not self.provider:
            raise ValueError(
                "Configuration must contain 'langextract.model.provider.name'"
            )

        if (
            "api_key" not in self.provider_kwargs
            and "LANGEXTRACT_API_KEY" in os.environ
        ):
            self.provider_kwargs["api_key"] = os.environ["LANGEXTRACT_API_KEY"]

        self.lx_model_config = lx_factory.ModelConfig(
            model_id=self.model_id,
            provider=self.provider,
            provider_kwargs=self.provider_kwargs,
        )

    def _get_provider_params(self):
        """Return supplementary params."""
        return {
            "config": self.lx_model_config,
        }
