import logging
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterable
from typing import Dict, Iterator, List, Optional, Union

from pandas import DataFrame
from presidio_analyzer import (
    AnalyzerEngine,
    BatchAnalyzerEngine,
    DictAnalyzerResult,
    RecognizerResult,
)

from presidio_structured.config import StructuredAnalysis

NON_PII_ENTITY_TYPE = "NON_PII"

logger = logging.getLogger("presidio-structured")


class AnalysisBuilder(ABC):
    """Abstract base class for a configuration generator."""

    def __init__(
        self,
        analyzer: Optional[AnalyzerEngine] = None,
        analyzer_score_threshold: Optional[float] = None,
        n_process: int = 1,
        batch_size: int = 1,
    ) -> None:
        """Initialize the configuration generator.

        :param analyzer: AnalyzerEngine instance
        :param analyzer_score_threshold: threshold for filtering out results
        :param batch_size: Batch size to process in a single iteration
        :param n_process: Number of processors to use. Defaults to `1`
        """
        default_score_threshold = (
            analyzer_score_threshold if analyzer_score_threshold is not None else 0
        )
        self.analyzer = (
            AnalyzerEngine(default_score_threshold=default_score_threshold)
            if analyzer is None
            else analyzer
        )
        self.batch_analyzer = BatchAnalyzerEngine(analyzer_engine=self.analyzer)
        self.n_process = n_process
        self.batch_size = batch_size

    @abstractmethod
    def generate_analysis(
        self,
        data: Union[Dict, DataFrame],
        language: str = "en",
        score_threshold: Optional[float] = None,
    ) -> StructuredAnalysis:
        """
        Abstract method to generate a configuration from the given data.

        :param data: The input data. Can be a dictionary or DataFrame instance.
        :return: The generated configuration.
        """
        pass

    def _remove_low_scores(
        self,
        key_recognizer_result_map: Dict[str, RecognizerResult],
        score_threshold: Optional[float] = None,
    ) -> Dict[str, RecognizerResult]:
        """
        Remove results for which the confidence is lower than the threshold.

        :param results: Dict of column names to RecognizerResult
        :param score_threshold: float value for minimum possible confidence
        :return: List[RecognizerResult]
        """
        if score_threshold is None:
            score_threshold = self.analyzer.default_score_threshold

        new_key_recognizer_result_map = {}
        for column, result in key_recognizer_result_map.items():
            if result.score >= score_threshold:
                new_key_recognizer_result_map[column] = result

        return new_key_recognizer_result_map


class JsonAnalysisBuilder(AnalysisBuilder):
    """Concrete configuration generator for JSON data."""

    def generate_analysis(
        self,
        data: Dict,
        language: str = "en",
    ) -> StructuredAnalysis:
        """
        Generate a configuration from the given JSON data.

        :param data: The input JSON data.
        :return: The generated configuration.
        """
        logger.debug("Starting JSON BatchAnalyzer analysis")
        analyzer_results = self.batch_analyzer.analyze_dict(
            input_dict=data,
            language=language,
            n_process=self.n_process,
            batch_size=self.batch_size,
        )

        key_recognizer_result_map = self._generate_analysis_from_results_json(
            analyzer_results
        )

        key_entity_map = {
            key: result.entity_type for key, result in key_recognizer_result_map.items()
        }

        return StructuredAnalysis(entity_mapping=key_entity_map)

    def _generate_analysis_from_results_json(
        self, analyzer_results: Iterator[DictAnalyzerResult], prefix: str = ""
    ) -> Dict[str, RecognizerResult]:
        """
        Generate a configuration from the given analyzer results. Always uses the first recognizer result if there are more than one.

        :param analyzer_results: The analyzer results.
        :param prefix: The prefix for the configuration keys.
        :return: The generated configuration.
        """  # noqa: E501
        key_recognizer_result_map = {}

        if not isinstance(analyzer_results, Iterable):
            logger.debug(
                "No analyzer results found, returning empty StructuredAnalysis"
            )
            return key_recognizer_result_map

        for result in analyzer_results:
            current_key = prefix + result.key

            if isinstance(result.value, dict) and isinstance(
                result.recognizer_results, Iterator
            ):
                nested_mappings = self._generate_analysis_from_results_json(
                    result.recognizer_results, prefix=current_key + "."
                )
                key_recognizer_result_map.update(nested_mappings)
            first_recognizer_result = next(iter(result.recognizer_results), None)
            if isinstance(first_recognizer_result, RecognizerResult):
                logger.debug(
                    f"Found result with entity {first_recognizer_result.entity_type} \
                        in {current_key}"
                )
                key_recognizer_result_map[current_key] = first_recognizer_result
        return key_recognizer_result_map


