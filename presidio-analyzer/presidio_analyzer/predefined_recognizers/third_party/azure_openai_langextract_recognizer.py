"""Azure OpenAI LangExtract Recognizer for PII/PHI detection."""

import logging
import os
from pathlib import Path
from typing import Optional

try:
    import langextract as lx

    LANGEXTRACT_AVAILABLE = True
except ImportError:  # pragma: no cover
    LANGEXTRACT_AVAILABLE = False
    lx = None

from presidio_analyzer.predefined_recognizers.third_party import (
    langextract_recognizer,
)

# Import provider module to trigger registration with LangExtract
# This must happen at module import time for the @register decorator to execute
try:
    from presidio_analyzer.predefined_recognizers.third_party import (
        azure_openai_provider,  # noqa: F401 - imported for side effects (registration)
    )
except ImportError:  # pragma: no cover
    pass

logger = logging.getLogger("presidio-analyzer")

LangExtractRecognizer = langextract_recognizer.LangExtractRecognizer

AZURE_OPENAI_DOCS_URL = "https://learn.microsoft.com/en-us/azure/ai-services/openai/"


class AzureOpenAILangExtractRecognizer(LangExtractRecognizer):
    """
    Concrete implementation of LangExtract recognizer using Azure OpenAI backend.

    Provides Azure OpenAI-specific functionality including:
    - Azure OpenAI endpoint and API key configuration
    - Deployment name management
    - API version control
    - Integration with custom Azure OpenAI provider via LangExtract registry
    """

    DEFAULT_API_VERSION = "2024-02-15-preview"

    DEFAULT_CONFIG_PATH = (
        Path(__file__).parent.parent.parent
        / "conf"
        / "langextract_config_azureopenai.yaml"
    )

    def __init__(
        self,
        model_id: Optional[str] = None,
        config_path: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        supported_language: str = "en",
        name: str = "Azure OpenAI LangExtract PII",
    ):
        """
        Initialize Azure OpenAI LangExtract recognizer for PII/PHI detection.

        Note: Azure OpenAI endpoint and API configuration are not validated
        during initialization. Any connectivity or authentication issues will
        be reported when analyze() is first called.

        Configuration priority for authentication (highest to lowest):
        1. Direct parameters (azure_endpoint, api_key, api_version)
        2. Environment variables (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
           AZURE_OPENAI_API_VERSION)

        Configuration priority for model_id (deployment name):
        1. Direct parameter (model_id)
        2. Config file (langextract.model.model_id)

        :param model_id: Azure OpenAI deployment name (e.g., "gpt-4",
            "gpt-4o"). Overrides config file.
        :param config_path: Path to YAML configuration file. If not provided,
            uses default config.
        :param azure_endpoint: Azure OpenAI endpoint URL (overrides env var).
        :param api_key: Azure OpenAI API key (overrides env var). If not
            provided, uses managed identity.
        :param api_version: Azure OpenAI API version (optional, defaults to
            "2024-02-15-preview").
        :param supported_language: Language this recognizer supports
            (optional, default: "en").
        :raises ImportError: If langextract is not installed.
        :raises ValueError: If Azure OpenAI endpoint is not provided via
            parameter or env var.
        """

        # Determine actual config path
        actual_config_path = (
            config_path if config_path else str(self.DEFAULT_CONFIG_PATH)
        )

        # Get Azure-specific settings with priority: parameter > env var
        self.azure_endpoint = azure_endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        self._validate_azure_endpoint(self.azure_endpoint)

        self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        self.api_version = (
            api_version
            or os.environ.get("AZURE_OPENAI_API_VERSION")
            or self.DEFAULT_API_VERSION
        )

        # Initialize parent class (loads config, sets self.model_id from config)
        super().__init__(
            config_path=actual_config_path,
            name=name,
            supported_language=supported_language,
            extract_params={
                "extract": {
                    "fence_output": True,
                    "use_schema_constraints": False,
                },
            },
        )

        # Override model_id if provided as parameter (deployment name)
        if model_id:
            self.model_id = model_id

    def _validate_azure_endpoint(self, azure_endpoint: Optional[str]) -> None:
        """
        Validate that Azure OpenAI endpoint is provided.

        :param azure_endpoint: Azure OpenAI endpoint URL.
        :raises ValueError: If endpoint is not provided.
        """
        if not azure_endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is required. Provide 'azure_endpoint' parameter "
                f"or set AZURE_OPENAI_ENDPOINT environment variable.\n"
                f"See {AZURE_OPENAI_DOCS_URL} for details."
            )

    def _get_provider_params(self):
        """Return Azure OpenAI-specific params."""
        model_id_with_prefix = f"azure:{self.model_id}"

        language_model_params = {
            "azure_endpoint": self.azure_endpoint,
            "api_version": self.api_version,
            "azure_deployment": self.model_id,
        }

        if self.api_key:
            language_model_params["api_key"] = self.api_key

        return {
            "model_id": model_id_with_prefix,
            "language_model_params": language_model_params,
        }
