"""Handles the entire logic of the Presidio-anonymizer and text anonymizing."""
import logging
from typing import List, Dict, Optional

from presidio_anonymizer.entities import (
    RecognizerResult,
    AnonymizerConfig, InvalidParamException,
)
from presidio_anonymizer.entities.engine.operator_metadata import OperatorMetadata
from presidio_anonymizer.entities.engine.result.engine_result import EngineResult
from presidio_anonymizer.operators import OperatorType
from presidio_anonymizer.operators.operators_factory import OperatorsFactory
from presidio_anonymizer.text_engine import TextEngine

DEFAULT = "replace"


class AnonymizerEngine:
    """
    AnonymizerEngine class.

    Handles the entire logic of the Presidio-anonymizer. Gets the original text
    and replaces the PII entities with the desired anonymizers.
    """

    def __init__(self):
        self.logger = logging.getLogger("presidio-anonymizer")
        self.text_engine = TextEngine()

    def anonymize(
            self,
            text: str,
            analyzer_results: List[RecognizerResult],
            anonymizers_config: Optional[Dict[str, AnonymizerConfig]] = None,
    ) -> EngineResult:
        """Anonymize method to anonymize the given text.

        :param text: the text we are anonymizing
        :param analyzer_results: A list of RecognizerResult class -> The results we
        received from the analyzer
        :param anonymizers_config: The configuration of the anonymizers we would like
        to use for each entity e.g.: {"PHONE_NUMBER":AnonymizerConfig("redact", {})}
        received from the analyzer
        :return: the anonymized text and a list of information
        about the anonymized entities.
        """
        analyzer_results = self._remove_conflicts_and_get_text_manipulation_data(
            analyzer_results)

        anonymizers_config = self.__check_or_add_default_anonymizer(anonymizers_config)

        return self.text_engine.operate(text,
                                        analyzer_results,
                                        anonymizers_config)

    def _remove_conflicts_and_get_text_manipulation_data(self, analyzer_results):
        """
        Iterate the list and create a sorted unique results list from it.

        Only insert results which are:
        1. Indices are not contained in other result.
        2. Have the same indices as other results but with larger score.
        :return: List
        """
        unique_text_metadata_elements = []
        # This list contains all elements which we need to check a single result
        # against. If a result is dropped, it can also be dropped from this list
        # since it is intersecting with another result and we selected the other one.
        other_elements = analyzer_results.copy()
        for result in analyzer_results:
            other_elements.remove(result)
            result_conflicted = self.__is_result_conflicted_with_other_elements(
                other_elements, result)
            if not result_conflicted:
                other_elements.append(result)
                unique_text_metadata_elements.append(result)
            else:
                self.logger.debug(
                    f"removing element {result} from results list due to conflict"
                )
        return unique_text_metadata_elements

    @staticmethod
    def get_anonymizers() -> List[str]:
        """Return a list of supported anonymizers."""
        names = [p for p in OperatorsFactory.get_anonymizers().keys()]
        return names

    @staticmethod
    def __is_result_conflicted_with_other_elements(other_elements, result):
        return any([result.has_conflict(other_element) for other_element in
                    other_elements])

    def __check_or_add_default_anonymizer(self,
                                          anonymizers_config: Dict[str, AnonymizerConfig]) -> \
            Dict[str, OperatorMetadata]:
        default_anonymizer = {"DEFAULT": AnonymizerConfig(DEFAULT)}
        if not anonymizers_config:
            return default_anonymizer
        if not anonymizers_config.get("DEFAULT"):
            anonymizers_config["DEFAULT"] = default_anonymizer
        return anonymizers_config