class TabularAnalysisBuilder(AnalysisBuilder):
    """Placeholder class for generalizing tabular data analysis builders (e.g. PySpark). Only implemented as PandasAnalysisBuilder for now."""  # noqa: E501

    pass


class PandasAnalysisBuilder(TabularAnalysisBuilder):
    """Concrete configuration generator for tabular data."""

    entity_selection_strategies = {"highest_confidence", "mixed", "most_common"}

    def generate_analysis(
        self,
        df: DataFrame,
        n: Optional[int] = None,
        language: str = "en",
        selection_strategy: str = "most_common",
        mixed_strategy_threshold: float = 0.5,
    ) -> StructuredAnalysis:
        """
        Generate a configuration from the given tabular data.

        :param df: The input tabular data (dataframe).
        :param n: The number of samples to be taken from the dataframe.
        :param language: The language to be used for analysis.
        :param selection_strategy: A string that specifies the entity selection strategy
        ('highest_confidence', 'mixed', or default to most common).
        :param mixed_strategy_threshold: A float value for the threshold to be used in
        the entity selection mixed strategy.
        :return: A StructuredAnalysis object containing the analysis results.
        """
        if not n:
            n = len(df)
        elif n > len(df):
            logger.debug(
                f"Number of samples ({n}) is larger than the number of rows \
                    ({len(df)}), using all rows"
            )
            n = len(df)

        df = df.sample(n, random_state=123)

        key_recognizer_result_map = self._generate_key_rec_results_map(
            df, language, selection_strategy, mixed_strategy_threshold
        )

        key_entity_map = {
            key: result.entity_type
            for key, result in key_recognizer_result_map.items()
            if result.entity_type != NON_PII_ENTITY_TYPE
        }

        return StructuredAnalysis(entity_mapping=key_entity_map)

    def _generate_key_rec_results_map(
        self,
        df: DataFrame,
        language: str,
        selection_strategy: str = "most_common",
        mixed_strategy_threshold: float = 0.5,
    ) -> Dict[str, RecognizerResult]:
        """
        Find the most common entity in a dataframe column.

        If more than one entity is found in a cell, the first one is used.

        :param df: The dataframe where entities will be searched.
        :param language: Language to be used in the analysis engine.
        :param selection_strategy: A string that specifies the entity selection strategy
        ('highest_confidence', 'mixed', or default to most common).
        :param mixed_strategy_threshold: A float value for the threshold to be used in
        the entity selection mixed strategy.
        :return: A dictionary mapping column names to the most common RecognizerResult.
        """
        column_analyzer_results_map = self._batch_analyze_df(df, language)
        key_recognizer_result_map = {}
        for column, analyzer_result in column_analyzer_results_map.items():
            key_recognizer_result_map[column] = self._find_entity_based_on_strategy(
                analyzer_result, selection_strategy, mixed_strategy_threshold
            )
        return key_recognizer_result_map

    def _batch_analyze_df(
        self, df: DataFrame, language: str
    ) -> Dict[str, List[List[RecognizerResult]]]:
        """
        Analyze each column in the dataframe for entities using the batch analyzer.

        :param df: The dataframe to be analyzed.
        :param language: The language configuration for the analyzer.
        :return: A dictionary mapping each column name to a \
            list of lists of RecognizerResults.
        """
        column_analyzer_results_map = {}
        for column in df.columns:
            logger.debug(f"Finding most common PII entity for column {column}")
            analyzer_results = self.batch_analyzer.analyze_iterator(
                [val for val in df[column]],
                language=language,
                n_process=self.n_process,
                batch_size=self.batch_size,
            )
            column_analyzer_results_map[column] = analyzer_results

        return column_analyzer_results_map

    def _find_entity_based_on_strategy(
        self,
        analyzer_results: List[List[RecognizerResult]],
        selection_strategy: str,
        mixed_strategy_threshold: float,
    ) -> RecognizerResult:
        """
        Determine the most suitable entity based on the specified selection strategy.

        :param analyzer_results: A nested list of RecognizerResult objects from the
        analysis results.
        :param selection_strategy: A string that specifies the entity selection strategy
        ('highest_confidence', 'mixed', or default to most common).
        :return: A RecognizerResult object representing the selected entity based on the
        given strategy.
        """
        if selection_strategy not in self.entity_selection_strategies:
            raise ValueError(
                f"Unsupported entity selection strategy: {selection_strategy}."
            )

        if not any(analyzer_results):
            return RecognizerResult(
                entity_type=NON_PII_ENTITY_TYPE, start=0, end=1, score=1.0
            )

        flat_results = self._flatten_results(analyzer_results)

        # Select the entity based on the desired strategy
        if selection_strategy == "highest_confidence":
            return self._select_highest_confidence_entity(flat_results)
        elif selection_strategy == "mixed":
            return self._select_mixed_strategy_entity(
                flat_results, mixed_strategy_threshold
            )

        return self._select_most_common_entity(flat_results)

    def _select_most_common_entity(self, flat_results):
        """
        Select the most common entity from the flattened analysis results.

        :param flat_results: A list of tuples containing index and RecognizerResult
        objects from the flattened analysis results.
        :return: A RecognizerResult object for the most commonly found entity type.
        """
        # Count occurrences of each entity type
        type_counter = Counter(res.entity_type for _, res in flat_results)
        most_common_type, most_common_count = type_counter.most_common(1)[0]

        # Calculate the score as the proportion of occurrences
        score = most_common_count / len(flat_results)

        return RecognizerResult(
            entity_type=most_common_type, start=0, end=1, score=score
        )

    def _select_highest_confidence_entity(self, flat_results):
        """
        Select the entity with the highest confidence score.

        :param flat_results: A list of tuples containing index and RecognizerResult
        objects from the flattened analysis results.
        :return: A RecognizerResult object for the entity with the highest confidence
        score.
        """
        score_aggregator = self._aggregate_scores(flat_results)

        # Find the highest score across all entities
        highest_score = max(
            max(scores) for scores in score_aggregator.values() if scores
        )

        # Find the entities with the highest score and count their occurrences
        entities_highest_score = {
            entity: scores.count(highest_score)
            for entity, scores in score_aggregator.items()
            if highest_score in scores
        }

        # Find the entity(ies) with the most number of high scores
        max_occurrences = max(entities_highest_score.values())
        highest_confidence_entities = [
            entity
            for entity, count in entities_highest_score.items()
            if count == max_occurrences
        ]

        return RecognizerResult(
            entity_type=highest_confidence_entities[0],
            start=0,
            end=1,
            score=highest_score,
        )

    def _select_mixed_strategy_entity(self, flat_results, mixed_strategy_threshold):
        """
        Select an entity using a mixed strategy.

        Chooses an entity based on the highest confidence score if it is above the
        threshold. Otherwise, it defaults to the most common entity.

        :param flat_results: A list of tuples containing index and RecognizerResult
        objects from the flattened analysis results.
        :return: A RecognizerResult object selected based on the mixed strategy.
        """
        # Check if mixed strategy threshold is within the valid range
        if not 0 <= mixed_strategy_threshold <= 1:
            raise ValueError(
                f"Invalid mixed strategy threshold: {mixed_strategy_threshold}."
            )

        score_aggregator = self._aggregate_scores(flat_results)

        # Check if the highest score is greater than threshold and select accordingly
        highest_score = max(
            max(scores) for scores in score_aggregator.values() if scores
        )
        if highest_score > mixed_strategy_threshold:
            return self._select_highest_confidence_entity(flat_results)
        else:
            return self._select_most_common_entity(flat_results)

    @staticmethod
    def _aggregate_scores(flat_results):
        """
        Aggregate the scores for each entity type from the flattened analysis results.

        :param flat_results: A list of tuples containing index and RecognizerResult
        objects from the flattened analysis results.
        :return: A dictionary with entity types as keys and lists of scores as values.
        """
        score_aggregator = {}
        for _, res in flat_results:
            if res.entity_type not in score_aggregator:
                score_aggregator[res.entity_type] = []
            score_aggregator[res.entity_type].append(res.score)
        return score_aggregator

    @staticmethod
    def _flatten_results(analyzer_results):
        """
        Flattens a nested lists of RecognizerResult objects into a list of tuples.

        :param analyzer_results: A nested list of RecognizerResult objects from
        the analysis results.
        :return: A flattened list of tuples containing index and RecognizerResult
        objects.
        """
        return [
            (cell_idx, res)
            for cell_idx, cell_results in enumerate(analyzer_results)
            for res in cell_results
        ]
