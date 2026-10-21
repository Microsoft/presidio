"""Handles the entire logic of the Presidio-anonymizer and text anonymizing."""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Type

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
        tmp_analyzer_results = self._merge_same_entity_type_intersections(
            analyzer_results
        )
        unique_text_metadata_elements = self._remove_contained_results(
            tmp_analyzer_results
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

    def _merge_same_entity_type_intersections(
        self, analyzer_results: List[RecognizerResult]
    ) -> List[RecognizerResult]:
        """
        Merge intersecting results of the same entity type into one result.

        One sorted sweep per entity type replaces the pairwise scan, which was
        quadratic in the number of results. A merged result keeps the union of
        the spans and the highest score, and takes the position of the last
        input it absorbed, so the order of the remaining results is unchanged.
        """
        by_entity_type: Dict[str, List[Tuple[int, RecognizerResult]]] = {}
        for position, result in enumerate(analyzer_results):
            by_entity_type.setdefault(result.entity_type, []).append((position, result))

        kept: List[Tuple[int, RecognizerResult]] = []
        for positioned_results in by_entity_type.values():
            positioned_results.sort(key=lambda item: (item[1].start, item[1].end))
            position, current = positioned_results[0]
            for next_position, result in positioned_results[1:]:
                if current.intersects(result) == 0:
                    kept.append((position, current))
                    position, current = next_position, result
                    continue
                self.logger.debug(
                    f"removing element {result} from results list due to merge"
                )
                current.start = min(current.start, result.start)
                current.end = max(current.end, result.end)
                current.score = max(current.score, result.score)
                position = max(position, next_position)
            kept.append((position, current))

        kept.sort(key=lambda item: item[0])
        return [result for _, result in kept]

    def _remove_contained_results(
        self, analyzer_results: List[RecognizerResult]
    ) -> List[RecognizerResult]:
        """
        Drop every result that has a conflict with another result.

        A result contained in another result is dropped. Of results with equal
        indices the highest score survives, the last one on a tie, which is what
        the pairwise comparison with has_conflict produced. Sorted by start and
        then by the longer span first, every result that can contain the current
        one has already been seen, so the largest end seen so far decides.
        """
        order = sorted(
            range(len(analyzer_results)),
            key=lambda index: (
                analyzer_results[index].start,
                -analyzer_results[index].end,
            ),
        )
        dropped: Set[int] = set()
        largest_end_seen: Optional[int] = None
        group_start = 0
        while group_start < len(order):
            first = analyzer_results[order[group_start]]
            group_end = group_start
            while group_end < len(order) and analyzer_results[
                order[group_end]
            ].equal_indices(first):
                group_end += 1
            group = order[group_start:group_end]
            if largest_end_seen is not None and largest_end_seen >= first.end:
                dropped.update(group)
            else:
                survivor = max(
                    group, key=lambda index: (analyzer_results[index].score, index)
                )
                dropped.update(index for index in group if index != survivor)
            if largest_end_seen is None or first.end > largest_end_seen:
                largest_end_seen = first.end
            group_start = group_end

        for index in sorted(dropped):
            self.logger.debug(
                f"removing element {analyzer_results[index]} "
                f"from results list due to conflict"
            )
        return [
            result
            for index, result in enumerate(analyzer_results)
            if index not in dropped
        ]

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
