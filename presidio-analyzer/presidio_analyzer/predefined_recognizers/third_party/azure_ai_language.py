import logging
import os
from typing import List, Optional

try:
    from azure.ai.textanalytics import TextAnalyticsClient
    from azure.core.credentials import AzureKeyCredential

except ImportError:
    TextAnalyticsClient = None
    AzureKeyCredential = None
from presidio_analyzer import AnalysisExplanation, RecognizerResult, RemoteRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")


class AzureAILanguageRecognizer(RemoteRecognizer):
    """Wrapper for PII detection using Azure AI Language."""

    def __init__(
        self,
        supported_entities: Optional[List[str]] = None,
        supported_language: str = "en",
        ta_client: Optional["TextAnalyticsClient"] = None,
        azure_ai_key: Optional[str] = None,
        azure_ai_endpoint: Optional[str] = None,
        name: Optional[str] = None,
        context: Optional[List[str]] = None,
    ):
        """
        Wrap the PII detection in Azure AI Language.

        :param supported_entities: List of supported entities for this recognizer.
        If None, all supported entities will be used.
        :param supported_language: Language code to use for the recognizer.
        :param ta_client: object of type TextAnalyticsClient. If missing,
        the client will be created using the key and endpoint.
        :param azure_ai_key: Azure AI for language key
        :param azure_ai_endpoint: Azure AI for language endpoint
        :param name: Name of the recognizer. Defaults to "Azure AI Language PII".
        :param context: List of context words to boost confidence score.

        For more info, see https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/overview
        """

        # `name` and `context` are appended last so existing positional callers
        # are unaffected. They exist because RecognizerListLoader passes both
        # when building a recognizer from a registry configuration, and
        # RemoteRecognizer.__init__ accepts neither **kwargs nor unknown keys.
        # Without them, any YAML entry naming this class raises TypeError before
        # the registry finishes loading (#1457, and again after #1800).
        super().__init__(
            supported_entities=supported_entities,
            supported_language=supported_language,
            name=name if name else "Azure AI Language PII",
            version="5.2.0",
            context=context,
        )

        is_available = bool(TextAnalyticsClient)
        if not ta_client and not is_available:
            raise ValueError(
                "Azure AI Language is not available. "
                "Please install the required dependencies:"
                "1. azure-ai-textanalytics"
                "2. azure-core"
            )

        if not supported_entities:
            self.supported_entities = self.__get_azure_ai_supported_entities()

        if not ta_client:
            ta_client = self.__authenticate_client(azure_ai_key, azure_ai_endpoint)
        self.ta_client = ta_client

    def get_supported_entities(self) -> List[str]:
        """
        Return the list of entities this recognizer can identify.

        :return: A list of the supported entities by this recognizer
        """
        return self.supported_entities

    @staticmethod
    def __get_azure_ai_supported_entities() -> List[str]:
        """Return the list of all supported entities for Azure AI Language."""
        from azure.ai.textanalytics._models import PiiEntityCategory

        return [r.value.upper() for r in PiiEntityCategory]

    @staticmethod
    def __authenticate_client(key: str, endpoint: str) -> TextAnalyticsClient:
        """Authenticate the client using the key and endpoint.

        :param key: Azure AI Language key
        :param endpoint: Azure AI Language endpoint
        """
        key = key if key else os.getenv("AZURE_AI_KEY", None)
        endpoint = endpoint if endpoint else os.getenv("AZURE_AI_ENDPOINT", None)
        if key is None:
            raise ValueError(
                "Azure AI Language key is required. "
                "Please provide a key or set the AZURE_AI_KEY environment variable."
            )
        if endpoint is None:
            raise ValueError(
                "Azure AI Language endpoint is required. "
                "Please provide an endpoint "
                "or set the AZURE_AI_ENDPOINT environment variable."
            )

        ta_credential = AzureKeyCredential(key)
        text_analytics_client = TextAnalyticsClient(
            endpoint=endpoint, credential=ta_credential
        )
        return text_analytics_client

    def analyze(
        self, text: str, entities: List[str] = None, nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """
        Analyze text using Azure AI Language.

        :param text: Text to analyze
        :param entities: List of entities to return
        :param nlp_artifacts: Object of type NlpArtifacts, not used in this recognizer.
        :return: A list of RecognizerResult, one per each entity found in the text.
        """
        if not entities:
            entities = self.supported_entities
        response = self.ta_client.recognize_pii_entities(
            [text], language=self.supported_language
        )
        results = [doc for doc in response if not doc.is_error]
        recognizer_results = []
        for res in results:
            for entity in res.entities:
                entity.category = entity.category.upper()
                if entity.category.lower() not in [
                    ent.lower() for ent in self.supported_entities
                ]:
                    continue
                if entity.category.lower() not in [ent.lower() for ent in entities]:
                    continue
                analysis_explanation = AzureAILanguageRecognizer._build_explanation(
                    original_score=entity.confidence_score,
                    entity_type=entity.category,
                )
                recognizer_results.append(
                    RecognizerResult(
                        entity_type=entity.category,
                        start=entity.offset,
                        end=entity.offset + entity.length,
                        score=entity.confidence_score,
                        analysis_explanation=analysis_explanation,
                    )
                )

        return recognizer_results

    @staticmethod
    def _build_explanation(
        original_score: float, entity_type: str
    ) -> AnalysisExplanation:
        explanation = AnalysisExplanation(
            recognizer=AzureAILanguageRecognizer.__class__.__name__,
            original_score=original_score,
            textual_explanation=f"Identified as {entity_type} by Azure AI Language",
        )
        return explanation
