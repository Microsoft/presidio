"""Azure authentication utilities for Presidio components."""

import logging
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential

try:
    from azure.identity import (
        ChainedTokenCredential,
        DefaultAzureCredential,
        EnvironmentCredential,
        ManagedIdentityCredential,
        WorkloadIdentityCredential,
    )

    AZURE_IDENTITY_AVAILABLE = True
except ImportError:  # pragma: no cover
    AZURE_IDENTITY_AVAILABLE = False
    ChainedTokenCredential = None
    DefaultAzureCredential = None
    EnvironmentCredential = None
    ManagedIdentityCredential = None
    WorkloadIdentityCredential = None

logger = logging.getLogger("presidio-analyzer")


def get_azure_credential() -> "TokenCredential":
    """
    Get an Azure credential with environment-aware fallback strategy.

    In development (ENV=development), uses DefaultAzureCredential which tries
    multiple authentication methods including Azure CLI, environment variables,
    and managed identity.

    In production (ENV!=development), uses a more restrictive ChainedTokenCredential
    that only tries:
    1. EnvironmentCredential (service principal via env vars)
    2. WorkloadIdentityCredential (Kubernetes workload identity)
    3. ManagedIdentityCredential (Azure managed identity)

    This production approach avoids interactive authentication methods and
    follows security best practices for production deployments.

    :return: Configured Azure credential instance.
    :raises ImportError: If azure-identity is not installed.
    """
    if not AZURE_IDENTITY_AVAILABLE:
        raise ImportError(
            "azure-identity is required for Azure authentication. "
            "Install it with: pip install azure-identity"
        )

    if os.getenv("ENV") == "development":
        credential = DefaultAzureCredential()  # CodeQL [SM05139] OK for dev
        logger.debug("Using DefaultAzureCredential (development mode)")
        return credential
    else:
        credential = ChainedTokenCredential(
            EnvironmentCredential(),
            WorkloadIdentityCredential(),
            ManagedIdentityCredential(),
        )
        logger.debug("Using ChainedTokenCredential (production mode)")
        return credential


def get_bearer_token_provider_for_scope(
    scope: str, credential: Optional["TokenCredential"] = None
):
    """
    Get a bearer token provider function for a specific Azure scope.

    This is commonly used with Azure OpenAI and other Azure Cognitive Services
    that require token-based authentication.

    :param scope: Azure scope for the token (e.g.,
        "https://cognitiveservices.azure.com/.default").
    :param credential: Optional Azure credential. If not provided, uses
        get_azure_credential().
    :return: Token provider function compatible with Azure SDK clients.
    :raises ImportError: If azure-identity is not installed.
    """
    if not AZURE_IDENTITY_AVAILABLE:
        raise ImportError(
            "azure-identity is required for token provider. "
            "Install it with: pip install azure-identity"
        )

    from azure.identity import get_bearer_token_provider

    if credential is None:
        credential = get_azure_credential()

    return get_bearer_token_provider(credential, scope)
