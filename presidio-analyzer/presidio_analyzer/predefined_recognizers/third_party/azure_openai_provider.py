"""Azure OpenAI Provider for LangExtract."""

import logging
import os
from typing import Optional

try:
    import langextract as lx
    import openai
    from langextract.providers.openai import OpenAILanguageModel

    LANGEXTRACT_OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    LANGEXTRACT_OPENAI_AVAILABLE = False
    lx = None
    OpenAILanguageModel = None
    openai = None

try:
    from presidio_analyzer.llm_utils.azure_auth_helper import (
        get_azure_credential,
        get_bearer_token_provider_for_scope,
    )

    AZURE_IDENTITY_AVAILABLE = True
except ImportError:  # pragma: no cover
    AZURE_IDENTITY_AVAILABLE = False
    get_azure_credential = None
    get_bearer_token_provider_for_scope = None

logger = logging.getLogger("presidio-analyzer")


if LANGEXTRACT_OPENAI_AVAILABLE:

    class AzureOpenAILanguageModel(OpenAILanguageModel):
        """
        Custom LangExtract provider for Azure OpenAI.

        This provider extends OpenAILanguageModel to support Azure-specific
        authentication and endpoint configuration. It reuses all inference logic
        from the parent class and only overrides client initialization.

        Registered to handle model_id with "azure:" prefix (e.g., "azure:gpt-4o").
        The recognizer adds this prefix automatically.
        """

        def __init__(
            self,
            model_id: str,
            api_key: Optional[str] = None,
            azure_endpoint: Optional[str] = None,
            api_version: Optional[str] = None,
            azure_deployment: Optional[str] = None,
            azure_ad_token_provider: Optional[any] = None,
            **kwargs,
        ):
            """
            Initialize Azure OpenAI provider.

            :param model_id: Azure OpenAI deployment name or model identifier.
            :param api_key: Azure OpenAI API key (or set AZURE_OPENAI_API_KEY
                env var). If not provided, will automatically use managed
                identity (ChainedTokenCredential).
            :param azure_endpoint: Azure OpenAI endpoint URL
                (or set AZURE_OPENAI_ENDPOINT env var).
            :param api_version: Azure OpenAI API version
                (or set AZURE_OPENAI_API_VERSION env var).
            :param azure_deployment: Explicit deployment name (optional,
                defaults to model_id).
            :param azure_ad_token_provider: Custom Azure AD token provider function.
            :param kwargs: Additional parameters passed to parent class.
            """
            # Strip 'azure:' prefix if present (added by recognizer)
            if model_id.lower().startswith("azure:"):
                clean_model_id = model_id[6:]  # len("azure:") = 6
            else:
                clean_model_id = model_id

            self.model_id = clean_model_id
            self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
            self.organization = None
            self.format_type = kwargs.get("format_type", lx.data.FormatType.JSON)
            self.temperature = kwargs.get("temperature", 0.0)
            self.max_workers = kwargs.get("max_workers", 10)
            self._extra_kwargs = kwargs

            # Azure-specific configuration
            self.azure_endpoint = azure_endpoint or os.environ.get(
                "AZURE_OPENAI_ENDPOINT"
            )
            self.api_version = api_version or os.environ.get(
                "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
            )
            self.azure_deployment = azure_deployment or clean_model_id

            # Validate and initialize Azure OpenAI client
            self._client = self._create_azure_openai_client(azure_ad_token_provider)

        def _create_azure_openai_client(
            self, azure_ad_token_provider: Optional[any] = None
        ):
            """
            Create and configure Azure OpenAI client with appropriate authentication.

            :param azure_ad_token_provider: Optional custom token provider
            :return: Configured AzureOpenAI client instance
            :raises ValueError: If azure_endpoint is not provided
            :raises ImportError: If azure-identity is needed but not available
            """
            if not self.azure_endpoint:
                raise ValueError(
                    "Azure OpenAI endpoint is required. Set AZURE_OPENAI_ENDPOINT "
                    "environment variable or pass azure_endpoint parameter."
                )

            if not self.api_key or azure_ad_token_provider:
                if not AZURE_IDENTITY_AVAILABLE and not azure_ad_token_provider:
                    raise ImportError(
                        "azure-identity is required for managed identity "
                        "authentication. Install it with: pip install azure-identity"
                    )

                if azure_ad_token_provider:
                    token_provider = azure_ad_token_provider
                    credential_type = "custom token provider"
                else:
                    token_provider = get_bearer_token_provider_for_scope(
                        "https://cognitiveservices.azure.com/.default"
                    )
                    credential_type = (
                        "DefaultAzureCredential (development)"
                        if os.getenv("ENV") == "development"
                        else "ChainedTokenCredential"
                    )

                client = openai.AzureOpenAI(
                    azure_ad_token_provider=token_provider,
                    azure_endpoint=self.azure_endpoint,
                    api_version=self.api_version,
                )

                logger.debug(
                    f"Initialized Azure OpenAI provider with {credential_type}"
                )
                return client
            else:
                client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.azure_endpoint,
                    api_version=self.api_version,
                )

                logger.debug(
                    "Initialized Azure OpenAI provider with API key authentication"
                )
                return client

        def _get_client_model_id(self) -> str:
            """
            Return the model/deployment identifier for API calls.

            For Azure OpenAI, this is the deployment name, not the base model name.

            :return: Azure deployment name.
            """
            return self.azure_deployment
else:  # pragma: no cover

    class AzureOpenAILanguageModel:
        """Placeholder when langextract is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "LangExtract with OpenAI support is not installed. "
                "Install it with: pip install presidio-analyzer[langextract,openai] "
                "or: pip install langextract[openai]"
            )


# Register the provider with LangExtract
if LANGEXTRACT_OPENAI_AVAILABLE:
    try:

        @lx.providers.registry.register(r"^azure:", priority=20)
        class RegisteredAzureOpenAILanguageModel(AzureOpenAILanguageModel):
            """
            Registered version of Azure OpenAI provider for LangExtract.

            This class is automatically discovered by LangExtract's provider registry
            and used when model_id matches any of the registered patterns.
            """

            pass

        logger.debug("Azure OpenAI provider registered with LangExtract")
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed to register Azure OpenAI provider: {e}")
        raise
