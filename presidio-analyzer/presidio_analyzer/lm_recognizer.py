import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from presidio_analyzer import RecognizerResult, RemoteRecognizer
from presidio_analyzer.llm_utils import (
    consolidate_generic_entities,
    ensure_generic_entity_support,
    filter_results_by_entities,
    filter_results_by_labels,
    filter_results_by_score,
    skip_unmapped_entities,
    validate_result_positions,
)

if TYPE_CHECKING:
    from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")


class LMRecognizer(RemoteRecognizer, ABC):
    """
    Base class for language model-based PII recognizers.

    Provides common functionality for LLM-based entity detection.
    Subclasses implement _call_llm() for specific LLM providers.
    """

    def __init__(
        self,
        supported_entities: Optional[List[str]] = None,
        supported_language: str = "en",
        name: Optional[str] = None,
        version: str = "1.0.0",
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        min_score: float = 0.5,
        labels_to_ignore: Optional[List[str]] = None,
        enable_generic_consolidation: bool = True,
    ):
        """Initialize LM recognizer.

        :param supported_entities: Entity types to detect.
        :param labels_to_ignore: Entity labels to skip.
        :param enable_generic_consolidation: Consolidate unknown
            entities to GENERIC_PII_ENTITY.
        """
        if not supported_entities:
            raise ValueError(
                "LMRecognizer requires at least one entity in 'supported_entities'"
            )

        super().__init__(
            supported_entities=supported_entities,
            supported_language=supported_language,
            name=name,
            version=version,
        )

        self.model_id = model_id
        self.temperature = temperature
        self.min_score = min_score
        self.labels_to_ignore = [label.lower() for label in (labels_to_ignore or [])]
        self.enable_generic_consolidation = enable_generic_consolidation

        self._generic_entities_logged = set()

        self.supported_entities = ensure_generic_entity_support(
            self.supported_entities, enable_generic_consolidation
        )

    @abstractmethod
    def _call_llm(
        self, text: str, entities: List[str], **kwargs
    ) -> List[RecognizerResult]:
        """
        Call LLM service and return RecognizerResult objects.

        Subclasses implement this to integrate with specific LLM providers.

        :param text: Text to analyze for PII.
        :param entities: Entity types to detect.
        :return: List of RecognizerResult objects.
        """
        ...

    def analyze(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        nlp_artifacts: Optional["NlpArtifacts"] = None,
    ) -> List[RecognizerResult]:
        """Analyze text for PII/PHI using LLM."""
        if not text or not text.strip():
            logger.debug("Empty text provided, returning empty results")
            return []

        if entities is None:
            requested_entities = self.supported_entities
        else:
            requested_entities = [e for e in entities if e in self.supported_entities]

        if not requested_entities:
            logger.debug(
                "No requested entities (%s) match supported entities (%s)",
                entities,
                self.supported_entities,
            )
            return []

        results = self._call_llm(text, requested_entities)

        filtered_results = self._filter_and_process_results(results, requested_entities)

        if filtered_results:
            logger.debug(
                "LLM recognizer found %d entities",
                len(filtered_results),
            )

        return filtered_results

    def _filter_and_process_results(
        self,
        results: List[RecognizerResult],
        requested_entities: Optional[List[str]] = None,
    ) -> List[RecognizerResult]:
        """Filter and process results."""
        filtered_results = filter_results_by_labels(results, self.labels_to_ignore)

        if self.enable_generic_consolidation:
            filtered_results = consolidate_generic_entities(
                filtered_results, self.supported_entities, self._generic_entities_logged
            )
        else:
            filtered_results = skip_unmapped_entities(
                filtered_results, self.supported_entities
            )

        if requested_entities:
            filtered_results = filter_results_by_entities(
                filtered_results, requested_entities
            )

        filtered_results = validate_result_positions(filtered_results)
        filtered_results = filter_results_by_score(filtered_results, self.min_score)

        return filtered_results

    def get_supported_entities(self) -> List[str]:
        """Return list of supported PII entity types."""
        return self.supported_entities
