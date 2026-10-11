"""Handles the entire logic of the Presidio-anonymizer and text anonymizing."""

import logging
import re
from typing import Dict, List, Optional, Type

from presidio_anonymizer.core import EngineBase
from presidio_anonymizer.entities import (
    ConflictResolutionStrategy,
    EngineResult,
    OperatorConfig,
    RecognizerResult,
)
from presidio_anonymizer.operators import Operator, OperatorType

DEFAULT = "replace"

logger = logging.getLogger("presidio-anonymizer")


class AnonymizerEngine(EngineBase):
    """
    AnonymizerEngine class.

    Handles the entire logic of the Presidio-anonymizer. Gets the original text
    and replaces the PII entities with the desired anonymizers.
    """

    def anonymize(
        self,
        text: str,
        analyzer_results: List[RecognizerResult],
        operators: Optional[Dict[str, OperatorConfig]] = None,
        conflict_resolution: ConflictResolutionStrategy = (
            ConflictResolutionStrategy.MERGE_SIMILAR_OR_CONTAINED
        ),
        merge_entities_with_spaces: bool = True,
    ) -> EngineResult:
        """Anonymize method to anonymize the given text.

        :param text: the text we are anonymizing
        :param analyzer_results: A list of RecognizerResult class -> The results we
        received from the analyzer
        :param operators: The configuration of the anonymizers we would like
        to use for each entity e.g.: {"PHONE_NUMBER":OperatorConfig("redact", {})}
        received from the analyzer
        :param conflict_resolution: The configuration designed to handle conflicts
        among entities
        :return: the anonymized text and a list of information about the
        anonymized entities.

        :example:

        >>> from presidio_anonymizer import AnonymizerEngine
        >>> from presidio_anonymizer.entities import RecognizerResult, OperatorConfig

        >>> # Initialize the engine with logger.
        >>> engine = AnonymizerEngine()

        >>> # Invoke the anonymize function with the text, analyzer results and
        >>> # Operators to define the anonymization type.
        >>> result = engine.anonymize(
        >>>     text="My name is Bond, James Bond",
        >>>     analyzer_results=[RecognizerResult(entity_type="PERSON",
        >>>                                        start=11,
        >>>                                        end=15,
        >>>                                        score=0.8),
        >>>                       RecognizerResult(entity_type="PERSON",
        >>>                                        start=17,
        >>>                                        end=27,
        >>>                                        score=0.8)],
        >>>     operators={"PERSON": OperatorConfig("replace", {"new_value": "BIP"})}
        >>> )

        >>> print(result)
        text: My name is BIP, BIP.
        items:
        [
            {'start': 16, 'end': 19, 'entity_type': 'PERSON',
             'text': 'BIP', 'operator': 'replace'},
            {'start': 11, 'end': 14, 'entity_type': 'PERSON',
             'text': 'BIP', 'operator': 'replace'}
        ]


        """
        # We do this to make sure the original analyzer_results object is not
        # modified
        analyzer_results = self._copy_recognizer_results(analyzer_results)

        # Sort because downstream processors like whitespace merging expect input to
        # be sorted by start, end to work correctly
        analyzer_results.sort(key=lambda x: (x.start, x.end))

        analyzer_results = self._remove_conflicts_and_get_text_manipulation_data(
            analyzer_results, conflict_resolution
        )

        if merge_entities_with_spaces:
            merged_results = self._merge_entities_with_spaces_between(
                text, analyzer_results
            )
        else:
            merged_results = analyzer_results

        operators = self.__check_or_add_default_operator(operators)

        return self._operate(
            text=text,
            pii_entities=merged_results,
            operators_metadata=operators,
            operator_type=OperatorType.Anonymize,
        )

    def add_anonymizer(self, anonymizer_cls: Type[Operator]) -> None:
        """
        Add a new anonymizer to the engine.

        anonymizer_cls: The anonymizer class to add to the engine.
        """
        logger.info(f"Added anonymizer {anonymizer_cls.__name__}")
        self.operators_factory.add_anonymize_operator(anonymizer_cls)

    def remove_anonymizer(self, anonymizer_cls: Type[Operator]) -> None:
        """
        Remove an anonymizer from the engine.

        anonymizer_cls: The anonymizer class to remove from the engine.
        """
        logger.info(f"Removed anonymizer {anonymizer_cls.__name__}")
        self.operators_factory.remove_anonymize_operator(anonymizer_cls)

    def _remove_conflicts_and_get_text_manipulation_data(
        self,
        analyzer_results: List[RecognizerResult],
        conflict_resolution: ConflictResolutionStrategy,
    ) -> List[RecognizerResult]:
        """
        Iterate the list and create a sorted unique results list from it.

        Only insert results which are:
        1. Indices are not contained in other result.
        2. Have the same indices as other results but with larger score.
        :return: List
        """
        tmp_analyzer_results = []
        # This list contains all elements which we need to check a single result
        # against. If a result is dropped, it can also be dropped from this list
        # since it is intersecting with another result and we selected the other one.
        other_elements = analyzer_results.copy()
        for result in analyzer_results:
            other_elements.remove(result)

            is_merge_same_entity_type = False
            for other_element in other_elements:
                if other_element.entity_type != result.entity_type:
                    continue
                if result.intersects(other_element) == 0:
                    continue

                other_element.start = min(result.start, other_element.start)
                other_element.end = max(result.end, other_element.end)
                other_element.score = max(result.score, other_element.score)
                is_merge_same_entity_type = True
                break
            if not is_merge_same_entity_type:
                other_elements.append(result)
                tmp_analyzer_results.append(result)
            else:
                self.logger.debug(
                    f"removing element {result} from " f"results list due to merge"
                )

        unique_text_metadata_elements = []
        # This list contains all elements which we need to check a single result
        # against. If a result is dropped, it can also be dropped from this list
        # since it is intersecting with another result and we selected the other one.
        other_elements = tmp_analyzer_results.copy()
        for result in tmp_analyzer_results:
            other_elements.remove(result)
            result_conflicted = self.__is_result_conflicted_with_other_elements(
                other_elements, result
            )
            if not result_conflicted:
                other_elements.append(result)
                unique_text_metadata_elements.append(result)
            else:
                self.logger.debug(
                    f"removing element {result} from results list due to conflict"
                )

        # This further improves the quality of handling the conflict between the
        # various entities overlapping. This will not drop the results insted
        # it adjust the start and end positions of overlapping results and removes
        # All types of conflicts among entities as well as text.
        if conflict_resolution == ConflictResolutionStrategy.REMOVE_INTERSECTIONS:
            # Sort by end as well, so after a trim the shorter of two results that
            # now share a start is resolved against the longer one, not skipped.
            unique_text_metadata_elements.sort(
                key=lambda element: (element.start, element.end)
            )
            elements_length = len(unique_text_metadata_elements)
            index = 0
            while index < elements_length - 1:
                current_entity = unique_text_metadata_elements[index]
                next_entity = unique_text_metadata_elements[index + 1]
                if current_entity.end <= next_entity.start:
                    index += 1
                else:
                    if current_entity.score >= next_entity.score:
                        next_entity.start = current_entity.end
                    else:
                        current_entity.end = next_entity.start
                    unique_text_metadata_elements.sort(
                        key=lambda element: (element.start, element.end)
                    )
            unique_text_metadata_elements = [
                element
                for element in unique_text_metadata_elements
                if element.start < element.end
            ]
        return unique_text_metadata_elements

    def _merge_entities_with_spaces_between(
        self, text: str, analyzer_results: List[RecognizerResult]
    ) -> List[RecognizerResult]:
        """Merge adjacent entities of the same type separated by whitespace."""
        merged_results = []
        prev_result = None
        for result in analyzer_results:
            if prev_result is not None:
                if prev_result.entity_type == result.entity_type:
                    if re.search(r"^( )+$", text[prev_result.end:result.start]):
                        merged_results.remove(prev_result)
                        result.start = prev_result.start
            merged_results.append(result)
            prev_result = result
        return merged_results

    def get_anonymizers(self) -> List[str]:
        """Return a list of supported anonymizers."""
        names = [p for p in self.operators_factory.get_anonymizers().keys()]
        return names

    @staticmethod
    def __is_result_conflicted_with_other_elements(other_elements, result):
        return any(
            [result.has_conflict(other_element) for other_element in other_elements]
        )

    @staticmethod
    def __check_or_add_default_operator(
        operators: Dict[str, OperatorConfig],
    ) -> Dict[str, OperatorConfig]:
        default_operator = OperatorConfig(DEFAULT)
        if not operators:
            return {"DEFAULT": default_operator}
        if not operators.get("DEFAULT"):
            operators["DEFAULT"] = default_operator
        return operators

    @staticmethod
    def _copy_recognizer_results(
        analyzer_results: List[RecognizerResult],
    ) -> List[RecognizerResult]:
        return [
            RecognizerResult(
                start=result.start,
                end=result.end,
                entity_type=result.entity_type,
                score=result.score,
            )
            for result in analyzer_results
        ]
